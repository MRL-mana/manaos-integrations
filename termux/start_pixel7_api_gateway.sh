#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

: "${PIXEL7_API_PORT:=5122}"
: "${PIXEL7_API_TAILSCALE_ONLY:=1}"

if [[ -z "${PIXEL7_API_TOKEN:-}" ]]; then
  echo "ERROR: PIXEL7_API_TOKEN is not set" >&2
  exit 2
fi

cd "$HOME"

if command -v termux-wake-lock >/dev/null 2>&1; then
  termux-wake-lock || true
fi

python -m pip -q install --upgrade fastapi uvicorn >/dev/null 2>&1 || true

echo "Starting Pixel7 API Gateway on :${PIXEL7_API_PORT} (tailscale_only=${PIXEL7_API_TAILSCALE_ONLY})"
python "$HOME/pixel7_api_gateway.py"
