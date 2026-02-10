#!/usr/bin/env bash
set -euo pipefail

# Quick PoC runner (Linux/macOS)
# Expects CURSOR_WEBHOOK_SECRET set in environment or .env sourced

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ -z "${CURSOR_WEBHOOK_SECRET:-}" ]; then
  echo "Warning: CURSOR_WEBHOOK_SECRET not set — running insecurely"
fi

echo "Starting webhook (background)..."
python manaos_integrations/cursor_webhook.py &
PID=$!
echo "Webhook PID=$PID"
sleep 1

echo "Sending signed request (1)"
python manaos_integrations/send_cursor_webhook.py || true
sleep 1

echo "Sending signed request (2) — should be accepted with new nonce"
python manaos_integrations/send_cursor_webhook.py || true
sleep 1

echo "Stopping webhook PID=$PID"
kill $PID || true

echo "Done"
