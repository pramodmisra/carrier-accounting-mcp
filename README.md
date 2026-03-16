# Carrier Accounting MCP

**Insurance Carrier Accounting Automation for Snellings Walters Insurance**

Automates the full carrier statement lifecycle: ingest → normalize → validate → review → post to Applied Epic.

---

## Quick Start

```bash
# 1. Clone and setup
git clone <repo>
cd carrier-accounting-mcp
pip install -r requirements.txt
playwright install chromium

# 2. Configure
cp .env.example .env
# Edit .env with your BigQuery and Epic credentials

# 3. Create BigQuery tables
bq query --use_legacy_sql=false < data_lake/schemas/staging_tables.sql

# 4. Start the MCP server (trial mode by default — safe)
python mcp_server/server.py

# 5. Start the monitoring dashboard
streamlit run dashboard/daily_monitoring.py

# 6. Run tests
pytest tests/ -v
```

---

## Core Workflow

```
1. ingest_carrier_statement(file, carrier, mode="trial")
      ↓ Parses PDF or Excel, normalizes with Claude LLM,
        validates against BigQuery, stages for review

2. Daily: accounting team reviews dashboard at localhost:8501
      ↓ Reviews exception queue, approves/rejects transactions

3. When ready for live: set mode="live" per carrier
      ↓ Auto-posts ≥95% confidence transactions to Epic
      ↓ <95% still go to human review queue
```

---

## Supported Carriers

- Nationwide (Excel)
- Travelers (PDF)
- *(Add more — see docs/adding_carriers.md)*

---

## Documentation

| Doc | Contents |
|---|---|
| `CLAUDE.md` | Full project context for Claude Code sessions |
| `docs/adding_carriers.md` | How to onboard a new carrier |
| `docs/trial_run_guide.md` | Guide for the accounting team |
| `docs/epic_sdk_setup.md` | Applied Epic SDK configuration |
| `carrier_configs/carrier_template.yaml` | Template for new carrier configs |

---

## Architecture

```
Carrier Files (PDF/Excel/Portal)
    → Ingestion (pdfplumber / pandas / playwright)
    → Normalization (Claude LLM → canonical schema)
    → Validation (BigQuery: policy match, duplicate check)
    → Confidence Scoring (auto ≥95%, review 80-94%, reject <80%)
    → Staging (BigQuery shadow table in trial / live table in live)
    → Applied Epic SDK (live mode only)
    → Audit Trail (BigQuery)
    → Daily Dashboard (Streamlit)
```

---

## Safety Features

- **Trial mode default**: Zero Epic writes until explicitly switched to live
- **Confidence thresholds**: Only ≥95% confidence transactions auto-post
- **Duplicate detection**: Prevents double-posting
- **Rollback support**: Can void Epic entries if needed
- **Full audit trail**: Every transaction tracked source → Epic entry ID
- **Human review queue**: Exceptions always go to accounting team before posting
