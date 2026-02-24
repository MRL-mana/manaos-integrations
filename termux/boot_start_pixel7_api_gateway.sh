#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Place this file at: ~/.termux/boot/boot_start_pixel7_api_gateway.sh
# Requires: Termux:Boot

# Export your token securely (example):
# export PIXEL7_API_TOKEN='...'

exec "$HOME/start_pixel7_api_gateway.sh" >>"$HOME/.pixel7_api_gateway.log" 2>&1
