#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS Control Panel — HTTP サーバー
=====================================
配置先: scripts/misc/manaos_dashboard_server.py

起動:
  python scripts/misc/manaos_dashboard_server.py [--port 9800]

ブラウザでアクセス:
  http://127.0.0.1:9800/

API:
  GET /api/status  → サービス一覧 (JSON)
  GET /api/events  → 直近50件イベント (JSON)
  GET /api/summary → events.summary.json の内容 (JSON)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

REPO_ROOT  = Path(__file__).parent.parent.parent
TOOLS_DIR  = REPO_ROOT / "tools"
STATIC_DIR = REPO_ROOT / "static"
SUMMARY_JSON = REPO_ROOT / "logs" / "events.summary.json"

sys.path.insert(0, str(TOOLS_DIR))
try:
    from events import read_events
except ImportError:
    def read_events(n=50): return []


def _run_manaosctl(*cmd_args: str) -> Any:
    """manaosctl を --json モードで呼び出して結果を返す。"""
    python = str(Path(sys.executable))
    manaosctl = str(TOOLS_DIR / "manaosctl.py")
    result = subprocess.run(
        [python, manaosctl, *cmd_args, "--json"],
        capture_output=True, text=True, timeout=30,
        cwd=str(REPO_ROOT),
    )
    try:
        return json.loads(result.stdout)
    except Exception:
        return {"error": result.stderr.strip()}


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # アクセスログ抑制

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status: int = 200) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = self.path.split("?")[0]

        if path == "/api/status":
            data = _run_manaosctl("status")
            self._send_json(data)

        elif path == "/api/events":
            events = read_events(n=50)
            self._send_json(events)

        elif path == "/api/summary":
            if SUMMARY_JSON.exists():
                try:
                    data = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
                except Exception:
                    data = {}
            else:
                data = {}
            self._send_json(data)

        elif path in ("/", "/index.html"):
            html_file = STATIC_DIR / "dashboard.html"
            if html_file.exists():
                self._send_html(html_file.read_text(encoding="utf-8"))
            else:
                self._send_html("<h1>dashboard.html not found</h1>", 404)

        else:
            self._send_json({"error": "not found"}, 404)


def main() -> None:
    parser = argparse.ArgumentParser(description="ManaOS Control Panel")
    parser.add_argument("--port", type=int, default=9800, help="ポート番号 (デフォルト: 9800)")
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", args.port), DashboardHandler)
    print(f"[ManaOS Control Panel] http://127.0.0.1:{args.port}/  (Ctrl+C で停止)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[停止]")


if __name__ == "__main__":
    main()
