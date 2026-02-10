#!/bin/bash
# Open WebUI voice script injector

INDEX_FILE="/app/build/index.html"

# Check if script tag already exists
if ! grep -q "voice.js" "$INDEX_FILE"; then
    echo "[Remi] Injecting voice script into index.html..."
    sed -i 's|</head>|<script src="/static/voice.js"></script></head>|' "$INDEX_FILE"
    echo "[Remi] Voice script injected!"
else
    echo "[Remi] Voice script already present, skipping."
fi

# Execute the original entrypoint
cd /app/backend
exec bash start.sh
