#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
母艦でリアルタイム音声クライアント（realtime_client.html）を配信する簡易HTTPサーバー。
Pixel 7 のブラウザで http://<母艦IP>:8766 を開き、母艦の WebSocket (8765) に接続して利用する。

使い方:
  母艦で:
    1. python voice_realtime_streaming.py   # または start_voice_secretary 等で WebSocket 8765 を起動
    2. python scripts/voice/serve_voice_client.py
  Pixel 7 で:
    http://<母艦のIP>:8766 を開く → URL に ws://<母艦のIP>:8765 を入力して「開始」
"""
import os
import sys
from pathlib import Path

# このスクリプトのディレクトリを基準に
SCRIPT_DIR = Path(__file__).resolve().parent
CLIENT_HTML = SCRIPT_DIR / "realtime_client.html"
PORT = int(os.getenv("VOICE_CLIENT_HTTP_PORT", "8766"))
HOST = os.getenv("VOICE_CLIENT_HTTP_HOST", "0.0.0.0")


def main():
    if not CLIENT_HTML.exists():
        print(f"Error: {CLIENT_HTML} not found.", file=sys.stderr)
        sys.exit(1)

    try:
        from http.server import HTTPServer, BaseHTTPRequestHandler
    except ImportError:
        import http.server as http
        HTTPServer = http.HTTPServer
        BaseHTTPRequestHandler = http.BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.strip("/") or "realtime_client.html"
            if path == "realtime_client.html" or path == "":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(CLIENT_HTML.read_bytes())
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            print(f"[voice client] {args[0]}")

    server = HTTPServer((HOST, PORT), Handler)
    print("Voice realtime client: http://{}:{} (open this on Pixel 7)".format(HOST, PORT))
    print("WebSocket (mothership): ws://<this_host>:8765")
    server.serve_forever()


if __name__ == "__main__":
    main()
