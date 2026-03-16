# Carrier Accounting MCP Server

<!-- mcp-name: io.github.pramodmisra/carrier-accounting-mcp -->

AI-powered carrier statement processing for US insurance agencies using Applied Epic.

## What It Does

Automates the full carrier accounting lifecycle:

1. **Ingest** carrier PDFs, Excel, and CSV statements (48+ carriers supported)
2. **Normalize** via Claude LLM — maps any carrier format to a canonical schema
3. **Reconcile** with 5-layer matching engine (99.5% accuracy)
4. **Score** confidence per transaction (policy match, name, amount, date, duplicates)
5. **Post** to Applied Epic via SDK, UI automation, or CSV batch import
6. **Monitor** with daily accuracy dashboards and exception queues

## MCP Tools (21 tools)

### Ingestion
- `ingest_carrier_statement` — Full pipeline: parse → normalize → validate → stage
- `ingest_pdf` — Ingest a PDF carrier statement
- `ingest_excel` — Ingest an Excel/CSV bordereaux

### Standalone Pipeline
- `normalize_transactions` — Parse + normalize without validation
- `validate_against_datalake` — Parse + normalize + validate (no staging)
- `score_confidence` — Score a single transaction's match confidence
- `browse_carrier_portal` — Download statements from carrier portals via Playwright

### Review Queue
- `get_exception_queue_today` — Transactions needing human review
- `approve` — Approve a transaction
- `reject` — Reject a transaction with reason
- `approve_run` — Bulk approve all review items from a run

### Epic Posting
- `post_to_epic` — Post via REST API
- `post_to_epic_via_browser` — Post via Playwright UI automation
- `generate_epic_import` — Generate Epic-compatible CSV
- `rollback` — Rollback posted entries

### Monitoring & Reports
- `daily_metrics` — Daily accuracy scorecard
- `carrier_accuracy` — Per-carrier accuracy over N days
- `run_history` — Recent ingestion runs
- `list_supported_carriers` — All 48+ configured carriers
- `reconciliation_report` — Posted vs Epic comparison
- `trial_diff_report` — Shadow mode: what would have posted vs Epic

## Supported Carriers (48+)

Hartford, Hanover, Central, Donegal, Liberty Mutual, Berkley, Progressive, Westfield,
Principal, Cigna, BCBS, Allied, Guardian, Unum, Sun Life, Accident Fund, Guard,
AmTrust, CNA, Sentry, and 28 more.

## Quick Start

```bash
pip install carrier-accounting-mcp
carrier-accounting-mcp --port 8000
```

Or add to Claude Desktop config:
```json
{
  "mcpServers": {
    "carrier-accounting": {
      "command": "carrier-accounting-mcp",
      "args": ["--port", "8000"]
    }
  }
}
```

## Part of 5G Vector

This MCP server is the AI engine behind [5G Vector](https://5gvector.com) — the data, analytics, and automation platform for Applied Epic insurance agencies.

Full web UI, team collaboration, Stripe billing, and multi-tenant support available at [5gvector.com/carrier-accounting](https://5gvector.com/carrier-accounting).
