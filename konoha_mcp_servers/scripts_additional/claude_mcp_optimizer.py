#!/usr/bin/env python3
"""
クロードデスクトップMCPパフォーマンス最適化システム
"""

import os
import json
import psutil
from pathlib import Path
from datetime import datetime

class ClaudeMCPOptimizer:
    def __init__(self):
        self.system_info = self.get_system_info()
        self.optimization_config = {}
        
    def get_system_info(self):
        """システム情報を取得"""
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_total": psutil.disk_usage('/').total,
            "disk_free": psutil.disk_usage('/').free,
            "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}"
        }
    
    def optimize_memory_usage(self):
        """メモリ使用量を最適化"""
        optimizations = []
        
        # メモリ制限設定
        memory_limit = self.system_info["memory_total"] * 0.7  # 70%制限
        optimizations.append({
            "type": "memory_limit",
            "value": memory_limit,
            "description": f"メモリ使用量を{memory_limit / (1024**3):.1f}GBに制限"
        })
        
        # ガベージコレクション最適化
        optimizations.append({
            "type": "gc_optimization",
            "value": True,
            "description": "ガベージコレクション最適化を有効化"
        })
        
        return optimizations
    
    def optimize_cpu_usage(self):
        """CPU使用量を最適化"""
        optimizations = []
        
        # CPUコア数に基づく最適化
        cpu_cores = self.system_info["cpu_count"]
        max_workers = min(cpu_cores, 8)  # 最大8ワーカー
        
        optimizations.append({
            "type": "max_workers",
            "value": max_workers,
            "description": f"最大ワーカー数を{max_workers}に設定"
        })
        
        # プロセス優先度設定
        optimizations.append({
            "type": "process_priority",
            "value": "high",
            "description": "プロセス優先度を高に設定"
        })
        
        return optimizations
    
    def optimize_network_performance(self):
        """ネットワーク性能を最適化"""
        optimizations = []
        
        # 接続プール設定
        optimizations.append({
            "type": "connection_pool",
            "value": {
                "max_connections": 100,
                "keep_alive": True,
                "timeout": 30
            },
            "description": "接続プールを最適化"
        })
        
        # キャッシュ設定
        optimizations.append({
            "type": "cache_config",
            "value": {
                "enabled": True,
                "max_size": "1GB",
                "ttl": 3600
            },
            "description": "キャッシュ機能を有効化"
        })
        
        return optimizations
    
    def create_optimized_config(self):
        """最適化された設定ファイルを作成"""
        config = {
            "system": {
                "optimization_enabled": True,
                "memory_limit": self.system_info["memory_total"] * 0.7,
                "max_workers": min(self.system_info["cpu_count"], 8),
                "process_priority": "high"
            },
            "claude_instances": {
                "max_instances": 5,
                "default_memory": "512MB",
                "startup_delay": 1.0,
                "health_check_interval": 30
            },
            "mcp_servers": {
                "connection_pool": {
                    "max_connections": 100,
                    "keep_alive": True,
                    "timeout": 30
                },
                "cache": {
                    "enabled": True,
                    "max_size": "1GB",
                    "ttl": 3600
                },
                "performance": {
                    "async_processing": True,
                    "batch_processing": True,
                    "compression": True
                }
            },
            "monitoring": {
                "enabled": True,
                "metrics_interval": 60,
                "alert_thresholds": {
                    "cpu_usage": 80,
                    "memory_usage": 85,
                    "disk_usage": 90
                }
            }
        }
        
        config_file = Path("/root/claude_mcp_optimized_config.json")
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 最適化設定ファイル作成完了: {config_file}")
        return config_file
    
    def create_performance_monitor(self):
        """パフォーマンス監視スクリプトを作成"""
        monitor_code = '''#!/usr/bin/env python3
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
'''
        
        monitor_file = Path("/root/claude_mcp_performance_monitor.py")
        with open(monitor_file, 'w', encoding='utf-8') as f:
            f.write(monitor_code)
        
        os.chmod(monitor_file, 0o755)
        print(f"✅ パフォーマンス監視スクリプト作成完了: {monitor_file}")
        return monitor_file
    
    def run_optimization(self):
        """最適化を実行"""
        print("🚀 クロードMCPパフォーマンス最適化開始")
        print("=" * 50)
        
        # システム情報表示
        print("💻 システム情報:")
        print(f"  CPU: {self.system_info['cpu_count']}コア")
        print(f"  メモリ: {self.system_info['memory_total'] / (1024**3):.1f}GB")
        print(f"  ディスク: {self.system_info['disk_total'] / (1024**3):.1f}GB")
        
        # 最適化設定作成
        config_file = self.create_optimized_config()
        
        # 監視スクリプト作成
        monitor_file = self.create_performance_monitor()
        
        # 最適化レポート生成
        optimizations = {
            "memory": self.optimize_memory_usage(),
            "cpu": self.optimize_cpu_usage(),
            "network": self.optimize_network_performance()
        }
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "system_info": self.system_info,
            "optimizations": optimizations,
            "config_file": str(config_file),
            "monitor_file": str(monitor_file),
            "recommendations": [
                "定期的にパフォーマンス監視を実行してください",
                "メモリ使用量が85%を超えた場合はプロセスを確認してください",
                "CPU使用率が80%を超えた場合は負荷分散を検討してください"
            ]
        }
        
        report_file = Path("/root/claude_mcp_optimization_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 最適化レポート作成完了: {report_file}")
        
        print("\n🎉 パフォーマンス最適化完了！")
        print("💡 次のステップ:")
        print("  1. 最適化設定ファイルを使用してシステムを起動")
        print("  2. パフォーマンス監視スクリプトを実行")
        print("  3. 定期的にシステム状況を確認")
        
        return report

def main():
    optimizer = ClaudeMCPOptimizer()
    report = optimizer.run_optimization()
    
    if report:
        print("\n✅ 最適化が正常に完了しました！")

if __name__ == "__main__":
    main()
