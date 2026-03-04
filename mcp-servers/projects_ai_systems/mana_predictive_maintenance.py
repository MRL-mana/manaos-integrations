#!/usr/bin/env python3
"""
Mana Predictive Maintenance
予測メンテナンスシステム - リソース使用量を予測して事前最適化
"""

import json
import logging
import sqlite3
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaPredictiveMaintenance:
    def __init__(self):
        self.db_path = "/root/mana_predictive.db"
        self.init_database()
        
        # 予測設定
        self.config = {
            "prediction_window_hours": 24,  # 24時間先を予測
            "data_points_required": 10,     # 予測に必要なデータポイント数
            "alert_threshold": 85,          # 警告閾値（%）
            "critical_threshold": 95        # 緊急閾値（%）
        }
        
        logger.info("🔮 Mana Predictive Maintenance 初期化完了")
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # メトリクス履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                cpu_percent REAL,
                memory_percent REAL,
                disk_percent REAL,
                process_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 予測結果テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_time TEXT,
                metric_type TEXT,
                current_value REAL,
                predicted_value REAL,
                trend TEXT,
                confidence REAL,
                recommendation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def record_current_metrics(self) -> Dict[str, Any]:
        """現在のメトリクスを記録"""
        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            process_count = len(psutil.pids())
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": cpu,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "process_count": process_count
            }
            
            # データベースに保存
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO metrics_history 
                (timestamp, cpu_percent, memory_percent, disk_percent, process_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                metrics["timestamp"],
                metrics["cpu_percent"],
                metrics["memory_percent"],
                metrics["disk_percent"],
                metrics["process_count"]
            ))
            
            conn.commit()
            conn.close()
            
            return metrics
            
        except Exception as e:
            logger.error(f"メトリクス記録エラー: {e}")
            return {}
    
    def get_historical_data(self, metric_type: str, hours: int = 24) -> List[float]:
        """履歴データ取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            cursor.execute(f'''
                SELECT {metric_type} FROM metrics_history
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            ''', (since,))
            
            data = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return data
            
        except Exception as e:
            logger.error(f"履歴データ取得エラー: {e}")
            return []
    
    def predict_simple_linear(self, data: List[float]) -> Tuple[float, float, str]:
        """シンプルな線形予測"""
        if len(data) < 2:
            return (data[-1] if data else 0, 0.0, "insufficient_data")
        
        # 最近のトレンドを計算
        recent_data = data[-10:] if len(data) >= 10 else data
        
        # 単純な線形回帰（最小二乗法）
        x = np.array(range(len(recent_data)))
        y = np.array(recent_data)
        
        # 傾き計算
        slope = np.polyfit(x, y, 1)[0]
        
        # 24時間後の予測値
        prediction_steps = 24  # 1時間ごとのデータと仮定
        predicted_value = recent_data[-1] + (slope * prediction_steps)
        
        # トレンド判定
        if slope > 1:
            trend = "increasing"
        elif slope < -1:
            trend = "decreasing"
        else:
            trend = "stable"
        
        # 信頼度（簡易的）
        confidence = min(len(data) / self.config["data_points_required"], 1.0)
        
        return (predicted_value, confidence, trend)
    
    def predict_all_metrics(self) -> Dict[str, Any]:
        """全メトリクスを予測"""
        logger.info("🔮 リソース使用量を予測中...")
        
        predictions = {}
        
        for metric_type in ["cpu_percent", "memory_percent", "disk_percent"]:
            data = self.get_historical_data(metric_type, 24)
            
            if not data:
                logger.warning(f"データ不足: {metric_type}")
                continue
            
            predicted, confidence, trend = self.predict_simple_linear(data)
            current = data[-1]
            
            # 推奨事項
            recommendation = self._generate_recommendation(
                metric_type, 
                current, 
                predicted, 
                trend
            )
            
            predictions[metric_type] = {
                "current": round(current, 1),
                "predicted_24h": round(predicted, 1),
                "trend": trend,
                "confidence": round(confidence, 2),
                "recommendation": recommendation
            }
            
            # データベースに保存
            self._save_prediction(metric_type, current, predicted, trend, confidence, recommendation)
        
        logger.info(f"✅ 予測完了: {len(predictions)}メトリクス")
        return predictions
    
    def _generate_recommendation(
        self, 
        metric_type: str, 
        current: float, 
        predicted: float, 
        trend: str
    ) -> str:
        """推奨事項生成"""
        metric_name = {
            "cpu_percent": "CPU",
            "memory_percent": "メモリ",
            "disk_percent": "ディスク"
        }.get(metric_type, metric_type)
        
        if predicted > self.config["critical_threshold"]:
            return f"🔴 緊急: 24時間以内に{metric_name}が{predicted:.1f}%に達する見込み。即座に最適化を実行してください。"
        elif predicted > self.config["alert_threshold"]:
            return f"🟡 警告: 24時間以内に{metric_name}が{predicted:.1f}%に達する見込み。早めの最適化を推奨します。"
        elif trend == "increasing" and predicted > current + 10:
            return f"🟢 注意: {metric_name}が増加傾向です。監視を継続してください。"
        else:
            return f"✅ 正常: {metric_name}は安定しています。"
    
    def _save_prediction(
        self, 
        metric_type: str, 
        current: float, 
        predicted: float, 
        trend: str, 
        confidence: float,
        recommendation: str
    ):
        """予測結果を保存"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            prediction_time = (datetime.now() + timedelta(hours=24)).isoformat()
            
            cursor.execute('''
                INSERT INTO predictions 
                (prediction_time, metric_type, current_value, predicted_value, trend, confidence, recommendation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (prediction_time, metric_type, current, predicted, trend, confidence, recommendation))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"予測保存エラー: {e}")

def main():
    pm = ManaPredictiveMaintenance()
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "record":
        # メトリクス記録
        metrics = pm.record_current_metrics()
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
    else:
        # メトリクス記録 + 予測
        metrics = pm.record_current_metrics()
        predictions = pm.predict_all_metrics()
        
        print("\n" + "=" * 60)
        print("🔮 予測メンテナンスレポート")
        print("=" * 60)
        
        for metric_type, pred in predictions.items():
            metric_name = metric_type.replace("_percent", "").upper()
            print(f"\n{metric_name}:")
            print(f"  現在: {pred['current']:.1f}%")
            print(f"  24時間後予測: {pred['predicted_24h']:.1f}%")
            print(f"  トレンド: {pred['trend']}")
            print(f"  信頼度: {pred['confidence']:.0%}")
            print(f"  {pred['recommendation']}")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

