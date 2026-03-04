#!/usr/bin/env python3
"""
ManaOS MCP Integration for SD Inference
SD Inference API + Gallery のManaOS統合
"""

import asyncio
import logging
from typing import Dict, Any
import requests

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaOSSDInferenceIntegration:
    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.gallery_url = "http://localhost:5559"
        self.session = requests.Session()
        
    async def check_services(self) -> Dict[str, Any]:
        """サービス状態確認"""
        try:
            # API確認
            api_status = "unknown"
            try:
                response = self.session.get(f"{self.api_base_url}/health", timeout=5)
                if response.status_code == 200:
                    api_status = "running"
                else:
                    api_status = "error"
            except Exception:
                api_status = "stopped"
            
            # Gallery確認
            gallery_status = "unknown"
            try:
                response = self.session.get(f"{self.gallery_url}/", timeout=5)
                if response.status_code == 200:
                    gallery_status = "running"
                else:
                    gallery_status = "error"
            except Exception:
                gallery_status = "stopped"
            
            # モデル数取得
            model_count = 0
            try:
                response = self.session.get(f"{self.api_base_url}/models", timeout=5)
                if response.status_code == 200:
                    models = response.json()
                    model_count = len(models)
            except Exception:
                pass
            
            return {
                "api_status": api_status,
                "gallery_status": gallery_status,
                "model_count": model_count,
                "api_url": self.api_base_url,
                "gallery_url": self.gallery_url
            }
            
        except Exception as e:
            logger.error(f"❌ サービス確認エラー: {e}")
            return {"error": str(e)}
    
    async def generate_image(self, prompt: str, model: str = "majicmixRealistic_v7.safetensors", 
                           steps: int = 30, guidance_scale: float = 7.5) -> Dict[str, Any]:
        """画像生成（ManaOS経由）"""
        try:
            payload = {
                "prompt": prompt,
                "model": model,
                "steps": steps,
                "guidance_scale": guidance_scale
            }
            
            response = self.session.post(f"{self.gallery_url}/api/generate", json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ ManaOS経由画像生成: {result.get('job_id', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ ManaOS画像生成エラー: {e}")
            return {"error": str(e)}
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """ジョブステータス確認"""
        try:
            response = self.session.get(f"{self.gallery_url}/api/job/{job_id}", timeout=5)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"❌ ジョブステータス確認エラー: {e}")
            return {"error": str(e)}
    
    async def get_gallery_images(self, limit: int = 20) -> Dict[str, Any]:
        """ギャラリー画像一覧取得"""
        try:
            response = self.session.get(f"{self.gallery_url}/api/images?limit={limit}", timeout=10)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ ギャラリー画像取得: {len(result.get('images', []))}枚")
            return result
            
        except Exception as e:
            logger.error(f"❌ ギャラリー画像取得エラー: {e}")
            return {"error": str(e)}
    
    async def backup_database(self) -> Dict[str, Any]:
        """データベースバックアップ"""
        try:
            response = self.session.post(f"{self.gallery_url}/api/backup", timeout=30)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ DBバックアップ: {result.get('success', False)}")
            return result
            
        except Exception as e:
            logger.error(f"❌ DBバックアップエラー: {e}")
            return {"error": str(e)}

# MCPツール定義（ManaOS統合用）
MANAOS_MCP_TOOLS = [
    {
        "name": "manaos_sd_status",
        "description": "ManaOS SD Inference サービス状態確認",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "manaos_generate_image",
        "description": "ManaOS経由で画像生成",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "生成プロンプト"},
                "model": {"type": "string", "description": "使用モデル名", "default": "majicmixRealistic_v7.safetensors"},
                "steps": {"type": "integer", "description": "推論ステップ数", "default": 30},
                "guidance_scale": {"type": "number", "description": "ガイダンススケール", "default": 7.5}
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "manaos_job_status",
        "description": "ManaOS ジョブステータス確認",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "ジョブID"}
            },
            "required": ["job_id"]
        }
    },
    {
        "name": "manaos_gallery_images",
        "description": "ManaOS ギャラリー画像一覧取得",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "取得件数", "default": 20}
            }
        }
    },
    {
        "name": "manaos_backup_db",
        "description": "ManaOS データベースバックアップ",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

async def main():
    """ManaOS統合メイン処理"""
    logger.info("🎯 ManaOS SD Inference Integration 起動中...")
    
    # 統合インスタンス初期化
    integration = ManaOSSDInferenceIntegration()
    
    # サービス状態確認
    status = await integration.check_services()
    logger.info(f"📊 サービス状態: {status}")
    
    logger.info("🎉 ManaOS SD Inference Integration 準備完了！")
    logger.info("利用可能ツール:")
    for tool in MANAOS_MCP_TOOLS:
        logger.info(f"  - {tool['name']}: {tool['description']}")

if __name__ == "__main__":
    asyncio.run(main())



















