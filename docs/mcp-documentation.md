# 5G Vector Carrier Accounting — MCP Server Documentation

## Overview

The Carrier Accounting MCP Server automates insurance carrier commission statement processing for US agencies using Applied Epic. Upload a PDF or Excel statement, and the server parses, normalizes, reconciles, and prepares transactions for posting to Epic — replacing hours of manual data entry with minutes of automated processing.

**Target Users:** Insurance agency accountants, controllers, and operations managers at Applied Epic agencies.

## Features

- **48+ carrier formats** supported out of the box
- **AI-powered normalization** — Claude maps any carrier format to a canonical schema
- **5-layer reconciliation** — 99.5% policy match accuracy that improves over time
- **Confidence scoring** — 5-factor weighted model (policy, name, amount, date, duplicate)
- **Trial/Live mode** — shadow mode for testing with zero Epic writes
- **Three Epic write paths** — REST API, UI automation, or CSV batch import
- **Self-learning** — every human approval teaches the system for next time

## Setup

### 1. Connect from Claude Desktop

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "carrier-accounting": {
      "type": "url",
      "url": "https://mcp.5gvector.com/carrier-accounting/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

### 2. Connect from Claude Code

```bash
claude mcp add --transport http carrier-accounting https://mcp.5gvector.com/carrier-accounting/mcp
```

### 3. Authentication

OAuth 2.0 authorization code flow:
1. Claude redirects you to the 5G Vector login page
2. Sign in with your 5gvector.com account
3. Authorize the MCP connection
4. You're connected — start using tools

**Scopes:**
- `read:statements` — parse and view carrier statements
- `read:analytics` — dashboards and reports
- `write:epic` — post transactions to Applied Epic
- `write:review` — approve/reject transactions

## Usage Examples

### Example 1: Process a Carrier Statement

**User:** "I have a Hartford commission statement. Parse it and show me what's in it."

**What happens:**
1. `ingest_carrier_statement` parses the PDF
2. `normalize_transactions` maps Hartford's fields to the canonical schema
3. Returns a table of transactions with policy numbers, insured names, premiums, and commissions

**Result:**
| Policy | Insured | Premium | Commission | Rate | Type |
|---|---|---|---|---|---|
| `20 WEC BS2DH2` | Sparkfly, Inc. | $2,814.00 | $253.26 | 9% | Premium |
| `20 WEC BS2DH2` | Sparkfly, Inc. | $1,406.00 | $0.00 | 0% | Premium |
| `20 WEC BS2DH2` | Sparkfly, Inc. | $1,127.00 | $112.70 | 10% | Premium |
| `20 WEC BS2DH2` | Sparkfly, Inc. | $1,857.00 | $111.42 | 6% | Premium |

### Example 2: Check Reconciliation Accuracy

**User:** "What's our auto-reconciliation rate this month? Show me the daily metrics."

**What happens:**
1. `daily_metrics` returns the scorecard
2. Shows total transactions, auto-approved %, review queue, posted count

**Result:**
- Total Transactions: 847
- Auto-Approved: 791 (93.4%)
- Review Queue: 41 (4.8%)
- Failed: 15 (1.8%)
- Avg Confidence: 96.2%

### Example 3: Score a Specific Transaction

**User:** "Score this: Hartford policy 20 WEC BS2DH2, client Sparkfly Inc, amount $477.20"

**What happens:**
1. `score_confidence` runs the 5-factor model
2. Looks up the policy in the data lake
3. Compares client name, amount, and date

**Result:**
- Confidence: 98.2%
- Classification: Auto-approve
- Policy Match: 100% (exact match)
- Name Match: 100%
- Amount Reasonable: 95%
- Not Duplicate: 100%

## Tool Reference

### Ingestion Tools
| Tool | Description | Read-Only |
|---|---|---|
| `ingest_carrier_statement` | Full pipeline: parse → normalize → validate → stage | No |
| `ingest_pdf` | Parse a PDF carrier statement | No |
| `ingest_excel` | Parse an Excel/CSV bordereaux | No |
| `normalize_transactions` | Parse + normalize without validation | Yes |
| `validate_against_datalake` | Parse + normalize + validate (no staging) | Yes |
| `browse_carrier_portal` | Download statements from carrier portals | No |

### Review Tools
| Tool | Description | Read-Only |
|---|---|---|
| `get_exception_queue_today` | Transactions needing review | Yes |
| `approve` | Approve a transaction | No |
| `reject` | Reject with reason | No |
| `approve_run` | Bulk approve a run | No |
| `score_confidence` | Score a single transaction | Yes |

### Epic Posting Tools
| Tool | Description | Read-Only |
|---|---|---|
| `post_to_epic` | Post via REST API | No |
| `post_to_epic_via_browser` | Post via Playwright UI | No |
| `generate_epic_import` | Generate CSV batch file | Yes |
| `rollback` | Void posted entries | No |

### Monitoring & Reports
| Tool | Description | Read-Only |
|---|---|---|
| `daily_metrics` | Daily accuracy scorecard | Yes |
| `carrier_accuracy` | Per-carrier metrics | Yes |
| `run_history` | Recent ingestion runs | Yes |
| `list_supported_carriers` | All 48+ carriers | Yes |
| `reconciliation_report` | Posted vs Epic comparison | Yes |
| `trial_diff_report` | Shadow mode diff report | Yes |

## Supported Carriers (48+)

Hartford, Hanover, Central Insurance, Donegal, Liberty Mutual, Berkley Net, Progressive, Westfield, State Auto, Principal Financial, Cigna, Blue Cross Blue Shield, Allied Benefits, Guardian, Unum, Sun Life, Accident Fund, Guard, AmTrust, CNA, Sentry, Lincoln Financial, Amwins, Orchid, Nippon, Beam Dental, Dearborn Group, Summit, Priority Risk, Cason Group, Safeco, SAS, Prudential, Standard, Western Surety, American Modern, FFVA, Memic, Genworth, Protective, Assurant Flood, Appalachian, and more.

## Troubleshooting

| Issue | Solution |
|---|---|
| "Authentication failed" | Re-authorize at 5gvector.com, check your token hasn't expired |
| "Carrier not supported" | The LLM normalization layer handles unknown carriers — it will attempt to parse any format |
| "Low confidence score" | Upload more statements for the same carrier — the system learns from your approvals |
| Slow response | Large PDFs (50+ pages) may take 10-15 seconds to parse |

## Support

- **Email:** support@5gvector.com
- **Issues:** https://github.com/pramodmisra/carrier-accounting-mcp/issues
- **Website:** https://5gvector.com/carrier-accounting
- **Full Platform:** https://5gvector.com (web UI, dashboards, team collaboration)
