# Deployment Guide — agency.5gvector.com

## DNS Setup

Add an A record for your server:

```
agency.5gvector.com  →  A  →  <your-server-ip>
```

## Quick Deploy

```bash
# 1. Clone the repo on your server
git clone <repo-url> /opt/carrier-accounting
cd /opt/carrier-accounting

# 2. Create .env file
cp .env.example .env
# Edit .env with your credentials (or leave blank for sandbox-only)

# 3. Deploy
docker compose -f deploy/docker-compose.prod.yml up -d

# 4. Verify
curl https://agency.5gvector.com/api/health
```

Caddy handles HTTPS certificates automatically via Let's Encrypt.

## Two Modes

### Sandbox (no credentials needed)
- Visit https://agency.5gvector.com
- Default mode — agencies can test all features with demo data
- Uses `/api/sandbox/*` endpoints
- Real PDF/Excel parsing works (upload your own files)
- Validation, scoring, and posting use synthetic demo data

### Production (connected to Epic + BigQuery)
- Click "Connect to Production" in the sidebar or visit `/onboarding`
- Step 1: Enter Applied Epic SDK credentials (optional — can use CSV imports)
- Step 2: Enter BigQuery project ID (optional — no policy validation without it)
- Step 3: Activate production mode
- All runs start in trial mode (zero Epic writes) until explicitly switched to live

## Environment Variables

```
# Required for production
ANTHROPIC_API_KEY=        # For LLM normalization
GOOGLE_CLOUD_PROJECT=     # BigQuery project
APPLIED_EPIC_SDK_URL=     # Epic API endpoint
APPLIED_EPIC_API_KEY=     # Epic API key
APPLIED_EPIC_AGENCY_ID=   # Your Epic agency ID

# Optional
DEV_API_KEY=dev-key-12345  # For development/testing auth bypass
DB_PASSWORD=carrier        # Postgres password
```

## Architecture

```
Internet
  ↓ HTTPS (443)
Caddy (reverse proxy + auto-SSL)
  ├─ /api/*  → FastAPI (8001)
  ├─ /*      → Next.js (3000)
  └─ /docs   → FastAPI OpenAPI
```
