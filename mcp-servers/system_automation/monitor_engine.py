#!/usr/bin/env python3
"""
統合監視システム
システム状態監視、異常検知、アラート管理
"""

import os
import psutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MonitorEngine:
    """統合監視システム"""
    
    def __init__(self, base_path: str = "/root"):
        self.base_path = Path(base_path)
        self.config_path = self.base_path / ".monitor_config.json"
        self.metrics_path = self.base_path / ".monitor_metrics.json"
        self.alerts_path = self.base_path / ".monitor_alerts.json"
        
        # デフォルト設定
        self.default_config = {
            "enabled": True,
            "check_interval_seconds": 60,
            "alert_thresholds": {
                "cpu_percent": 80,
                "memory_percent": 85,
                "disk_percent": 90,
                "load_avg": 4.0,
                "process_count": 1000
            },
            "monitoring": {
                "cpu": True,
                "memory": True,
                "disk": True,
                "network": True,
                "processes": True,
                "services": True
            },
            "alert_channels": {
                "log": True,
                "file": True,
                "email": False,
                "telegram": False
            }
        }
        
        self.config = self.load_config()
        self.metrics = self.load_metrics()
        self.alerts = self.load_alerts()
        
    def load_config(self) -> dict:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"設定読み込みエラー: {e}")
                return self.default_config
        return self.default_config
    
    def save_config(self):
        """設定を保存"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
    
    def load_metrics(self) -> dict:
        """メトリクスを読み込む"""
        if self.metrics_path.exists():
            try:
                with open(self.metrics_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"メトリクス読み込みエラー: {e}")
                return {"history": []}
        return {"history": []}
    
    def save_metrics(self):
        """メトリクスを保存"""
        try:
            # 履歴を最新100件に制限
            if len(self.metrics["history"]) > 100:
                self.metrics["history"] = self.metrics["history"][-100:]
            
            with open(self.metrics_path, 'w', encoding='utf-8') as f:
                json.dump(self.metrics, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"メトリクス保存エラー: {e}")
    
    def load_alerts(self) -> list:
        """アラートを読み込む"""
        if self.alerts_path.exists():
            try:
                with open(self.alerts_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"アラート読み込みエラー: {e}")
                return []
        return []
    
    def save_alerts(self):
        """アラートを保存"""
        try:
            # 最新100件に制限
            if len(self.alerts) > 100:
                self.alerts = self.alerts[-100:]
            
            with open(self.alerts_path, 'w', encoding='utf-8') as f:
                json.dump(self.alerts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"アラート保存エラー: {e}")
    
    def collect_cpu_metrics(self) -> Dict:
        """CPUメトリクス収集"""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        load_avg = os.getloadavg()  # type: ignore[attr-defined]
        
        return {
            "cpu_percent": cpu_percent,
            "cpu_count": cpu_count,
            "cpu_freq_mhz": cpu_freq.current if cpu_freq else 0,
            "load_avg_1m": load_avg[0],
            "load_avg_5m": load_avg[1],
            "load_avg_15m": load_avg[2]
        }
    
    def collect_memory_metrics(self) -> Dict:
        """メモリメトリクス収集"""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "memory_percent": memory.percent,
            "swap_total_gb": round(swap.total / (1024**3), 2),
            "swap_used_gb": round(swap.used / (1024**3), 2),
            "swap_percent": swap.percent
        }
    
    def collect_disk_metrics(self) -> Dict:
        """ディスクメトリクス収集"""
        disk = psutil.disk_usage(self.base_path)  # type: ignore
        
        return {
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_percent": disk.percent
        }
    
    def collect_network_metrics(self) -> Dict:
        """ネットワークメトリクス収集"""
        net_io = psutil.net_io_counters()
        
        return {
            "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
            "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errors_in": net_io.errin,
            "errors_out": net_io.errout
        }
    
    def collect_process_metrics(self) -> Dict:
        """プロセスメトリクス収集"""
        processes = list(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']))
        
        # CPU/メモリ使用率トップ5
        cpu_top = sorted(processes, key=lambda x: x.info['cpu_percent'] or 0, reverse=True)[:5]
        memory_top = sorted(processes, key=lambda x: x.info['memory_percent'] or 0, reverse=True)[:5]
        
        return {
            "process_count": len(processes),
            "cpu_top_5": [
                {"name": p.info['name'], "cpu": p.info['cpu_percent']}
                for p in cpu_top
            ],
            "memory_top_5": [
                {"name": p.info['name'], "memory": p.info['memory_percent']}
                for p in memory_top
            ]
        }
    
    def collect_all_metrics(self) -> Dict:
        """全メトリクス収集"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {},
            "memory": {},
            "disk": {},
            "network": {},
            "processes": {}
        }
        
        if self.config["monitoring"]["cpu"]:
            metrics["cpu"] = self.collect_cpu_metrics()
        
        if self.config["monitoring"]["memory"]:
            metrics["memory"] = self.collect_memory_metrics()
        
        if self.config["monitoring"]["disk"]:
            metrics["disk"] = self.collect_disk_metrics()
        
        if self.config["monitoring"]["network"]:
            metrics["network"] = self.collect_network_metrics()
        
        if self.config["monitoring"]["processes"]:
            metrics["processes"] = self.collect_process_metrics()
        
        # 履歴に追加
        self.metrics["history"].append(metrics)
        self.metrics["latest"] = metrics
        self.save_metrics()
        
        return metrics
    
    def check_thresholds(self, metrics: Dict) -> List[Dict]:
        """閾値チェック"""
        alerts = []
        thresholds = self.config["alert_thresholds"]
        
        # CPUチェック
        if "cpu_percent" in metrics.get("cpu", {}):
            if metrics["cpu"]["cpu_percent"] > thresholds["cpu_percent"]:
                alerts.append({
                    "level": "WARNING",
                    "type": "CPU",
                    "message": f"CPU使用率が高いです: {metrics['cpu']['cpu_percent']:.1f}%",
                    "value": metrics["cpu"]["cpu_percent"],
                    "threshold": thresholds["cpu_percent"]
                })
        
        # メモリチェック
        if "memory_percent" in metrics.get("memory", {}):
            if metrics["memory"]["memory_percent"] > thresholds["memory_percent"]:
                alerts.append({
                    "level": "WARNING",
                    "type": "MEMORY",
                    "message": f"メモリ使用率が高いです: {metrics['memory']['memory_percent']:.1f}%",
                    "value": metrics["memory"]["memory_percent"],
                    "threshold": thresholds["memory_percent"]
                })
        
        # ディスクチェック
        if "disk_percent" in metrics.get("disk", {}):
            if metrics["disk"]["disk_percent"] > thresholds["disk_percent"]:
                alerts.append({
                    "level": "CRITICAL",
                    "type": "DISK",
                    "message": f"ディスク使用率が高いです: {metrics['disk']['disk_percent']:.1f}%",
                    "value": metrics["disk"]["disk_percent"],
                    "threshold": thresholds["disk_percent"]
                })
        
        # ロードアベレージチェック
        if "load_avg_1m" in metrics.get("cpu", {}):
            if metrics["cpu"]["load_avg_1m"] > thresholds["load_avg"]:
                alerts.append({
                    "level": "WARNING",
                    "type": "LOAD",
                    "message": f"システムロードが高いです: {metrics['cpu']['load_avg_1m']:.2f}",
                    "value": metrics["cpu"]["load_avg_1m"],
                    "threshold": thresholds["load_avg"]
                })
        
        # プロセス数チェック
        if "process_count" in metrics.get("processes", {}):
            if metrics["processes"]["process_count"] > thresholds["process_count"]:
                alerts.append({
                    "level": "WARNING",
                    "type": "PROCESSES",
                    "message": f"プロセス数が多いです: {metrics['processes']['process_count']}個",
                    "value": metrics["processes"]["process_count"],
                    "threshold": thresholds["process_count"]
                })
        
        return alerts
    
    def send_alert(self, alert: Dict):
        """アラート送信"""
        alert["timestamp"] = datetime.now().isoformat()
        
        # ログ出力
        if self.config["alert_channels"]["log"]:
            logger.warning(f"[{alert['level']}] {alert['type']}: {alert['message']}")
        
        # ファイル保存
        if self.config["alert_channels"]["file"]:
            self.alerts.append(alert)
            self.save_alerts()
        
        # TODO: メール、Telegram通知は実装予定
    
    def run_monitoring_cycle(self) -> Dict:
        """監視サイクル実行"""
        logger.info("監視サイクル開始")
        
        # メトリクス収集
        metrics = self.collect_all_metrics()
        
        # 閾値チェック
        alerts = self.check_thresholds(metrics)
        
        # アラート送信
        for alert in alerts:
            self.send_alert(alert)
        
        result = {
            "timestamp": metrics["timestamp"],
            "metrics": metrics,
            "alerts_count": len(alerts),
            "alerts": alerts
        }
        
        logger.info(f"監視サイクル完了: {len(alerts)}個のアラート")
        
        return result
    
    def get_system_status(self) -> Dict:
        """システムステータス取得"""
        latest = self.metrics.get("latest", {})
        
        status = {
            "monitoring_enabled": self.config["enabled"],
            "last_check": latest.get("timestamp"),
            "current_metrics": latest,
            "recent_alerts": self.alerts[-10:] if self.alerts else [],
            "alert_count_24h": len([a for a in self.alerts if 
                datetime.fromisoformat(a["timestamp"]) > datetime.now() - timedelta(hours=24)])
        }
        
        return status
    
    def get_health_score(self) -> Dict:
        """ヘルススコア計算"""
        latest = self.metrics.get("latest", {})
        
        score = 100
        issues = []
        
        # CPU
        if "cpu_percent" in latest.get("cpu", {}):
            cpu_percent = latest["cpu"]["cpu_percent"]
            if cpu_percent > 90:
                score -= 30
                issues.append("CPU使用率が極めて高い")
            elif cpu_percent > 80:
                score -= 15
                issues.append("CPU使用率が高い")
        
        # メモリ
        if "memory_percent" in latest.get("memory", {}):
            mem_percent = latest["memory"]["memory_percent"]
            if mem_percent > 95:
                score -= 30
                issues.append("メモリ不足")
            elif mem_percent > 85:
                score -= 15
                issues.append("メモリ使用率が高い")
        
        # ディスク
        if "disk_percent" in latest.get("disk", {}):
            disk_percent = latest["disk"]["disk_percent"]
            if disk_percent > 95:
                score -= 40
                issues.append("ディスク容量不足")
            elif disk_percent > 90:
                score -= 20
                issues.append("ディスク使用率が高い")
        
        # アラート数
        recent_alerts = len([a for a in self.alerts if 
            datetime.fromisoformat(a["timestamp"]) > datetime.now() - timedelta(hours=1)])
        if recent_alerts > 10:
            score -= 20
            issues.append("多数のアラートが発生")
        elif recent_alerts > 5:
            score -= 10
            issues.append("アラートが発生")
        
        return {
            "health_score": max(0, score),
            "health_level": "EXCELLENT" if score >= 90 else "GOOD" if score >= 70 else "WARNING" if score >= 50 else "CRITICAL",
            "issues": issues,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """メイン実行"""
    monitor = MonitorEngine()
    
    print("=" * 60)
    print("📊 統合監視システム")
    print("=" * 60)
    
    # ステータス表示
    status = monitor.get_system_status()
    print("\n📊 システムステータス:")
    print(f"  監視有効: {'✅' if status['monitoring_enabled'] else '❌'}")
    print(f"  最終チェック: {status['last_check']}")
    
    # ヘルススコア
    health = monitor.get_health_score()
    print(f"\n🏥 ヘルススコア: {health['health_score']}/100 ({health['health_level']})")
    
    if health['issues']:
        print("  問題:")
        for issue in health['issues']:
            print(f"    - {issue}")
    
    # 現在のメトリクス
    if status['current_metrics']:
        metrics = status['current_metrics']
        print("\n📈 現在のメトリクス:")
        
        if "cpu" in metrics:
            print(f"  CPU: {metrics['cpu'].get('cpu_percent', 0):.1f}%")
        
        if "memory" in metrics:
            print(f"  メモリ: {metrics['memory'].get('memory_percent', 0):.1f}%")
        
        if "disk" in metrics:
            print(f"  ディスク: {metrics['disk'].get('disk_percent', 0):.1f}%")
    
    # アラート表示
    if status['recent_alerts']:
        print("\n⚠️  最近のアラート:")
        for alert in status['recent_alerts'][-5:]:
            print(f"  [{alert['level']}] {alert['type']}: {alert['message']}")
    
    # メニュー
    print("\n実行する操作を選択:")
    print("  1. 監視サイクル実行")
    print("  2. メトリクス表示")
    print("  3. アラート一覧")
    print("  4. ヘルスチェック")
    print("  0. 終了")
    
    choice = input("\n選択 (0-4): ").strip()
    
    if choice == "1":
        print("\n🚀 監視サイクル実行中...")
        result = monitor.run_monitoring_cycle()
        print(f"\n✅ 監視完了: {result['alerts_count']}個のアラート")
    
    elif choice == "2":
        print("\n📊 メトリクス:")
        metrics = monitor.collect_all_metrics()
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
    
    elif choice == "3":
        print("\n⚠️  アラート一覧:")
        for alert in monitor.alerts[-20:]:
            print(f"  [{alert['timestamp']}] [{alert['level']}] {alert['message']}")
    
    elif choice == "4":
        print("\n🏥 ヘルスチェック:")
        health = monitor.get_health_score()
        print(json.dumps(health, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

