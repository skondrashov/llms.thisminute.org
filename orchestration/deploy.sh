#!/usr/bin/env bash
# Deploy Orchestration to thisminute.org/orchestration
# Static files served by nginx. API proxied to FastAPI via nginx.
#
# Usage:
#   bash deploy.sh           # Deploy frontend only
#   bash deploy.sh --api     # Deploy frontend + API
#
# ======================================================================
# ONE-TIME MIGRATION (2026-04-11): rhizome → orchestration
# ----------------------------------------------------------------------
# This repo was renamed from `rhizome/` to `orchestration/` and the deploy
# target on the VM needs to follow. Running this script WITHOUT doing the
# migration first will create a parallel /opt/orchestration directory and
# leave the old /opt/rhizome + rhizome-api systemd unit running side by
# side. Do the migration once, then this script works normally.
#
# On the VM (as sudo):
#
#   # Stop the old service
#   sudo systemctl stop rhizome-api || true
#   sudo systemctl disable rhizome-api || true
#
#   # Move the directory
#   sudo mv /opt/rhizome /opt/orchestration
#
#   # Rename the SQLite DB file (if the old one exists)
#   sudo mv /opt/orchestration/api/rhizome.db \
#           /opt/orchestration/api/orchestration.db 2>/dev/null || true
#
#   # Remove the old unit file (this script will recreate it as
#   # orchestration-api on the next --api deploy)
#   sudo rm /etc/systemd/system/rhizome-api.service
#   sudo systemctl daemon-reload
#
#   # Update nginx. Rename the location block from /rhizome/ to
#   # /orchestration/ and any proxy_pass references. Then:
#   sudo nginx -t && sudo systemctl reload nginx
#
#   # Optional: remove the now-dead directories
#   sudo rm -rf /opt/crucible 2>/dev/null || true   # crucible is gone
#
# After the migration, run this script normally (bash deploy.sh --api on
# the first post-migration deploy so the new systemd unit gets written).
# ======================================================================

set -euo pipefail

INSTANCE="thisminute"
ZONE="us-central1-a"
REMOTE_DIR="/opt/orchestration"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_API=false

if [[ "${1:-}" == "--api" ]]; then
    DEPLOY_API=true
fi

echo "=== Deploying Orchestration ==="

# 1. Build data.js from structure files
echo "[1/4] Building data.js..."
python "$SCRIPT_DIR/build.py"

# 2. Upload static files to server
echo "[2/4] Uploading static files..."
gcloud compute scp "$SCRIPT_DIR/index.html" "$SCRIPT_DIR/evolution.html" "$SCRIPT_DIR/data.js" "$INSTANCE:$REMOTE_DIR/" --zone="$ZONE"

# 3. Deploy API (if requested)
if $DEPLOY_API; then
    echo "[3/4] Deploying API..."
    gcloud compute scp --recurse "$SCRIPT_DIR/api" "$INSTANCE:$REMOTE_DIR/" --zone="$ZONE"
    gcloud compute ssh "$INSTANCE" --zone="$ZONE" --command="
        cd $REMOTE_DIR &&
        python3 -m venv --system-site-packages $REMOTE_DIR/venv 2>/dev/null || true &&
        $REMOTE_DIR/venv/bin/pip install -r api/requirements.txt -q &&
        $REMOTE_DIR/venv/bin/python api/init_db.py &&
        sudo tee /etc/systemd/system/orchestration-api.service > /dev/null <<'UNIT'
[Unit]
Description=Orchestration Social API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/orchestration
ExecStart=/opt/orchestration/venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8100
Restart=always
RestartSec=5
Environment=ORCHESTRATION_DB_PATH=/opt/orchestration/api/orchestration.db

[Install]
WantedBy=multi-user.target
UNIT
        sudo chown -R www-data:www-data $REMOTE_DIR/api/ &&
        sudo chmod 775 $REMOTE_DIR/api/ &&
        sudo systemctl daemon-reload &&
        sudo systemctl enable orchestration-api &&
        sudo systemctl restart orchestration-api &&
        echo 'API service restarted'
    "
else
    echo "[3/4] Skipping API deploy (use --api to include)"
fi

# 4. Verify
echo "[4/4] Verifying..."
sleep 1
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://thisminute.org/orchestration/" 2>/dev/null || echo "failed")
echo ""
if [ "$STATUS" = "200" ]; then
    echo "=== Live at: https://thisminute.org/orchestration ==="
else
    echo "=== Deploy complete (HTTP $STATUS) ==="
    echo "Check: https://thisminute.org/orchestration"
fi

if $DEPLOY_API; then
    API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://thisminute.org/orchestration/api/health" 2>/dev/null || echo "failed")
    if [ "$API_STATUS" = "200" ]; then
        echo "=== API healthy ==="
    else
        echo "=== API check: HTTP $API_STATUS (may need nginx proxy config) ==="
    fi
fi
