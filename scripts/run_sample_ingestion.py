"""
Local test runner — ingest all sample carrier statements
and produce a report WITHOUT needing BigQuery or Epic.

Usage: python scripts/run_sample_ingestion.py

Outputs a JSON report to reports/ingestion_test_report.json
"""

import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.tools.ingestion import ingest_statement, detect_file_format

SAMPLE_DIR = Path(__file__).parent.parent / "direct bill sample data" / "Direct bill Automation"
REPORT_DIR = Path(__file__).parent.parent / "reports"


def parse_filename_amount(filename: str) -> float | None:
    """Extract expected dollar amount from filename like 'Carrier 1234.56.pdf'."""
    stem = Path(filename).stem
    parts = stem.rsplit(" ", 1)
    if len(parts) == 2:
        try:
            return float(parts[1].replace(",", ""))
        except ValueError:
            return None
    return None


def collect_files() -> list[Path]:
    """Find all parseable statement files."""
    files = []
    for folder in [SAMPLE_DIR, SAMPLE_DIR / "Current Statements"]:
        if not folder.exists():
            continue
        for f in folder.iterdir():
            if f.suffix.lower() in (".pdf", ".xlsx", ".xls", ".csv"):
                files.append(f)
    return sorted(files, key=lambda f: f.name)


def run_ingestion_test():
    files = collect_files()
    print(f"Found {len(files)} carrier statement files\n")

    results = []
    total_rows = 0
    success_count = 0
    error_count = 0
    carriers_seen = set()

    for i, f in enumerate(files, 1):
        carrier_name = f.stem.split()[0]
        carrier_slug = carrier_name.lower().replace(" ", "_")
        expected_amount = parse_filename_amount(f.name)
        file_format = f.suffix.lower().lstrip(".")

        print(f"[{i:3d}/{len(files)}] {f.name} ... ", end="", flush=True)

        try:
            result = ingest_statement(str(f), carrier_slug, "trial")
            row_count = len(result["raw_rows"])
            total_rows += row_count
            success_count += 1
            carriers_seen.add(carrier_slug)

            # Peek at columns if Excel
            columns = result.get("columns", [])

            # Peek at first row
            first_row = result["raw_rows"][0] if result["raw_rows"] else {}
            # Clean up for JSON serialization
            first_row_clean = {}
            for k, v in first_row.items():
                if not k.startswith("_"):
                    first_row_clean[k] = str(v)[:100] if v else ""

            entry = {
                "file": f.name,
                "carrier": carrier_slug,
                "format": result["format"],
                "status": "success",
                "rows_extracted": row_count,
                "expected_amount": expected_amount,
                "columns": columns[:15] if columns else [],
                "first_row_sample": first_row_clean,
                "has_tables": any("_raw_text" not in r for r in result["raw_rows"]),
                "has_raw_text_only": all("_raw_text" in r for r in result["raw_rows"]),
            }

            status = f"{row_count} rows"
            if entry["has_raw_text_only"]:
                status += " (raw text, no tables)"

            print(f"OK - {status}")

        except Exception as e:
            error_count += 1
            entry = {
                "file": f.name,
                "carrier": carrier_slug,
                "format": file_format,
                "status": "error",
                "error": str(e),
                "rows_extracted": 0,
            }
            print(f"ERROR - {e}")

        results.append(entry)

    # Build summary
    pdf_results = [r for r in results if r["format"] == "pdf"]
    excel_results = [r for r in results if r["format"] in ("excel", "xlsx", "xls", "csv")]

    pdf_with_tables = [r for r in pdf_results if r.get("has_tables")]
    pdf_text_only = [r for r in pdf_results if r.get("has_raw_text_only")]

    summary = {
        "run_at": datetime.utcnow().isoformat(),
        "total_files": len(files),
        "success": success_count,
        "errors": error_count,
        "success_rate_pct": round(success_count / len(files) * 100, 1) if files else 0,
        "total_rows_extracted": total_rows,
        "unique_carriers": len(carriers_seen),
        "carriers": sorted(carriers_seen),
        "by_format": {
            "pdf": {
                "total": len(pdf_results),
                "with_tables": len(pdf_with_tables),
                "text_only": len(pdf_text_only),
            },
            "excel_csv": {
                "total": len(excel_results),
            },
        },
    }

    report = {"summary": summary, "results": results}

    # Write report
    REPORT_DIR.mkdir(exist_ok=True)
    report_path = REPORT_DIR / "ingestion_test_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Print summary
    print(f"\n{'='*60}")
    print(f"INGESTION TEST REPORT")
    print(f"{'='*60}")
    print(f"Files tested:      {len(files)}")
    print(f"Successful:        {success_count} ({summary['success_rate_pct']}%)")
    print(f"Errors:            {error_count}")
    print(f"Total rows parsed: {total_rows}")
    print(f"Unique carriers:   {len(carriers_seen)}")
    print(f"\nPDF breakdown:")
    print(f"  With tables:     {len(pdf_with_tables)}")
    print(f"  Text only (LLM): {len(pdf_text_only)}")
    print(f"\nExcel/CSV:         {len(excel_results)}")
    print(f"\nCarriers: {', '.join(sorted(carriers_seen))}")
    print(f"\nReport saved to: {report_path}")

    if error_count > 0:
        print(f"\nERRORS:")
        for r in results:
            if r["status"] == "error":
                print(f"  {r['file']}: {r['error']}")

    return report


if __name__ == "__main__":
    run_ingestion_test()
