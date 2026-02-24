#!/usr/bin/env python3
"""Send a signed Cursor webhook request for testing replay protection.

Usage:
  CURSOR_WEBHOOK_SECRET=secret python send_cursor_webhook.py
"""
import os
import time
import uuid
import json
import hmac
import hashlib
import requests

SECRET = os.getenv("CURSOR_WEBHOOK_SECRET", "")
URL = os.getenv("CURSOR_WEBHOOK_URL", "http://127.0.0.1:9700/cursor/webhook")

if not SECRET:
    print("Warning: CURSOR_WEBHOOK_SECRET not set; request will be unsigned")

BODY = {"content": "テストメッセージ from send_cursor_webhook.py", "metadata": {"source": "cursor", "user": "mana"}}
raw = json.dumps(BODY).encode("utf-8")

ts = str(int(time.time()))
nonce = uuid.uuid4().hex

# compute signature over raw body (HMAC-SHA256)
if SECRET:
    mac = hmac.new(SECRET.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    sig = f"sha256={mac}"
else:
    sig = ""

headers = {
    "Content-Type": "application/json",
    "X-Cursor-Timestamp": ts,
    "X-Cursor-Nonce": nonce,
}
if sig:
    headers["X-Cursor-Signature"] = sig

print(f"POST {URL} headers={headers}")
resp = requests.post(URL, data=raw, headers=headers)
print(resp.status_code)
print(resp.text)
