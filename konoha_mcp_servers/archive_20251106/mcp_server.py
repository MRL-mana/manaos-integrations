#!/usr/bin/env python3
"""
ManaOS MCP Server for SD Inference
画像生成・修正・強化のMCPツールを提供
"""

import asyncio
from typing import Dict, Any
import requests
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SDInferenceMCP:
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.session = requests.Session()
        
    async def generate_image(self, prompt: str, model: str = "majicmixRealistic_v7.safetensors", 
                           steps: int = 30, guidance_scale: float = 7.5, 
                           width: int = 512, height: int = 512) -> Dict[str, Any]:
        """画像生成"""
        try:
            payload = {
                "prompt": prompt,
                "model": model,
                "steps": steps,
                "guidance_scale": guidance_scale,
                "width": width,
                "height": height
            }
            
            response = self.session.post(f"{self.api_base_url}/generate", json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"画像生成完了: {result.get('filename', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"画像生成エラー: {e}")
            return {"error": str(e)}
    
    async def inpaint_face(self, image_path: str, face_prompt: str = "beautiful face") -> Dict[str, Any]:
        """顔修正"""
        try:
            payload = {
                "image_path": image_path,
                "face_prompt": face_prompt
            }
            
            response = self.session.post(f"{self.api_base_url}/inpaint", json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"顔修正完了: {result.get('output_path', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"顔修正エラー: {e}")
            return {"error": str(e)}
    
    async def enhance_adult(self, image_path: str, enhancement_type: str = "sexy") -> Dict[str, Any]:
        """アダルト強化"""
        try:
            payload = {
                "image_path": image_path,
                "enhancement_type": enhancement_type
            }
            
            response = self.session.post(f"{self.api_base_url}/enhance", json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"アダルト強化完了: {result.get('output_path', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"アダルト強化エラー: {e}")
            return {"error": str(e)}
    
    async def get_models(self) -> Dict[str, Any]:
        """利用可能モデル一覧取得"""
        try:
            response = self.session.get(f"{self.api_base_url}/models")
            response.raise_for_status()
            
            models = response.json()
            logger.info(f"モデル一覧取得: {len(models)}個")
            return {"models": models}
            
        except Exception as e:
            logger.error(f"モデル一覧取得エラー: {e}")
            return {"error": str(e)}

# MCPツール定義
MCP_TOOLS = [
    {
        "name": "generate_image",
        "description": "Stable Diffusionで画像を生成",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "生成プロンプト"},
                "model": {"type": "string", "description": "使用モデル名", "default": "majicmixRealistic_v7.safetensors"},
                "steps": {"type": "integer", "description": "推論ステップ数", "default": 30},
                "guidance_scale": {"type": "number", "description": "ガイダンススケール", "default": 7.5},
                "width": {"type": "integer", "description": "画像幅", "default": 512},
                "height": {"type": "integer", "description": "画像高さ", "default": 512}
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "inpaint_face",
        "description": "画像の顔部分を修正",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "修正対象画像パス"},
                "face_prompt": {"type": "string", "description": "顔修正プロンプト", "default": "beautiful face"}
            },
            "required": ["image_path"]
        }
    },
    {
        "name": "enhance_adult",
        "description": "画像をアダルト向けに強化",
        "inputSchema": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "強化対象画像パス"},
                "enhancement_type": {"type": "string", "description": "強化タイプ", "default": "sexy"}
            },
            "required": ["image_path"]
        }
    },
    {
        "name": "get_models",
        "description": "利用可能なモデル一覧を取得",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

async def main():
    """MCPサーバーメイン処理"""
    logger.info("SD Inference MCP Server 起動中...")
    
    # SD Inference APIのヘルスチェック
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            logger.info("✅ SD Inference API接続成功")
        else:
            logger.error("❌ SD Inference API接続失敗")
            return
    except Exception as e:
        logger.error(f"❌ SD Inference API接続エラー: {e}")
        return
    
    # MCPサーバー初期化
    mcp = SDInferenceMCP()
    
    # モデル一覧取得テスト
    models_result = await mcp.get_models()
    if "error" not in models_result:
        logger.info(f"✅ モデル一覧取得成功: {len(models_result['models'])}個")
    else:
        logger.error(f"❌ モデル一覧取得失敗: {models_result['error']}")
    
    logger.info("🎯 MCP Server準備完了！")
    logger.info("利用可能ツール:")
    for tool in MCP_TOOLS:
        logger.info(f"  - {tool['name']}: {tool['description']}")

if __name__ == "__main__":
    asyncio.run(main())



















