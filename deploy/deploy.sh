#!/bin/bash
set -e

# ============================================================
# Deploy carrier-accounting to agency.5gvector.com
# Run this on your VPS/server after DNS is pointed
#
# Prerequisites:
#   - Ubuntu 22.04+ or Debian 12+
#   - SSH access as root or sudo user
#   - DNS: agency.5gvector.com → A → this server's IP
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/<repo>/deploy/deploy.sh | bash
#   OR
#   bash deploy/deploy.sh
# ============================================================

echo "============================================"
echo "Carrier Accounting — Deployment Script"
echo "Target: agency.5gvector.com"
echo "============================================"
echo ""

APP_DIR="/opt/carrier-accounting"
REPO_DIR=$(dirname "$(dirname "$(readlink -f "$0")")")

# ---- Step 1: Install Docker if needed ----
if ! command -v docker &> /dev/null; then
    echo "[1/6] Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "  Docker installed."
else
    echo "[1/6] Docker already installed."
fi

if ! command -v docker compose &> /dev/null; then
    echo "  Installing Docker Compose plugin..."
    apt-get update -qq && apt-get install -y -qq docker-compose-plugin
fi

# ---- Step 2: Copy app to /opt ----
echo "[2/6] Setting up application directory..."
if [ "$REPO_DIR" != "$APP_DIR" ]; then
    mkdir -p "$APP_DIR"
    rsync -a --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
          --exclude='.env' --exclude='uploads' --exclude='exports' \
          "$REPO_DIR/" "$APP_DIR/"
fi
cd "$APP_DIR"

# ---- Step 3: Create .env if it doesn't exist ----
echo "[3/6] Configuring environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    # Generate a random dev API key for sandbox access
    DEV_KEY=$(openssl rand -hex 16)
    DB_PASS=$(openssl rand -hex 12)
    sed -i "s/^DEV_API_KEY=.*/DEV_API_KEY=$DEV_KEY/" .env 2>/dev/null || true
    echo "" >> .env
    echo "# Generated during deployment" >> .env
    echo "DEV_API_KEY=$DEV_KEY" >> .env
    echo "DB_PASSWORD=$DB_PASS" >> .env
    echo "  Created .env with generated keys."
    echo "  Edit .env to add your Anthropic/Epic/BigQuery keys for production mode."
else
    echo "  .env already exists — keeping existing config."
fi

# ---- Step 4: Build containers ----
echo "[4/6] Building Docker containers (this takes a few minutes)..."
docker compose -f deploy/docker-compose.prod.yml build --quiet

# ---- Step 5: Start services ----
echo "[5/6] Starting services..."
docker compose -f deploy/docker-compose.prod.yml up -d

# ---- Step 6: Verify ----
echo "[6/6] Verifying deployment..."
sleep 5

# Check API health
if curl -sf http://localhost:8001/api/health > /dev/null 2>&1; then
    echo "  API: OK"
else
    echo "  API: Starting up (may take a moment)..."
fi

# Check web
if curl -sf http://localhost:3000 > /dev/null 2>&1; then
    echo "  Web: OK"
else
    echo "  Web: Starting up (may take a moment)..."
fi

echo ""
echo "============================================"
echo "  Deployment complete!"
echo "============================================"
echo ""
echo "  URL:       https://agency.5gvector.com"
echo "  API docs:  https://agency.5gvector.com/docs"
echo "  Health:    https://agency.5gvector.com/api/health"
echo ""
echo "  Sandbox mode is active by default."
echo "  No credentials needed — agencies can test immediately."
echo ""
echo "  To add production credentials, edit /opt/carrier-accounting/.env"
echo "  then: docker compose -f deploy/docker-compose.prod.yml restart api"
echo ""
echo "  Logs: docker compose -f deploy/docker-compose.prod.yml logs -f"
echo ""
