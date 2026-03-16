"""Tests for the Epic batch CSV import generator (Gap #3)."""

import pytest
from decimal import Decimal
from datetime import date

from mcp_server.schemas.canonical import (
    CanonicalTransaction, TransactionType, TransactionStatus, RunMode
)
from mcp_server.tools.epic_batch_import import (
    _transaction_to_import_row,
    generate_epic_import_csv,
    generate_epic_import_string,
    EPIC_IMPORT_COLUMNS,
)


@pytest.fixture
def sample_transactions():
    return [
        CanonicalTransaction(
            transaction_id="txn-001",
            run_id="run-001",
            source_file="test.pdf",
            carrier="nationwide",
            policy_number="POL-12345",
            epic_policy_id="EP-001",
            epic_client_id="CL-001",
            client_name="Acme Corporation",
            effective_date=date(2025, 1, 15),
            amount=Decimal("1500.00"),
            transaction_type=TransactionType.PREMIUM,
            line_of_business="Commercial Auto",
            producer_code="PR-100",
        ),
        CanonicalTransaction(
            transaction_id="txn-002",
            run_id="run-001",
            source_file="test.pdf",
            carrier="nationwide",
            policy_number="POL-67890",
            epic_policy_id="EP-002",
            epic_client_id="CL-002",
            client_name="Beta LLC",
            effective_date=date(2025, 2, 1),
            amount=Decimal("2500.00"),
            transaction_type=TransactionType.COMMISSION,
            commission_rate=Decimal("0.15"),
        ),
    ]


class TestTransactionToImportRow:
    def test_basic_conversion(self, sample_transactions):
        row = _transaction_to_import_row(sample_transactions[0])
        assert row["PolicyNumber"] == "POL-12345"
        assert row["ClientName"] == "Acme Corporation"
        assert row["Amount"] == "1500.00"
        assert row["TransactionType"] == "premium"
        assert row["EffectiveDate"] == "01/15/2025"
        assert row["ReferenceNumber"] == "txn-001"
        assert row["Source"] == "carrier_accounting_mcp"

    def test_all_columns_present(self, sample_transactions):
        row = _transaction_to_import_row(sample_transactions[0])
        for col in EPIC_IMPORT_COLUMNS:
            assert col in row

    def test_commission_rate(self, sample_transactions):
        row = _transaction_to_import_row(sample_transactions[1])
        assert row["CommissionRate"] == "0.15"

    def test_missing_optional_fields(self):
        txn = CanonicalTransaction(
            transaction_id="txn-minimal",
            run_id="run-001",
            source_file="test.pdf",
            carrier="travelers",
            policy_number="POL-999",
            amount=Decimal("100.00"),
        )
        row = _transaction_to_import_row(txn)
        assert row["EffectiveDate"] == ""
        assert row["LineOfBusiness"] == ""
        assert row["CommissionRate"] == ""


class TestGenerateEpicImportCsv:
    def test_empty_transactions(self):
        result = generate_epic_import_csv([])
        assert result["status"] == "empty"
        assert result["row_count"] == 0

    def test_generates_file(self, sample_transactions, tmp_path):
        output = str(tmp_path / "test_import.csv")
        result = generate_epic_import_csv(sample_transactions, output)
        assert result["status"] == "generated"
        assert result["row_count"] == 2
        assert result["file_path"] == output
        assert result["total_amount"] == "4000.00"
        assert len(result["preview"]) == 2

        # Verify file content
        import csv
        with open(output, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["PolicyNumber"] == "POL-12345"
        assert rows[1]["PolicyNumber"] == "POL-67890"


class TestGenerateEpicImportString:
    def test_empty(self):
        assert generate_epic_import_string([]) == ""

    def test_returns_csv_string(self, sample_transactions):
        csv_str = generate_epic_import_string(sample_transactions)
        lines = csv_str.strip().split("\n")
        assert len(lines) == 3  # header + 2 data rows
        assert "PolicyNumber" in lines[0]
        assert "POL-12345" in lines[1]
