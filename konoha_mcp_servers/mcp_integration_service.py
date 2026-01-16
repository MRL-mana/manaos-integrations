#!/usr/bin/env python3
"""
MCP Integration Service
PostgreSQL to AI Learning統合サービス
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# パス設定
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - MCP_INTEGRATION - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 設定
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "manaos")
POSTGRES_USER = os.getenv("POSTGRES_USER", "manaos")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

AI_LEARNING_DATA_DIR = Path("/root/ai_learning_system/data")
AI_LEARNING_DATA_DIR.mkdir(parents=True, exist_ok=True)


class MCPIntegrationService:
    """MCP統合サービス - PostgreSQL to AI Learning"""
    
    def __init__(self):
        self.postgres_conn = None
        self.ai_learning_data_file = AI_LEARNING_DATA_DIR / "learned_patterns.json"
        self.sync_interval = 300  # 5分ごと
        
    async def connect_postgres(self):
        """PostgreSQLに接続"""
        try:
            import psycopg2
            self.postgres_conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD
            )
            logger.info("✅ PostgreSQL接続成功")
            return True
        except ImportError:
            logger.warning("⚠️ psycopg2がインストールされていません")
            return False
        except Exception as e:
            logger.error(f"❌ PostgreSQL接続エラー: {e}")
            return False
    
    def load_ai_learning_data(self) -> Dict:
        """AI Learningデータを読み込み"""
        if self.ai_learning_data_file.exists():
            try:
                import json
                with open(self.ai_learning_data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"AI Learningデータ読み込みエラー: {e}")
        return {"patterns": [], "last_sync": None}
    
    def save_ai_learning_data(self, data: Dict):
        """AI Learningデータを保存"""
        try:
            import json
            data["last_sync"] = datetime.now().isoformat()
            with open(self.ai_learning_data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("✅ AI Learningデータ保存完了")
        except Exception as e:
            logger.error(f"AI Learningデータ保存エラー: {e}")
    
    async def sync_postgres_to_ai_learning(self):
        """PostgreSQL → AI Learning同期"""
        if not self.postgres_conn:
            if not await self.connect_postgres():
                return
        
        try:
            cursor = self.postgres_conn.cursor()
            
            # 最近のアクション履歴を取得
            cursor.execute("""
                SELECT action, context, timestamp 
                FROM action_history 
                WHERE timestamp > NOW() - INTERVAL '24 hours'
                ORDER BY timestamp DESC
                LIMIT 100
            """)
            
            actions = cursor.fetchall()
            logger.info(f"📊 {len(actions)}件のアクションを取得")
            
            # AI Learningデータを読み込み
            ai_data = self.load_ai_learning_data()
            
            # パターンを抽出して学習
            patterns = []
            for action, context, timestamp in actions:
                pattern = {
                    "action": action,
                    "context": context or {},
                    "timestamp": timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
                    "frequency": 1
                }
                
                # 既存パターンとマージ
                existing = next((p for p in ai_data["patterns"] if p.get("action") == action), None)
                if existing:
                    existing["frequency"] += 1
                    existing["last_seen"] = pattern["timestamp"]
                else:
                    ai_data["patterns"].append(pattern)
            
            # データを保存
            self.save_ai_learning_data(ai_data)
            logger.info(f"✅ {len(patterns)}件のパターンを学習")
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"❌ 同期エラー: {e}")
    
    async def run_continuous_sync(self):
        """継続的な同期を実行"""
        logger.info("🚀 MCP Integration Service 起動")
        logger.info(f"  同期間隔: {self.sync_interval}秒")
        
        while True:
            try:
                await self.sync_postgres_to_ai_learning()
                await asyncio.sleep(self.sync_interval)
            except KeyboardInterrupt:
                logger.info("⏹️  サービス停止")
                break
            except Exception as e:
                logger.error(f"❌ 実行エラー: {e}")
                await asyncio.sleep(60)  # エラー時は1分待機
    
    def cleanup(self):
        """クリーンアップ"""
        if self.postgres_conn:
            self.postgres_conn.close()
            logger.info("✅ PostgreSQL接続を閉じました")


async def main():
    """メイン関数"""
    service = MCPIntegrationService()
    try:
        await service.run_continuous_sync()
    finally:
        service.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

