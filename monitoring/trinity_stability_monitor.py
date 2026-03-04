#!/usr/bin/env python3
"""
Stability Monitor - システム安定性監視

CPU、メモリ、感情パラメータ、DB書き込み頻度などを
リアルタイムで監視し、異常を検知します。

使用方法:
    python3 stability_monitor.py --start
    python3 stability_monitor.py --status
"""

import sys
import json
import time
import sqlite3
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import threading

workspace = Path("/root/trinity_workspace")
sys.path.insert(0, str(workspace / "evolution"))
sys.path.insert(0, str(workspace / "bridge"))


class StabilityMetrics:
    """安定性メトリクス"""
    
    def __init__(self):
        self.cpu_history = []
        self.memory_history = []
        self.emotion_history = []
        self.db_write_history = []
        self.max_history = 60  # 60分保持
        
    def add_cpu(self, value: float):
        self._add_metric(self.cpu_history, value)
        
    def add_memory(self, value: float):
        self._add_metric(self.memory_history, value)
        
    def add_emotion_variance(self, value: float):
        self._add_metric(self.emotion_history, value)
        
    def add_db_writes(self, value: int):
        self._add_metric(self.db_write_history, value)
        
    def _add_metric(self, history: List, value):
        history.append({
            'timestamp': datetime.now().isoformat(),
            'value': value
        })
        if len(history) > self.max_history:
            history.pop(0)
            
    def get_stats(self) -> Dict:
        """統計情報を取得"""
        return {
            'cpu': self._calc_stats(self.cpu_history),
            'memory': self._calc_stats(self.memory_history),
            'emotion_variance': self._calc_stats(self.emotion_history),
            'db_writes': self._calc_stats(self.db_write_history)
        }
        
    def _calc_stats(self, history: List) -> Dict:
        if not history:
            return {'avg': 0, 'max': 0, 'min': 0, 'current': 0}
        
        values = [h['value'] for h in history]
        return {
            'avg': sum(values) / len(values),
            'max': max(values),
            'min': min(values),
            'current': values[-1] if values else 0,
            'count': len(values)
        }


class StabilityMonitor:
    """安定性監視システム"""
    
    def __init__(self, workspace_path: str = "/root/trinity_workspace"):
        self.workspace = Path(workspace_path)
        self.metrics = StabilityMetrics()
        
        # 閾値設定
        self.thresholds = {
            'cpu_warning': 20,
            'cpu_critical': 30,
            'memory_warning': 500,  # MB
            'memory_critical': 700,
            'emotion_variance_warning': 0.3,
            'emotion_variance_critical': 0.5,
            'db_writes_warning': 100,  # per hour
            'db_writes_critical': 200
        }
        
        # アラート履歴
        self.alerts = []
        self.alert_cooldown = {}  # アラートのクールダウン管理
        
        # 監視スレッド
        self.running = False
        self.monitor_thread = None
        
        # DB接続
        self.consciousness_db = self.workspace / "shared" / "consciousness.db"
        self.reflection_db = self.workspace / "shared" / "reflection_memory.db"
        
    def start(self):
        """監視開始"""
        if self.running:
            print("⚠️  Monitor already running")
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        print("✅ Stability Monitor started")
        print(f"   PID: {psutil.Process().pid}")
        print(f"   Workspace: {self.workspace}")
        
    def stop(self):
        """監視停止"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("⏹️  Stability Monitor stopped")
        
    def _monitor_loop(self):
        """メインモニタリングループ"""
        while self.running:
            try:
                # メトリクス収集
                cpu = self._check_cpu()
                memory = self._check_memory()
                emotion_var = self._check_emotion_variance()
                db_writes = self._check_db_write_rate()
                
                # メトリクス記録
                self.metrics.add_cpu(cpu)
                self.metrics.add_memory(memory)
                self.metrics.add_emotion_variance(emotion_var)
                self.metrics.add_db_writes(db_writes)
                
                # アラート判定
                self._check_alerts(cpu, memory, emotion_var, db_writes)
                
                # 60秒待機
                time.sleep(60)
                
            except Exception as e:
                print(f"[ERROR] Monitor loop error: {e}")
                time.sleep(60)
                
    def _check_cpu(self) -> float:
        """CPU使用率チェック"""
        return psutil.cpu_percent(interval=1)
        
    def _check_memory(self) -> float:
        """メモリ使用量チェック（MB）"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
        
    def _check_emotion_variance(self) -> float:
        """感情パラメータの変動チェック"""
        try:
            if not self.consciousness_db.exists():
                return 0.0
                
            conn = sqlite3.connect(self.consciousness_db)
            cursor = conn.cursor()
            
            # 過去1時間の思考から感情変動を推定
            since = (datetime.now() - timedelta(hours=1)).isoformat()
            cursor.execute("""
                SELECT COUNT(*) FROM thought_history
                WHERE timestamp > ?
            """, (since,))
            
            thought_count = cursor.fetchone()[0]
            
            conn.close()
            
            # 思考数が多すぎる = 感情が不安定
            # 正常: 10-30件/時間
            if thought_count > 50:
                return 0.4
            elif thought_count > 30:
                return 0.2
            else:
                return 0.1
                
        except Exception as e:
            print(f"[WARN] Emotion variance check error: {e}")
            return 0.0
            
    def _check_db_write_rate(self) -> int:
        """DB書き込み頻度チェック（1時間あたり）"""
        try:
            count = 0
            
            # reflection_memory.dbの書き込み
            if self.reflection_db.exists():
                conn = sqlite3.connect(self.reflection_db)
                cursor = conn.cursor()
                
                since = (datetime.now() - timedelta(hours=1)).isoformat()
                cursor.execute("""
                    SELECT COUNT(*) FROM actions WHERE timestamp > ?
                """, (since,))
                
                count += cursor.fetchone()[0]
                conn.close()
                
            return count
            
        except Exception as e:
            print(f"[WARN] DB write rate check error: {e}")
            return 0
            
    def _check_alerts(self, cpu: float, memory: float, 
                     emotion_var: float, db_writes: int):
        """アラート判定"""
        now = datetime.now()
        
        # CPU
        if cpu > self.thresholds['cpu_critical']:
            self._fire_alert('critical', 'cpu', cpu, f"CPU usage critical: {cpu:.1f}%")
        elif cpu > self.thresholds['cpu_warning']:
            self._fire_alert('warning', 'cpu', cpu, f"CPU usage high: {cpu:.1f}%")
            
        # Memory
        if memory > self.thresholds['memory_critical']:
            self._fire_alert('critical', 'memory', memory, f"Memory usage critical: {memory:.0f}MB")
        elif memory > self.thresholds['memory_warning']:
            self._fire_alert('warning', 'memory', memory, f"Memory usage high: {memory:.0f}MB")
            
        # Emotion Variance
        if emotion_var > self.thresholds['emotion_variance_critical']:
            self._fire_alert('critical', 'emotion', emotion_var, 
                           f"Emotion highly unstable: {emotion_var:.2f}")
        elif emotion_var > self.thresholds['emotion_variance_warning']:
            self._fire_alert('warning', 'emotion', emotion_var, 
                           f"Emotion variance elevated: {emotion_var:.2f}")
            
        # DB Writes
        if db_writes > self.thresholds['db_writes_critical']:
            self._fire_alert('critical', 'db_writes', db_writes, 
                           f"DB write rate critical: {db_writes}/h")
        elif db_writes > self.thresholds['db_writes_warning']:
            self._fire_alert('warning', 'db_writes', db_writes, 
                           f"DB write rate high: {db_writes}/h")
            
    def _fire_alert(self, level: str, category: str, value: float, message: str):
        """アラート発行"""
        # クールダウンチェック（同じカテゴリのアラートは10分に1回まで）
        now = datetime.now()
        if category in self.alert_cooldown:
            last_alert = self.alert_cooldown[category]
            if (now - last_alert).total_seconds() < 600:
                return
                
        alert = {
            'timestamp': now.isoformat(),
            'level': level,
            'category': category,
            'value': value,
            'message': message
        }
        
        self.alerts.append(alert)
        self.alert_cooldown[category] = now
        
        # ログ出力
        icon = "🚨" if level == 'critical' else "⚠️"
        print(f"{icon} [{level.upper()}] {message}")
        
        # アラートを永続化
        self._save_alert(alert)
        
    def _save_alert(self, alert: Dict):
        """アラートをファイルに保存"""
        alert_file = self.workspace / "logs" / "stability_alerts.jsonl"
        alert_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(alert_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(alert) + '\n')
            
    def get_status(self) -> Dict:
        """現在のステータスを取得"""
        stats = self.metrics.get_stats()
        
        # 最近のアラート（過去1時間）
        recent_alerts = [
            a for a in self.alerts
            if (datetime.now() - datetime.fromisoformat(a['timestamp'])).total_seconds() < 3600
        ]
        
        return {
            'running': self.running,
            'pid': psutil.Process().pid if self.running else None,
            'uptime': self._get_uptime(),
            'metrics': stats,
            'recent_alerts': len(recent_alerts),
            'thresholds': self.thresholds
        }
        
    def _get_uptime(self) -> str:
        """稼働時間を取得"""
        if not self.running:
            return "Not running"
        
        process = psutil.Process()
        create_time = datetime.fromtimestamp(process.create_time())
        uptime = datetime.now() - create_time
        
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)
        
        return f"{hours}h {minutes}m"
        
    def print_status(self):
        """ステータスを表示"""
        status = self.get_status()
        
        print("\n" + "="*60)
        print("📊 Stability Monitor Status")
        print("="*60)
        print(f"Running: {'✅ Yes' if status['running'] else '❌ No'}")
        print(f"Uptime: {status['uptime']}")
        print()
        
        print("📈 Metrics:")
        for name, stats in status['metrics'].items():
            print(f"  {name}:")
            print(f"    Current: {stats['current']:.2f}")
            print(f"    Average: {stats['avg']:.2f}")
            print(f"    Max: {stats['max']:.2f}")
        print()
        
        print(f"🚨 Recent Alerts: {status['recent_alerts']}")
        print("="*60)


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Trinity Stability Monitor')
    parser.add_argument('--start', action='store_true', help='Start monitoring')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    
    args = parser.parse_args()
    
    monitor = StabilityMonitor()
    
    if args.start or args.daemon:
        monitor.start()
        
        if args.daemon:
            print("Running in daemon mode (Ctrl+C to stop)...")
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                monitor.stop()
                print("\n👋 Goodbye!")
        else:
            # 10秒間テスト実行
            time.sleep(10)
            monitor.print_status()
            monitor.stop()
            
    elif args.status:
        # 既存プロセスのステータスチェック（簡易版）
        print("Checking monitor status...")
        monitor.print_status()
    else:
        print("Usage: python3 stability_monitor.py --start | --status | --daemon")
        return 1
        
    return 0


if __name__ == '__main__':
    sys.exit(main())


