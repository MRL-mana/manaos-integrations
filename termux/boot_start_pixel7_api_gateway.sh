#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Place this file at: ~/.termux/boot/boot_start_pixel7_api_gateway.sh
# Requires: Termux:Boot

# Export your token securely (example):
# export PIXEL7_API_TOKEN='...'

# Marker log (best-effort) so we can confirm Termux:Boot actually ran.
MARK_DIR="/storage/emulated/0/Download"
TS="$(date '+%Y-%m-%d %H:%M:%S' 2>/dev/null || true)"
{
	echo "[$TS] Termux:Boot: start"
	echo "HOME=$HOME"
	ls -l "$HOME/start_pixel7_api_gateway.sh" 2>/dev/null || true
} >>"$MARK_DIR/pixel7_termux_boot.log" 2>/dev/null || true

# Start gateway in background; keep stdout/stderr in $HOME log.
(
	"$HOME/start_pixel7_api_gateway.sh" >>"$HOME/.pixel7_api_gateway.log" 2>&1
) &

echo "[$TS] Termux:Boot: launched" >>"$MARK_DIR/pixel7_termux_boot.log" 2>/dev/null || true
