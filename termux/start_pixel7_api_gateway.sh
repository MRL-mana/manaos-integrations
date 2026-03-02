#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

: "${PIXEL7_API_PORT:=5122}"
: "${PIXEL7_API_TAILSCALE_ONLY:=1}"
: "${PIXEL7_API_PROFILE:=core}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -z "${PIXEL7_API_TOKEN:-}" ]] && [[ -f "./api_token.txt" ]]; then
  PIXEL7_API_TOKEN="$(cat ./api_token.txt | tr -d '\r\n')"
  export PIXEL7_API_TOKEN
fi

if [[ -z "${PIXEL7_API_TOKEN:-}" ]]; then
  echo "ERROR: PIXEL7_API_TOKEN is not set" >&2
  exit 2
fi

if command -v termux-wake-lock >/dev/null 2>&1; then
  termux-wake-lock || true
fi

if ! python -c 'import fastapi, uvicorn' >/dev/null 2>&1; then
  echo "Installing Python deps (FastAPI stack; pydantic<2 to avoid Rust builds)..."
  python -m pip install --upgrade \
    "pydantic<2" \
    "fastapi<0.100" \
    "uvicorn<0.23"
fi

python -c 'import fastapi, uvicorn, pydantic; import sys; sys.exit(0 if int(pydantic.VERSION.split(".")[0]) < 2 else 1)' >/dev/null 2>&1 || {
  echo "ERROR: fastapi/uvicorn/pydantic install failed (need pydantic<2)" >&2
  exit 3
}

echo "Starting Pixel7 API Gateway on :${PIXEL7_API_PORT} (tailscale_only=${PIXEL7_API_TAILSCALE_ONLY}, profile=${PIXEL7_API_PROFILE})"
python "$SCRIPT_DIR/pixel7_api_gateway.py"
