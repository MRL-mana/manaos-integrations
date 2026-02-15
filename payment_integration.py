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

try:
    from manaos_integrations._paths import (
        PAYMENT_INTEGRATION_PORT,
        REVENUE_TRACKER_PORT,
    )
except Exception:  # pragma: no cover
    try:
        from _paths import (  # type: ignore
            PAYMENT_INTEGRATION_PORT,
            REVENUE_TRACKER_PORT,
        )
    except Exception:  # pragma: no cover
        REVENUE_TRACKER_PORT = int(os.getenv("REVENUE_TRACKER_PORT", "5117"))
        PAYMENT_INTEGRATION_PORT = int(
            os.getenv("PAYMENT_INTEGRATION_PORT", "5119")
        )

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import (
    ManaOSErrorHandler,
    ErrorCategory,
    ErrorSeverity,
)
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_service_logger("payment-integration")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("PaymentIntegration")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

app = Flask(__name__)
CORS(app)

# 設定
REVENUE_TRACKER_URL = os.getenv(
    "REVENUE_TRACKER_URL",
    f"http://127.0.0.1:{REVENUE_TRACKER_PORT}",
)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")

def process_stripe_payment(amount: float, currency: str = "JPY", product_id: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Stripe決済処理
    実際のStripe APIを使用して決済を処理
    
    Args:
        amount: 決済金額
        currency: 通貨コード（デフォルト: JPY）
        product_id: 製品ID（オプション）
        metadata: 追加メタデータ（オプション）
    
    Returns:
        決済結果
    """
    if not STRIPE_SECRET_KEY:
        return {
            "status": "error",
            "error": "Stripe API key not configured"
        }
    
    try:
        # Stripe APIをインポート（オプション）
        stripe = None
        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            
            # 金額を最小通貨単位に変換（例: JPYの場合はそのまま、USDの場合はセント）
            if currency.upper() == "JPY":
                amount_in_cents = int(amount)  # 円は整数
            else:
                amount_in_cents = int(amount * 100)  # その他の通貨はセント単位
            
            # PaymentIntentを作成
            payment_intent_data = {
                "amount": amount_in_cents,
                "currency": currency.lower(),
                "automatic_payment_methods": {
                    "enabled": True
                }
            }
            
            # メタデータを追加
            if metadata:
                payment_intent_data["metadata"] = metadata
            
            if product_id:
                payment_intent_data["metadata"] = payment_intent_data.get("metadata", {})
                payment_intent_data["metadata"]["product_id"] = product_id
            
            payment_intent = stripe.PaymentIntent.create(**payment_intent_data)
            
            logger.info(f"Stripe決済処理成功: {payment_intent.id} ({amount} {currency})")
            
            return {
                "status": "success",
                "payment_id": payment_intent.id,
                "client_secret": payment_intent.client_secret,
                "amount": amount,
                "currency": currency,
                "status": payment_intent.status
            }
            
        except ImportError:
            # stripeライブラリがインストールされていない場合はモック実装
            logger.warning("stripeライブラリがインストールされていません。モック実装を使用します。")
            logger.info(f"Stripe決済処理（モック）: {amount} {currency}")
            
            return {
                "status": "success",
                "payment_id": f"stripe_mock_{datetime.now().timestamp()}",
                "amount": amount,
                "currency": currency,
                "note": "モック実装: stripeライブラリをインストールしてください (pip install stripe)"
            }
    
    except Exception as e:
        # stripeライブラリがインポートされている場合のみStripeErrorをチェック
        if stripe and hasattr(stripe, 'error'):
            if isinstance(e, stripe.error.StripeError):
                logger.error(f"Stripe APIエラー: {e}")
                return {
                    "status": "error",
                    "error": f"Stripe API error: {str(e)}",
                    "error_type": e.__class__.__name__
                }
        
        # その他のエラー
        logger.error(f"Stripe決済エラー: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def process_paypal_payment(amount: float, currency: str = "JPY", product_id: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    PayPal決済処理
    実際のPayPal APIを使用して決済を処理
    
    Args:
        amount: 決済金額
        currency: 通貨コード（デフォルト: JPY）
        product_id: 製品ID（オプション）
        metadata: 追加メタデータ（オプション）
    
    Returns:
        決済結果
    """
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        return {
            "status": "error",
            "error": "PayPal credentials not configured"
        }
    
    try:
        # PayPal APIをインポート（オプション）
        try:
            from paypalrestsdk import Payment as PayPalPayment
            import paypalrestsdk
            
            # PayPal SDK設定
            paypalrestsdk.configure({
                "mode": os.getenv("PAYPAL_MODE", "sandbox"),  # "sandbox" or "live"
                "client_id": PAYPAL_CLIENT_ID,
                "client_secret": PAYPAL_CLIENT_SECRET
            })
            
            logger.info(f"PayPal決済処理開始: {amount} {currency}")
            
            # Paymentオブジェクトを作成
            payment = PayPalPayment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "transactions": [{
                    "amount": {
                        "total": f"{amount:.2f}",
                        "currency": currency.upper()
                    },
                    "description": f"Payment for product: {product_id}" if product_id else "Payment",
                    "custom": json.dumps(metadata) if metadata else None
                }],
                "redirect_urls": {
                    "return_url": os.getenv(
                        "PAYPAL_RETURN_URL",
                        f"http://127.0.0.1:{PAYMENT_INTEGRATION_PORT}/api/payment/paypal/return",
                    ),
                    "cancel_url": os.getenv(
                        "PAYPAL_CANCEL_URL",
                        f"http://127.0.0.1:{PAYMENT_INTEGRATION_PORT}/api/payment/paypal/cancel",
                    )
                }
            })
            
            # Paymentを作成
            if payment.create():
                logger.info(f"PayPal決済処理成功: {payment.id}")
                
                # 承認URLを取得
                approval_url = None
                for link in payment.links:
                    if link.rel == "approval_url":
                        approval_url = link.href
                        break
                
                return {
                    "status": "success",
                    "payment_id": payment.id,
                    "approval_url": approval_url,
                    "amount": amount,
                    "currency": currency,
                    "state": payment.state
                }
            else:
                error_msg = payment.error if hasattr(payment, 'error') else "Unknown PayPal error"
                logger.error(f"PayPal決済エラー: {error_msg}")
                return {
                    "status": "error",
                    "error": str(error_msg)
                }
            
        except ImportError:
            # paypalrestsdkライブラリがインストールされていない場合はモック実装
            logger.warning("paypalrestsdkライブラリがインストールされていません。モック実装を使用します。")
            logger.info(f"PayPal決済処理（モック）: {amount} {currency}")
            
            return {
                "status": "success",
                "payment_id": f"paypal_mock_{datetime.now().timestamp()}",
                "amount": amount,
                "currency": currency,
                "note": "モック実装: paypalrestsdkライブラリをインストールしてください (pip install paypalrestsdk)"
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

