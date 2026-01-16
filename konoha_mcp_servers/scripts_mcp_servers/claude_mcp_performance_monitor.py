#!/usr/bin/env python3
"""
クロードMCPパフォーマンス監視システム
"""

import psutil
import json
import time
from datetime import datetime

class PerformanceMonitor:
    def __init__(self):
        self.metrics = []
        self.thresholds = {
            "cpu_usage": 80,
            "memory_usage": 85,
            "disk_usage": 90
        }
    
    def collect_metrics(self):
        """メトリクスを収集"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            },
            "network": {
                "bytes_sent": psutil.net_io_counters().bytes_sent,
                "bytes_recv": psutil.net_io_counters().bytes_recv
            }
        }
        
        self.metrics.append(metrics)
        return metrics
    
    def check_alerts(self, metrics):
        """アラートをチェック"""
        alerts = []
        
        if metrics["cpu_percent"] > self.thresholds["cpu_usage"]:
            alerts.append({
                "type": "cpu_high",
                "value": metrics["cpu_percent"],
                "threshold": self.thresholds["cpu_usage"],
                "message": f"CPU使用率が{metrics['cpu_percent']:.1f}%です"
            })
        
        if metrics["memory"]["percent"] > self.thresholds["memory_usage"]:
            alerts.append({
                "type": "memory_high",
                "value": metrics["memory"]["percent"],
                "threshold": self.thresholds["memory_usage"],
                "message": f"メモリ使用率が{metrics['memory']['percent']:.1f}%です"
            })
        
        if metrics["disk"]["percent"] > self.thresholds["disk_usage"]:
            alerts.append({
                "type": "disk_high",
                "value": metrics["disk"]["percent"],
                "threshold": self.thresholds["disk_usage"],
                "message": f"ディスク使用率が{metrics['disk']['percent']:.1f}%です"
            })
        
        return alerts
    
    def generate_report(self):
        """レポートを生成"""
        if not self.metrics:
            return None
        
        latest = self.metrics[-1]
        
        report = {
            "timestamp": latest["timestamp"],
            "summary": {
                "cpu_usage": latest["cpu_percent"],
                "memory_usage": latest["memory"]["percent"],
                "disk_usage": latest["disk"]["percent"]
            },
            "alerts": self.check_alerts(latest),
            "recommendations": self.generate_recommendations(latest)
        }
        
        return report
    
    def generate_recommendations(self, metrics):
        """推奨事項を生成"""
        recommendations = []
        
        if metrics["cpu_percent"] > 70:
            recommendations.append("CPU使用率が高いです。不要なプロセスを終了してください。")
        
        if metrics["memory"]["percent"] > 75:
            recommendations.append("メモリ使用率が高いです。メモリ使用量の多いプロセスを確認してください。")
        
        if metrics["disk"]["percent"] > 80:
            recommendations.append("ディスク使用率が高いです。不要なファイルを削除してください。")
        
        return recommendations
    
    def run_monitor(self, duration_minutes=60):
        """監視を実行"""
        print(f"🔍 パフォーマンス監視開始（{duration_minutes}分間）")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        while time.time() < end_time:
            metrics = self.collect_metrics()
            alerts = self.check_alerts(metrics)
            
            if alerts:
                print(f"⚠️ アラート検出: {len(alerts)}件")
                for alert in alerts:
                    print(f"  - {alert['message']}")
            
            time.sleep(60)  # 1分間隔
        
        report = self.generate_report()
        return report

if __name__ == "__main__":
    monitor = PerformanceMonitor()
    report = monitor.run_monitor(5)  # 5分間監視
    
    if report:
        print("📊 パフォーマンスレポート:")
        print(json.dumps(report, indent=2, ensure_ascii=False))
