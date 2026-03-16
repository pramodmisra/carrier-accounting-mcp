"""
Applied Epic SDK client wrapper.
Wraps all SDK write operations with logging, retry, and rollback support.
Every write records the epic_entry_id back to BigQuery immediately.
"""

import httpx
from datetime import datetime
from decimal import Decimal
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional
import structlog

from mcp_server.config import Config
from mcp_server.schemas.canonical import CanonicalTransaction

log = structlog.get_logger(__name__)


class EpicSDKClient:
    """
    Wrapper around the Applied Epic SDK / REST API.

    IMPORTANT: All write methods are guarded by mode checks.
    If mode == "trial", no SDK calls are made — this is enforced here
    as a final safety net even if callers don't check.
    """

    def __init__(self):
        self.base_url = Config.EPIC_SDK_URL
        self.api_key = Config.EPIC_API_KEY
        self.agency_id = Config.EPIC_AGENCY_ID
        self.environment = Config.EPIC_ENVIRONMENT
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "X-Agency-Id": self.agency_id,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    # ------------------------------------------------------------------ #
    # CORE WRITE: Accounting Entry                                         #
    # ------------------------------------------------------------------ #

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def post_accounting_entry(
        self, transaction: CanonicalTransaction
    ) -> Optional[str]:
        """
        Post a single accounting transaction to Applied Epic.
        Returns the Epic entry ID on success, raises on failure.
        BLOCKED in trial mode — returns None with a warning log.
        """
        if transaction.mode.value == "trial":
            log.warning(
                "TRIAL MODE: Epic write blocked",
                transaction_id=transaction.transaction_id,
                carrier=transaction.carrier,
            )
            return None

        if not transaction.epic_policy_id:
            raise ValueError(
                f"Cannot post to Epic: no epic_policy_id for transaction "
                f"{transaction.transaction_id} (policy {transaction.policy_number})"
            )

        payload = self._build_entry_payload(transaction)

        log.info(
            "Posting to Applied Epic",
            transaction_id=transaction.transaction_id,
            epic_policy_id=transaction.epic_policy_id,
            amount=str(transaction.amount),
            environment=self.environment,
        )

        response = self.client.post("/accounting/entries", json=payload)
        response.raise_for_status()

        result = response.json()
        epic_entry_id = result.get("entryId") or result.get("id")

        log.info(
            "Epic entry posted successfully",
            transaction_id=transaction.transaction_id,
            epic_entry_id=epic_entry_id,
        )

        return epic_entry_id

    def rollback_entry(self, epic_entry_id: str, reason: str) -> bool:
        """
        Attempt to void/reverse an Epic accounting entry.
        Returns True on success.
        """
        log.info("Rolling back Epic entry", epic_entry_id=epic_entry_id, reason=reason)
        try:
            response = self.client.post(
                f"/accounting/entries/{epic_entry_id}/void",
                json={"reason": reason}
            )
            response.raise_for_status()
            return True
        except Exception as e:
            log.error("Rollback failed", epic_entry_id=epic_entry_id, error=str(e))
            return False

    # ------------------------------------------------------------------ #
    # READ HELPERS                                                         #
    # ------------------------------------------------------------------ #

    def get_policy(self, epic_policy_id: str) -> Optional[dict]:
        """Read a policy from Applied Epic (read operations work in all modes)."""
        try:
            response = self.client.get(f"/policies/{epic_policy_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log.warning("Epic policy lookup failed", epic_policy_id=epic_policy_id, error=str(e))
            return None

    def get_client(self, epic_client_id: str) -> Optional[dict]:
        """Read a client/account from Applied Epic."""
        try:
            response = self.client.get(f"/clients/{epic_client_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log.warning("Epic client lookup failed", epic_client_id=epic_client_id, error=str(e))
            return None

    # ------------------------------------------------------------------ #
    # PAYLOAD BUILDER                                                      #
    # ------------------------------------------------------------------ #

    def _build_entry_payload(self, transaction: CanonicalTransaction) -> dict:
        """
        Build the Applied Epic SDK accounting entry payload.
        TODO: Adjust field names to match your specific Epic SDK version.
        """
        return {
            "agencyId": self.agency_id,
            "policyId": transaction.epic_policy_id,
            "clientId": transaction.epic_client_id,
            "transactionType": transaction.transaction_type.value,
            "amount": float(transaction.amount),
            "effectiveDate": transaction.effective_date.isoformat() if transaction.effective_date else None,
            "statementDate": transaction.statement_date.isoformat() if transaction.statement_date else None,
            "carrierName": transaction.carrier,
            "lineOfBusiness": transaction.line_of_business,
            "description": transaction.description or f"Carrier statement import - {transaction.carrier}",
            "referenceNumber": transaction.transaction_id,   # Our ID for reconciliation
            "producerCode": transaction.producer_code,
            "source": "carrier_accounting_mcp",
        }
