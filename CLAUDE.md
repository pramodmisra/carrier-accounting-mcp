# Carrier Accounting MCP — Claude Code Context

## Project Overview

This is an **Insurance Carrier Accounting MCP Server** for Snellings Walters Insurance.
It automates the full carrier statement lifecycle:
1. Ingest carrier PDFs and Excel bordereaux files
2. Browse carrier portals to download statements
3. Normalize and validate transactions against the BigQuery data lake
4. Post approved entries to Applied Epic via the SDK
5. Provide a daily accuracy dashboard for the accounting team

## Architecture

```
Carrier PDFs/Excel/Portals
         ↓
[MCP: Ingestion Layer]       — pdfplumber, pandas, playwright
         ↓
[MCP: Normalization Layer]   — Claude LLM maps raw → canonical schema
         ↓
[MCP: Validation Layer]      — BigQuery: match policies, check duplicates
         ↓
[Confidence Scoring]         — ≥95% auto-queue, <95% human review queue
         ↓
[Staging / Trial Mode]       — Shadow writes to BQ, NOT Epic
         ↓ (approved)
[MCP: Epic Write Layer]      — Applied Epic SDK posts entries
         ↓
[Audit Trail in Data Lake]   — Full lineage: source file → Epic entry ID
         ↓
[Daily Monitoring Dashboard] — Streamlit + BigQuery
```

## Repository Structure

```
carrier-accounting-mcp/
├── CLAUDE.md                          ← YOU ARE HERE
├── README.md
├── requirements.txt
├── pyproject.toml
├── .env.example
├── mcp_server/
│   ├── server.py                      ← Main MCP server entrypoint
│   ├── config.py                      ← All configuration
│   ├── tools/
│   │   ├── ingestion.py               ← PDF/Excel parsing tools
│   │   ├── normalization.py           ← LLM normalization tools
│   │   ├── validation.py              ← BigQuery validation tools
│   │   ├── staging.py                 ← Trial/shadow mode tools
│   │   ├── epic_writer.py             ← Applied Epic SDK write tools
│   │   ├── monitoring.py              ← Daily metrics & exception queue
│   │   └── browser.py                 ← Playwright carrier portal tools
│   ├── schemas/
│   │   ├── canonical.py               ← Canonical transaction dataclass
│   │   └── carrier_schemas/           ← Per-carrier field mappings
│   └── services/
│       ├── bigquery_client.py         ← BQ connection + query helpers
│       ├── epic_sdk_client.py         ← Applied Epic SDK wrapper
│       └── confidence_scorer.py       ← Confidence scoring logic
├── data_lake/
│   ├── schemas/
│   │   ├── staging_tables.sql         ← BQ staging + shadow table DDL
│   │   └── audit_tables.sql           ← Audit trail DDL
│   └── queries/
│       ├── validate_policy.sql
│       ├── check_duplicate.sql
│       └── daily_metrics.sql
├── dashboard/
│   └── daily_monitoring.py            ← Streamlit daily scorecard
├── carrier_configs/
│   ├── README.md
│   └── carrier_template.yaml          ← Template for onboarding new carriers
├── tests/
│   ├── test_ingestion.py
│   ├── test_normalization.py
│   └── test_validation.py
└── docs/
    ├── architecture.md
    ├── adding_carriers.md
    ├── trial_run_guide.md
    └── epic_sdk_setup.md
```

## Key Concepts

### Canonical Transaction Schema
Every carrier statement — regardless of format — is normalized to:
```python
{
  "run_id": str,                   # Unique run identifier
  "source_file": str,              # Original filename
  "carrier": str,                  # e.g. "nationwide", "travelers"
  "policy_number": str,            # Carrier policy number
  "epic_policy_id": str | None,    # Matched Epic policy ID
  "client_name": str,
  "effective_date": date,
  "transaction_type": str,         # "premium", "commission", "return_premium"
  "amount": Decimal,
  "confidence_score": float,       # 0.0–1.0
  "status": str,                   # "pending", "approved", "rejected", "posted"
  "mode": str,                     # "trial" or "live"
  "epic_entry_id": str | None,     # Set after SDK write
  "created_at": datetime,
  "reviewed_by": str | None,
  "review_notes": str | None
}
```

### Confidence Score Thresholds
- **≥ 0.95** → Auto-queue for posting (with accounting team oversight in trial phase)
- **0.80–0.94** → Human review queue
- **< 0.80** → Flagged for manual investigation

### Trial vs Live Mode
- **trial**: All validation runs, but writes go to `staging.carrier_entries_shadow` in BigQuery only. Zero Epic writes.
- **live**: Validated + approved transactions post to Epic via SDK. Audit written to BQ.

### Phased Rollout
- Phase 1 (Weeks 1–2): All carriers in trial mode
- Phase 2 (Weeks 3–4): 1–2 clean carriers go live
- Phase 3 (Month 2): Auto-post ≥95% confidence, rest to review queue
- Phase 4 (Month 3+): Full production, humans handle exceptions only

## Environment Variables (see .env.example)

```
GOOGLE_CLOUD_PROJECT=snellings-walters-prod
BIGQUERY_DATASET=sw_carrier_accounting
BIGQUERY_STAGING_DATASET=sw_staging
APPLIED_EPIC_SDK_URL=
APPLIED_EPIC_API_KEY=
APPLIED_EPIC_AGENCY_ID=
ANTHROPIC_API_KEY=                 # For normalization LLM calls
```

## BigQuery Tables Used

### Source (read-only)
- `combined_policy_master` — validated premium/policy reference
- `sw_complete_analytics_v3` — extended policy analytics view

### Written by this system
- `sw_carrier_accounting.carrier_entries_shadow` — trial mode staging
- `sw_carrier_accounting.carrier_entries_live` — approved live transactions
- `sw_carrier_accounting.run_log` — per-run metadata
- `sw_carrier_accounting.audit_trail` — full lineage

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run MCP server locally
python mcp_server/server.py

# Run in trial mode against test fixtures
python mcp_server/server.py --mode=trial

# Run dashboard
streamlit run dashboard/daily_monitoring.py

# Run tests
pytest tests/ -v

# Install playwright browsers
playwright install chromium
```

## MCP Tools Reference

### Ingestion
- `ingest_pdf_statement(file_path, carrier, mode)` → run_id
- `ingest_excel_bordereaux(file_path, carrier, mode)` → run_id
- `browse_carrier_portal(carrier, credentials, mode)` → run_id

### Validation
- `validate_run(run_id)` → validation_report
- `get_exception_queue(date?)` → list of transactions needing review

### Review
- `approve_transaction(transaction_id, reviewer)` → status
- `reject_transaction(transaction_id, reviewer, reason)` → status
- `approve_batch(run_id, reviewer)` → approval_summary

### Posting
- `post_run_to_epic(run_id)` → posting_report
- `rollback_run(run_id, reason)` → rollback_status

### Monitoring
- `get_daily_metrics(date?)` → daily_scorecard
- `get_run_history(days?)` → list of runs
- `get_carrier_accuracy(carrier, days?)` → accuracy_report

## Adding a New Carrier

See `docs/adding_carriers.md`. The short version:
1. Copy `carrier_configs/carrier_template.yaml` → `carrier_configs/{carrier_name}.yaml`
2. Define field mappings (policy_number_field, premium_field, etc.)
3. Add a schema entry in `mcp_server/schemas/carrier_schemas/`
4. Run trial mode for 2 weeks before enabling live writes
5. Review accuracy dashboard before promoting to auto-post

## Notes for Claude Code Sessions

- Always check `combined_policy_master` for the canonical premium/policy reference
- The `best_billed_premium` and `best_premium` fields are the validated premium sources
- Producer matching uses the TeamMapping table logic already built
- For Epic SDK calls: wrap every write in a try/except and log the epic_entry_id back to BQ immediately
- Never write to `carrier_entries_live` without a `confidence_score >= 0.95` AND mode == "live"
- The dashboard Streamlit app connects directly to BigQuery — keep queries in `data_lake/queries/`

## Current Status

- [ ] MCP server skeleton built
- [ ] Ingestion tools (PDF + Excel) implemented
- [ ] Normalization prompt engineered
- [ ] BigQuery validation queries written
- [ ] Staging/shadow mode implemented
- [ ] Epic SDK client wrapped
- [ ] Daily monitoring dashboard built
- [ ] Trial run with first carrier
- [ ] Phase 1 sign-off from accounting team
