#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VSCode 側の簡易メモリフック
- VSCode からローカル HTTP 経由でメモリ検索を呼び出すサンプル
- 実際は VSCode 拡張（TypeScript）を作るが、まずはローカルテスト用のHTTPサーバを提供
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from urllib.parse import urlparse, parse_qs
from mem0_integration import Mem0Integration

PORT = int(os.getenv('MANAOS_VSCODE_HOOK_PORT', '5210'))

mem = Mem0Integration()

class Handler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/search':
            qs = parse_qs(parsed.query)
            q = qs.get('q', [''])[0]
            results = mem.search_memories(q)
            self._set_headers()
            self.wfile.write(json.dumps({'results': results}, ensure_ascii=False).encode('utf-8'))
            return
        self._set_headers(404)
        self.wfile.write(json.dumps({'error': 'not found'}).encode('utf-8'))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/add':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            payload = json.loads(body.decode('utf-8') or '{}')
            text = payload.get('text')
            meta = payload.get('meta')
            mem.add_memory(text, metadata=meta)
            self._set_headers(201)
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
            return
        self._set_headers(404)
        self.wfile.write(json.dumps({'error': 'not found'}).encode('utf-8'))

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', PORT), Handler)
    print(f'VSCode memory hook listening on http://127.0.0.1:{PORT}')
    server.serve_forever()
