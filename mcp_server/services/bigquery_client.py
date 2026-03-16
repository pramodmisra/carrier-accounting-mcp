"""
BigQuery client service.
Handles all data lake reads and writes for the carrier accounting pipeline.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from google.cloud import bigquery
from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter

from mcp_server.config import Config
from mcp_server.schemas.canonical import CanonicalTransaction, RunSummary


class BigQueryClient:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = bigquery.Client(project=Config.GCP_PROJECT)
        return self._client

    # ------------------------------------------------------------------ #
    # POLICY VALIDATION                                                    #
    # ------------------------------------------------------------------ #

    def find_policy_by_carrier_number(
        self, carrier: str, policy_number: str
    ) -> Optional[dict]:
        """
        Look up an Epic policy by carrier policy number.
        Uses combined_policy_master as the source of truth.
        Returns dict with epic_policy_id, epic_client_id, client_name,
        best_billed_premium, best_premium, or None if not found.
        """
        query = f"""
            SELECT
                PolicyId           AS epic_policy_id,
                ClientId           AS epic_client_id,
                ClientName         AS client_name,
                PolicyNumber       AS epic_policy_number,
                CarrierPolicyNum   AS carrier_policy_number,
                best_billed_premium,
                best_premium,
                LineOfBusiness     AS line_of_business,
                ProducerCode       AS producer_code,
                PolicyStatus       AS policy_status
            FROM `{Config.policy_master_table()}`
            WHERE
                LOWER(CarrierName) LIKE LOWER(@carrier)
                AND (
                    CarrierPolicyNum = @policy_number
                    OR PolicyNumber  = @policy_number
                )
            LIMIT 1
        """
        job_config = QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("carrier", "STRING", f"%{carrier}%"),
                ScalarQueryParameter("policy_number", "STRING", policy_number),
            ]
        )
        rows = list(self.client.query(query, job_config=job_config).result())
        return dict(rows[0]) if rows else None

    def check_duplicate(self, carrier: str, policy_number: str, amount: Decimal,
                        effective_date: date) -> bool:
        """Return True if an identical transaction already exists in live or shadow table."""
        query = f"""
            SELECT COUNT(*) AS cnt
            FROM `{Config.live_table()}`
            WHERE
                carrier = @carrier
                AND policy_number = @policy_number
                AND amount = CAST(@amount AS NUMERIC)
                AND effective_date = @effective_date
                AND status NOT IN ('rejected', 'rolled_back')
        """
        job_config = QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("carrier", "STRING", carrier),
                ScalarQueryParameter("policy_number", "STRING", policy_number),
                ScalarQueryParameter("amount", "STRING", str(amount)),
                ScalarQueryParameter("effective_date", "DATE", effective_date.isoformat()),
            ]
        )
        rows = list(self.client.query(query, job_config=job_config).result())
        return rows[0]["cnt"] > 0

    # ------------------------------------------------------------------ #
    # STAGING WRITES                                                       #
    # ------------------------------------------------------------------ #

    def write_to_shadow(self, transactions: list[CanonicalTransaction]) -> int:
        """Write transactions to shadow/staging table (trial mode). Returns rows inserted."""
        table_ref = self.client.get_table(Config.shadow_table())
        rows = [t.to_dict() for t in transactions]
        errors = self.client.insert_rows_json(table_ref, rows)
        if errors:
            raise RuntimeError(f"BigQuery insert errors: {errors}")
        return len(rows)

    def write_to_live(self, transactions: list[CanonicalTransaction]) -> int:
        """Write approved transactions to live table. Returns rows inserted."""
        table_ref = self.client.get_table(Config.live_table())
        rows = [t.to_dict() for t in transactions]
        errors = self.client.insert_rows_json(table_ref, rows)
        if errors:
            raise RuntimeError(f"BigQuery insert errors: {errors}")
        return len(rows)

    def update_transaction_status(
        self,
        transaction_id: str,
        status: str,
        epic_entry_id: Optional[str] = None,
        reviewed_by: Optional[str] = None,
        review_notes: Optional[str] = None,
    ):
        """Update a transaction's status after review or Epic posting."""
        updates = [f"status = '{status}'", f"updated_at = CURRENT_TIMESTAMP()"]
        if epic_entry_id:
            updates.append(f"epic_entry_id = '{epic_entry_id}'")
            updates.append("epic_posted_at = CURRENT_TIMESTAMP()")
        if reviewed_by:
            updates.append(f"reviewed_by = '{reviewed_by}'")
            updates.append("reviewed_at = CURRENT_TIMESTAMP()")
        if review_notes:
            updates.append(f"review_notes = '{review_notes}'")

        # Update both live and shadow tables
        for table in [Config.live_table(), Config.shadow_table()]:
            query = f"""
                UPDATE `{table}`
                SET {', '.join(updates)}
                WHERE transaction_id = '{transaction_id}'
            """
            self.client.query(query).result()

    # ------------------------------------------------------------------ #
    # RUN LOG                                                              #
    # ------------------------------------------------------------------ #

    def write_run_log(self, run: RunSummary):
        table_ref = self.client.get_table(Config.run_log_table())
        row = {
            "run_id": run.run_id,
            "source_file": run.source_file,
            "carrier": run.carrier,
            "mode": run.mode.value,
            "total_transactions": run.total_transactions,
            "auto_approved": run.auto_approved,
            "review_queue": run.review_queue,
            "failed": run.failed,
            "posted_to_epic": run.posted_to_epic,
            "total_amount": str(run.total_amount),
            "started_at": run.started_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "status": run.status,
        }
        errors = self.client.insert_rows_json(table_ref, [row])
        if errors:
            raise RuntimeError(f"Run log write error: {errors}")

    # ------------------------------------------------------------------ #
    # MONITORING QUERIES                                                   #
    # ------------------------------------------------------------------ #

    def get_daily_metrics(self, target_date: Optional[date] = None) -> dict:
        """Returns daily scorecard metrics for the monitoring dashboard."""
        if target_date is None:
            target_date = date.today()

        query = f"""
            WITH combined AS (
                SELECT * FROM `{Config.shadow_table()}` WHERE mode = 'trial'
                UNION ALL
                SELECT * FROM `{Config.live_table()}` WHERE mode = 'live'
            )
            SELECT
                COUNT(*) AS total_transactions,
                COUNTIF(status IN ('approved', 'posted'))         AS auto_approved,
                COUNTIF(status = 'review')                        AS review_queue,
                COUNTIF(status = 'failed')                        AS failed,
                COUNTIF(status = 'posted')                        AS posted_to_epic,
                COUNTIF(status = 'rejected')                      AS rejected,
                AVG(confidence_score)                             AS avg_confidence,
                SUM(CAST(amount AS NUMERIC))                      AS total_amount
            FROM combined
            WHERE DATE(created_at) = @target_date
        """
        job_config = QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("target_date", "DATE", target_date.isoformat())
            ]
        )
        rows = list(self.client.query(query, job_config=job_config).result())
        return dict(rows[0]) if rows else {}

    def get_exception_queue(self, target_date: Optional[date] = None) -> list[dict]:
        """Returns transactions that need human review."""
        date_filter = f"AND DATE(created_at) = '{target_date.isoformat()}'" if target_date else ""
        query = f"""
            SELECT *
            FROM `{Config.shadow_table()}`
            WHERE status = 'review'
            {date_filter}
            ORDER BY confidence_score ASC, created_at DESC
            LIMIT 200
        """
        rows = list(self.client.query(query).result())
        return [dict(r) for r in rows]

    def get_carrier_accuracy(self, carrier: str, days: int = 30) -> dict:
        """Returns accuracy metrics for a specific carrier over N days."""
        query = f"""
            SELECT
                carrier,
                COUNT(*) AS total,
                AVG(confidence_score) AS avg_confidence,
                COUNTIF(status = 'posted') / COUNT(*) AS post_rate,
                COUNTIF(status = 'rejected') / COUNT(*) AS rejection_rate,
                COUNTIF(validation_errors != '[]') / COUNT(*) AS error_rate
            FROM `{Config.live_table()}`
            WHERE
                carrier = @carrier
                AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
            GROUP BY carrier
        """
        job_config = QueryJobConfig(
            query_parameters=[
                ScalarQueryParameter("carrier", "STRING", carrier),
                ScalarQueryParameter("days", "INT64", days),
            ]
        )
        rows = list(self.client.query(query, job_config=job_config).result())
        return dict(rows[0]) if rows else {}
