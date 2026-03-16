# Privacy Policy — 5G Vector Carrier Accounting MCP Server

**Effective Date:** March 16, 2026
**Company:** 5G Vector Technologies
**Contact:** privacy@5gvector.com

---

## Information We Collect

### Account Information
- Email address (for authentication via OAuth)
- Organization name and agency details

### Usage Data
- Tool invocations (which tools were called, timestamps, error rates)
- File metadata (filenames, file sizes, carrier names — NOT file contents stored)
- Aggregate performance metrics (reconciliation rates, match scores)

### Agency Configuration
- Applied Epic SDK connection details (API URL, agency ID — stored encrypted)
- BigQuery project configuration (project ID — stored encrypted)
- Carrier-specific field mappings

## Information We Do NOT Collect or Store

- **We do not store the content of uploaded carrier statements** — files are processed in memory and discarded
- **We do not store individual policy details** from your Applied Epic system outside of active processing
- **We do not store client/insured personal information** (names, addresses, SSNs)
- **We do not sell, share, or provide your data to third parties**
- **We do not use your data to train AI models**

## How We Use Information

- Execute MCP tool requests on your behalf
- Improve reconciliation accuracy through learned carrier-to-policy mappings (per-org, never shared)
- Monitor service health and uptime
- Send service notifications (outages, updates)

## Data Retention

| Data Type | Retention |
|---|---|
| Account data | Until account deletion |
| Usage metrics | 90 days rolling |
| OAuth tokens | Until expiry or revocation |
| Learned mappings | Until account deletion (improves your reconciliation over time) |
| Uploaded files | Not retained — processed in memory only |

## Third-Party Services

| Service | Purpose | Data Shared |
|---|---|---|
| Auth0 | Authentication (OAuth 2.0) | Email, auth tokens |
| Railway | Server hosting | Encrypted in transit/at rest |
| Anthropic Claude API | LLM normalization of carrier statements | Statement text (not stored by Anthropic per their policy) |
| Google BigQuery | Your agency's data lake (if connected) | We connect but do not store your BQ data |

## Security

- All data encrypted in transit (TLS 1.2+)
- All credentials encrypted at rest
- SOC 2-aligned security practices
- Annual security review

## Your Rights

- **Access:** Request a copy of your data
- **Deletion:** Request complete account and data deletion
- **Portability:** Export your learned mappings and configuration
- **Revocation:** Revoke OAuth access at any time via your MCP client settings

## Contact

- Email: privacy@5gvector.com
- Address: Atlanta, GA
- Website: https://5gvector.com
