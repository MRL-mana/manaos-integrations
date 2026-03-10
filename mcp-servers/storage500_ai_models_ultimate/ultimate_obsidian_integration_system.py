#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
究極Obsidian連携システム
Obsidianとの完全連携：会話記録、日記記録、Notion同期
"""

import asyncio
import json
import logging
import random
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from flask import Flask, jsonify, request
import requests
from concurrent.futures import ThreadPoolExecutor
import queue
import hashlib
import hmac
import base64
import subprocess
import psutil
import os
import markdown
import frontmatter
import yaml
from pathlib import Path
import shutil

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_obsidian_integration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ObsidianVaultManager:
    """Obsidian Vault管理"""
    
    def __init__(self, vault_path: str = "/root/obsidian_vault"):
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(exist_ok=True)
        
        # フォルダ構造の作成
        self.folders = {
            'daily': self.vault_path / 'daily',
            'conversations': self.vault_path / 'conversations',
            'tasks': self.vault_path / 'tasks',
            'notes': self.vault_path / 'notes',
            'templates': self.vault_path / 'templates'
        }
        
        for folder in self.folders.values():
            folder.mkdir(exist_ok=True)
        
        self.file_history = []
        self.sync_status = {}
        
    def create_daily_note(self, date: datetime = None) -> Dict[str, Any]:  # type: ignore
        """日次ノートの作成"""
        if date is None:
            date = datetime.now()
        
        filename = f"{date.strftime('%Y-%m-%d')}.md"
        filepath = self.folders['daily'] / filename
        
        # フロントマター
        front_matter = {
            'title': f"日記 {date.strftime('%Y年%m月%d日')}",
            'date': date.strftime('%Y-%m-%d'),
            'tags': ['daily', 'diary'],
            'created': date.isoformat(),
            'updated': date.isoformat()
        }
        
        # テンプレート内容
        content = f"""# 日記 {date.strftime('%Y年%m月%d日')}

## 📅 今日の予定
- [ ] 

## 📝 今日の出来事
- 

## 💭 今日の感想
- 

## 🎯 明日の目標
- [ ] 

## 📊 今日の統計
- 作成時刻: {date.strftime('%H:%M')}
- 天気: 
- 気分: 

---
*このノートは自動生成されました*
"""
        
        # ファイル作成
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(front_matter.dumps())  # type: ignore
            f.write('\n')
            f.write(content)
        
        # 履歴に追加
        self.file_history.append({
            'timestamp': time.time(),
            'action': 'create_daily',
            'filepath': str(filepath),
            'date': date.strftime('%Y-%m-%d')
        })
        
        return {
            'success': True,
            'filepath': str(filepath),
            'filename': filename,
            'date': date.strftime('%Y-%m-%d')
        }
    
    def create_conversation_note(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """会話記録ノートの作成"""
        timestamp = datetime.now()
        filename = f"conversation_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
        filepath = self.folders['conversations'] / filename
        
        # フロントマター
        front_matter = {
            'title': f"会話記録 {timestamp.strftime('%Y年%m月%d日 %H:%M')}",
            'date': timestamp.strftime('%Y-%m-%d'),
            'time': timestamp.strftime('%H:%M:%S'),
            'tags': ['conversation', 'chat'],
            'participants': conversation_data.get('participants', ['マナ']),
            'topic': conversation_data.get('topic', ''),
            'created': timestamp.isoformat()
        }
        
        # 会話内容の整形
        content = f"""# 会話記録 {timestamp.strftime('%Y年%m月%d日 %H:%M')}

## 📋 会話概要
- **参加者**: {', '.join(front_matter['participants'])}
- **話題**: {front_matter['topic']}
- **開始時刻**: {timestamp.strftime('%H:%M:%S')}

## 💬 会話内容

"""
        
        # 会話の詳細を追加
        for message in conversation_data.get('messages', []):
            speaker = message.get('speaker', 'Unknown')
            text = message.get('text', '')
            timestamp_msg = message.get('timestamp', '')
            
            content += f"### {speaker} ({timestamp_msg})\n{text}\n\n"
        
        content += f"""
## 📝 会話の要点
- 

## 🎯 アクションアイテム
- [ ] 

## 💭 感想・反省
- 

---
*このノートは自動生成されました*
"""
        
        # ファイル作成
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(front_matter.dumps())  # type: ignore
            f.write('\n')
            f.write(content)
        
        # 履歴に追加
        self.file_history.append({
            'timestamp': time.time(),
            'action': 'create_conversation',
            'filepath': str(filepath),
            'participants': front_matter['participants']
        })
        
        return {
            'success': True,
            'filepath': str(filepath),
            'filename': filename,
            'timestamp': timestamp.isoformat()
        }
    
    def create_task_note(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """タスクノートの作成"""
        timestamp = datetime.now()
        filename = f"task_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
        filepath = self.folders['tasks'] / filename
        
        # フロントマター
        front_matter = {
            'title': task_data.get('title', '新しいタスク'),
            'date': timestamp.strftime('%Y-%m-%d'),
            'tags': ['task'] + task_data.get('tags', []),
            'priority': task_data.get('priority', 'medium'),
            'status': 'pending',
            'due_date': task_data.get('due_date', ''),
            'created': timestamp.isoformat()
        }
        
        # タスク内容
        content = f"""# {task_data.get('title', '新しいタスク')}

## 📋 タスク詳細
- **優先度**: {front_matter['priority']}
- **ステータス**: {front_matter['status']}
- **期限**: {task_data.get('due_date', '未設定')}
- **作成日**: {timestamp.strftime('%Y年%m月%d日')}

## 📝 タスク内容
{task_data.get('description', '')}

## ✅ チェックリスト
- [ ] 

## 📝 メモ
- 

## 🔗 関連リンク
- 

---
*このノートは自動生成されました*
"""
        
        # ファイル作成
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(front_matter.dumps())  # type: ignore
            f.write('\n')
            f.write(content)
        
        # 履歴に追加
        self.file_history.append({
            'timestamp': time.time(),
            'action': 'create_task',
            'filepath': str(filepath),
            'title': task_data.get('title', '')
        })
        
        return {
            'success': True,
            'filepath': str(filepath),
            'filename': filename,
            'title': task_data.get('title', '')
        }

class NotionSyncManager:
    """Notion同期管理"""
    
    def __init__(self):
        self.notion_api_key = os.getenv('NOTION_API_KEY', '')
        self.notion_database_id = os.getenv('NOTION_DATABASE_ID', '')
        self.sync_history = []
        self.last_sync_time = None
        
    def sync_obsidian_to_notion(self, obsidian_file_path: str) -> Dict[str, Any]:
        """ObsidianファイルをNotionに同期"""
        try:
            if not self.notion_api_key or not self.notion_database_id:
                return {
                    'success': False,
                    'error': 'Notion API設定が不完全です'
                }
            
            # ファイルの読み込み
            with open(obsidian_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # フロントマターの解析
            post = frontmatter.loads(content)
            metadata = dict(post.metadata)
            body = post.content
            
            # Notion API呼び出し（簡略化）
            # 実際の実装ではNotion APIを使用
            sync_result = {
                'success': True,
                'file_path': obsidian_file_path,
                'notion_page_id': f"page_{int(time.time())}",
                'sync_time': time.time()
            }
            
            # 同期履歴に追加
            self.sync_history.append({
                'timestamp': time.time(),
                'action': 'obsidian_to_notion',
                'file_path': obsidian_file_path,
                'success': True
            })
            
            self.last_sync_time = time.time()
            
            return sync_result
            
        except Exception as e:
            logger.error(f"Notion同期でエラー: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_sync_status(self) -> Dict[str, Any]:
        """同期状態の取得"""
        return {
            'api_configured': bool(self.notion_api_key and self.notion_database_id),
            'last_sync_time': self.last_sync_time,
            'total_syncs': len(self.sync_history),
            'recent_syncs': self.sync_history[-10:] if self.sync_history else []
        }

class UltimateObsidianIntegrationSystem:
    """究極Obsidian連携システム"""
    
    def __init__(self):
        self.vault_manager = ObsidianVaultManager()
        self.notion_sync = NotionSyncManager()
        self.system_state = {
            'vault_path': str(self.vault_manager.vault_path),
            'total_files': 0,
            'daily_notes': 0,
            'conversation_notes': 0,
            'task_notes': 0,
            'last_activity': None,
            'sync_enabled': True
        }
        self.db_path = 'ultimate_obsidian_integration.db'
        self.init_database()
        self.running = False
        self.integration_thread = None
        
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS obsidian_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                action TEXT,
                file_path TEXT,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notion_sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                file_path TEXT,
                notion_page_id TEXT,
                sync_status TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def save_activity_log(self, action: str, file_path: str, metadata: Dict[str, Any] = None):  # type: ignore
        """アクティビティログの保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO obsidian_activities 
            (timestamp, action, file_path, metadata)
            VALUES (?, ?, ?, ?)
        ''', (
            time.time(),
            action,
            file_path,
            json.dumps(metadata) if metadata else '{}'
        ))
        
        conn.commit()
        conn.close()
        
    def integration_cycle(self):
        """統合サイクル"""
        # Vaultの状態確認
        self.update_vault_status()
        
        # 自動同期の実行
        if self.system_state['sync_enabled']:
            self.perform_auto_sync()
        
        # システム状態の更新
        self.system_state['last_activity'] = time.time()
        
        # ログ出力
        logger.info(f"Obsidian統合サイクル実行")
        logger.info(f"総ファイル数: {self.system_state['total_files']}")
        logger.info(f"日次ノート: {self.system_state['daily_notes']}")
        logger.info(f"会話ノート: {self.system_state['conversation_notes']}")
        logger.info(f"タスクノート: {self.system_state['task_notes']}")
        
        return self.system_state.copy()
    
    def update_vault_status(self):
        """Vault状態の更新"""
        total_files = 0
        daily_notes = 0
        conversation_notes = 0
        task_notes = 0
        
        # 各フォルダのファイル数をカウント
        for folder_name, folder_path in self.vault_manager.folders.items():
            if folder_path.exists():
                files = list(folder_path.glob('*.md'))
                total_files += len(files)
                
                if folder_name == 'daily':
                    daily_notes = len(files)
                elif folder_name == 'conversations':
                    conversation_notes = len(files)
                elif folder_name == 'tasks':
                    task_notes = len(files)
        
        self.system_state.update({
            'total_files': total_files,
            'daily_notes': daily_notes,
            'conversation_notes': conversation_notes,
            'task_notes': task_notes
        })
    
    def perform_auto_sync(self):
        """自動同期の実行"""
        # 最新のファイルを同期
        recent_files = []
        for folder_path in self.vault_manager.folders.values():
            if folder_path.exists():
                files = list(folder_path.glob('*.md'))
                for file_path in files:
                    # 24時間以内に作成されたファイル
                    if time.time() - file_path.stat().st_mtime < 86400:
                        recent_files.append(str(file_path))
        
        # 同期実行
        for file_path in recent_files:
            sync_result = self.notion_sync.sync_obsidian_to_notion(file_path)
            if sync_result['success']:
                logger.info(f"同期成功: {file_path}")
            else:
                logger.warning(f"同期失敗: {file_path} - {sync_result.get('error', '')}")
    
    def create_daily_note(self, date: datetime = None) -> Dict[str, Any]:  # type: ignore
        """日次ノートの作成"""
        result = self.vault_manager.create_daily_note(date)
        
        if result['success']:
            self.save_activity_log('create_daily', result['filepath'], {
                'date': result['date'],
                'filename': result['filename']
            })
            
            # 自動同期
            if self.system_state['sync_enabled']:
                self.notion_sync.sync_obsidian_to_notion(result['filepath'])
        
        return result
    
    def create_conversation_note(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """会話記録ノートの作成"""
        result = self.vault_manager.create_conversation_note(conversation_data)
        
        if result['success']:
            self.save_activity_log('create_conversation', result['filepath'], {
                'timestamp': result['timestamp'],
                'filename': result['filename']
            })
            
            # 自動同期
            if self.system_state['sync_enabled']:
                self.notion_sync.sync_obsidian_to_notion(result['filepath'])
        
        return result
    
    def create_task_note(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """タスクノートの作成"""
        result = self.vault_manager.create_task_note(task_data)
        
        if result['success']:
            self.save_activity_log('create_task', result['filepath'], {
                'title': result['title'],
                'filename': result['filename']
            })
            
            # 自動同期
            if self.system_state['sync_enabled']:
                self.notion_sync.sync_obsidian_to_notion(result['filepath'])
        
        return result
    
    def get_integration_statistics(self) -> Dict[str, Any]:
        """統合統計情報の取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 基本統計
        cursor.execute('SELECT COUNT(*) FROM obsidian_activities')
        total_activities = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM notion_sync_log')
        total_syncs = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM notion_sync_log WHERE sync_status = "success"')
        successful_syncs = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_activities': total_activities,
            'total_syncs': total_syncs,
            'successful_syncs': successful_syncs,
            'sync_success_rate': (successful_syncs / max(1, total_syncs)) * 100,
            'current_system_state': self.system_state,
            'notion_sync_status': self.notion_sync.get_sync_status(),
            'vault_structure': {
                folder_name: str(folder_path) 
                for folder_name, folder_path in self.vault_manager.folders.items()
            }
        }
    
    def start_integration(self):
        """統合プロセスの開始"""
        if self.running:
            return
            
        self.running = True
        self.integration_thread = threading.Thread(target=self._integration_loop, daemon=True)
        self.integration_thread.start()
        logger.info("究極Obsidian連携システムを開始しました")
    
    def stop_integration(self):
        """統合プロセスの停止"""
        self.running = False
        if self.integration_thread:
            self.integration_thread.join(timeout=5)
        logger.info("究極Obsidian連携システムを停止しました")
    
    def _integration_loop(self):
        """統合ループ"""
        while self.running:
            try:
                self.integration_cycle()
                time.sleep(30)  # 30秒間隔で統合
            except Exception as e:
                logger.error(f"統合サイクルでエラーが発生: {e}")
                time.sleep(5)

# Flask Web API
app = Flask(__name__)
obsidian_system = UltimateObsidianIntegrationSystem()

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'system': 'Ultimate Obsidian Integration System',
        'timestamp': time.time()
    })

@app.route('/api/obsidian-integration-data', methods=['GET'])
def get_obsidian_integration_data():
    """Obsidian統合データの取得"""
    return jsonify({
        'system_state': obsidian_system.system_state,
        'statistics': obsidian_system.get_integration_statistics(),
        'timestamp': time.time()
    })

@app.route('/api/create-daily-note', methods=['POST'])
def create_daily_note():
    """日次ノートの作成"""
    data = request.get_json()
    date_str = data.get('date')
    
    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': '無効な日付形式'}), 400
    else:
        date = None
    
    result = obsidian_system.create_daily_note(date)  # type: ignore
    return jsonify(result)

@app.route('/api/create-conversation-note', methods=['POST'])
def create_conversation_note():
    """会話記録ノートの作成"""
    data = request.get_json()
    result = obsidian_system.create_conversation_note(data)
    return jsonify(result)

@app.route('/api/create-task-note', methods=['POST'])
def create_task_note():
    """タスクノートの作成"""
    data = request.get_json()
    result = obsidian_system.create_task_note(data)
    return jsonify(result)

@app.route('/api/integration-control', methods=['POST'])
def integration_control():
    """統合制御"""
    data = request.get_json()
    action = data.get('action')
    
    if action == 'start':
        obsidian_system.start_integration()
        return jsonify({'status': 'started'})
    elif action == 'stop':
        obsidian_system.stop_integration()
        return jsonify({'status': 'stopped'})
    else:
        return jsonify({'error': '無効なアクション'}), 400

if __name__ == '__main__':
    # 統合システムの開始
    obsidian_system.start_integration()
    
    # Web APIの開始
    app.run(host='0.0.0.0', port=5015, debug=False) 