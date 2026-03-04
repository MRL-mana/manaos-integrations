#!/usr/bin/env python3
"""
Cognitive Bridge - AI間のトークンストリーム監視と記憶同期システム

このモジュールは、Trinity AIエージェント間のコミュニケーションを監視し、
重要な情報を記憶層に自動同期します。

主要機能:
- AI間のメッセージストリーム監視
- 重要イベントの検出と記録
- メモリ層への自動同期
- リアルタイム通信ブリッジ
"""

import json
import time
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import threading
import queue


class CognitiveBridge:
    """AI間の認知ブリッジシステム"""
    
    def __init__(self, workspace_path: str = "/root/trinity_workspace"):
        self.workspace = Path(workspace_path)
        self.shared_dir = self.workspace / "shared"
        self.memory_dir = self.shared_dir / "memory"
        self.logs_dir = self.workspace / "logs"
        
        # データベース接続
        self.db_path = self.shared_dir / "cognitive_memory.db"
        self.init_database()
        
        # メッセージキュー
        self.message_queue = queue.Queue()
        
        # 監視スレッド
        self.running = False
        self.monitor_thread = None
        
    def init_database(self):
        """認知記憶データベースの初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # メッセージストリームテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_stream (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source_agent TEXT NOT NULL,
                target_agent TEXT,
                message_type TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 5,
                processed BOOLEAN DEFAULT 0
            )
        """)
        
        # 認知イベントテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cognitive_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                agent TEXT NOT NULL,
                description TEXT,
                metadata TEXT,
                reflection_score REAL
            )
        """)
        
        # 記憶同期ログ
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                sync_type TEXT NOT NULL,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                items_synced INTEGER,
                status TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        
    def start_monitoring(self):
        """監視スレッドを開始"""
        if self.running:
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("[INFO] Cognitive Bridge monitoring started")
        
    def stop_monitoring(self):
        """監視スレッドを停止"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("[INFO] Cognitive Bridge monitoring stopped")
        
    def _monitor_loop(self):
        """メインモニタリングループ"""
        while self.running:
            try:
                # tasks.jsonの変更を監視
                self._check_task_updates()
                
                # sync_status.jsonの変更を監視
                self._check_sync_status()
                
                # キューからメッセージを処理
                self._process_message_queue()
                
                time.sleep(1)  # 1秒ごとにチェック
                
            except Exception as e:
                print(f"[ERROR] Monitor loop error: {e}")
                
    def _check_task_updates(self):
        """タスク更新の監視"""
        tasks_file = self.shared_dir / "tasks.json"
        if not tasks_file.exists():
            return
            
        try:
            with open(tasks_file, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
                
            # 新しいタスクや更新されたタスクを検出
            for task in tasks.get('tasks', []):
                self._process_task_event(task)
                
        except Exception as e:
            print(f"[ERROR] Task check error: {e}")
            
    def _check_sync_status(self):
        """同期状態の監視"""
        sync_file = self.shared_dir / "sync_status.json"
        if not sync_file.exists():
            return
            
        try:
            with open(sync_file, 'r', encoding='utf-8') as f:
                sync_data = json.load(f)
                
            # エージェントの状態変化を検出
            for agent, status in sync_data.get('agents', {}).items():
                self._process_agent_status(agent, status)
                
        except Exception as e:
            print(f"[ERROR] Sync check error: {e}")
            
    def _process_message_queue(self):
        """メッセージキューの処理"""
        try:
            while not self.message_queue.empty():
                message = self.message_queue.get_nowait()
                self._store_message(message)
                self.message_queue.task_done()
        except queue.Empty:
            pass
            
    def _process_task_event(self, task: Dict):
        """タスクイベントの処理"""
        # 重要度判定
        importance = self._calculate_importance(task)
        
        if importance >= 7:  # 重要度7以上のみ記録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO cognitive_events 
                (timestamp, event_type, agent, description, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                'task_update',
                task.get('assigned_to', 'unknown'),
                task.get('title', 'Untitled'),
                json.dumps(task)
            ))
            
            conn.commit()
            conn.close()
            
    def _process_agent_status(self, agent: str, status: str):
        """エージェントステータスの処理"""
        # ステータス変化を記録
        memory_file = self.memory_dir / f"{agent}_status.json"
        
        status_data = {
            'timestamp': datetime.now().isoformat(),
            'agent': agent,
            'status': status
        }
        
        # ファイルに記録
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2)
            
    def _calculate_importance(self, task: Dict) -> int:
        """タスクの重要度を計算"""
        importance = 5  # デフォルト
        
        # 優先度による重み付け
        priority = task.get('priority', 'medium')
        if priority == 'high':
            importance += 3
        elif priority == 'critical':
            importance += 5
            
        # キーワードによる重み付け
        keywords = ['bug', 'error', 'critical', 'urgent', 'security']
        title = task.get('title', '').lower()
        for keyword in keywords:
            if keyword in title:
                importance += 2
                break
                
        return min(importance, 10)  # 最大10
        
    def _store_message(self, message: Dict):
        """メッセージをデータベースに保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO message_stream 
            (timestamp, source_agent, target_agent, message_type, content, importance)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            message.get('timestamp', datetime.now().isoformat()),
            message.get('source', 'unknown'),
            message.get('target'),
            message.get('type', 'message'),
            message.get('content', ''),
            message.get('importance', 5)
        ))
        
        conn.commit()
        conn.close()
        
    def send_message(self, source: str, target: Optional[str], 
                    message_type: str, content: str, importance: int = 5):
        """メッセージを送信（キューに追加）"""
        message = {
            'timestamp': datetime.now().isoformat(),
            'source': source,
            'target': target,
            'type': message_type,
            'content': content,
            'importance': importance
        }
        self.message_queue.put(message)
        
    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """最近の認知イベントを取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, event_type, agent, description, metadata
            FROM cognitive_events
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        events = []
        for row in cursor.fetchall():
            events.append({
                'timestamp': row[0],
                'event_type': row[1],
                'agent': row[2],
                'description': row[3],
                'metadata': json.loads(row[4]) if row[4] else None
            })
            
        conn.close()
        return events
        
    def sync_to_memory(self, source: str, data: Dict) -> bool:
        """データをメモリ層に同期"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            memory_file = self.memory_dir / f"sync_{source}_{timestamp}.json"
            
            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            # 同期ログに記録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO sync_log 
                (timestamp, sync_type, source, target, items_synced, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                'manual_sync',
                source,
                'memory_layer',
                len(data.get('items', [])),
                'success'
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Sync failed: {e}")
            return False
            
    def get_stats(self) -> Dict:
        """統計情報を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # メッセージ数
        cursor.execute("SELECT COUNT(*) FROM message_stream")
        message_count = cursor.fetchone()[0]
        
        # イベント数
        cursor.execute("SELECT COUNT(*) FROM cognitive_events")
        event_count = cursor.fetchone()[0]
        
        # 同期回数
        cursor.execute("SELECT COUNT(*) FROM sync_log WHERE status = 'success'")
        sync_count = cursor.fetchone()[0]
        
        # エージェント別メッセージ数
        cursor.execute("""
            SELECT source_agent, COUNT(*) 
            FROM message_stream 
            GROUP BY source_agent
        """)
        agent_messages = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total_messages': message_count,
            'total_events': event_count,
            'successful_syncs': sync_count,
            'agent_messages': agent_messages,
            'status': 'online' if self.running else 'offline'
        }


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Cognitive Bridge')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--test', action='store_true', help='Run test mode')
    
    args = parser.parse_args()
    
    bridge = CognitiveBridge()
    
    if args.test:
        # テストモード
        print("=== Cognitive Bridge Test ===")
        print(f"Database: {bridge.db_path}")
        print(f"Memory Dir: {bridge.memory_dir}")
        
        bridge.start_monitoring()
        
        try:
            bridge.send_message('remi', 'luna', 'task_assign', 
                               'Test task assignment', importance=8)
            time.sleep(2)
            
            stats = bridge.get_stats()
            print("\nStats:")
            print(json.dumps(stats, indent=2))
            
            events = bridge.get_recent_events(limit=10)
            print(f"\nRecent Events: {len(events)}")
            for event in events[:3]:
                print(f"  - [{event['agent']}] {event['description']}")
                
        finally:
            bridge.stop_monitoring()
            print("\nBridge stopped")
    else:
        # Daemonモード（デフォルト）
        print("🚀 Cognitive Bridge starting...")
        print(f"Database: {bridge.db_path}")
        
        bridge.start_monitoring()
        
        try:
            print("✅ Cognitive Bridge running (Ctrl+C to stop)")
            while True:
                time.sleep(60)
                # 定期的に統計をログ出力
                stats = bridge.get_stats()
                if stats['total_messages'] % 10 == 0 and stats['total_messages'] > 0:
                    print(f"[INFO] Messages: {stats['total_messages']}, Events: {stats['total_events']}")
        except KeyboardInterrupt:
            print("\n⏹️  Shutting down...")
        finally:
            bridge.stop_monitoring()
            print("👋 Cognitive Bridge stopped")


if __name__ == '__main__':
    main()


