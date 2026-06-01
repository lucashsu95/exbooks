#!/bin/bash
set -euo pipefail

# ── 設定 ────────────────────────────────────────────────────────
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE="docker compose -f $APP_DIR/docker-compose.yml"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:${PORT:-80}/health/}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-60}"
HEALTH_INTERVAL_SECONDS="${HEALTH_INTERVAL_SECONDS:-2}"

echo "========================================"
echo "  Exbook Deploy — $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# ── 建置 & 啟動 ────────────────────────────────────────────────
echo ""
echo "[1/3] Building images..."
$COMPOSE build --no-cache web

echo ""
echo "[2/3] Starting services..."
$COMPOSE up -d

echo ""
echo "[3/3] Checking health..."

check_health() {
  python3 - "$HEALTH_URL" <<'PY'
import json
import sys
import urllib.error
import urllib.request

url = sys.argv[1]

try:
    with urllib.request.urlopen(url, timeout=5) as response:
        payload = json.load(response)
        if response.status != 200:
            raise SystemExit(1)
        if payload.get("status") == "ok" and payload.get("database") == "ok":
            print("healthy")
            raise SystemExit(0)
        raise SystemExit(1)
except Exception as exc:
    print(f"unhealthy: {exc}", file=sys.stderr)
    raise SystemExit(1)
PY
}

deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))
while [ "$SECONDS" -lt "$deadline" ]; do
    if check_health >/dev/null 2>&1; then
        echo "✓ Health endpoint is ready: $HEALTH_URL"
        break
    fi
    sleep "$HEALTH_INTERVAL_SECONDS"
done

if ! check_health >/dev/null 2>&1; then
    echo "✗ Health check failed after ${HEALTH_TIMEOUT_SECONDS}s: $HEALTH_URL"
    $COMPOSE ps
    exit 1
fi

echo ""
echo "Deploy complete."
