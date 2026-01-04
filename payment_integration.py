#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💳 ManaOS 決済統合システム
外部決済API（Stripe、PayPal等）との統合
"""

import os
import json
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("PaymentIntegration")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

app = Flask(__name__)
CORS(app)

# 設定
REVENUE_TRACKER_URL = os.getenv("REVENUE_TRACKER_URL", "http://localhost:5117")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")

def process_stripe_payment(amount: float, currency: str = "JPY", product_id: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """Stripe決済処理"""
    if not STRIPE_SECRET_KEY:
        return {
            "status": "error",
            "error": "Stripe API key not configured"
        }
    
    try:
        # Stripe API呼び出し（実装が必要）
        # ここではモック実装
        logger.info(f"Stripe決済処理: {amount} {currency}")
        
        # 実際の実装では、Stripe APIを使用
        # import stripe
        # stripe.api_key = STRIPE_SECRET_KEY
        # payment_intent = stripe.PaymentIntent.create(...)
        
        return {
            "status": "success",
            "payment_id": f"stripe_{datetime.now().timestamp()}",
            "amount": amount,
            "currency": currency
        }
    except Exception as e:
        logger.error(f"Stripe決済エラー: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def process_paypal_payment(amount: float, currency: str = "JPY", product_id: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """PayPal決済処理"""
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        return {
            "status": "error",
            "error": "PayPal credentials not configured"
        }
    
    try:
        # PayPal API呼び出し（実装が必要）
        logger.info(f"PayPal決済処理: {amount} {currency}")
        
        # 実際の実装では、PayPal APIを使用
        # ここではモック実装
        
        return {
            "status": "success",
            "payment_id": f"paypal_{datetime.now().timestamp()}",
            "amount": amount,
            "currency": currency
        }
    except Exception as e:
        logger.error(f"PayPal決済エラー: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def record_payment(product_id: Optional[str], amount: float, currency: str, payment_method: str, payment_id: str):
    """決済を記録"""
    try:
        response = httpx.post(
            f"{REVENUE_TRACKER_URL}/api/revenue",
            json={
                "product_id": product_id,
                "product_type": "sale",
                "amount": amount,
                "currency": currency,
                "source": payment_method,
                "metadata": {
                    "payment_id": payment_id,
                    "payment_method": payment_method
                }
            },
            timeout=5
        )
        
        return response.status_code == 200
    except Exception as e:
        logger.error(f"決済記録エラー: {e}")
        return False

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "service": "Payment Integration",
        "stripe_configured": bool(STRIPE_SECRET_KEY),
        "paypal_configured": bool(PAYPAL_CLIENT_ID)
    })

@app.route('/api/payment/stripe', methods=['POST'])
def stripe_payment_endpoint():
    """Stripe決済"""
    data = request.get_json()
    
    amount = float(data.get("amount", 0.0))
    currency = data.get("currency", "JPY")
    product_id = data.get("product_id")
    metadata = data.get("metadata")
    
    result = process_stripe_payment(amount, currency, product_id, metadata)
    
    if result["status"] == "success":
        # 決済を記録
        record_payment(
            product_id,
            amount,
            currency,
            "stripe",
            result.get("payment_id", "")
        )
    
    return jsonify(result)

@app.route('/api/payment/paypal', methods=['POST'])
def paypal_payment_endpoint():
    """PayPal決済"""
    data = request.get_json()
    
    amount = float(data.get("amount", 0.0))
    currency = data.get("currency", "JPY")
    product_id = data.get("product_id")
    metadata = data.get("metadata")
    
    result = process_paypal_payment(amount, currency, product_id, metadata)
    
    if result["status"] == "success":
        # 決済を記録
        record_payment(
            product_id,
            amount,
            currency,
            "paypal",
            result.get("payment_id", "")
        )
    
    return jsonify(result)

@app.route('/api/payment/methods', methods=['GET'])
def get_payment_methods():
    """利用可能な決済方法を取得"""
    methods = []
    
    if STRIPE_SECRET_KEY:
        methods.append({
            "id": "stripe",
            "name": "Stripe",
            "enabled": True
        })
    
    if PAYPAL_CLIENT_ID:
        methods.append({
            "id": "paypal",
            "name": "PayPal",
            "enabled": True
        })
    
    return jsonify({
        "methods": methods,
        "count": len(methods)
    })

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5119))
    logger.info(f"💳 Payment Integration起動中... (ポート: {port})")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

