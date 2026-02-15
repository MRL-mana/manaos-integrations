#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎨 ManaOS 成果物自動商品化システム
Content Generation (5109) の成果物を自動的に商品化
"""

import os
import json
import httpx
from datetime import datetime
from typing import Dict, Any, Optional, List
from flask import Flask, request, jsonify
from flask_cors import CORS

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("ProductAutomation")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

app = Flask(__name__)
CORS(app)

# 設定
CONTENT_GENERATION_URL = os.getenv("CONTENT_GENERATION_URL", "http://127.0.0.1:5109")
REVENUE_TRACKER_URL = os.getenv("REVENUE_TRACKER_URL", "http://127.0.0.1:5117")

def get_generated_contents(content_type: Optional[str] = None, status: str = "draft", limit: int = 10) -> List[Dict[str, Any]]:
    """生成コンテンツを取得"""
    try:
        params = {"limit": limit}
        if content_type:
            params["content_type"] = content_type
        if status:
            params["status"] = status
        
        timeout = timeout_config.get("api_call", 10.0)
        response = httpx.get(
            f"{CONTENT_GENERATION_URL}/api/contents",
            params=params,
            timeout=timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("results", [])
        else:
            error = error_handler.handle_exception(
                Exception(f"Content Generation接続失敗: HTTP {response.status_code}"),
                context={"service": "Content Generation", "url": CONTENT_GENERATION_URL},
                user_message="コンテンツの取得に失敗しました"
            )
            logger.warning(f"コンテンツ取得エラー: {error.message}")
            return []
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"service": "Content Generation", "url": CONTENT_GENERATION_URL},
            user_message="コンテンツの取得に失敗しました"
        )
        logger.error(f"コンテンツ取得エラー: {error.message}")
        return []

def create_product_from_content(content: Dict[str, Any]) -> Optional[str]:
    """コンテンツから商品を作成"""
    try:
        content_id = content.get("content_id", "")
        content_type = content.get("content_type", "")
        title = content.get("title", "")
        description = content.get("content", "")[:500]  # 最初の500文字
        
        # コンテンツタイプに応じた価格設定
        price_map = {
            "blog_draft": 500.0,
            "note_article": 300.0,
            "zenn_article": 300.0,
            "template_product": 1000.0
        }
        price = price_map.get(content_type, 0.0)
        
        # 商品ID生成
        product_id = f"product_{content_id}"
        
        # Revenue Trackerに商品登録
        response = httpx.post(
            f"{REVENUE_TRACKER_URL}/api/product",
            json={
                "product_id": product_id,
                "product_type": content_type,
                "title": title,
                "description": description,
                "price": price,
                "currency": "JPY",
                "file_path": content.get("file_path", ""),
                "metadata": {
                    "source_content_id": content_id,
                    "source_type": "content_generation",
                    "auto_generated": True
                }
            },
            timeout=5
        )
        
        if response.status_code == 200:
            logger.info(f"✅ 商品作成完了: {product_id}")
            return product_id
        else:
            logger.error(f"商品作成エラー: HTTP {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"商品作成エラー: {e}")
        return None

def auto_productize_contents():
    """未商品化のコンテンツを自動的に商品化"""
    contents = get_generated_contents(status="draft", limit=20)
    
    productized_count = 0
    for content in contents:
        product_id = create_product_from_content(content)
        if product_id:
            productized_count += 1
    
    logger.info(f"✅ 自動商品化完了: {productized_count}件")
    return productized_count

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Product Automation"})

@app.route('/api/auto-productize', methods=['POST'])
def auto_productize_endpoint():
    """自動商品化実行"""
    try:
        count = auto_productize_contents()
        return jsonify({
            "status": "success",
            "productized_count": count,
            "message": f"{count}件のコンテンツを商品化しました"
        })
    except Exception as e:
        logger.error(f"自動商品化エラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/productize/<content_id>', methods=['POST'])
def productize_content_endpoint(content_id: str):
    """特定コンテンツを商品化"""
    try:
        contents = get_generated_contents()
        content = next((c for c in contents if c.get("content_id") == content_id), None)
        
        if not content:
            return jsonify({
                "status": "error",
                "error": "Content not found"
            }), 404
        
        product_id = create_product_from_content(content)
        
        if product_id:
            return jsonify({
                "status": "success",
                "product_id": product_id,
                "message": "商品化完了"
            })
        else:
            return jsonify({
                "status": "error",
                "error": "Failed to create product"
            }), 500
    except Exception as e:
        logger.error(f"商品化エラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5118))
    logger.info(f"🎨 Product Automation起動中... (ポート: {port})")
    
    # 起動時に自動商品化実行（オプション）
    if os.getenv("AUTO_PRODUCTIZE_ON_START", "False").lower() == "true":
        logger.info("自動商品化を実行します...")
        auto_productize_contents()
    
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

