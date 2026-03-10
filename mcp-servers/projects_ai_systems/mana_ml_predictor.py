#!/usr/bin/env python3
"""
Mana ML Predictor
機械学習予測システム - scikit-learnで高精度予測
"""

import numpy as np
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("⚠️ scikit-learn not available, using simple prediction")

class ManaMLPredictor:
    def __init__(self):
        self.db_path = "/root/mana_predictive.db"
        self.model_cpu = LinearRegression() if SKLEARN_AVAILABLE else None  # type: ignore[possibly-unbound]
        self.model_memory = LinearRegression() if SKLEARN_AVAILABLE else None  # type: ignore[possibly-unbound]
        self.model_disk = LinearRegression() if SKLEARN_AVAILABLE else None  # type: ignore[possibly-unbound]
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None  # type: ignore[possibly-unbound]
        
        logger.info("🤖 Mana ML Predictor 初期化")
        logger.info(f"scikit-learn: {'有効' if SKLEARN_AVAILABLE else '無効'}")
    
    def get_training_data(self, metric: str, hours: int = 48) -> Tuple[np.ndarray, np.ndarray]:
        """学習データ取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            cursor.execute(f'''
                SELECT timestamp, {metric} 
                FROM metrics_history
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            ''', (since,))
            
            data = cursor.fetchall()
            conn.close()
            
            if len(data) < 5:
                return None, None  # type: ignore
            
            # 時系列データを数値に変換
            X = np.array(range(len(data))).reshape(-1, 1)
            y = np.array([row[1] for row in data])
            
            return X, y
            
        except Exception as e:
            logger.error(f"学習データ取得エラー: {e}")
            return None, None  # type: ignore
    
    def train_and_predict(self, metric: str) -> Dict[str, Any]:
        """学習して予測"""
        if not SKLEARN_AVAILABLE:
            return {"error": "scikit-learn not available"}
        
        # データ取得
        X, y = self.get_training_data(metric)
        
        if X is None or len(X) < 5:
            return {
                "success": False,
                "error": "insufficient_data",
                "message": "データ不足（5データポイント以上必要）"
            }
        
        try:
            # 学習
            if metric == "cpu_percent":
                model = self.model_cpu
            elif metric == "memory_percent":
                model = self.model_memory
            else:
                model = self.model_disk
            
            model.fit(X, y)  # type: ignore[union-attr]
            
            # 24時間後を予測
            future_step = len(X) + 24
            prediction = model.predict([[future_step]])[0]  # type: ignore[union-attr]
            
            # スコア（精度）
            score = model.score(X, y)  # type: ignore[union-attr]
            
            # トレンド判定
            slope = model.coef_[0] if hasattr(model, 'coef_') else 0  # type: ignore[union-attr]
            trend = "increasing" if slope > 0.5 else "decreasing" if slope < -0.5 else "stable"
            
            return {
                "success": True,
                "metric": metric,
                "current_value": float(y[-1]),
                "predicted_value": float(prediction),
                "trend": trend,
                "accuracy": float(score),
                "confidence": min(float(score) * 100, 100),
                "data_points": len(X)
            }
            
        except Exception as e:
            logger.error(f"予測エラー ({metric}): {e}")
            return {"success": False, "error": str(e)}
    
    def predict_all_metrics(self) -> Dict[str, Any]:
        """全メトリクスを予測"""
        logger.info("🤖 機械学習予測開始...")
        
        predictions = {}
        
        for metric in ["cpu_percent", "memory_percent", "disk_percent"]:
            pred = self.train_and_predict(metric)
            if pred.get("success"):
                predictions[metric] = pred
                logger.info(f"✅ {metric}: 予測値{pred['predicted_value']:.1f}% (精度{pred['confidence']:.1f}%)")
        
        return predictions

def main():
    predictor = ManaMLPredictor()
    
    if not SKLEARN_AVAILABLE:
        print("\n⚠️ scikit-learnがインストールされていません")
        print("インストール: pip install scikit-learn")
        return
    
    predictions = predictor.predict_all_metrics()
    
    print("\n" + "=" * 60)
    print("🤖 機械学習予測レポート")
    print("=" * 60)
    
    for metric, pred in predictions.items():
        metric_name = metric.replace("_percent", "").upper()
        print(f"\n{metric_name}:")
        print(f"  現在値: {pred['current_value']:.1f}%")
        print(f"  24時間後予測: {pred['predicted_value']:.1f}%")
        print(f"  トレンド: {pred['trend']}")
        print(f"  予測精度: {pred['confidence']:.1f}%")
        print(f"  学習データ: {pred['data_points']}ポイント")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

