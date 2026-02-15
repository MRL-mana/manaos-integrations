"""
予測的メンテナンスシステム
リソース使用予測と自動最適化
"""

import json
import time
import psutil
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("scikit-learnがインストールされていません。予測機能が制限されます。")


class PredictiveMaintenance:
    """予測的メンテナンスシステム"""
    
    def __init__(self, history_size: int = 100):
        """
        初期化
        
        Args:
            history_size: 履歴サイズ
        """
        self.history_size = history_size
        self.metrics_history = {
            "cpu": deque(maxlen=history_size),
            "memory": deque(maxlen=history_size),
            "disk": deque(maxlen=history_size),
            "network": deque(maxlen=history_size),
            "timestamp": deque(maxlen=history_size)
        }
        
        self.predictions = {}
        self.alerts = []
        self.storage_path = Path("predictive_maintenance_state.json")
        self._load_state()
        
        # 予測モデル（scikit-learnが利用可能な場合）
        self.models = {}
        self.scalers = {}
        
        if SKLEARN_AVAILABLE:
            self._initialize_models()
    
    def _initialize_models(self):
        """予測モデルを初期化"""
        for metric in ["cpu", "memory", "disk"]:
            self.models[metric] = LinearRegression()
            self.scalers[metric] = StandardScaler()
    
    def _load_state(self):
        """状態を読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    for key, values in state.get("metrics_history", {}).items():
                        self.metrics_history[key] = deque(values[-self.history_size:], maxlen=self.history_size)
                    self.alerts = state.get("alerts", [])[-50:]  # 最新50件のみ
            except Exception:
                pass
    
    def _save_state(self, max_retries: int = 3):
        """状態を保存（リトライ機能付き）"""
        for attempt in range(max_retries):
            try:
                from pathlib import Path
                self.storage_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path = Path(str(self.storage_path) + '.tmp')
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "metrics_history": {k: list(v) for k, v in self.metrics_history.items()},
                        "alerts": self.alerts[-50:],
                        "last_updated": datetime.now().isoformat()
                    }, f, ensure_ascii=False, indent=2)
                temp_path.replace(self.storage_path)
                return
            except Exception as e:
                if attempt == max_retries - 1:
                    from manaos_logger import get_logger
                    logger = get_logger(__name__)
                    logger.warning(f"状態保存エラー（{max_retries}回リトライ後）: {e}")
                else:
                    import time
                    time.sleep(0.1 * (attempt + 1))
    
    def collect_metrics(self) -> Dict[str, float]:
        """
        メトリクスを収集
        
        Returns:
            メトリクスの辞書
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            metrics = {
                "cpu": cpu_percent,
                "memory": memory.percent,
                "disk": disk.percent,
                "network_sent": network.bytes_sent / (1024 * 1024),  # MB
                "network_recv": network.bytes_recv / (1024 * 1024),  # MB
                "timestamp": time.time()
            }
            
            # 履歴に追加
            self.metrics_history["cpu"].append(cpu_percent)
            self.metrics_history["memory"].append(memory.percent)
            self.metrics_history["disk"].append(disk.percent)
            self.metrics_history["network"].append(metrics["network_sent"] + metrics["network_recv"])
            self.metrics_history["timestamp"].append(metrics["timestamp"])
            
            self._save_state()
            
            return metrics
            
        except Exception as e:
            print(f"メトリクス収集エラー: {e}")
            return {}
    
    def predict_future_usage(self, metric: str, hours_ahead: int = 1) -> Optional[float]:
        """
        将来の使用率を予測
        
        Args:
            metric: メトリクス名（cpu, memory, disk）
            hours_ahead: 何時間先を予測するか
            
        Returns:
            予測値（パーセント）
        """
        if not SKLEARN_AVAILABLE or metric not in ["cpu", "memory", "disk"]:
            return None
        
        if len(self.metrics_history[metric]) < 10:
            return None
        
        try:
            # データを準備
            X = np.array(list(range(len(self.metrics_history[metric])))).reshape(-1, 1)
            y = np.array(list(self.metrics_history[metric]))
            
            # スケーリング
            X_scaled = self.scalers[metric].fit_transform(X)
            
            # モデルを訓練
            self.models[metric].fit(X_scaled, y)
            
            # 将来の値を予測
            future_point = len(self.metrics_history[metric]) + hours_ahead
            future_X = np.array([[future_point]])
            future_X_scaled = self.scalers[metric].transform(future_X)
            prediction = self.models[metric].predict(future_X_scaled)[0]
            
            return max(0, min(100, prediction))  # 0-100の範囲に制限
            
        except Exception as e:
            print(f"予測エラー: {e}")
            return None
    
    def check_thresholds(self, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        閾値をチェック
        
        Args:
            metrics: メトリクスの辞書
            
        Returns:
            アラートのリスト
        """
        alerts = []
        thresholds = {
            "cpu": 80.0,
            "memory": 85.0,
            "disk": 90.0
        }
        
        for metric, threshold in thresholds.items():
            value = metrics.get(metric, 0)
            if value > threshold:
                alert = {
                    "type": "threshold_exceeded",
                    "metric": metric,
                    "value": value,
                    "threshold": threshold,
                    "severity": "high" if value > threshold * 1.2 else "medium",
                    "timestamp": datetime.now().isoformat()
                }
                alerts.append(alert)
                self.alerts.append(alert)
        
        # 予測ベースのアラート
        for metric in ["cpu", "memory", "disk"]:
            prediction = self.predict_future_usage(metric, hours_ahead=1)
            if prediction and prediction > thresholds[metric]:
                alert = {
                    "type": "predicted_threshold",
                    "metric": metric,
                    "predicted_value": prediction,
                    "threshold": thresholds[metric],
                    "hours_ahead": 1,
                    "severity": "medium",
                    "timestamp": datetime.now().isoformat()
                }
                alerts.append(alert)
        
        self._save_state()
        return alerts
    
    def get_recommendations(self, metrics: Dict[str, float]) -> List[str]:
        """
        推奨事項を取得
        
        Args:
            metrics: メトリクスの辞書
            
        Returns:
            推奨事項のリスト
        """
        recommendations = []
        
        # CPU推奨事項
        cpu = metrics.get("cpu", 0)
        if cpu > 80:
            recommendations.append("CPU使用率が高いです。不要なプロセスを終了することを検討してください。")
        elif cpu < 20:
            recommendations.append("CPU使用率が低いです。より多くのタスクを実行できます。")
        
        # メモリ推奨事項
        memory = metrics.get("memory", 0)
        if memory > 85:
            recommendations.append("メモリ使用率が高いです。キャッシュをクリアすることを検討してください。")
        
        # ディスク推奨事項
        disk = metrics.get("disk", 0)
        if disk > 90:
            recommendations.append("ディスク使用率が高いです。不要なファイルを削除することを検討してください。")
        
        # 予測ベースの推奨事項
        for metric in ["cpu", "memory", "disk"]:
            prediction = self.predict_future_usage(metric, hours_ahead=2)
            if prediction and prediction > 80:
                recommendations.append(f"{metric.upper()}使用率が2時間以内に{prediction:.1f}%に達する可能性があります。事前に対策を検討してください。")
        
        return recommendations
    
    def get_status(self) -> Dict[str, Any]:
        """状態を取得"""
        current_metrics = self.collect_metrics()
        alerts = self.check_thresholds(current_metrics)
        recommendations = self.get_recommendations(current_metrics)
        
        predictions = {}
        for metric in ["cpu", "memory", "disk"]:
            pred_1h = self.predict_future_usage(metric, hours_ahead=1)
            pred_2h = self.predict_future_usage(metric, hours_ahead=2)
            if pred_1h or pred_2h:
                predictions[metric] = {
                    "1h": pred_1h,
                    "2h": pred_2h
                }
        
        return {
            "current_metrics": current_metrics,
            "predictions": predictions,
            "alerts": alerts,
            "recommendations": recommendations,
            "alert_count": len(self.alerts),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("予測的メンテナンスシステムテスト")
    print("=" * 60)
    
    maintenance = PredictiveMaintenance()
    
    # メトリクスを収集
    print("\nメトリクスを収集中...")
    metrics = maintenance.collect_metrics()
    print(f"現在のメトリクス: {metrics}")
    
    # 状態を取得
    status = maintenance.get_status()
    print(f"\n状態:")
    print(f"  アラート数: {status['alert_count']}")
    print(f"  推奨事項: {len(status['recommendations'])}件")
    
    if status['recommendations']:
        print("\n推奨事項:")
        for rec in status['recommendations']:
            print(f"  - {rec}")
    
    if status['predictions']:
        print("\n予測:")
        for metric, preds in status['predictions'].items():
            print(f"  {metric}: 1時間後={preds.get('1h', 'N/A'):.1f}%, 2時間後={preds.get('2h', 'N/A'):.1f}%")


if __name__ == "__main__":
    main()

