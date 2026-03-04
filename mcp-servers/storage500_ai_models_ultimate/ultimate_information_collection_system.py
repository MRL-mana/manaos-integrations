#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
究極情報収集システム
情報収集Botの再分類、ジャンル分け、自動分類精度向上
"""

import json
import logging
import random
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from flask import Flask, jsonify, request
import requests
import hashlib
import os
import re
from dataclasses import dataclass
from enum import Enum

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_information_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class InformationCategory(Enum):
    """情報カテゴリ"""
    TECHNOLOGY = "technology"
    BUSINESS = "business"
    FINANCE = "finance"
    AI_ML = "ai_ml"
    CRYPTO = "crypto"
    GENERAL = "general"

@dataclass
class InformationItem:
    """情報アイテム"""
    id: str
    title: str
    content: str
    url: str
    source: str
    category: InformationCategory
    confidence: float
    tags: List[str]
    published_at: Optional[datetime]
    collected_at: datetime
    sentiment: float
    importance_score: float

class ContentAnalyzer:
    """コンテンツ分析エンジン"""
    
    def __init__(self):
        self.category_keywords = {
            InformationCategory.TECHNOLOGY: ['technology', 'tech', 'software', 'hardware', 'programming'],
            InformationCategory.BUSINESS: ['business', 'company', 'startup', 'enterprise', 'market'],
            InformationCategory.FINANCE: ['finance', 'money', 'investment', 'stock', 'trading'],
            InformationCategory.AI_ML: ['ai', 'artificial intelligence', 'machine learning', 'deep learning'],
            InformationCategory.CRYPTO: ['cryptocurrency', 'bitcoin', 'ethereum', 'blockchain', 'crypto']
        }
        
    def analyze_content(self, title: str, content: str) -> Dict[str, Any]:
        """コンテンツの分析"""
        text = (title + ' ' + content).lower()
        
        # カテゴリ分類
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            confidence = min(1.0, best_category[1] / 3.0)
            category = best_category[0]
        else:
            category = InformationCategory.GENERAL
            confidence = 0.1
        
        # 感情分析（簡略化）
        positive_words = ['good', 'great', 'excellent', 'amazing', 'success']
        negative_words = ['bad', 'terrible', 'awful', 'failure', 'problem']
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        total_sentiment = positive_count + negative_count
        sentiment = (positive_count - negative_count) / max(1, total_sentiment)
        
        # 重要度スコア
        importance_score = min(1.0, len(title.split()) / 20.0 + len(content.split()) / 500.0)
        
        # タグ抽出
        tags = [word for word in text.split() if len(word) > 3][:5]
        
        return {
            'category': category,
            'confidence': confidence,
            'sentiment': sentiment,
            'importance_score': importance_score,
            'tags': tags
        }

class UltimateInformationCollectionSystem:
    """究極情報収集システム"""
    
    def __init__(self):
        self.content_analyzer = ContentAnalyzer()
        self.information_items: Dict[str, InformationItem] = {}
        self.system_state = {
            'total_items': 0,
            'categorized_items': 0,
            'collection_cycles': 0,
            'last_collection': None,
            'category_distribution': {},
            'average_confidence': 0.0,
            'average_sentiment': 0.0
        }
        self.db_path = 'ultimate_information_collection.db'
        self.init_database()
        self.running = False
        self.collection_thread = None
        
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS information_items (
                id TEXT PRIMARY KEY,
                title TEXT,
                content TEXT,
                url TEXT,
                source TEXT,
                category TEXT,
                confidence REAL,
                tags TEXT,
                published_at TEXT,
                collected_at TEXT,
                sentiment REAL,
                importance_score REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def save_information_item(self, item: InformationItem):
        """情報アイテムの保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO information_items 
            (id, title, content, url, source, category, confidence, tags,
             published_at, collected_at, sentiment, importance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item.id, item.title, item.content, item.url, item.source,
            item.category.value, item.confidence, json.dumps(item.tags),
            item.published_at.isoformat() if item.published_at else None,
            item.collected_at.isoformat(), item.sentiment, item.importance_score
        ))
        
        conn.commit()
        conn.close()
        
    def collection_cycle(self):
        """収集サイクル"""
        # サンプルデータ生成
        sample_items = [
            {
                'title': 'AI Technology Breakthrough in Machine Learning',
                'content': 'Scientists have discovered a new approach to machine learning that could revolutionize the field of artificial intelligence.',
                'url': 'https://example.com/ai-breakthrough',
                'source': 'Tech News',
                'published_at': datetime.now() - timedelta(hours=2)
            },
            {
                'title': 'Bitcoin Reaches New All-Time High',
                'content': 'Cryptocurrency markets are experiencing unprecedented growth as Bitcoin reaches new record levels.',
                'url': 'https://example.com/bitcoin-high',
                'source': 'Finance Daily',
                'published_at': datetime.now() - timedelta(hours=1)
            },
            {
                'title': 'New Startup Raises $10M in Series A Funding',
                'content': 'Innovative startup company has successfully raised significant funding to expand their business operations.',
                'url': 'https://example.com/startup-funding',
                'source': 'Business Weekly',
                'published_at': datetime.now() - timedelta(hours=3)
            }
        ]
        
        # 分析と分類
        for raw_item in sample_items:
            analysis = self.content_analyzer.analyze_content(
                raw_item['title'], raw_item['content']
            )
            
            # InformationItemの作成
            item_id = hashlib.md5(f"{raw_item['url']}_{time.time()}".encode()).hexdigest()
            
            item = InformationItem(
                id=item_id,
                title=raw_item['title'],
                content=raw_item['content'],
                url=raw_item['url'],
                source=raw_item['source'],
                category=analysis['category'],
                confidence=analysis['confidence'],
                tags=analysis['tags'],
                published_at=raw_item['published_at'],
                collected_at=datetime.now(),
                sentiment=analysis['sentiment'],
                importance_score=analysis['importance_score']
            )
            
            # 保存
            self.information_items[item_id] = item
            self.save_information_item(item)
        
        # システム状態の更新
        self.update_system_state()
        
        # ログ出力
        logger.info(f"情報収集サイクル実行")
        logger.info(f"収集アイテム数: {len(sample_items)}")
        logger.info(f"総アイテム数: {self.system_state['total_items']}")
        logger.info(f"分類済みアイテム数: {self.system_state['categorized_items']}")
        
        return self.system_state.copy()
    
    def update_system_state(self):
        """システム状態の更新"""
        total_items = len(self.information_items)
        categorized_items = len([item for item in self.information_items.values() 
                               if item.category != InformationCategory.GENERAL])
        
        # カテゴリ分布
        category_distribution = {}
        for item in self.information_items.values():
            category = item.category.value
            category_distribution[category] = category_distribution.get(category, 0) + 1
        
        # 平均値の計算
        confidences = [item.confidence for item in self.information_items.values()]
        sentiments = [item.sentiment for item in self.information_items.values()]
        
        avg_confidence = np.mean(confidences) if confidences else 0.0
        avg_sentiment = np.mean(sentiments) if sentiments else 0.0
        
        self.system_state.update({
            'total_items': total_items,
            'categorized_items': categorized_items,
            'collection_cycles': self.system_state['collection_cycles'] + 1,
            'last_collection': time.time(),
            'category_distribution': category_distribution,
            'average_confidence': avg_confidence,
            'average_sentiment': avg_sentiment
        })
    
    def get_items_by_category(self, category: InformationCategory) -> List[Dict[str, Any]]:
        """カテゴリ別アイテム取得"""
        items = [item for item in self.information_items.values() if item.category == category]
        return [self.item_to_dict(item) for item in items]
    
    def item_to_dict(self, item: InformationItem) -> Dict[str, Any]:
        """アイテムを辞書に変換"""
        return {
            'id': item.id,
            'title': item.title,
            'content': item.content[:200] + '...' if len(item.content) > 200 else item.content,
            'url': item.url,
            'source': item.source,
            'category': item.category.value,
            'category_name': item.category.name,
            'confidence': item.confidence,
            'tags': item.tags,
            'published_at': item.published_at.isoformat() if item.published_at else None,
            'collected_at': item.collected_at.isoformat(),
            'sentiment': item.sentiment,
            'importance_score': item.importance_score
        }
    
    def start_collection(self):
        """収集プロセスの開始"""
        if self.running:
            return
            
        self.running = True
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()
        logger.info("究極情報収集システムを開始しました")
    
    def stop_collection(self):
        """収集プロセスの停止"""
        self.running = False
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        logger.info("究極情報収集システムを停止しました")
    
    def _collection_loop(self):
        """収集ループ"""
        while self.running:
            try:
                self.collection_cycle()
                time.sleep(3600)  # 1時間間隔で収集
            except Exception as e:
                logger.error(f"収集サイクルでエラーが発生: {e}")
                time.sleep(300)  # 5分待機

# Flask Web API
app = Flask(__name__)
collection_system = UltimateInformationCollectionSystem()

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'system': 'Ultimate Information Collection System',
        'timestamp': time.time()
    })

@app.route('/api/information-collection-data', methods=['GET'])
def get_information_collection_data():
    """情報収集データの取得"""
    return jsonify({
        'system_state': collection_system.system_state,
        'timestamp': time.time()
    })

@app.route('/api/items/category/<category>', methods=['GET'])
def get_items_by_category(category):
    """カテゴリ別アイテム取得"""
    try:
        category_enum = InformationCategory(category)
        items = collection_system.get_items_by_category(category_enum)
        return jsonify(items)
    except ValueError:
        return jsonify({'error': '無効なカテゴリ'}), 400

@app.route('/api/collection-control', methods=['POST'])
def collection_control():
    """収集制御"""
    data = request.get_json()
    action = data.get('action')
    
    if action == 'start':
        collection_system.start_collection()
        return jsonify({'status': 'started'})
    elif action == 'stop':
        collection_system.stop_collection()
        return jsonify({'status': 'stopped'})
    else:
        return jsonify({'error': '無効なアクション'}), 400

if __name__ == '__main__':
    # 収集プロセスの開始
    collection_system.start_collection()
    
    # Web APIの開始
    app.run(host='0.0.0.0', port=5017, debug=False) 