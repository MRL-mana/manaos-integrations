#!/usr/bin/env python3
# Claude出力ファイル監視・自動送信システム

import os
import time
import json
import requests
import logging
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

class ClaudeFileHandler(FileSystemEventHandler):
    """Claude出力ファイル監視ハンドラー"""
    
    def __init__(self, mcp_url="http://localhost:8421/receive/claude"):
        self.mcp_url = mcp_url
        self.processed_files = set()
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.expanduser('~/mrl-mcp/logs/claude_watchdog.log')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def on_created(self, event):
        """ファイル作成時の処理"""
        if not event.is_directory and event.src_path.endswith('.txt'):
            self.logger.info(f"新しいClaudeファイルを検出: {event.src_path}")
            # 少し待ってから処理（ファイル書き込み完了を待つ）
            threading.Timer(2.0, self.process_file, args=[event.src_path]).start()
    
    def on_modified(self, event):
        """ファイル変更時の処理"""
        if not event.is_directory and event.src_path.endswith('.txt'):
            # 既に処理済みでない場合のみ処理
            if event.src_path not in self.processed_files:
                self.logger.info(f"Claudeファイルが更新されました: {event.src_path}")
                threading.Timer(1.0, self.process_file, args=[event.src_path]).start()
    
    def process_file(self, file_path):
        """ファイルを処理してMCPに送信"""
        try:
            # ファイル読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # ファイル名から情報を抽出
            filename = os.path.basename(file_path)
            timestamp = datetime.now().isoformat()
            
            # MCPに送信するデータ
            data = {
                "content": content,
                "source": "claude_desktop",
                "metadata": {
                    "filename": filename,
                    "file_path": file_path,
                    "detected_at": timestamp,
                    "type": "claude_export"
                }
            }
            
            # MCPサーバーに送信
            response = requests.post(
                self.mcp_url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"✅ ClaudeファイルをMCPに送信成功: {filename}")
                self.processed_files.add(file_path)
                
                # 成功したファイルを移動（オプション）
                self.move_to_processed(file_path)
            else:
                self.logger.error(f"❌ MCP送信失敗: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.logger.error(f"❌ ファイル処理エラー: {str(e)}")
    
    def move_to_processed(self, file_path):
        """処理済みファイルを移動"""
        try:
            processed_dir = os.path.expanduser("~/claude_exports/processed")
            os.makedirs(processed_dir, exist_ok=True)
            
            filename = os.path.basename(file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"processed_{timestamp}_{filename}"
            new_path = os.path.join(processed_dir, new_filename)
            
            os.rename(file_path, new_path)
            self.logger.info(f"📁 ファイルを移動: {file_path} → {new_path}")
            
  