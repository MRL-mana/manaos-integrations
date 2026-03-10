#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursorチャット履歴統合ビューア（完成版）
すべてのワークスペースのチャット履歴を検索・閲覧できるツール
"""
import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import argparse
import sys

# Windowsでのエンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

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
                print(f"⚠️  ワークスペース {ws_dir.name} の読み込みエラー: {e}", file=sys.stderr)
                continue
        
        # タイムスタンプでソート（新しい順）
        all_chats.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        self.chat_history_cache = all_chats
        return all_chats
    
    def _extract_chats_from_db(self, db_path: Path, workspace_id: str) -> List[Dict[str, Any]]:
        """SQLiteデータベースからチャット履歴を抽出"""
        chats = []
        
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # aiService.generationsからチャット履歴を取得
            cursor.execute("SELECT value FROM ItemTable WHERE key = 'aiService.generations'")
            generations_row = cursor.fetchone()
            
            if generations_row:
                try:
                    value = generations_row['value']
                    if isinstance(value, bytes):
                        data = json.loads(value.decode('utf-8'))
                    else:
                        data = json.loads(value)
                    
                    if isinstance(data, list):
                        for gen in data:
                            if isinstance(gen, dict):
                                chats.append({
                                    'workspace_id': workspace_id,
                                    'type': 'generation',
                                    'text': gen.get('textDescription', ''),
                                    'timestamp': gen.get('unixMs', 0),
                                    'generation_uuid': gen.get('generationUUID', ''),
                                    'raw': gen
                                })
                except Exception as e:
                    pass
            
            # aiService.promptsからプロンプト履歴を取得
            cursor.execute("SELECT value FROM ItemTable WHERE key = 'aiService.prompts'")
            prompts_row = cursor.fetchone()
            
            if prompts_row:
                try:
                    value = prompts_row['value']
                    if isinstance(value, bytes):
                        data = json.loads(value.decode('utf-8'))
                    else:
                        data = json.loads(value)
                    
                    if isinstance(data, list):
                        for prompt in data:
                            if isinstance(prompt, dict):
                                chats.append({
                                    'workspace_id': workspace_id,
                                    'type': 'prompt',
                                    'text': prompt.get('text', ''),
                                    'timestamp': 0,  # promptsにはタイムスタンプがない場合がある
                                    'command_type': prompt.get('commandType', 0),
                                    'raw': prompt
                                })
                except Exception as e:
                    pass
            
            conn.close()
        except Exception as e:
            print(f"⚠️  データベース読み込みエラー ({db_path}): {e}", file=sys.stderr)
        
        return chats
    
    def search_chats(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """チャット履歴を検索"""
        if not self.chat_history_cache:
            self.scan_all_workspaces()
        
        query_lower = query.lower()
        results = []
        
        for chat in self.chat_history_cache:
            text = str(chat.get('text', '')).lower()
            if query_lower in text:
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
            
            current_workspace = None
            for chat in self.chat_history_cache:
                ws_id = chat.get('workspace_id', 'unknown')
                if ws_id != current_workspace:
                    current_workspace = ws_id
                    f.write(f"\n## ワークスペース: {ws_id}\n\n")
                
                chat_type = chat.get('type', 'unknown')
                text = chat.get('text', '')
                timestamp = chat.get('timestamp', 0)
                
                if timestamp:
                    dt = datetime.fromtimestamp(timestamp / 1000) if timestamp > 1000000000000 else datetime.fromtimestamp(timestamp)
                    time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    time_str = '不明'
                
                f.write(f"### {chat_type.upper()} ({time_str})\n\n")
                f.write(f"{text}\n\n")
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
                workspace_stats[ws_id] = {'total': 0, 'generations': 0, 'prompts': 0}
            workspace_stats[ws_id]['total'] += 1
            chat_type = chat.get('type', 'unknown')
            if chat_type == 'generation':
                workspace_stats[ws_id]['generations'] += 1
            elif chat_type == 'prompt':
                workspace_stats[ws_id]['prompts'] += 1
        
        print(f"\nワークスペース別チャット数:")
        for ws_id, stats in sorted(workspace_stats.items(), key=lambda x: x[1]['total'], reverse=True):
            print(f"  {ws_id}:")
            print(f"    総数: {stats['total']}件")
            print(f"    - Generations: {stats['generations']}件")
            print(f"    - Prompts: {stats['prompts']}件")
        print("=" * 80)

    def export_to_html(self, output_path: Optional[Path] = None) -> str:
        """チャット履歴をHTML形式でエクスポート（ブラウザで開ける）"""
        if not self.chat_history_cache:
            self.scan_all_workspaces()

        if output_path is None:
            output_path = Path.cwd() / "cursor_chat_history.html"

        rows = []
        for chat in self.chat_history_cache:
            text = (chat.get('text') or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace('\n', '<br>')
            ts = chat.get('timestamp', 0)
            if ts:
                dt = datetime.fromtimestamp(ts / 1000) if ts > 1000000000000 else datetime.fromtimestamp(ts)
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                time_str = '—'
            ws = chat.get('workspace_id', 'unknown')
            typ = chat.get('type', 'unknown')
            rows.append(f'<tr><td>{time_str}</td><td>{ws}</td><td>{typ}</td><td class="content">{text}</td></tr>')

        html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cursor チャット履歴</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; background: #1e1e1e; color: #d4d4d4; }}
h1 {{ color: #fff; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #444; padding: 8px 12px; text-align: left; vertical-align: top; }}
th {{ background: #2d2d2d; color: #569cd6; }}
tr:nth-child(even) {{ background: #252526; }}
.content {{ max-width: 60%; word-break: break-word; }}
small {{ color: #858585; }}
</style>
</head>
<body>
<h1>Cursor チャット履歴（全{len(self.chat_history_cache)}件）</h1>
<p><small>更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
<table>
<thead><tr><th>日時</th><th>ワークスペース</th><th>種類</th><th>内容</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody>
</table>
</body>
</html>"""

        output_path.write_text(html, encoding='utf-8')
        return str(output_path)


def main():
    parser = argparse.ArgumentParser(description='Cursorチャット履歴統合ビューア')
    parser.add_argument('--search', '-s', type=str, help='検索クエリ')
    parser.add_argument('--list', '-l', type=int, default=20, help='最近のチャットを表示（件数）')
    parser.add_argument('--export', '-e', type=str, help='Markdown形式でエクスポート（ファイルパス）')
    parser.add_argument('--html', action='store_true', help='HTML形式でエクスポートしてブラウザで開く')
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
                print(f"{i}. [{chat.get('workspace_id', 'unknown')}] {chat.get('type', 'unknown')}")
                text = chat.get('text', '')
                if len(text) > 200:
                    text = text[:200] + "..."
                print(f"   {text}")
                print()
        elif args.export:
            output_path = viewer.export_to_markdown(Path(args.export))
            print(f"✅ エクスポート完了: {output_path}")
        elif args.html:
            output_path = viewer.export_to_html()
            print(f"✅ HTMLを出力しました: {output_path}")
            # ブラウザで開く
            import webbrowser
            webbrowser.open(output_path)
        else:
            # デフォルト: 最近のチャットを表示
            chats = viewer.list_recent_chats(args.list)
            print(f"\n最近のチャット ({len(chats)}件):\n")
            for i, chat in enumerate(chats, 1):
                print(f"{i}. [{chat.get('workspace_id', 'unknown')}] {chat.get('type', 'unknown')}")
                text = chat.get('text', '')
                if len(text) > 200:
                    text = text[:200] + "..."
                print(f"   {text}")
                print()
    
    except Exception as e:
        print(f"❌ エラー: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
