"""
Realistic demo data for the sandbox environment.
Based on actual carrier statement patterns from Snellings Walters data.
No real PII — all names, policy numbers, and amounts are synthetic.
"""

from datetime import date, timedelta
from decimal import Decimal
import random

# Synthetic insured names
DEMO_INSUREDS = [
    "Apex Manufacturing LLC", "Brightside Properties Inc", "Cascade Plumbing Co",
    "Delta Freight Services", "Eagle Eye Security", "Foxworth Dental Group",
    "Granite Construction LLC", "Harbor View Restaurant", "Ironside Auto Repair",
    "Jetstream Aviation Inc", "Keystone Consulting", "Lakewood Apartments LLC",
    "Metro Landscape Services", "Northwind Technologies", "Oakridge Senior Living",
    "Pacific Coast Imports", "Quantum Lab Solutions", "Riverside Veterinary Clinic",
    "Summit Roofing Co", "Tidewater Marine Services", "Unity Health Partners",
    "Valley Creek Farm Supply", "Westbrook Engineering", "Zenith Solar Energy",
]

DEMO_CARRIERS = {
    "hartford": {"display": "The Hartford", "rates": [0.09, 0.10, 0.12, 0.15]},
    "hanover": {"display": "Hanover Insurance", "rates": [0.05, 0.10, 0.12, 0.15, 0.18]},
    "donegal": {"display": "Donegal Insurance", "rates": [0.08, 0.11, 0.12, 0.15]},
    "central": {"display": "Central Insurance", "rates": [0.09, 0.10, 0.125, 0.15, 0.175, 0.20]},
    "liberty": {"display": "Liberty Mutual", "rates": [0.10, 0.12, 0.15, 0.18]},
    "berkley": {"display": "Berkley Net Underwriters", "rates": [0.09, 0.10]},
    "progressive": {"display": "Progressive", "rates": [0.10, 0.12]},
    "westfield": {"display": "Westfield Insurance", "rates": [0.10, 0.12, 0.15]},
    "principal": {"display": "Principal Financial", "rates": [0.06, 0.10, 0.13, 0.15, 0.20]},
    "cigna": {"display": "Cigna", "rates": [0.05, 0.08, 0.10]},
}

LOB_OPTIONS = [
    "Commercial Auto", "General Liability", "Workers Compensation",
    "Commercial Property", "Professional Liability", "Homeowners",
    "Personal Auto", "Umbrella", "Business Owners Policy", "Flood",
]

TXN_TYPES = ["premium", "commission", "return_premium", "endorsement", "cancellation"]


def _rand_policy(carrier: str) -> str:
    prefixes = {
        "hartford": "HTF", "hanover": "HAN", "donegal": "DON", "central": "CEN",
        "liberty": "LBM", "berkley": "BNT", "progressive": "PRG", "westfield": "WST",
        "principal": "PFG", "cigna": "CGN",
    }
    prefix = prefixes.get(carrier, "POL")
    return f"{prefix}-{random.randint(100000, 999999)}"


def generate_demo_transactions(
    carrier: str = "hartford",
    count: int = 15,
    base_date: date | None = None,
) -> list[dict]:
    """Generate realistic demo transactions for a carrier."""
    if base_date is None:
        base_date = date.today()

    carrier_info = DEMO_CARRIERS.get(carrier, DEMO_CARRIERS["hartford"])
    txns = []

    for i in range(count):
        insured = random.choice(DEMO_INSUREDS)
        rate = random.choice(carrier_info["rates"])
        premium = round(random.uniform(200, 25000), 2)
        commission = round(premium * rate, 2)
        eff_date = base_date - timedelta(days=random.randint(0, 60))
        lob = random.choice(LOB_OPTIONS)
        txn_type = random.choices(TXN_TYPES, weights=[50, 30, 5, 10, 5])[0]

        if txn_type in ("return_premium", "cancellation"):
            premium = -premium
            commission = -commission

        txns.append({
            "transaction_id": f"demo-{carrier}-{i:04d}",
            "run_id": f"demo-run-{carrier}",
            "carrier": carrier,
            "policy_number": _rand_policy(carrier),
            "client_name": insured,
            "epic_policy_id": f"EP-{random.randint(10000, 99999)}",
            "epic_client_id": f"CL-{random.randint(10000, 99999)}",
            "amount": str(Decimal(str(commission))),
            "premium": str(Decimal(str(premium))),
            "commission_rate": str(rate),
            "transaction_type": txn_type,
            "effective_date": eff_date.isoformat(),
            "line_of_business": lob,
            "confidence_score": round(random.uniform(0.75, 1.0), 4),
            "status": "approved" if random.random() > 0.15 else "review",
            "mode": "trial",
            "validation_warnings": [],
            "validation_errors": [],
            "auto_approved": random.random() > 0.2,
            "created_at": base_date.isoformat(),
        })

    return txns


def generate_demo_daily_metrics(target_date: date | None = None) -> dict:
    """Generate realistic daily metrics for the sandbox dashboard."""
    total = random.randint(80, 250)
    auto_rate = random.uniform(0.88, 0.97)
    auto = int(total * auto_rate)
    review = int(total * random.uniform(0.02, 0.08))
    rejected = total - auto - review
    posted = int(auto * random.uniform(0.85, 1.0))
    failed = auto - posted

    return {
        "total_transactions": total,
        "auto_approved": auto,
        "review_queue": review,
        "failed": failed,
        "posted_to_epic": posted,
        "rejected": rejected,
        "avg_confidence": round(random.uniform(0.91, 0.97), 4),
        "total_amount": round(random.uniform(50000, 500000), 2),
    }


def generate_demo_run_history(days: int = 7) -> list[dict]:
    """Generate demo run history."""
    runs = []
    for i in range(days * 2):
        carrier = random.choice(list(DEMO_CARRIERS.keys()))
        total = random.randint(5, 80)
        auto = int(total * random.uniform(0.85, 0.98))
        review = total - auto
        runs.append({
            "run_id": f"demo-run-{i:04d}",
            "source_file": f"{DEMO_CARRIERS[carrier]['display']} Statement {random.randint(1,30)}.pdf",
            "carrier": carrier,
            "mode": "trial",
            "total_transactions": total,
            "auto_approved": auto,
            "review_queue": review,
            "failed": 0,
            "posted_to_epic": 0,
            "total_amount": str(round(random.uniform(5000, 100000), 2)),
            "started_at": (date.today() - timedelta(days=i // 2)).isoformat(),
            "status": "completed",
        })
    return runs


def generate_demo_carrier_accuracy(carrier: str, days: int = 30) -> dict:
    return {
        "carrier": carrier,
        "total": random.randint(100, 500),
        "avg_confidence": round(random.uniform(0.90, 0.98), 4),
        "post_rate": round(random.uniform(0.85, 0.98), 4),
        "rejection_rate": round(random.uniform(0.01, 0.05), 4),
        "error_rate": round(random.uniform(0.01, 0.03), 4),
    }


def generate_demo_exception_queue(count: int = 8) -> list[dict]:
    """Generate demo review queue items."""
    queue = []
    for i in range(count):
        carrier = random.choice(list(DEMO_CARRIERS.keys()))
        insured = random.choice(DEMO_INSUREDS)
        premium = round(random.uniform(500, 15000), 2)
        rate = random.choice(DEMO_CARRIERS[carrier]["rates"])
        commission = round(premium * rate, 2)

        warnings = []
        errors = []
        score = round(random.uniform(0.80, 0.94), 4)

        if score < 0.85:
            warnings.append(f"Client name mismatch: statement='{insured}' vs Epic='Similar Name LLC'")
        if score < 0.82:
            warnings.append(f"Amount ${commission} differs from Epic premium ${premium * 1.1:.2f}")

        queue.append({
            "transaction_id": f"demo-review-{i:04d}",
            "run_id": f"demo-run-review",
            "carrier": carrier,
            "policy_number": _rand_policy(carrier),
            "client_name": insured,
            "amount": str(commission),
            "transaction_type": "premium",
            "confidence_score": score,
            "status": "review",
            "validation_warnings": warnings,
            "validation_errors": errors,
            "effective_date": date.today().isoformat(),
            "line_of_business": random.choice(LOB_OPTIONS),
        })

    return sorted(queue, key=lambda x: x["confidence_score"])


def generate_demo_reconciliation(run_id: str | None = None) -> dict:
    """Generate a demo reconciliation report."""
    total = random.randint(20, 60)
    matched = int(total * random.uniform(0.90, 0.98))
    mismatched = total - matched
    return {
        "status": "complete",
        "filters": {"run_id": run_id, "carrier": None, "date": date.today().isoformat()},
        "summary": {
            "total_checked": total,
            "matched": matched,
            "mismatched": mismatched,
            "missing_in_epic": random.randint(0, 2),
            "epic_api_errors": 0,
            "match_rate_pct": round(matched / total * 100, 1),
        },
        "mismatched": [
            {
                "transaction_id": f"demo-mismatch-{i}",
                "epic_entry_id": f"EPIC-{random.randint(10000, 99999)}",
                "policy_number": _rand_policy("hartford"),
                "amount": str(round(random.uniform(500, 5000), 2)),
                "carrier": random.choice(list(DEMO_CARRIERS.keys())),
                "discrepancies": [{"field": "amount", "ours": "1500.00", "epic": "1475.00", "delta": "25.00"}],
            }
            for i in range(mismatched)
        ],
        "missing_in_epic": [],
        "epic_errors": [],
        "matched_sample": [],
    }


def generate_demo_trial_diff(run_id: str | None = None) -> dict:
    """Generate a demo trial diff report."""
    total = random.randint(15, 40)
    would_auto = int(total * random.uniform(0.85, 0.96))
    would_review = total - would_auto
    return {
        "status": "complete",
        "filters": {"run_id": run_id, "carrier": None, "date": date.today().isoformat()},
        "summary": {
            "total_transactions": total,
            "would_auto_post": would_auto,
            "would_send_to_review": would_review,
            "would_reject": 0,
            "auto_post_rate_pct": round(would_auto / total * 100, 1),
            "policy_match_rate_pct": round(random.uniform(95, 100), 1),
            "amount_match_rate_pct": round(random.uniform(92, 99), 1),
            "total_our_amount": str(round(random.uniform(20000, 100000), 2)),
            "total_epic_amount": str(round(random.uniform(20000, 100000), 2)),
            "net_delta": str(round(random.uniform(-500, 500), 2)),
        },
        "recommendation": "Good accuracy. Review the exceptions, then consider promoting to live.",
        "comparisons": [],
    }
