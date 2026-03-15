#!/usr/bin/env bash
# Deploy Main Menu to thisminute.org/mainmenu
# Served directly by nginx as static files (same pattern as /rhizome).
#
# First deploy: run with --setup to create remote dir and nginx config.
# Usage: bash deploy.sh [--setup]
set -euo pipefail

INSTANCE="thisminute"
ZONE="us-central1-a"
REMOTE_DIR="/opt/mainmenu"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# First-time setup: create dir and add nginx location block
if [[ "${1:-}" == "--setup" ]]; then
    echo "=== First-time setup ==="

    echo "[1/3] Creating remote directory..."
    gcloud compute ssh "$INSTANCE" --zone="$ZONE" --command="sudo mkdir -p $REMOTE_DIR/api/v1 && sudo chown -R \$(whoami) $REMOTE_DIR"

    echo "[2/3] Adding nginx location block..."
    gcloud compute ssh "$INSTANCE" --zone="$ZONE" --command="
        if ! grep -q '/mainmenu' /etc/nginx/sites-available/thisminute; then
            sudo sed -i '/location \/static\//i\\
    # Main Menu - static software directory\\
    location /mainmenu/ {\\
        alias /opt/mainmenu/;\\
        index index.html;\\
        try_files \\\$uri \\\$uri/ /mainmenu/index.html;\\
    }\\
' /etc/nginx/sites-available/thisminute
            sudo nginx -t && sudo systemctl reload nginx
            echo 'Nginx config updated.'
        else
            echo 'Nginx location block already exists.'
        fi
    "

    echo "[3/3] Setup complete. Now run: bash deploy.sh"
    exit 0
fi

echo "=== Deploying Main Menu ==="

# 1. Build all outputs
echo "[1/3] Building..."
python "$SCRIPT_DIR/build.py"

# 2. Upload files to server
echo "[2/3] Uploading files..."
gcloud compute scp \
    "$SCRIPT_DIR/index.html" \
    "$SCRIPT_DIR/data.js" \
    "$SCRIPT_DIR/taxonomy.js" \
    "$SCRIPT_DIR/schema.json" \
    "$SCRIPT_DIR/llms.txt" \
    "$SCRIPT_DIR/llms-full.txt" \
    "$INSTANCE:$REMOTE_DIR/" --zone="$ZONE"

gcloud compute scp \
    "$SCRIPT_DIR/api/v1/catalog.json" \
    "$SCRIPT_DIR/api/v1/categories.json" \
    "$INSTANCE:$REMOTE_DIR/api/v1/" --zone="$ZONE"

# 3. Verify
echo "[3/3] Verifying..."
sleep 1
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://thisminute.org/mainmenu/" 2>/dev/null || echo "failed")
echo ""
if [ "$STATUS" = "200" ]; then
    echo "=== Live at: https://thisminute.org/mainmenu ==="
else
    echo "=== Deploy complete (HTTP $STATUS) ==="
    echo "Check: https://thisminute.org/mainmenu"
fi
