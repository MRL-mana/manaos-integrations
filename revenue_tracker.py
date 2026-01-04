#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💰 ManaOS 収益追跡システム
コスト・収益の管理、成果物の自動商品化
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("RevenueTracker")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

app = Flask(__name__)
CORS(app)

# データベース初期化
DB_PATH = Path(__file__).parent / "revenue_tracker.db"

def init_db():
    """データベース初期化"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # コスト記録テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            cost_type TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'JPY',
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 収益記録テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS revenue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT,
            product_type TEXT,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'JPY',
            source TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 成果物テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT UNIQUE NOT NULL,
            product_type TEXT NOT NULL,
            title TEXT,
            description TEXT,
            price REAL,
            currency TEXT DEFAULT 'JPY',
            file_path TEXT,
            status TEXT DEFAULT 'draft',
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("✅ Revenue Tracker DB初期化完了")

init_db()

def add_cost(service_name: str, cost_type: str, amount: float, currency: str = "JPY", metadata: Optional[Dict] = None):
    """コストを記録"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO costs (service_name, cost_type, amount, currency, metadata)
        VALUES (?, ?, ?, ?, ?)
    """, (service_name, cost_type, amount, currency, json.dumps(metadata or {})))
    
    conn.commit()
    conn.close()

def add_revenue(product_id: Optional[str], product_type: str, amount: float, currency: str = "JPY", source: str = "unknown", metadata: Optional[Dict] = None):
    """収益を記録"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO revenue (product_id, product_type, amount, currency, source, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (product_id, product_type, amount, currency, source, json.dumps(metadata or {})))
    
    conn.commit()
    conn.close()

def create_product(product_id: str, product_type: str, title: str, description: str = "", price: float = 0.0, currency: str = "JPY", file_path: str = "", metadata: Optional[Dict] = None):
    """成果物を作成"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO products (product_id, product_type, title, description, price, currency, file_path, status, metadata, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'draft', ?, CURRENT_TIMESTAMP)
    """, (product_id, product_type, title, description, price, currency, file_path, json.dumps(metadata or {})))
    
    conn.commit()
    conn.close()

def get_statistics(days: int = 30) -> Dict[str, Any]:
    """統計情報を取得"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    start_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    # コスト合計
    cursor.execute("""
        SELECT SUM(amount) FROM costs
        WHERE created_at >= ?
    """, (start_date,))
    total_costs = cursor.fetchone()[0] or 0.0
    
    # 収益合計
    cursor.execute("""
        SELECT SUM(amount) FROM revenue
        WHERE created_at >= ?
    """, (start_date,))
    total_revenue = cursor.fetchone()[0] or 0.0
    
    # 利益
    profit = total_revenue - total_costs
    
    # サービス別コスト
    cursor.execute("""
        SELECT service_name, SUM(amount) as total
        FROM costs
        WHERE created_at >= ?
        GROUP BY service_name
        ORDER BY total DESC
    """, (start_date,))
    costs_by_service = {row[0]: row[1] for row in cursor.fetchall()}
    
    # 成果物数
    cursor.execute("""
        SELECT COUNT(*) FROM products
        WHERE created_at >= ?
    """, (start_date,))
    product_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "period_days": days,
        "total_costs": total_costs,
        "total_revenue": total_revenue,
        "profit": profit,
        "profit_margin": (profit / total_revenue * 100) if total_revenue > 0 else 0.0,
        "costs_by_service": costs_by_service,
        "product_count": product_count
    }

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Revenue Tracker"})

@app.route('/api/cost', methods=['POST'])
def add_cost_endpoint():
    """コスト記録"""
    data = request.get_json()
    
    service_name = data.get("service_name", "unknown")
    cost_type = data.get("cost_type", "api_call")
    amount = float(data.get("amount", 0.0))
    currency = data.get("currency", "JPY")
    metadata = data.get("metadata")
    
    add_cost(service_name, cost_type, amount, currency, metadata)
    
    return jsonify({
        "status": "success",
        "message": "コストを記録しました"
    })

@app.route('/api/revenue', methods=['POST'])
def add_revenue_endpoint():
    """収益記録"""
    data = request.get_json()
    
    product_id = data.get("product_id")
    product_type = data.get("product_type", "unknown")
    amount = float(data.get("amount", 0.0))
    currency = data.get("currency", "JPY")
    source = data.get("source", "unknown")
    metadata = data.get("metadata")
    
    add_revenue(product_id, product_type, amount, currency, source, metadata)
    
    return jsonify({
        "status": "success",
        "message": "収益を記録しました"
    })

@app.route('/api/product', methods=['POST'])
def create_product_endpoint():
    """成果物作成"""
    data = request.get_json()
    
    product_id = data.get("product_id")
    if not product_id:
        return jsonify({"status": "error", "error": "product_id is required"}), 400
    
    product_type = data.get("product_type", "unknown")
    title = data.get("title", "")
    description = data.get("description", "")
    price = float(data.get("price", 0.0))
    currency = data.get("currency", "JPY")
    file_path = data.get("file_path", "")
    metadata = data.get("metadata")
    
    create_product(product_id, product_type, title, description, price, currency, file_path, metadata)
    
    return jsonify({
        "status": "success",
        "message": "成果物を作成しました",
        "product_id": product_id
    })

@app.route('/api/statistics', methods=['GET'])
def get_statistics_endpoint():
    """統計情報取得"""
    days = request.args.get("days", 30, type=int)
    stats = get_statistics(days)
    return jsonify(stats)

@app.route('/api/products', methods=['GET'])
def get_products_endpoint():
    """成果物一覧取得"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    status = request.args.get("status")
    if status:
        cursor.execute("""
            SELECT * FROM products
            WHERE status = ?
            ORDER BY created_at DESC
        """, (status,))
    else:
        cursor.execute("""
            SELECT * FROM products
            ORDER BY created_at DESC
        """)
    
    products = []
    for row in cursor.fetchall():
        products.append({
            "id": row[0],
            "product_id": row[1],
            "product_type": row[2],
            "title": row[3],
            "description": row[4],
            "price": row[5],
            "currency": row[6],
            "file_path": row[7],
            "status": row[8],
            "metadata": json.loads(row[9] or "{}"),
            "created_at": row[10],
            "updated_at": row[11]
        })
    
    conn.close()
    
    return jsonify({
        "products": products,
        "count": len(products)
    })

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5117))
    logger.info(f"💰 Revenue Tracker起動中... (ポート: {port})")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

