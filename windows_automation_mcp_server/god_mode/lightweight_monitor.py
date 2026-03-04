#!/usr/bin/env python3
"""
軽量監視システム - Netdata/Prometheus代替
リアルタイムシステム監視＋アラート
"""

import psutil
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, asdict

@dataclass
class SystemMetrics:
    """システムメトリクス"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent: int
    network_recv: int
    process_count: int
    load_avg: List[float]

@dataclass
class Alert:
    """アラート"""
    alert_id: str
    timestamp: float
    level: str  # info, warning, critical
    metric: str
    value: float
    threshold: float
    message: str

class LightweightMonitor:
    """軽量監視システム"""
    
    def __init__(self):
        self.data_dir = Path("/root/god_mode/monitoring")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.metrics_file = self.data_dir / "metrics.jsonl"
        self.alerts_file = self.data_dir / "alerts.jsonl"
        self.config_file = self.data_dir / "thresholds.json"
        
        self.thresholds = self._load_thresholds()
        self._last_network = psutil.net_io_counters()
    
    def _load_thresholds(self) -> Dict:
        """閾値設定読み込み"""
        default_thresholds = {
            "cpu_warning": 70.0,
            "cpu_critical": 90.0,
            "memory_warning": 75.0,
            "memory_critical": 90.0,
            "disk_warning": 80.0,
            "disk_critical": 95.0,
            "process_warning": 200,
            "process_critical": 300
        }
        
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            with open(self.config_file, 'w') as f:
                json.dump(default_thresholds, f, indent=2)
            return default_thresholds
    
    def collect_metrics(self) -> SystemMetrics:
        """メトリクス収集"""
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        net = psutil.net_io_counters()
        net_sent = net.bytes_sent
        net_recv = net.bytes_recv
        
        process_count = len(psutil.pids())
        load_avg = list(psutil.getloadavg())
        
        metrics = SystemMetrics(
            timestamp=time.time(),
            cpu_percent=cpu,
            memory_percent=memory,
            disk_percent=disk,
            network_sent=net_sent,
            network_recv=net_recv,
            process_count=process_count,
            load_avg=load_avg
        )
        
        return metrics
    
    def check_alerts(self, metrics: SystemMetrics) -> List[Alert]:
        """アラートチェック"""
        alerts = []
        
        # CPU チェック
        if metrics.cpu_percent >= self.thresholds['cpu_critical']:
            alerts.append(Alert(
                alert_id=f"cpu_critical_{int(metrics.timestamp)}",
                timestamp=metrics.timestamp,
                level="critical",
                metric="cpu",
                value=metrics.cpu_percent,
                threshold=self.thresholds['cpu_critical'],
                message=f"CPU使用率が危険レベル: {metrics.cpu_percent:.1f}%"
            ))
        elif metrics.cpu_percent >= self.thresholds['cpu_warning']:
            alerts.append(Alert(
                alert_id=f"cpu_warning_{int(metrics.timestamp)}",
                timestamp=metrics.timestamp,
                level="warning",
                metric="cpu",
                value=metrics.cpu_percent,
                threshold=self.thresholds['cpu_warning'],
                message=f"CPU使用率が高い: {metrics.cpu_percent:.1f}%"
            ))
        
        # メモリチェック
        if metrics.memory_percent >= self.thresholds['memory_critical']:
            alerts.append(Alert(
                alert_id=f"memory_critical_{int(metrics.timestamp)}",
                timestamp=metrics.timestamp,
                level="critical",
                metric="memory",
                value=metrics.memory_percent,
                threshold=self.thresholds['memory_critical'],
                message=f"メモリ使用率が危険レベル: {metrics.memory_percent:.1f}%"
            ))
        elif metrics.memory_percent >= self.thresholds['memory_warning']:
            alerts.append(Alert(
                alert_id=f"memory_warning_{int(metrics.timestamp)}",
                timestamp=metrics.timestamp,
                level="warning",
                metric="memory",
                value=metrics.memory_percent,
                threshold=self.thresholds['memory_warning'],
                message=f"メモリ使用率が高い: {metrics.memory_percent:.1f}%"
            ))
        
        # ディスクチェック
        if metrics.disk_percent >= self.thresholds['disk_critical']:
            alerts.append(Alert(
                alert_id=f"disk_critical_{int(metrics.timestamp)}",
                timestamp=metrics.timestamp,
                level="critical",
                metric="disk",
                value=metrics.disk_percent,
                threshold=self.thresholds['disk_critical'],
                message=f"ディスク使用率が危険レベル: {metrics.disk_percent:.1f}%"
            ))
        elif metrics.disk_percent >= self.thresholds['disk_warning']:
            alerts.append(Alert(
                alert_id=f"disk_warning_{int(metrics.timestamp)}",
                timestamp=metrics.timestamp,
                level="warning",
                metric="disk",
                value=metrics.disk_percent,
                threshold=self.thresholds['disk_warning'],
                message=f"ディスク使用率が高い: {metrics.disk_percent:.1f}%"
            ))
        
        return alerts
    
    def save_metrics(self, metrics: SystemMetrics):
        """メトリクス保存"""
        with open(self.metrics_file, 'a') as f:
            f.write(json.dumps(asdict(metrics), ensure_ascii=False) + '\n')
    
    def save_alerts(self, alerts: List[Alert]):
        """アラート保存"""
        if not alerts:
            return
        
        with open(self.alerts_file, 'a') as f:
            for alert in alerts:
                f.write(json.dumps(asdict(alert), ensure_ascii=False) + '\n')
        
        # Slack通知（critical のみ）
        try:
            from level3.slack_notifier import notify
            for alert in alerts:
                if alert.level == "critical":
                    notify(alert.message, "error", "システム警告")
        except IOError:
            pass
    
    def get_current_status(self) -> Dict:
        """現在のステータス取得"""
        metrics = self.collect_metrics()
        alerts = self.check_alerts(metrics)
        
        # Level 3プロセスチェック
        level3_processes = self._check_level3_processes()
        
        # 最近のアラート
        recent_alerts = self._get_recent_alerts(minutes=60)
        
        return {
            "metrics": asdict(metrics),
            "alerts": [asdict(a) for a in alerts],
            "level3_processes": level3_processes,
            "recent_alerts_count": len(recent_alerts),
            "health_score": self._calculate_health_score(metrics, recent_alerts)
        }
    
    def _check_level3_processes(self) -> Dict:
        """Level 3プロセス確認"""
        processes = {
            "agi_evolution": False,
            "auto_bug_fix": False,
            "webhook_server": False
        }
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                
                if 'agi_evolution_engine.py' in cmdline:
                    processes['agi_evolution'] = True
                elif 'auto_bug_fix_system.py' in cmdline:
                    processes['auto_bug_fix'] = True
                elif 'github_webhook_server.py' in cmdline:
                    processes['webhook_server'] = True
            except Exception:
                continue
        
        return processes
    
    def _get_recent_alerts(self, minutes: int = 60) -> List[Dict]:
        """最近のアラート取得"""
        if not self.alerts_file.exists():
            return []
        
        cutoff = time.time() - (minutes * 60)
        recent = []
        
        with open(self.alerts_file, 'r') as f:
            for line in f:
                try:
                    alert = json.loads(line)
                    if alert.get('timestamp', 0) >= cutoff:
                        recent.append(alert)
                except IOError:
                    continue
        
        return recent
    
    def _calculate_health_score(self, metrics: SystemMetrics, recent_alerts: List) -> int:
        """健全性スコア計算（0-100）"""
        score = 100
        
        # CPU負荷
        if metrics.cpu_percent > 90:
            score -= 20
        elif metrics.cpu_percent > 70:
            score -= 10
        
        # メモリ負荷
        if metrics.memory_percent > 90:
            score -= 20
        elif metrics.memory_percent > 75:
            score -= 10
        
        # ディスク使用量
        if metrics.disk_percent > 95:
            score -= 15
        elif metrics.disk_percent > 80:
            score -= 5
        
        # 最近のアラート
        critical_count = sum(1 for a in recent_alerts if a.get('level') == 'critical')
        warning_count = sum(1 for a in recent_alerts if a.get('level') == 'warning')
        
        score -= critical_count * 10
        score -= warning_count * 3
        
        return max(0, score)
    
    def monitor_continuous(self, interval: int = 60):
        """連続監視"""
        print(f"🔍 監視開始（{interval}秒間隔）")
        print("Ctrl+C で停止")
        print("")
        
        try:
            while True:
                metrics = self.collect_metrics()
                alerts = self.check_alerts(metrics)
                
                self.save_metrics(metrics)
                self.save_alerts(alerts)
                
                # 表示
                timestamp = datetime.fromtimestamp(metrics.timestamp).strftime("%H:%M:%S")
                print(f"[{timestamp}] CPU: {metrics.cpu_percent:5.1f}% | "
                      f"MEM: {metrics.memory_percent:5.1f}% | "
                      f"DISK: {metrics.disk_percent:5.1f}% | "
                      f"Alerts: {len(alerts)}")
                
                if alerts:
                    for alert in alerts:
                        emoji = "🔥" if alert.level == "critical" else "⚠️"
                        print(f"  {emoji} {alert.message}")
                
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n監視停止")

# グローバルインスタンス
_monitor = None

def get_monitor() -> LightweightMonitor:
    """グローバル監視取得"""
    global _monitor
    if _monitor is None:
        _monitor = LightweightMonitor()
    return _monitor

# テスト実行
if __name__ == "__main__":
    import sys
    
    monitor = LightweightMonitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        monitor.monitor_continuous(interval)
    else:
        print("\n" + "=" * 70)
        print("🔍 軽量監視システム - 現在のステータス")
        print("=" * 70)
        
        status = monitor.get_current_status()
        
        metrics = status['metrics']
        print("\n📊 システムメトリクス:")
        print(f"  CPU: {metrics['cpu_percent']:.1f}%")
        print(f"  メモリ: {metrics['memory_percent']:.1f}%")
        print(f"  ディスク: {metrics['disk_percent']:.1f}%")
        print(f"  プロセス数: {metrics['process_count']}")
        print(f"  ロードアベレージ: {', '.join(f'{x:.2f}' for x in metrics['load_avg'])}")
        
        print("\n🤖 Level 3プロセス:")
        for name, running in status['level3_processes'].items():
            status_emoji = "✅" if running else "❌"
            print(f"  {status_emoji} {name}")
        
        print(f"\n💯 健全性スコア: {status['health_score']}/100")
        
        if status['alerts']:
            print(f"\n⚠️  現在のアラート: {len(status['alerts'])}件")
            for alert in status['alerts']:
                print(f"  • {alert['message']}")
        else:
            print("\n✅ アラートなし")
        
        print("\n" + "=" * 70)
        print("💡 連続監視: python3 lightweight_monitor.py continuous [間隔秒]")
        print("=" * 70)

