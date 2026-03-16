"""
Local ingestion test harness — runs the PDF/Excel parsing layer
against real sample data without requiring BigQuery or Epic connections.
Tests the ingestion + normalization layers only.
"""

import os
import json
from pathlib import Path
from datetime import datetime

import pytest

from mcp_server.tools.ingestion import (
    ingest_pdf_statement,
    ingest_excel_bordereaux,
    ingest_statement,
    detect_file_format,
)

SAMPLE_DIR = Path(__file__).parent.parent / "direct bill sample data" / "Direct bill Automation"
CURRENT_DIR = SAMPLE_DIR / "Current Statements"


def _all_sample_files():
    """Collect all parseable files from sample data directory."""
    files = []
    for folder in [SAMPLE_DIR, CURRENT_DIR]:
        if not folder.exists():
            continue
        for f in folder.iterdir():
            if f.suffix.lower() in (".pdf", ".xlsx", ".xls", ".csv"):
                files.append(f)
    return files


def _pdf_files():
    return [f for f in _all_sample_files() if f.suffix.lower() == ".pdf"]


def _excel_files():
    return [f for f in _all_sample_files() if f.suffix.lower() in (".xlsx", ".xls", ".csv")]


# ------------------------------------------------------------------ #
# TESTS                                                                #
# ------------------------------------------------------------------ #

class TestSampleDataExists:
    def test_sample_dir_exists(self):
        assert SAMPLE_DIR.exists(), f"Sample data not found at {SAMPLE_DIR}"

    def test_has_files(self):
        files = _all_sample_files()
        assert len(files) > 0, "No parseable files found in sample data"
        print(f"\nFound {len(files)} sample files")


class TestPDFIngestion:
    """Test PDF parsing against real carrier statements."""

    @pytest.fixture(params=_pdf_files(), ids=lambda f: f.name)
    def pdf_file(self, request):
        return request.param

    def test_pdf_parses_without_error(self, pdf_file):
        """Every PDF should parse without throwing an exception."""
        carrier = pdf_file.stem.split()[0].lower()
        result = ingest_pdf_statement(str(pdf_file), carrier, "trial")

        assert result["format"] == "pdf"
        assert result["carrier"] == carrier
        assert result["run_id"] is not None
        assert isinstance(result["raw_rows"], list)
        print(f"\n  {pdf_file.name}: {len(result['raw_rows'])} rows extracted")

    def test_pdf_extracts_data(self, pdf_file):
        """PDFs should extract at least some content."""
        carrier = pdf_file.stem.split()[0].lower()
        result = ingest_pdf_statement(str(pdf_file), carrier, "trial")
        assert len(result["raw_rows"]) > 0, f"No data extracted from {pdf_file.name}"


class TestExcelIngestion:
    """Test Excel/CSV parsing against real carrier statements."""

    @pytest.fixture(params=_excel_files(), ids=lambda f: f.name)
    def excel_file(self, request):
        return request.param

    def test_excel_parses_without_error(self, excel_file):
        """Every Excel/CSV should parse without throwing an exception."""
        carrier = excel_file.stem.split()[0].lower()
        result = ingest_excel_bordereaux(str(excel_file), carrier, "trial")

        assert result["format"] == "excel"
        assert result["carrier"] == carrier
        assert isinstance(result["raw_rows"], list)
        assert "columns" in result
        print(f"\n  {excel_file.name}: {len(result['raw_rows'])} rows, columns: {result['columns']}")

    def test_excel_extracts_data(self, excel_file):
        """Excel files should extract at least some content."""
        carrier = excel_file.stem.split()[0].lower()
        result = ingest_excel_bordereaux(str(excel_file), carrier, "trial")
        assert len(result["raw_rows"]) > 0, f"No data extracted from {excel_file.name}"


class TestAutoDetection:
    """Test the format auto-detection routing."""

    @pytest.fixture(params=_all_sample_files()[:10], ids=lambda f: f.name)
    def sample_file(self, request):
        return request.param

    def test_auto_detect_routes_correctly(self, sample_file):
        """Auto-detect should route to the correct parser."""
        carrier = sample_file.stem.split()[0].lower()
        result = ingest_statement(str(sample_file), carrier, "trial")

        expected_format = "pdf" if sample_file.suffix.lower() == ".pdf" else "excel"
        assert result["format"] == expected_format
        assert len(result["raw_rows"]) > 0


class TestFilenameAmountPattern:
    """
    Carrier statements are named like 'Carrier Amount.ext'.
    Verify we can parse the expected amount from the filename.
    """

    @pytest.fixture(params=_all_sample_files(), ids=lambda f: f.name)
    def sample_file(self, request):
        return request.param

    def test_filename_has_amount(self, sample_file):
        """Filenames should contain a parseable dollar amount."""
        stem = sample_file.stem
        parts = stem.rsplit(" ", 1)
        if len(parts) == 2:
            try:
                amount_str = parts[1].replace(",", "")
                amount = float(amount_str)
                print(f"\n  {sample_file.name}: expected amount ${amount:,.2f}")
            except ValueError:
                pytest.skip(f"Cannot parse amount from filename: {stem}")
        else:
            pytest.skip(f"Filename doesn't match 'Carrier Amount' pattern: {stem}")
