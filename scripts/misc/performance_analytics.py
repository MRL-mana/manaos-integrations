"""
パフォーマンス分析システム
詳細な分析とレポート生成
"""

import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import statistics

import psutil


class PerformanceAnalytics:
    """パフォーマンス分析システム"""
    
    def __init__(self):
        """初期化"""
        self.metrics_data = defaultdict(list)
        self.performance_reports = []
        self.storage_path = Path("performance_analytics_state.json")
        self._load_state()
    
    def _load_state(self):
        """状態を読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.metrics_data = defaultdict(list, state.get("metrics_data", {}))
                    self.performance_reports = state.get("reports", [])[-50:]
            except Exception:
                self.metrics_data = defaultdict(list)
                self.performance_reports = []
        else:
            self.metrics_data = defaultdict(list)
            self.performance_reports = []
    
    def _save_state(self):
        """状態を保存"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "metrics_data": dict(self.metrics_data),
                    "reports": self.performance_reports[-50:],
                    "last_updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"状態保存エラー: {e}")
    
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
            
            # データに追加
            for key, value in metrics.items():
                if key != "timestamp":
                    self.metrics_data[key].append({
                        "value": value,
                        "timestamp": datetime.now().isoformat()
                    })
            
            # 最新1000件のみ保持
            for key in self.metrics_data:
                if len(self.metrics_data[key]) > 1000:
                    self.metrics_data[key] = self.metrics_data[key][-1000:]
            
            self._save_state()
            return metrics
            
        except Exception as e:
            print(f"メトリクス収集エラー: {e}")
            return {}
    
    def analyze_performance(
        self,
        metric: str,
        time_range: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        パフォーマンスを分析
        
        Args:
            metric: メトリクス名
            time_range: 時間範囲（オプション）
            
        Returns:
            分析結果
        """
        if metric not in self.metrics_data:
            return {}
        
        data = self.metrics_data[metric]
        
        # 時間範囲でフィルタ
        if time_range:
            cutoff = datetime.now() - time_range
            data = [
                d for d in data
                if datetime.fromisoformat(d["timestamp"]) > cutoff
            ]
        
        if not data:
            return {}
        
        values = [d["value"] for d in data]
        
        analysis = {
            "metric": metric,
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "time_range": str(time_range) if time_range else "all"
        }
        
        # パーセンタイル
        if len(values) > 0:
            sorted_values = sorted(values)
            analysis["p95"] = sorted_values[int(len(sorted_values) * 0.95)]
            analysis["p99"] = sorted_values[int(len(sorted_values) * 0.99)]
        
        return analysis
    
    def generate_report(
        self,
        time_range: Optional[timedelta] = None,
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        レポートを生成
        
        Args:
            time_range: 時間範囲（オプション）
            metrics: メトリクスのリスト（オプション）
            
        Returns:
            レポート
        """
        if metrics is None:
            metrics = list(self.metrics_data.keys())
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "time_range": str(time_range) if time_range else "all",
            "metrics": {},
            "summary": {}
        }
        
        # 各メトリクスを分析
        for metric in metrics:
            analysis = self.analyze_performance(metric, time_range)
            if analysis:
                report["metrics"][metric] = analysis
        
        # サマリー
        if report["metrics"]:
            report["summary"] = {
                "total_metrics": len(report["metrics"]),
                "average_cpu": report["metrics"].get("cpu", {}).get("mean", 0),
                "average_memory": report["metrics"].get("memory", {}).get("mean", 0),
                "peak_cpu": report["metrics"].get("cpu", {}).get("max", 0),
                "peak_memory": report["metrics"].get("memory", {}).get("max", 0)
            }
        
        # レポート履歴に追加
        self.performance_reports.append(report)
        self._save_state()
        
        return report
    
    def detect_anomalies(self, metric: str, threshold: float = 2.0) -> List[Dict[str, Any]]:
        """
        異常値を検出
        
        Args:
            metric: メトリクス名
            threshold: 閾値（標準偏差の倍数）
            
        Returns:
            異常値のリスト
        """
        if metric not in self.metrics_data:
            return []
        
        analysis = self.analyze_performance(metric)
        if not analysis:
            return []
        
        mean = analysis["mean"]
        std_dev = analysis["std_dev"]
        
        anomalies = []
        for data_point in self.metrics_data[metric]:
            value = data_point["value"]
            z_score = abs((value - mean) / std_dev) if std_dev > 0 else 0
            
            if z_score > threshold:
                anomalies.append({
                    "value": value,
                    "z_score": z_score,
                    "timestamp": data_point["timestamp"],
                    "deviation": value - mean
                })
        
        return anomalies
    
    def get_trends(self, metric: str, days: int = 7) -> Dict[str, Any]:
        """
        トレンドを取得
        
        Args:
            metric: メトリクス名
            days: 日数
            
        Returns:
            トレンド情報
        """
        if metric not in self.metrics_data:
            return {}
        
        time_range = timedelta(days=days)
        cutoff = datetime.now() - time_range
        
        recent_data = [
            d for d in self.metrics_data[metric]
            if datetime.fromisoformat(d["timestamp"]) > cutoff
        ]
        
        if len(recent_data) < 2:
            return {}
        
        values = [d["value"] for d in recent_data]
        
        # 線形トレンドを計算（簡易版）
        n = len(values)
        x = list(range(n))
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator > 0 else 0
        
        return {
            "metric": metric,
            "period_days": days,
            "data_points": n,
            "trend": "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable",
            "slope": slope,
            "average": y_mean,
            "first_value": values[0],
            "last_value": values[-1],
            "change": values[-1] - values[0],
            "change_percent": ((values[-1] - values[0]) / values[0] * 100) if values[0] > 0 else 0
        }


def main():
    """テスト用メイン関数"""
    print("パフォーマンス分析システムテスト")
    print("=" * 60)
    
    analytics = PerformanceAnalytics()
    
    # メトリクスを収集
    print("\nメトリクスを収集中...")
    for _ in range(5):
        metrics = analytics.collect_metrics()
        print(f"  CPU: {metrics.get('cpu', 0):.1f}%, Memory: {metrics.get('memory', 0):.1f}%")
        time.sleep(1)
    
    # パフォーマンスを分析
    print("\nパフォーマンスを分析中...")
    cpu_analysis = analytics.analyze_performance("cpu")
    print(f"CPU分析: {cpu_analysis}")
    
    # レポートを生成
    print("\nレポートを生成中...")
    report = analytics.generate_report(time_range=timedelta(minutes=5))
    print(f"レポート: {report['summary']}")
    
    # トレンドを取得
    print("\nトレンドを取得中...")
    trend = analytics.get_trends("cpu", days=1)
    print(f"トレンド: {trend}")


if __name__ == "__main__":
    main()



















