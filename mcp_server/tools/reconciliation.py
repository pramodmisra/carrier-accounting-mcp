"""
Gaps #4 and #5:
  #4 — Reconciliation report: compare posted transactions against Epic entries
  #5 — Trial-mode side-by-side diff: what WOULD have posted vs what's in Epic
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import structlog

from mcp_server.config import Config
from mcp_server.services.bigquery_client import BigQueryClient
from mcp_server.services.epic_sdk_client import EpicSDKClient

log = structlog.get_logger(__name__)

bq = BigQueryClient()
epic = EpicSDKClient()


# ------------------------------------------------------------------ #
# GAP #4: RECONCILIATION REPORT                                       #
# ------------------------------------------------------------------ #

def reconciliation_report(
    run_id: Optional[str] = None,
    carrier: Optional[str] = None,
    target_date: Optional[date] = None,
) -> dict:
    """
    Compare posted transactions in our data lake against Applied Epic.
    For each posted transaction, reads the Epic entry and checks for
    discrepancies in amount, policy, status.

    Args:
        run_id: Specific run to reconcile (optional)
        carrier: Filter by carrier (optional)
        target_date: Filter by date (optional, defaults to today)

    Returns:
        Dict with matched, mismatched, missing_in_epic, summary stats
    """
    from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter

    if target_date is None:
        target_date = date.today()

    # Build filter clauses
    filters = ["status = 'posted'", "epic_entry_id IS NOT NULL"]
    params = []

    if run_id:
        filters.append("run_id = @run_id")
        params.append(ScalarQueryParameter("run_id", "STRING", run_id))
    if carrier:
        filters.append("carrier = @carrier")
        params.append(ScalarQueryParameter("carrier", "STRING", carrier))
    if target_date and not run_id:
        filters.append("DATE(created_at) = @target_date")
        params.append(ScalarQueryParameter("target_date", "DATE", target_date.isoformat()))

    where_clause = " AND ".join(filters)

    query = f"""
        SELECT
            transaction_id,
            run_id,
            carrier,
            policy_number,
            epic_policy_id,
            epic_client_id,
            client_name,
            amount,
            transaction_type,
            epic_entry_id,
            epic_posted_at,
            confidence_score
        FROM `{Config.live_table()}`
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT 500
    """
    job_config = QueryJobConfig(query_parameters=params)
    rows = list(bq.client.query(query, job_config=job_config).result())

    if not rows:
        return {
            "status": "no_data",
            "message": "No posted transactions found for the given filters",
            "filters": {"run_id": run_id, "carrier": carrier, "date": str(target_date)},
        }

    matched = []
    mismatched = []
    missing_in_epic = []
    epic_errors = []

    for row in rows:
        row_dict = dict(row)
        epic_entry_id = row_dict["epic_entry_id"]

        # Try to read the entry from Epic
        try:
            epic_data = epic.client.get(
                f"/accounting/entries/{epic_entry_id}"
            )
            if epic_data.status_code == 404:
                missing_in_epic.append({
                    "transaction_id": row_dict["transaction_id"],
                    "epic_entry_id": epic_entry_id,
                    "policy_number": row_dict["policy_number"],
                    "amount": str(row_dict["amount"]),
                    "issue": "Entry not found in Epic — may have been voided or deleted",
                })
                continue

            epic_data.raise_for_status()
            epic_entry = epic_data.json()

            # Compare key fields
            discrepancies = []
            epic_amount = Decimal(str(epic_entry.get("amount", 0)))
            our_amount = Decimal(str(row_dict["amount"]))

            if abs(epic_amount - our_amount) > Decimal("0.01"):
                discrepancies.append({
                    "field": "amount",
                    "ours": str(our_amount),
                    "epic": str(epic_amount),
                })

            epic_policy = epic_entry.get("policyId", "")
            if epic_policy and epic_policy != row_dict.get("epic_policy_id"):
                discrepancies.append({
                    "field": "epic_policy_id",
                    "ours": row_dict.get("epic_policy_id"),
                    "epic": epic_policy,
                })

            epic_status = epic_entry.get("status", "")
            if epic_status in ("voided", "reversed", "deleted"):
                discrepancies.append({
                    "field": "status",
                    "ours": "posted",
                    "epic": epic_status,
                })

            record = {
                "transaction_id": row_dict["transaction_id"],
                "epic_entry_id": epic_entry_id,
                "policy_number": row_dict["policy_number"],
                "amount": str(our_amount),
                "carrier": row_dict["carrier"],
            }

            if discrepancies:
                record["discrepancies"] = discrepancies
                mismatched.append(record)
            else:
                matched.append(record)

        except Exception as e:
            epic_errors.append({
                "transaction_id": row_dict["transaction_id"],
                "epic_entry_id": epic_entry_id,
                "error": str(e),
            })

    total = len(rows)
    match_rate = (len(matched) / total * 100) if total > 0 else 0

    log.info("Reconciliation complete",
             total=total, matched=len(matched),
             mismatched=len(mismatched), missing=len(missing_in_epic))

    return {
        "status": "complete",
        "filters": {"run_id": run_id, "carrier": carrier, "date": str(target_date)},
        "summary": {
            "total_checked": total,
            "matched": len(matched),
            "mismatched": len(mismatched),
            "missing_in_epic": len(missing_in_epic),
            "epic_api_errors": len(epic_errors),
            "match_rate_pct": round(match_rate, 1),
        },
        "mismatched": mismatched,
        "missing_in_epic": missing_in_epic,
        "epic_errors": epic_errors,
        "matched_sample": matched[:10],
    }


# ------------------------------------------------------------------ #
# GAP #5: TRIAL-MODE SIDE-BY-SIDE DIFF REPORT                        #
# ------------------------------------------------------------------ #

def trial_diff_report(
    run_id: Optional[str] = None,
    carrier: Optional[str] = None,
    target_date: Optional[date] = None,
) -> dict:
    """
    Side-by-side comparison: what the system WOULD have posted to Epic
    (from shadow table) vs what currently exists in Epic for those policies.

    This is the key report for the accounting team during trial/shadow mode.
    Shows every parsed transaction alongside the existing Epic data for
    that policy, highlighting deltas.

    Args:
        run_id: Specific trial run to diff (optional)
        carrier: Filter by carrier (optional)
        target_date: Filter by date (optional, defaults to today)

    Returns:
        Dict with side-by-side comparisons, delta summary, and recommendations
    """
    from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter

    if target_date is None:
        target_date = date.today()

    # Fetch shadow (trial) transactions
    filters = ["mode = 'trial'"]
    params = []

    if run_id:
        filters.append("run_id = @run_id")
        params.append(ScalarQueryParameter("run_id", "STRING", run_id))
    if carrier:
        filters.append("carrier = @carrier")
        params.append(ScalarQueryParameter("carrier", "STRING", carrier))
    if target_date and not run_id:
        filters.append("DATE(created_at) = @target_date")
        params.append(ScalarQueryParameter("target_date", "DATE", target_date.isoformat()))

    where_clause = " AND ".join(filters)

    query = f"""
        SELECT
            transaction_id,
            run_id,
            carrier,
            policy_number,
            epic_policy_id,
            epic_client_id,
            client_name,
            amount,
            transaction_type,
            effective_date,
            confidence_score,
            status,
            auto_approved,
            validation_warnings,
            validation_errors
        FROM `{Config.shadow_table()}`
        WHERE {where_clause}
        ORDER BY confidence_score DESC, created_at DESC
        LIMIT 500
    """
    job_config = QueryJobConfig(query_parameters=params)
    shadow_rows = list(bq.client.query(query, job_config=job_config).result())

    if not shadow_rows:
        return {
            "status": "no_data",
            "message": "No trial-mode transactions found for the given filters",
            "filters": {"run_id": run_id, "carrier": carrier, "date": str(target_date)},
        }

    comparisons = []
    total_our_amount = Decimal("0")
    total_epic_amount = Decimal("0")
    policy_match_count = 0
    amount_match_count = 0
    would_auto_post = 0
    would_review = 0
    would_reject = 0

    for row in shadow_rows:
        row_dict = dict(row)
        our_amount = Decimal(str(row_dict["amount"]))
        total_our_amount += our_amount

        epic_policy_id = row_dict.get("epic_policy_id")
        comparison = {
            "transaction_id": row_dict["transaction_id"],
            "carrier": row_dict["carrier"],
            "policy_number": row_dict["policy_number"],
            "client_name": row_dict["client_name"],
            "confidence_score": row_dict["confidence_score"],
            "status": row_dict["status"],
            "our_data": {
                "amount": str(our_amount),
                "transaction_type": row_dict["transaction_type"],
                "effective_date": str(row_dict.get("effective_date", "")),
            },
            "epic_data": None,
            "deltas": [],
        }

        # Classify
        status = row_dict["status"]
        if status in ("approved",) and row_dict.get("auto_approved"):
            would_auto_post += 1
        elif status == "review":
            would_review += 1
        else:
            would_reject += 1

        # Look up the policy in Epic if we have a match
        if epic_policy_id:
            policy_match_count += 1
            epic_policy = epic.get_policy(epic_policy_id)

            if epic_policy:
                epic_premium = Decimal(str(
                    epic_policy.get("totalPremium") or
                    epic_policy.get("billedPremium") or 0
                ))
                total_epic_amount += epic_premium

                comparison["epic_data"] = {
                    "epic_policy_id": epic_policy_id,
                    "client_name": epic_policy.get("clientName", ""),
                    "premium": str(epic_premium),
                    "policy_status": epic_policy.get("status", ""),
                    "line_of_business": epic_policy.get("lineOfBusiness", ""),
                }

                # Compute deltas
                if abs(our_amount - epic_premium) > Decimal("0.01"):
                    delta_pct = (
                        float((our_amount - epic_premium) / epic_premium * 100)
                        if epic_premium != 0 else 0
                    )
                    comparison["deltas"].append({
                        "field": "amount",
                        "ours": str(our_amount),
                        "epic": str(epic_premium),
                        "delta": str(our_amount - epic_premium),
                        "delta_pct": round(delta_pct, 1),
                    })
                else:
                    amount_match_count += 1

                epic_client = epic_policy.get("clientName", "")
                if epic_client and row_dict["client_name"]:
                    from mcp_server.services.confidence_scorer import ConfidenceScorer
                    name_sim = ConfidenceScorer._name_similarity(
                        row_dict["client_name"], epic_client
                    )
                    if name_sim < 0.8:
                        comparison["deltas"].append({
                            "field": "client_name",
                            "ours": row_dict["client_name"],
                            "epic": epic_client,
                            "similarity": round(name_sim, 2),
                        })
            else:
                comparison["epic_data"] = {
                    "epic_policy_id": epic_policy_id,
                    "error": "Could not read policy from Epic API",
                }
        else:
            comparison["epic_data"] = {"error": "No Epic policy match found"}

        # Add warnings/errors
        warnings = row_dict.get("validation_warnings")
        errors = row_dict.get("validation_errors")
        if warnings:
            comparison["warnings"] = warnings if isinstance(warnings, list) else [warnings]
        if errors:
            comparison["errors"] = errors if isinstance(errors, list) else [errors]

        comparisons.append(comparison)

    total = len(shadow_rows)
    policy_match_rate = (policy_match_count / total * 100) if total > 0 else 0
    amount_match_rate = (amount_match_count / policy_match_count * 100) if policy_match_count > 0 else 0
    auto_post_rate = (would_auto_post / total * 100) if total > 0 else 0

    # Build recommendation
    if auto_post_rate >= 95:
        recommendation = "Excellent accuracy. This carrier is ready for live mode."
    elif auto_post_rate >= 85:
        recommendation = "Good accuracy. Review the exceptions, then consider promoting to live."
    elif auto_post_rate >= 70:
        recommendation = "Moderate accuracy. Continue trial runs and investigate recurring issues."
    else:
        recommendation = "Low accuracy. Check carrier schema mappings and normalization prompts."

    log.info("Trial diff report generated",
             total=total, policy_match_rate=policy_match_rate,
             auto_post_rate=auto_post_rate)

    return {
        "status": "complete",
        "filters": {"run_id": run_id, "carrier": carrier, "date": str(target_date)},
        "summary": {
            "total_transactions": total,
            "would_auto_post": would_auto_post,
            "would_send_to_review": would_review,
            "would_reject": would_reject,
            "auto_post_rate_pct": round(auto_post_rate, 1),
            "policy_match_rate_pct": round(policy_match_rate, 1),
            "amount_match_rate_pct": round(amount_match_rate, 1),
            "total_our_amount": str(total_our_amount),
            "total_epic_amount": str(total_epic_amount),
            "net_delta": str(total_our_amount - total_epic_amount),
        },
        "recommendation": recommendation,
        "comparisons": comparisons,
    }
