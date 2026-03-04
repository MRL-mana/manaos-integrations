#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIアシスタント統合システム
Gemini APIとObsidian-Notionシステムを統合した高度なAIアシスタント
"""

import os
import sys
import time
import json
import yaml
import logging
import threading
import sqlite3
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from pathlib import Path

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_assistant.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AIAssistantIntegration:
    """AIアシスタント統合システム"""
    
    def __init__(self):
        self.config = self.load_config()
        self.running = True
        self.conversation_history = []
        self.setup_gemini()
        self.setup_database()
    
    def load_config(self) -> Dict[str, Any]:
        """設定読み込み"""
        try:
            with open('gemini_api_config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info("AIアシスタント設定読み込み完了")
            return config
        except Exception as e:
            logger.error(f"設定読み込みエラー: {e}")
            return {}
    
    def setup_gemini(self):
        """Gemini API設定"""
        try:
            api_key = self.config.get('gemini_api_key', '')
            if api_key and api_key != "AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx":
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                logger.info("Gemini API設定完了")
            else:
                logger.warning("有効なGemini APIキーが設定されていません")
                self.model = None
        except Exception as e:
            logger.error(f"Gemini API設定エラー: {e}")
            self.model = None
    
    def setup_database(self):
        """データベース設定"""
        try:
            self.db_path = 'ai_assistant.db'
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 会話履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    user_input TEXT,
                    ai_response TEXT,
                    context TEXT
                )
            ''')
            
            # 知識ベーステーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    content TEXT,
                    created_at TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("AIアシスタントデータベース設定完了")
        except Exception as e:
            logger.error(f"データベース設定エラー: {e}")
    
    def get_obsidian_context(self) -> str:
        """Obsidian Vaultからコンテキスト取得"""
        try:
            context = []
            vault_path = Path("obsidian_vault")
            
            if vault_path.exists():
                # 最近のファイルを取得
                recent_files = []
                for file_path in vault_path.rglob("*.md"):
                    if file_path.is_file():
                        stat = file_path.stat()
                        recent_files.append((file_path, stat.st_mtime))
                
                # 最新の10ファイルを取得
                recent_files.sort(key=lambda x: x[1], reverse=True)
                for file_path, _ in recent_files[:10]:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()[:500]  # 最初の500文字
                            context.append(f"ファイル: {file_path.name}\n内容: {content}")
                    except Exception as e:
                        logger.error(f"ファイル読み込みエラー {file_path}: {e}")
            
            return "\n\n".join(context)
        except Exception as e:
            logger.error(f"Obsidianコンテキスト取得エラー: {e}")
            return ""
    
    def get_notion_context(self) -> str:
        """Notionからコンテキスト取得"""
        try:
            # Notion APIから最新のページ情報を取得
            # 実際の実装ではNotion APIを使用
            return "Notionデータベースから最新の情報を取得"
        except Exception as e:
            logger.error(f"Notionコンテキスト取得エラー: {e}")
            return ""
    
    def generate_response(self, user_input: str, context: str = "") -> str:
        """AI応答生成"""
        try:
            if not self.model:
                return "Gemini APIが設定されていません。APIキーを確認してください。"
            
            # プロンプト構築
            prompt = f"""
あなたは高度なAIアシスタントです。以下のコンテキストを参考にして、ユーザーの質問に回答してください。

コンテキスト:
{context}

ユーザーの質問: {user_input}

以下の点に注意して回答してください:
1. 日本語で丁寧に回答
2. 実用的で具体的なアドバイスを提供
3. 必要に応じてObsidianやNotionの活用方法を提案
4. システムの最適化提案も含める

回答:
"""
            
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"AI応答生成エラー: {e}")
            return f"エラーが発生しました: {e}"
    
    def save_conversation(self, user_input: str, ai_response: str, context: str = ""):
        """会話履歴保存"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO conversations (timestamp, user_input, ai_response, context)
                VALUES (?, ?, ?, ?)
            ''', (datetime.now().isoformat(), user_input, ai_response, context))
            
            conn.commit()
            conn.close()
            logger.info("会話履歴保存完了")
        except Exception as e:
            logger.error(f"会話履歴保存エラー: {e}")
    
    def get_conversation_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """会話履歴取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, user_input, ai_response
                FROM conversations
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    'timestamp': row[0],
                    'user_input': row[1],
                    'ai_response': row[2]
                })
            
            conn.close()
            return history
        except Exception as e:
            logger.error(f"会話履歴取得エラー: {e}")
            return []
    
    def add_knowledge(self, category: str, content: str):
        """知識ベース追加"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO knowledge_base (category, content, created_at)
                VALUES (?, ?, ?)
            ''', (category, content, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            logger.info(f"知識ベース追加: {category}")
        except Exception as e:
            logger.error(f"知識ベース追加エラー: {e}")
    
    def search_knowledge(self, query: str) -> List[Dict[str, str]]:
        """知識ベース検索"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT category, content, created_at
                FROM knowledge_base
                WHERE content LIKE ? OR category LIKE ?
                ORDER BY created_at DESC
            ''', (f'%{query}%', f'%{query}%'))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'category': row[0],
                    'content': row[1],
                    'created_at': row[2]
                })
            
            conn.close()
            return results
        except Exception as e:
            logger.error(f"知識ベース検索エラー: {e}")
            return []
    
    def run_interactive(self):
        """インタラクティブモード実行"""
        print("🤖 AIアシスタント統合システム開始")
        print("コマンド:")
        print("  /help - ヘルプ表示")
        print("  /history - 会話履歴表示")
        print("  /knowledge <query> - 知識ベース検索")
        print("  /add <category> <content> - 知識ベース追加")
        print("  /quit - 終了")
        print()
        
        while self.running:
            try:
                user_input = input("🤖 AIアシスタント > ").strip()
                
                if not user_input:
                    continue
                
                if user_input.startswith('/'):
                    self.handle_command(user_input)
                else:
                    # コンテキスト取得
                    obsidian_context = self.get_obsidian_context()
                    notion_context = self.get_notion_context()
                    context = f"Obsidian: {obsidian_context}\nNotion: {notion_context}"
                    
                    # AI応答生成
                    response = self.generate_response(user_input, context)
                    print(f"\n🤖 AI: {response}\n")
                    
                    # 会話履歴保存
                    self.save_conversation(user_input, response, context)
                    
            except KeyboardInterrupt:
                print("\nAIアシスタントを終了します...")
                break
            except Exception as e:
                logger.error(f"インタラクティブモードエラー: {e}")
                print(f"エラーが発生しました: {e}")
    
    def handle_command(self, command: str):
        """コマンド処理"""
        parts = command.split(' ', 1)
        cmd = parts[0].lower()
        
        if cmd == '/help':
            print("""
🤖 AIアシスタントコマンド一覧:
  /help - このヘルプを表示
  /history - 会話履歴を表示
  /knowledge <query> - 知識ベースを検索
  /add <category> <content> - 知識ベースに追加
  /quit - 終了
            """)
        
        elif cmd == '/history':
            history = self.get_conversation_history(5)
            print("\n📝 最近の会話履歴:")
            for conv in history:
                print(f"時間: {conv['timestamp']}")
                print(f"質問: {conv['user_input']}")
                print(f"回答: {conv['ai_response'][:100]}...")
                print("-" * 50)
        
        elif cmd == '/knowledge' and len(parts) > 1:
            query = parts[1]
            results = self.search_knowledge(query)
            print(f"\n🔍 知識ベース検索結果: '{query}'")
            for result in results:
                print(f"カテゴリ: {result['category']}")
                print(f"内容: {result['content']}")
                print("-" * 30)
        
        elif cmd == '/add' and len(parts) > 1:
            content_parts = parts[1].split(' ', 1)
            if len(content_parts) > 1:
                category = content_parts[0]
                content = content_parts[1]
                self.add_knowledge(category, content)
                print(f"✅ 知識ベースに追加: {category}")
            else:
                print("❌ 形式: /add <category> <content>")
        
        elif cmd == '/quit':
            self.running = False
            print("AIアシスタントを終了します...")
        
        else:
            print("❌ 無効なコマンドです。'/help'でヘルプを表示してください。")
    
    def run(self):
        """メイン実行"""
        logger.info("AIアシスタント統合システム開始")
        self.run_interactive()

def main():
    """メイン関数"""
    assistant = AIAssistantIntegration()
    assistant.run()

if __name__ == "__main__":
    main() 