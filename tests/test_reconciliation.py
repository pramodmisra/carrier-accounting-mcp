"""Tests for reconciliation and trial diff report tools (Gaps #4 and #5)."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from decimal import Decimal


class TestReconciliationReport:
    @patch("mcp_server.tools.reconciliation.epic")
    @patch("mcp_server.tools.reconciliation.bq")
    def test_no_posted_transactions(self, mock_bq, mock_epic):
        from mcp_server.tools.reconciliation import reconciliation_report

        mock_bq.client.query.return_value.result.return_value = []
        result = reconciliation_report(run_id="run-999")
        assert result["status"] == "no_data"

    @patch("mcp_server.tools.reconciliation.epic")
    @patch("mcp_server.tools.reconciliation.bq")
    def test_matched_transactions(self, mock_bq, mock_epic):
        from mcp_server.tools.reconciliation import reconciliation_report

        # Mock BQ returning one posted transaction
        mock_row = {
            "transaction_id": "txn-001",
            "run_id": "run-001",
            "carrier": "nationwide",
            "policy_number": "POL-123",
            "epic_policy_id": "EP-001",
            "epic_client_id": "CL-001",
            "client_name": "Acme Corp",
            "amount": Decimal("1500.00"),
            "transaction_type": "premium",
            "epic_entry_id": "EPIC-ENT-001",
            "epic_posted_at": "2025-01-15T10:00:00",
            "confidence_score": 0.98,
        }
        mock_bq.client.query.return_value.result.return_value = [mock_row]
        mock_bq.client.project = "test-project"

        # Mock Epic API returning matching entry
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "amount": 1500.00,
            "policyId": "EP-001",
            "status": "active",
        }
        mock_response.raise_for_status = MagicMock()
        mock_epic.client.get.return_value = mock_response

        result = reconciliation_report(run_id="run-001")
        assert result["status"] == "complete"
        assert result["summary"]["total_checked"] == 1
        assert result["summary"]["matched"] == 1
        assert result["summary"]["mismatched"] == 0

    @patch("mcp_server.tools.reconciliation.epic")
    @patch("mcp_server.tools.reconciliation.bq")
    def test_mismatched_amount(self, mock_bq, mock_epic):
        from mcp_server.tools.reconciliation import reconciliation_report

        mock_row = {
            "transaction_id": "txn-002",
            "run_id": "run-001",
            "carrier": "travelers",
            "policy_number": "POL-456",
            "epic_policy_id": "EP-002",
            "epic_client_id": "CL-002",
            "client_name": "Beta LLC",
            "amount": Decimal("2000.00"),
            "transaction_type": "premium",
            "epic_entry_id": "EPIC-ENT-002",
            "epic_posted_at": "2025-01-15T10:00:00",
            "confidence_score": 0.95,
        }
        mock_bq.client.query.return_value.result.return_value = [mock_row]
        mock_bq.client.project = "test-project"

        # Epic has a different amount
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "amount": 1800.00,  # Mismatch!
            "policyId": "EP-002",
            "status": "active",
        }
        mock_response.raise_for_status = MagicMock()
        mock_epic.client.get.return_value = mock_response

        result = reconciliation_report(run_id="run-001")
        assert result["summary"]["mismatched"] == 1
        assert result["mismatched"][0]["discrepancies"][0]["field"] == "amount"


class TestTrialDiffReport:
    @patch("mcp_server.tools.reconciliation.epic")
    @patch("mcp_server.tools.reconciliation.bq")
    def test_no_shadow_transactions(self, mock_bq, mock_epic):
        from mcp_server.tools.reconciliation import trial_diff_report

        mock_bq.client.query.return_value.result.return_value = []
        result = trial_diff_report(run_id="run-999")
        assert result["status"] == "no_data"

    @patch("mcp_server.tools.reconciliation.epic")
    @patch("mcp_server.tools.reconciliation.bq")
    def test_diff_with_policy_match(self, mock_bq, mock_epic):
        from mcp_server.tools.reconciliation import trial_diff_report

        mock_row = {
            "transaction_id": "txn-trial-001",
            "run_id": "run-trial-001",
            "carrier": "nationwide",
            "policy_number": "POL-123",
            "epic_policy_id": "EP-001",
            "epic_client_id": "CL-001",
            "client_name": "Acme Corp",
            "amount": Decimal("1500.00"),
            "transaction_type": "premium",
            "effective_date": date(2025, 1, 15),
            "confidence_score": 0.97,
            "status": "approved",
            "auto_approved": True,
            "validation_warnings": [],
            "validation_errors": [],
        }
        mock_bq.client.query.return_value.result.return_value = [mock_row]
        mock_bq.client.project = "test-project"

        # Mock Epic policy read
        mock_epic.get_policy.return_value = {
            "clientName": "Acme Corp",
            "totalPremium": 1500.00,
            "status": "active",
            "lineOfBusiness": "Commercial Auto",
        }

        result = trial_diff_report(run_id="run-trial-001")
        assert result["status"] == "complete"
        assert result["summary"]["total_transactions"] == 1
        assert result["summary"]["would_auto_post"] == 1
        assert result["summary"]["policy_match_rate_pct"] == 100.0
        assert "recommendation" in result

    @patch("mcp_server.tools.reconciliation.epic")
    @patch("mcp_server.tools.reconciliation.bq")
    def test_recommendation_text(self, mock_bq, mock_epic):
        from mcp_server.tools.reconciliation import trial_diff_report

        # All auto-approved
        mock_row = {
            "transaction_id": "txn-001",
            "run_id": "run-001",
            "carrier": "nationwide",
            "policy_number": "POL-123",
            "epic_policy_id": "EP-001",
            "epic_client_id": "CL-001",
            "client_name": "Acme",
            "amount": Decimal("1000.00"),
            "transaction_type": "premium",
            "effective_date": date.today(),
            "confidence_score": 0.99,
            "status": "approved",
            "auto_approved": True,
            "validation_warnings": [],
            "validation_errors": [],
        }
        mock_bq.client.query.return_value.result.return_value = [mock_row]
        mock_bq.client.project = "test-project"
        mock_epic.get_policy.return_value = {"totalPremium": 1000.00, "clientName": "Acme"}

        result = trial_diff_report(run_id="run-001")
        assert "ready for live" in result["recommendation"].lower()
