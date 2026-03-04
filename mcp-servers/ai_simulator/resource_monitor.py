"""
AI Simulator Resource Monitor
リソース監視とアラートシステム
"""

import psutil
import time
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class ResourceMetrics:
    """リソースメトリクス"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    disk_used_mb: float
    network_sent_mb: float
    network_recv_mb: float
    process_count: int
    load_average: List[float]

@dataclass
class AlertRule:
    """アラートルール"""
    name: str
    metric: str
    threshold: float
    operator: str  # '>', '<', '>=', '<=', '=='
    severity: str  # 'info', 'warning', 'critical'
    enabled: bool = True

class ResourceMonitor:
    """リソース監視クラス"""
    
    def __init__(self, check_interval: float = 1.0):
        self.check_interval = check_interval
        self.is_monitoring = False
        self.metrics_history: List[ResourceMetrics] = []
        self.alert_rules: List[AlertRule] = []
        self.alert_callbacks: List[Callable] = []
        self.logger = self._setup_logger()
        
        # 初期アラートルール設定
        self._setup_default_alerts()
    
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('resource_monitor')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler('/app/logs/resource_monitor.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _setup_default_alerts(self):
        """デフォルトアラートルール設定"""
        default_rules = [
            AlertRule("High CPU", "cpu_percent", 80.0, ">", "warning"),
            AlertRule("Critical CPU", "cpu_percent", 95.0, ">", "critical"),
            AlertRule("High Memory", "memory_percent", 80.0, ">", "warning"),
            AlertRule("Critical Memory", "memory_percent", 95.0, ">", "critical"),
            AlertRule("High Disk", "disk_usage_percent", 90.0, ">", "warning"),
            AlertRule("Critical Disk", "disk_usage_percent", 98.0, ">", "critical"),
            AlertRule("High Process Count", "process_count", 100, ">", "warning"),
        ]
        
        self.alert_rules.extend(default_rules)
    
    def collect_metrics(self) -> ResourceMetrics:
        """メトリクス収集"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # メモリ使用量
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / 1024 / 1024
            
            # ディスク使用量
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_used_mb = disk.used / 1024 / 1024
            
            # ネットワークI/O
            network = psutil.net_io_counters()
            network_sent_mb = network.bytes_sent / 1024 / 1024
            network_recv_mb = network.bytes_recv / 1024 / 1024
            
            # プロセス数
            process_count = len(psutil.pids())
            
            # ロードアベレージ
            load_average = list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0.0, 0.0, 0.0]
            
            return ResourceMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                disk_usage_percent=disk_usage_percent,
                disk_used_mb=disk_used_mb,
                network_sent_mb=network_sent_mb,
                network_recv_mb=network_recv_mb,
                process_count=process_count,
                load_average=load_average
            )
            
        except Exception as e:
            self.logger.error(f"Failed to collect metrics: {e}")
            raise
    
    def check_alerts(self, metrics: ResourceMetrics):
        """アラートチェック"""
        for rule in self.alert_rules:
            if not rule.enabled:
                continue
            
            try:
                metric_value = getattr(metrics, rule.metric)
                
                # 閾値チェック
                alert_triggered = False
                if rule.operator == '>':
                    alert_triggered = metric_value > rule.threshold
                elif rule.operator == '<':
                    alert_triggered = metric_value < rule.threshold
                elif rule.operator == '>=':
                    alert_triggered = metric_value >= rule.threshold
                elif rule.operator == '<=':
                    alert_triggered = metric_value <= rule.threshold
                elif rule.operator == '==':
                    alert_triggered = metric_value == rule.threshold
                
                if alert_triggered:
                    self._trigger_alert(rule, metric_value, metrics)
                    
            except Exception as e:
                self.logger.error(f"Alert check failed for rule {rule.name}: {e}")
    
    def _trigger_alert(self, rule: AlertRule, value: float, metrics: ResourceMetrics):
        """アラート発火"""
        alert_data = {
            'rule_name': rule.name,
            'severity': rule.severity,
            'metric': rule.metric,
            'value': value,
            'threshold': rule.threshold,
            'operator': rule.operator,
            'timestamp': datetime.now().isoformat(),
            'metrics': asdict(metrics)
        }
        
        # ログ出力
        log_level = getattr(logging, rule.severity.upper())
        self.logger.log(log_level, f"ALERT: {rule.name} - {rule.metric}={value} {rule.operator} {rule.threshold}")
        
        # コールバック実行
        for callback in self.alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")
    
    def add_alert_callback(self, callback: Callable):
        """アラートコールバック追加"""
        self.alert_callbacks.append(callback)
    
    def add_alert_rule(self, rule: AlertRule):
        """アラートルール追加"""
        self.alert_rules.append(rule)
        self.logger.info(f"Added alert rule: {rule.name}")
    
    def start_monitoring(self):
        """監視開始"""
        self.is_monitoring = True
        self.logger.info("Resource monitoring started")
        
        while self.is_monitoring:
            try:
                # メトリクス収集
                metrics = self.collect_metrics()
                self.metrics_history.append(metrics)
                
                # 履歴保持（最新1000件）
                if len(self.metrics_history) > 1000:
                    self.metrics_history = self.metrics_history[-1000:]
                
                # アラートチェック
                self.check_alerts(metrics)
                
                # 待機
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                time.sleep(self.check_interval)
    
    def stop_monitoring(self):
        """監視停止"""
        self.is_monitoring = False
        self.logger.info("Resource monitoring stopped")
    
    def get_current_metrics(self) -> Optional[ResourceMetrics]:
        """現在のメトリクス取得"""
        if self.metrics_history:
            return self.metrics_history[-1]
        return None
    
    def get_metrics_summary(self, duration_minutes: int = 5) -> Dict:
        """メトリクスサマリー取得"""
        if not self.metrics_history:
            return {}
        
        # 指定時間内のメトリクスを取得
        cutoff_time = time.time() - (duration_minutes * 60)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {}
        
        # 統計計算
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        
        return {
            'duration_minutes': duration_minutes,
            'sample_count': len(recent_metrics),
            'cpu': {
                'avg': sum(cpu_values) / len(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values)
            },
            'memory': {
                'avg': sum(memory_values) / len(memory_values),
                'max': max(memory_values),
                'min': min(memory_values)
            },
            'latest': asdict(recent_metrics[-1])
        }

if __name__ == "__main__":
    # ログディレクトリ作成
    import os
    os.makedirs('/app/logs', exist_ok=True)
    
    # リソースモニター起動
    monitor = ResourceMonitor(check_interval=2.0)
    
    # アラートコールバック設定
    def alert_handler(alert_data):
        print(f"ALERT: {alert_data['rule_name']} - {alert_data['value']}")
    
    monitor.add_alert_callback(alert_handler)
    
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("Stopping monitor...")
    finally:
        monitor.stop_monitoring()