#!/usr/bin/env python3
"""
🎯 ManaOS System Registration Template
新規システム作成時に使うテンプレート - 自動的にManaOSに登録される

使い方:
1. このテンプレートをコピー
2. システムを実装
3. 起動時に自動的にManaOSに登録される
4. もう孤立しない！
"""

import os
import json
import logging
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# =====================================
# 📝 システム情報（ここを編集）
# =====================================
SYSTEM_INFO = {
    "name": "My New System",  # システム名
    "description": "新しいシステムの説明",  # 説明
    "category": "automation",  # カテゴリ: automation, ai, dashboard, integration, etc.
    "port": 7100,  # ポート番号
    "priority": "medium",  # 優先度: high, medium, low
    "auto_start": False,  # 自動起動するか
    "version": "1.0.0",  # バージョン
    "author": "Mana"  # 作成者
}

# ManaOSダッシュボードのURL
MANAOS_DASHBOARD_URL = "http://localhost:9999"
MANAOS_REGISTRY_FILE = "/root/manaos_systems_registry.json"

class SystemStatus(BaseModel):
    """システムステータス"""
    status: str = "healthy"
    uptime: float = 0.0
    version: str = SYSTEM_INFO["version"]
    timestamp: str = ""

class ManaOSIntegration:
    """ManaOS統合機能"""
    
    @staticmethod
    def register_to_manaos():
        """ManaOSにシステムを登録"""
        try:
            # レジストリファイル読み込み
            if os.path.exists(MANAOS_REGISTRY_FILE):
                with open(MANAOS_REGISTRY_FILE, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
            else:
                registry = {"systems": {}, "last_updated": ""}
            
            # システム情報を追加
            system_id = SYSTEM_INFO["name"].lower().replace(" ", "_")
            registry["systems"][system_id] = {
                **SYSTEM_INFO,
                "registered_at": datetime.now().isoformat(),
                "status": "active",
                "health_check_url": f"http://localhost:{SYSTEM_INFO['port']}/api/status"
            }
            registry["last_updated"] = datetime.now().isoformat()
            
            # レジストリファイルに保存
            with open(MANAOS_REGISTRY_FILE, 'w', encoding='utf-8') as f:
                json.dump(registry, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ ManaOSに登録完了: {SYSTEM_INFO['name']}")
            logger.info(f"📊 ダッシュボード: {MANAOS_DASHBOARD_URL}")
            
            return True
        except Exception as e:
            logger.error(f"❌ ManaOS登録エラー: {e}")
            return False
    
    @staticmethod
    def deregister_from_manaos():
        """ManaOSから登録解除"""
        try:
            if os.path.exists(MANAOS_REGISTRY_FILE):
                with open(MANAOS_REGISTRY_FILE, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
                
                system_id = SYSTEM_INFO["name"].lower().replace(" ", "_")
                if system_id in registry["systems"]:
                    registry["systems"][system_id]["status"] = "stopped"
                    registry["last_updated"] = datetime.now().isoformat()
                    
                    with open(MANAOS_REGISTRY_FILE, 'w', encoding='utf-8') as f:
                        json.dump(registry, f, indent=2, ensure_ascii=False)
                    
                    logger.info(f"🛑 ManaOSから登録解除: {SYSTEM_INFO['name']}")
        except Exception as e:
            logger.error(f"❌ 登録解除エラー: {e}")

# =====================================
# 🚀 FastAPIアプリケーション
# =====================================
app = FastAPI(
    title=SYSTEM_INFO["name"],
    description=SYSTEM_INFO["description"],
    version=SYSTEM_INFO["version"]
)

# システム起動時刻
START_TIME = datetime.now()

@app.get("/api/status")
async def get_status():
    """ヘルスチェックエンドポイント（ManaOS用）"""
    uptime = (datetime.now() - START_TIME).total_seconds()
    return {
        "status": "healthy",
        "name": SYSTEM_INFO["name"],
        "version": SYSTEM_INFO["version"],
        "uptime_seconds": uptime,
        "timestamp": datetime.now().isoformat(),
        "category": SYSTEM_INFO["category"],
        "priority": SYSTEM_INFO["priority"]
    }

@app.get("/api/info")
async def get_info():
    """システム情報取得"""
    return SYSTEM_INFO

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": f"Welcome to {SYSTEM_INFO['name']}",
        "status": "running",
        "health_check": f"http://localhost:{SYSTEM_INFO['port']}/api/status",
        "info": f"http://localhost:{SYSTEM_INFO['port']}/api/info"
    }

# =====================================
# ✨ あなたのコードをここに追加
# =====================================

@app.get("/api/hello")
async def hello():
    """サンプルエンドポイント"""
    return {
        "message": "Hello from ManaOS integrated system!",
        "system": SYSTEM_INFO["name"]
    }

# ここに追加のエンドポイントや機能を実装

# =====================================
# 🎬 メイン処理
# =====================================

def main():
    """メイン処理"""
    print("=" * 70)
    print(f"🚀 {SYSTEM_INFO['name']} 起動中...")
    print("=" * 70)
    print(f"📝 説明: {SYSTEM_INFO['description']}")
    print(f"🔌 ポート: {SYSTEM_INFO['port']}")
    print(f"📊 カテゴリ: {SYSTEM_INFO['category']}")
    print(f"⭐ 優先度: {SYSTEM_INFO['priority']}")
    print("=" * 70)
    
    # ManaOSに自動登録
    print("🔗 ManaOSに登録中...")
    if ManaOSIntegration.register_to_manaos():
        print(f"✅ ManaOSダッシュボードで確認可能: {MANAOS_DASHBOARD_URL}")
    else:
        print("⚠️  ManaOS登録に失敗（システムは起動します）")
    
    print("=" * 70)
    print(f"🌐 API: http://localhost:{SYSTEM_INFO['port']}")
    print(f"📊 Status: http://localhost:{SYSTEM_INFO['port']}/api/status")
    print(f"ℹ️  Info: http://localhost:{SYSTEM_INFO['port']}/api/info")
    print("=" * 70)
    
    try:
        # サーバー起動
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=SYSTEM_INFO["port"],
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 システム停止中...")
        ManaOSIntegration.deregister_from_manaos()
        print("👋 システムを停止しました")

if __name__ == "__main__":
    main()

