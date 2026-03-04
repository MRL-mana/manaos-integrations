#!/usr/bin/env python3
"""
Mana AI Task Predictor
AIタスク予測システム - Trinity Secretary + Predictive Maintenance統合
過去のパターンから次のタスクを予測
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaAITaskPredictor:
    def __init__(self):
        # Trinity Secretaryのデータベース
        self.trinity_db = "/root/trinity_secretary_enhanced.db"
        self.predictor_db = "/root/mana_task_predictor.db"
        
        self.init_database()
        
        # 予測設定
        self.config = {
            "prediction_confidence_threshold": 0.6,
            "max_predictions": 5,
            "time_window_days": 30
        }
        
        logger.info("🔮 Mana AI Task Predictor 初期化完了")
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.predictor_db)
        cursor = conn.cursor()
        
        # 予測タスクテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predicted_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                predicted_title TEXT,
                predicted_category TEXT,
                predicted_priority TEXT,
                confidence REAL,
                reasoning TEXT,
                suggested_due_date TEXT,
                created BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # タスクパターンテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT,
                frequency TEXT,
                typical_time TEXT,
                typical_day TEXT,
                confidence REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def analyze_task_patterns(self) -> Dict[str, Any]:
        """タスクパターン分析"""
        try:
            conn = sqlite3.connect(self.trinity_db)
            cursor = conn.cursor()
            
            # 過去30日のタスクを取得
            since = (datetime.now() - timedelta(days=30)).isoformat()
            
            cursor.execute('''
                SELECT title, category, priority, due_date, created_at
                FROM smart_tasks
                WHERE created_at >= ?
                ORDER BY created_at DESC
            ''', (since,))
            
            tasks = cursor.fetchall()
            conn.close()
            
            if not tasks:
                return {"patterns": [], "message": "データ不足"}
            
            # カテゴリ別頻度
            categories = Counter([task[1] for task in tasks if task[1]])
            
            # 優先度パターン
            priorities = Counter([task[2] for task in tasks if task[2]])
            
            # 曜日パターン（よく作成される曜日）
            weekdays = []
            for task in tasks:
                try:
                    created = datetime.fromisoformat(task[4])
                    weekdays.append(created.strftime("%A"))
                except Exception:
                    continue
            
            weekday_pattern = Counter(weekdays)
            
            # タイトルキーワード分析
            all_words = []
            for task in tasks:
                words = task[0].split() if task[0] else []
                all_words.extend([w for w in words if len(w) > 2])
            
            common_keywords = Counter(all_words).most_common(10)
            
            patterns = {
                "total_tasks": len(tasks),
                "most_common_category": categories.most_common(1)[0] if categories else ("general", 0),
                "most_common_priority": priorities.most_common(1)[0] if priorities else ("medium", 0),
                "most_active_day": weekday_pattern.most_common(1)[0] if weekday_pattern else ("Monday", 0),
                "common_keywords": common_keywords,
                "categories": dict(categories),
                "priorities": dict(priorities)
            }
            
            logger.info(f"パターン分析完了: {len(tasks)}タスク")
            return patterns
            
        except Exception as e:
            logger.error(f"パターン分析エラー: {e}")
            return {}
    
    def predict_next_tasks(self) -> List[Dict[str, Any]]:
        """次のタスクを予測"""
        logger.info("🔮 タスク予測中...")
        
        patterns = self.analyze_task_patterns()
        
        if not patterns or "most_common_category" not in patterns:
            return []
        
        predictions = []
        
        # パターンベースの予測
        category, cat_count = patterns["most_common_category"]
        priority, pri_count = patterns["most_common_priority"]
        
        # 信頼度計算
        total = patterns["total_tasks"]
        confidence = cat_count / total if total > 0 else 0
        
        # 曜日ベースの予測
        now = datetime.now()
        most_active_day = patterns.get("most_active_day", ("Monday", 0))[0]
        
        # 予測タスク生成
        if confidence > 0.3:  # 30%以上の信頼度
            # よく使うキーワードから予測
            keywords = patterns.get("common_keywords", [])
            
            if keywords:
                top_keyword = keywords[0][0]
                
                predictions.append({
                    "predicted_title": f"{top_keyword}関連のタスク",
                    "predicted_category": category,
                    "predicted_priority": priority,
                    "confidence": round(confidence, 2),
                    "reasoning": f"過去{total}タスク中{cat_count}タスクが{category}カテゴリ",
                    "suggested_due_date": (now + timedelta(days=3)).strftime("%Y-%m-%d")
                })
        
        # 定期タスクの予測（例：週次レポート、月次チェック）
        if "レポート" in str(patterns.get("common_keywords", [])):
            predictions.append({
                "predicted_title": "週次レポート作成",
                "predicted_category": "仕事",
                "predicted_priority": "medium",
                "confidence": 0.7,
                "reasoning": "週次レポートが頻繁に作成されています",
                "suggested_due_date": (now + timedelta(days=7)).strftime("%Y-%m-%d")
            })
        
        # データベースに保存
        self._save_predictions(predictions)
        
        logger.info(f"✅ {len(predictions)}個のタスクを予測")
        return predictions
    
    def _save_predictions(self, predictions: List[Dict[str, Any]]):
        """予測を保存"""
        try:
            conn = sqlite3.connect(self.predictor_db)
            cursor = conn.cursor()
            
            for pred in predictions:
                cursor.execute('''
                    INSERT INTO predicted_tasks 
                    (predicted_title, predicted_category, predicted_priority, confidence, reasoning, suggested_due_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    pred["predicted_title"],
                    pred["predicted_category"],
                    pred["predicted_priority"],
                    pred["confidence"],
                    pred["reasoning"],
                    pred["suggested_due_date"]
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"予測保存エラー: {e}")

def main():
    predictor = ManaAITaskPredictor()
    
    print("\n" + "=" * 60)
    print("🔮 AIタスク予測レポート")
    print("=" * 60)
    
    patterns = predictor.analyze_task_patterns()
    print("\nタスクパターン分析:")
    print(f"  総タスク数: {patterns.get('total_tasks', 0)}")
    print(f"  最多カテゴリ: {patterns.get('most_common_category', ('N/A', 0))[0]}")
    print(f"  最多優先度: {patterns.get('most_common_priority', ('N/A', 0))[0]}")
    print(f"  最もアクティブな曜日: {patterns.get('most_active_day', ('N/A', 0))[0]}")
    
    predictions = predictor.predict_next_tasks()
    
    if predictions:
        print(f"\n予測されたタスク: {len(predictions)}個")
        for i, pred in enumerate(predictions, 1):
            print(f"\n  {i}. {pred['predicted_title']}")
            print(f"     カテゴリ: {pred['predicted_category']}")
            print(f"     優先度: {pred['predicted_priority']}")
            print(f"     信頼度: {pred['confidence']:.0%}")
            print(f"     期限推奨: {pred['suggested_due_date']}")
            print(f"     理由: {pred['reasoning']}")
    else:
        print("\n予測タスクなし（データ蓄積中）")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

