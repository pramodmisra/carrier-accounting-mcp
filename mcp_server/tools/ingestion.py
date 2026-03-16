"""
Ingestion tools — parse carrier PDF and Excel statements.
Raw parsed data flows to the normalization layer next.
"""

import uuid
import pandas as pd
import pdfplumber
from pathlib import Path
from datetime import datetime
from typing import Optional
import structlog

from mcp_server.schemas.canonical import CanonicalTransaction, RunMode, TransactionStatus
from mcp_server.schemas.carrier_schemas import get_carrier_schema

log = structlog.get_logger(__name__)


def ingest_pdf_statement(
    file_path: str,
    carrier: str,
    mode: str = "trial",
    run_id: Optional[str] = None,
) -> dict:
    """
    Parse a carrier PDF statement into raw transaction records.
    Returns a dict with run_id and list of raw extracted rows.
    The normalization layer converts these to CanonicalTransaction objects.

    Args:
        file_path: Path to the PDF file
        carrier: Carrier slug (e.g. 'nationwide', 'travelers')
        mode: 'trial' or 'live'
        run_id: Optional run ID (generated if not provided)
    """
    run_id = run_id or str(uuid.uuid4())
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    schema = get_carrier_schema(carrier)
    log.info("Ingesting PDF", file=str(file_path), carrier=carrier, run_id=run_id)

    raw_rows = []
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            # Try table extraction first
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    headers = [str(h).strip() if h else f"col_{i}"
                               for i, h in enumerate(table[0])]
                    for row_idx, row in enumerate(table[1:], start=1):
                        if any(cell for cell in row):  # Skip empty rows
                            row_dict = {
                                headers[i]: (row[i] or "").strip()
                                for i in range(min(len(headers), len(row)))
                            }
                            row_dict["_source_page"] = page_num
                            row_dict["_source_row"] = row_idx
                            raw_rows.append(row_dict)
            else:
                # Fallback: raw text extraction (LLM will parse in normalization layer)
                text = page.extract_text() or ""
                if text.strip():
                    raw_rows.append({
                        "_raw_text": text,
                        "_source_page": page_num,
                        "_source_row": 0,
                        "_format": "raw_text",
                    })

    log.info("PDF extraction complete",
             run_id=run_id, pages=len(pdf.pages) if 'pdf' in dir() else 0,
             raw_rows=len(raw_rows))

    return {
        "run_id": run_id,
        "source_file": str(file_path),
        "carrier": carrier,
        "mode": mode,
        "format": "pdf",
        "carrier_schema": schema.carrier_slug,
        "raw_rows": raw_rows,
        "extracted_at": datetime.utcnow().isoformat(),
    }


def ingest_excel_bordereaux(
    file_path: str,
    carrier: str,
    mode: str = "trial",
    run_id: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> dict:
    """
    Parse a carrier Excel bordereaux into raw transaction records.
    Handles multi-sheet workbooks — uses first sheet unless specified.

    Args:
        file_path: Path to the Excel file (.xlsx or .xls)
        carrier: Carrier slug
        mode: 'trial' or 'live'
        run_id: Optional run ID
        sheet_name: Specific sheet to parse (optional)
    """
    run_id = run_id or str(uuid.uuid4())
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")

    schema = get_carrier_schema(carrier)
    log.info("Ingesting Excel/CSV", file=str(file_path), carrier=carrier, run_id=run_id)

    suffix = file_path.suffix.lower()
    available_sheets = []
    target_sheet = ""

    if suffix == ".csv":
        # CSV files — use pd.read_csv; on_bad_lines handles ragged rows
        df = pd.read_csv(file_path, dtype=str, on_bad_lines="skip")
        target_sheet = "csv"
        available_sheets = ["csv"]
    elif suffix == ".xls":
        # .xls files: may be real Excel (xlrd) or HTML-disguised-as-XLS
        try:
            df = pd.read_excel(file_path, dtype=str, engine="xlrd")
        except Exception:
            # Fallback: try reading as HTML table (common in insurance carrier exports)
            try:
                dfs = pd.read_html(str(file_path))
                # Concatenate all tables and stringify columns
                df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
                df.columns = [str(c) for c in df.columns]
                df = df.astype(str)
            except Exception:
                df = pd.read_excel(file_path, dtype=str)
        target_sheet = "Sheet1"
        available_sheets = [target_sheet]
    else:
        # .xlsx / .xlsm — standard openpyxl path
        xl = pd.ExcelFile(file_path)
        available_sheets = xl.sheet_names
        target_sheet = sheet_name or available_sheets[0]
        df = pd.read_excel(file_path, sheet_name=target_sheet, dtype=str)

    # Drop fully empty rows
    df = df.dropna(how="all")

    # Convert to list of dicts
    raw_rows = []
    for row_idx, row in df.iterrows():
        row_dict = row.to_dict()
        row_dict["_source_sheet"] = target_sheet
        row_dict["_source_row"] = row_idx + 2  # +2 for 1-indexed + header row
        raw_rows.append(row_dict)

    log.info("Excel/CSV extraction complete",
             run_id=run_id, rows=len(raw_rows),
             sheets=available_sheets)

    return {
        "run_id": run_id,
        "source_file": str(file_path),
        "carrier": carrier,
        "mode": mode,
        "format": "excel",
        "carrier_schema": schema.carrier_slug,
        "available_sheets": available_sheets,
        "parsed_sheet": target_sheet,
        "columns": list(df.columns),
        "raw_rows": raw_rows,
        "extracted_at": datetime.utcnow().isoformat(),
    }


def detect_file_format(file_path: str) -> str:
    """Detect whether a file is PDF, Excel, or CSV."""
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    elif suffix in {".xlsx", ".xls", ".xlsm", ".csv"}:
        return "excel"
    elif suffix == ".rtf":
        raise ValueError(f"RTF files not supported — convert to PDF first: {file_path}")
    else:
        raise ValueError(f"Unsupported file format: {suffix}")


def ingest_statement(
    file_path: str,
    carrier: str,
    mode: str = "trial",
    run_id: Optional[str] = None,
) -> dict:
    """
    Auto-detect file format and route to the correct ingestion function.
    Convenience wrapper for the MCP tool layer.
    """
    fmt = detect_file_format(file_path)
    if fmt == "pdf":
        return ingest_pdf_statement(file_path, carrier, mode, run_id)
    else:
        return ingest_excel_bordereaux(file_path, carrier, mode, run_id)
