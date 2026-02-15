"""
会話履歴管理システム
会話の保存・検索・エクスポート
"""

import json
from manaos_logger import get_logger, get_service_logger
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import sqlite3

logger = get_service_logger("llm-conversation-history")


class ConversationHistory:
    """会話履歴管理クラス"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初期化
        
        Args:
            db_path: データベースパス（Noneの場合は自動決定）
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path.home() / "llm_conversations.db"
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """データベースを初期化"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model TEXT,
                metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation_id 
            ON conversations(conversation_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON conversations(timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        メッセージを追加
        
        Args:
            conversation_id: 会話ID
            role: ロール（user/assistant）
            content: メッセージ内容
            model: モデル名
            metadata: メタデータ
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversations 
            (conversation_id, role, content, model, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            conversation_id,
            role,
            content,
            model,
            json.dumps(metadata) if metadata else None
        ))
        
        conn.commit()
        conn.close()
    
    def get_conversation(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        会話を取得
        
        Args:
            conversation_id: 会話ID
            
        Returns:
            メッセージリスト
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT role, content, model, metadata, timestamp
            FROM conversations
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
        """, (conversation_id,))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                "role": row[0],
                "content": row[1],
                "model": row[2],
                "metadata": json.loads(row[3]) if row[3] else None,
                "timestamp": row[4]
            })
        
        conn.close()
        return messages
    
    def search_conversations(
        self,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        会話を検索
        
        Args:
            query: 検索クエリ
            limit: 最大件数
            
        Returns:
            会話リスト
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT conversation_id, MAX(timestamp) as last_message
            FROM conversations
            WHERE content LIKE ?
            GROUP BY conversation_id
            ORDER BY last_message DESC
            LIMIT ?
        """, (f"%{query}%", limit))
        
        conversations = []
        for row in cursor.fetchall():
            conversation_id = row[0]
            messages = self.get_conversation(conversation_id)
            conversations.append({
                "conversation_id": conversation_id,
                "last_message": row[1],
                "message_count": len(messages),
                "messages": messages
            })
        
        conn.close()
        return conversations
    
    def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        会話リストを取得
        
        Args:
            limit: 最大件数
            offset: オフセット
            
        Returns:
            会話リスト
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT conversation_id, COUNT(*) as message_count, 
                   MIN(timestamp) as first_message, MAX(timestamp) as last_message
            FROM conversations
            GROUP BY conversation_id
            ORDER BY last_message DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        conversations = []
        for row in cursor.fetchall():
            conversations.append({
                "conversation_id": row[0],
                "message_count": row[1],
                "first_message": row[2],
                "last_message": row[3]
            })
        
        conn.close()
        return conversations
    
    def export_conversation(
        self,
        conversation_id: str,
        format: str = "json"
    ) -> str:
        """
        会話をエクスポート
        
        Args:
            conversation_id: 会話ID
            format: フォーマット（json/markdown/text）
            
        Returns:
            エクスポートされた文字列
        """
        messages = self.get_conversation(conversation_id)
        
        if format == "json":
            return json.dumps({
                "conversation_id": conversation_id,
                "messages": messages
            }, ensure_ascii=False, indent=2)
        
        elif format == "markdown":
            lines = [f"# 会話: {conversation_id}\n"]
            for msg in messages:
                role = "ユーザー" if msg["role"] == "user" else "アシスタント"
                lines.append(f"## {role}")
                lines.append(msg["content"])
                lines.append("")
            return "\n".join(lines)
        
        elif format == "text":
            lines = [f"会話ID: {conversation_id}\n"]
            for msg in messages:
                role = "ユーザー" if msg["role"] == "user" else "アシスタント"
                lines.append(f"{role}: {msg['content']}")
            return "\n".join(lines)
        
        else:
            raise ValueError(f"不明なフォーマット: {format}")
    
    def delete_conversation(self, conversation_id: str):
        """会話を削除"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM conversations
            WHERE conversation_id = ?
        """, (conversation_id,))
        
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(DISTINCT conversation_id) FROM conversations")
        conversation_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM conversations")
        message_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM conversations")
        row = cursor.fetchone()
        first_conversation = row[0]
        last_conversation = row[1]
        
        conn.close()
        
        return {
            "conversation_count": conversation_count,
            "message_count": message_count,
            "first_conversation": first_conversation,
            "last_conversation": last_conversation
        }

