#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS Moltbot ダッシュボード Webサーバー
http://localhost:5000 でダッシュボードを表示
"""

import os
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import webbrowser

class DashboardHandler(SimpleHTTPRequestHandler):
    """ダッシュボード用のリクエストハンドラー"""
    
    def do_GET(self):
        if self.path == '/' or self.path == '':
            self.path = '/moltbot_dashboard.html'
        return super().do_GET()


def start_dashboard_server(port=5000):
    """ダッシュボード Webサーバーを起動"""
    
    # ワークディレクトリを設定
    workspace = Path(__file__).parent
    os.chdir(workspace)
    
    print('╔═══════════════════════════════════════════════════════════╗')
    print('║  🌐 ManaOS Moltbot ダッシュボード Webサーバー           ║')
    print('╚═══════════════════════════════════════════════════════════╝')
    print()
    print(f"📍 ワークディレクトリ: {workspace}")
    print()
    
    # サーバーを起動
    server = HTTPServer(('127.0.0.1', port), DashboardHandler)
    
    print(f"✅ サーバー起動: http://127.0.0.1:{port}")
    print()
    print("🌐 ブラウザで自動的に開きます...")
    print()
    print("停止するには: Ctrl+C を押してください")
    print()
    
    # ブラウザを別スレッドで開く
    def open_browser():
        import time
        time.sleep(1)  # サーバー起動を待つ
        url = f'http://127.0.0.1:{port}/'
        print(f"📂 ブラウザを開く: {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"(ブラウザ自動起動に失敗: {e})")
    
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("✅ サーバーを停止しました")
        server.shutdown()


if __name__ == "__main__":
    start_dashboard_server(port=5000)
