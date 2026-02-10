#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursorチャット履歴統合ビューア（修正版）
すべてのワークスペースのチャット履歴を検索・閲覧できるツール
"""
import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import argparse

class CursorChatHistoryViewer:
    """Cursorチャット履歴ビューア"""
    
    def __init__(self):
        self.appdata = os.getenv('APPDATA')
        if not self.appdata:
            raise RuntimeError("APPDATA環境変数が見つかりません")
        
        self.workspace_storage = Path(self.appdata) / "Cursor" / "User" / "workspaceStorage"
        self.chat_history_cache = []
    
    def scan_all_workspaces(self) -> List[Dict[str, Any]]:
        """すべてのワークスペースのチャット履歴をスキャン"""
        if not self.workspace_storage.exists():
            return []
        
        all_chats = []
        
        for ws_dir in self.workspace_storage.iterdir():
            if not ws_dir.is_dir():
                continue
            
            db_path = ws_dir / "state.vscdb"
            if not db_path.exists():
                continue
            
            try:
                chats = self._extract_chats_from_db(db_path, ws_dir.name)
                all_chats.extend(chats)
            except Exception as e:
                print(f"⚠️  ワークスペース {ws_dir.name} の読み込みエラー: {e}")
                continue
        
        # 日時でソート（新しい順）
        all_chats.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        self.chat_history_cache = all_chats
        return all_chats
    
    def _extract_chats_from_db(self, db_path: Path, workspace_id: str) -> List[Dict[str, Any]]:
        """SQLiteデータベースからチャット履歴を抽出"""
        chats = []
        
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # チャットデータのキーを検索
            cursor.execute("""
                SELECT key, value 
                FROM ItemTable 
                WHERE key LIKE 'workbench.panel.aichat.%.chatdata'
                ORDER BY key
            """)
            
            for row in cursor.fetchall():
                key = row['key']
                value = row['value']
                
                try:
                    # BLOBを文字列に変換
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    
                    # JSON文字列をパース
                    if isinstance(value, str):
                        data = json.loads(value)
                    else:
                        data = value
                    
                    # チャットデータを抽出
                    chat_data = self._parse_chat_data(key, data, workspace_id)
                    if chat_data:
                        chats.extend(chat_data if isinstance(chat_data, list) else [chat_data])
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    # JSONでない場合はスキップ
                    continue
                except Exception as e:
                    # その他のエラーは無視
                    continue
            
            conn.close()
        except Exception as e:
            print(f"⚠️  データベース読み込みエラー ({db_path}): {e}")
        
        return chats
    
    def _parse_chat_data(self, key: str, data: Any, workspace_id: str) -> Optional[List[Dict[str, Any]]]:
        """チャットデータをパース"""
        chats = []
        
        # データ構造に応じてチャットを抽出
        if isinstance(data, dict):
            # messages配列を探す
            if 'messages' in data:
                for msg in data['messages']:
                    if isinstance(msg, dict):
                        chats.append({
                            'workspace_id': workspace_id,
                            'chat_id': key.split('.')[-2] if '.' in key else 'unknown',
                            'role': msg.get('role', msg.get('author', {}).get('role', 'unknown')),
                            'content': msg.get('content', msg.get('text', '')),
                            'timestamp': msg.get('timestamp', msg.get('createdAt', '')),
                            'raw': msg
                        })
            elif 'content' in data or 'text' in data:
                # 単一メッセージ
                chats.append({
                    'workspace_id': workspace_id,
                    'chat_id': key.split('.')[-2] if '.' in key else 'unknown',
                    'role': data.get('role', data.get('author', {}).get('role', 'unknown')),
                    'content': data.get('content', data.get('text', '')),
                    'timestamp': data.get('timestamp', data.get('createdAt', '')),
                    'raw': data
                })
            elif isinstance(data, list):
                # リスト形式の場合
                for item in data:
                    if isinstance(item, dict):
                        chats.append({
                            'workspace_id': workspace_id,
                            'chat_id': key.split('.')[-2] if '.' in key else 'unknown',
                            'role': item.get('role', item.get('author', {}).get('role', 'unknown')),
                            'content': item.get('content', item.get('text', '')),
                            'timestamp': item.get('timestamp', item.get('createdAt', '')),
                            'raw': item
                        })
        
        return chats if chats else None
    
    def search_chats(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """チャット履歴を検索"""
        if not self.chat_history_cache:
            self.scan_all_workspaces()
        
        query_lower = query.lower()
        results = []
        
        for chat in self.chat_history_cache:
            content = str(chat.get('content', '')).lower()
            if query_lower in content:
                results.append(chat)
                if len(results) >= limit:
                    break
        
        return results
    
    def list_recent_chats(self, limit: int = 20) -> List[Dict[str, Any]]:
        """最近のチャットを一覧表示"""
        if not self.chat_history_cache:
            self.scan_all_workspaces()
        
        return self.chat_history_cache[:limit]
    
    def export_to_markdown(self, output_path: Optional[Path] = None) -> str:
        """チャット履歴をMarkdown形式でエクスポート"""
        if not self.chat_history_cache:
            self.scan_all_workspaces()
        
        if output_path is None:
            output_path = Path.cwd() / f"cursor_chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Cursor チャット履歴統合エクスポート\n\n")
            f.write(f"エクスポート日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"総チャット数: {len(self.chat_history_cache)}\n\n")
            f.write("---\n\n")
            
            current_chat_id = None
            for chat in self.chat_history_cache:
                chat_id = chat.get('chat_id', 'unknown')
                if chat_id != current_chat_id:
                    current_chat_id = chat_id
                    ws_id = chat.get('workspace_id', 'unknown')
                    f.write(f"\n## チャット: {chat_id} (ワークスペース: {ws_id})\n\n")
                
                role = chat.get('role', 'unknown')
                content = chat.get('content', '')
                timestamp = chat.get('timestamp', '')
                
                role_name = "ユーザー" if role == "user" else "アシスタント"
                f.write(f"### {role_name} ({timestamp})\n\n")
                f.write(f"{content}\n\n")
                f.write("---\n\n")
        
        return str(output_path)
    
    def print_summary(self):
        """サマリーを表示"""
        if not self.chat_history_cache:
            self.scan_all_workspaces()
        
        print("=" * 80)
        print("Cursor チャット履歴統合ビューア")
        print("=" * 80)
        print(f"総チャット数: {len(self.chat_history_cache)}")
        
        # ワークスペース別の集計
        workspace_stats = {}
        for chat in self.chat_history_cache:
            ws_id = chat.get('workspace_id', 'unknown')
            if ws_id not in workspace_stats:
                workspace_stats[ws_id] = 0
            workspace_stats[ws_id] += 1
        
        print(f"\nワークスペース別チャット数:")
        for ws_id, count in sorted(workspace_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {ws_id}: {count}件")
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description='Cursorチャット履歴統合ビューア')
    parser.add_argument('--search', '-s', type=str, help='検索クエリ')
    parser.add_argument('--list', '-l', type=int, default=20, help='最近のチャットを表示（件数）')
    parser.add_argument('--export', '-e', type=str, help='Markdown形式でエクスポート（ファイルパス）')
    parser.add_argument('--summary', action='store_true', help='サマリーを表示')
    
    args = parser.parse_args()
    
    try:
        viewer = CursorChatHistoryViewer()
        
        if args.summary:
            viewer.print_summary()
        elif args.search:
            results = viewer.search_chats(args.search)
            print(f"\n検索結果: {len(results)}件\n")
            for i, chat in enumerate(results, 1):
                print(f"{i}. [{chat.get('workspace_id', 'unknown')}] {chat.get('role', 'unknown')}")
                content = chat.get('content', '')
                if len(content) > 200:
                    content = content[:200] + "..."
                print(f"   {content}")
                print()
        elif args.export:
            output_path = viewer.export_to_markdown(Path(args.export))
            print(f"✅ エクスポート完了: {output_path}")
        else:
            # デフォルト: 最近のチャットを表示
            chats = viewer.list_recent_chats(args.list)
            print(f"\n最近のチャット ({len(chats)}件):\n")
            for i, chat in enumerate(chats, 1):
                print(f"{i}. [{chat.get('workspace_id', 'unknown')}] {chat.get('role', 'unknown')}")
                content = chat.get('content', '')
                if len(content) > 200:
                    content = content[:200] + "..."
                print(f"   {content}")
                print()
    
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
