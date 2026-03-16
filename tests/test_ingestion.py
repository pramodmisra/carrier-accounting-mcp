"""Tests for the ingestion tools."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from mcp_server.tools.ingestion import (
    detect_file_format,
    ingest_pdf_statement,
    ingest_excel_bordereaux,
    ingest_statement,
)


class TestDetectFileFormat:
    def test_pdf(self):
        assert detect_file_format("statement.pdf") == "pdf"

    def test_xlsx(self):
        assert detect_file_format("bordereaux.xlsx") == "excel"

    def test_xls(self):
        assert detect_file_format("bordereaux.xls") == "excel"

    def test_csv(self):
        assert detect_file_format("data.csv") == "excel"

    def test_unsupported(self):
        with pytest.raises(ValueError, match="Unsupported file format"):
            detect_file_format("statement.docx")


class TestIngestPdfStatement:
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            ingest_pdf_statement("/nonexistent/file.pdf", "nationwide")

    @patch("mcp_server.tools.ingestion.pdfplumber")
    def test_basic_pdf_extraction(self, mock_pdfplumber, tmp_path):
        # Create a dummy PDF file
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()

        mock_page = MagicMock()
        mock_page.extract_tables.return_value = [
            [
                ["Policy Number", "Insured", "Premium"],
                ["POL-001", "Acme Corp", "1500.00"],
            ]
        ]
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf

        result = ingest_pdf_statement(str(pdf_path), "nationwide", "trial")

        assert result["carrier"] == "nationwide"
        assert result["mode"] == "trial"
        assert result["format"] == "pdf"
        assert len(result["raw_rows"]) == 1
        assert result["raw_rows"][0]["Policy Number"] == "POL-001"


class TestIngestExcelBordereaux:
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            ingest_excel_bordereaux("/nonexistent/file.xlsx", "travelers")


class TestIngestStatement:
    @patch("mcp_server.tools.ingestion.ingest_pdf_statement")
    def test_routes_pdf(self, mock_pdf):
        mock_pdf.return_value = {"format": "pdf"}
        result = ingest_statement("test.pdf", "nationwide")
        mock_pdf.assert_called_once()

    @patch("mcp_server.tools.ingestion.ingest_excel_bordereaux")
    def test_routes_excel(self, mock_excel):
        mock_excel.return_value = {"format": "excel"}
        result = ingest_statement("test.xlsx", "nationwide")
        mock_excel.assert_called_once()
