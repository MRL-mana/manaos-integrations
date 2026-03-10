#!/usr/bin/env python3
"""
👁️ リアルタイムシステム監視＆異常検知
CPU、メモリ、ディスク、ネットワークを監視してアラート
"""

import psutil
import time
from datetime import datetime
import json
from pathlib import Path

class SystemMonitor:
    def __init__(self):
        self.thresholds = {
            "cpu": 80.0,      # CPU 80%以上で警告
            "memory": 85.0,   # メモリ 85%以上で警告
            "disk": 90.0,     # ディスク 90%以上で警告
            "load": 4.0       # ロードアベレージ 4.0以上で警告
        }
        self.alerts = []
        self.log_file = "/root/logs/system_monitor.log"
        Path("/root/logs").mkdir(exist_ok=True)
    
    def log(self, msg, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {msg}"
        print(log_msg)
        with open(self.log_file, 'a') as f:
            f.write(log_msg + "\n")
    
    def check_cpu(self):
        """CPU監視"""
        cpu_percent = psutil.cpu_percent(interval=1)
        load_avg = psutil.getloadavg()[0]
        
        status = "🟢 正常"
        if cpu_percent > self.thresholds["cpu"]:
            status = "🔴 警告"
            self.alerts.append(f"CPU使用率が高い: {cpu_percent}%")
            self.log(f"⚠️ CPU: {cpu_percent}% (閾値: {self.thresholds['cpu']}%)", "WARNING")
        
        if load_avg > self.thresholds["load"]:
            self.alerts.append(f"ロードアベレージが高い: {load_avg:.2f}")
            self.log(f"⚠️ Load Average: {load_avg:.2f} (閾値: {self.thresholds['load']})", "WARNING")
        
        return {
            "status": status,
            "cpu_percent": cpu_percent,
            "load_average": load_avg,
            "cpu_count": psutil.cpu_count()
        }
    
    def check_memory(self):
        """メモリ監視"""
        mem = psutil.virtual_memory()
        
        status = "🟢 正常"
        if mem.percent > self.thresholds["memory"]:
            status = "🔴 警告"
            self.alerts.append(f"メモリ使用率が高い: {mem.percent}%")
            self.log(f"⚠️ メモリ: {mem.percent}% (閾値: {self.thresholds['memory']}%)", "WARNING")
        
        return {
            "status": status,
            "percent": mem.percent,
            "used_gb": mem.used / 1024**3,
            "total_gb": mem.total / 1024**3,
            "available_gb": mem.available / 1024**3
        }
    
    def check_disk(self):
        """ディスク監視"""
        disk = psutil.disk_usage('/')
        
        status = "🟢 正常"
        if disk.percent > self.thresholds["disk"]:
            status = "🔴 警告"
            self.alerts.append(f"ディスク使用率が高い: {disk.percent}%")
            self.log(f"⚠️ ディスク: {disk.percent}% (閾値: {self.thresholds['disk']}%)", "WARNING")
        
        # ディスクI/O
        io = psutil.disk_io_counters()
        
        return {
            "status": status,
            "percent": disk.percent,
            "used_gb": disk.used / 1024**3,
            "free_gb": disk.free / 1024**3,
            "total_gb": disk.total / 1024**3,
            "read_mb": io.read_bytes / 1024**2,  # type: ignore[union-attr]
            "write_mb": io.write_bytes / 1024**2  # type: ignore[union-attr]
        }
    
    def check_network(self):
        """ネットワーク監視"""
        net = psutil.net_io_counters()
        
        return {
            "bytes_sent_mb": net.bytes_sent / 1024**2,
            "bytes_recv_mb": net.bytes_recv / 1024**2,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "errors": net.errin + net.errout
        }
    
    def check_processes(self):
        """プロセス監視"""
        high_cpu = []
        high_mem = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if proc.info['cpu_percent'] > 50:
                    high_cpu.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu': proc.info['cpu_percent']
                    })
                if proc.info['memory_percent'] > 5:
                    high_mem.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'memory': proc.info['memory_percent']
                    })
            except Exception:
                pass
        
        return {
            "total": len(list(psutil.process_iter())),
            "high_cpu": high_cpu[:5],
            "high_memory": high_mem[:5]
        }
    
    def get_snapshot(self):
        """システムスナップショット取得"""
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "cpu": self.check_cpu(),
            "memory": self.check_memory(),
            "disk": self.check_disk(),
            "network": self.check_network(),
            "processes": self.check_processes(),
            "alerts": self.alerts.copy()
        }
        
        self.alerts.clear()
        return snapshot
    
    def monitor_continuous(self, interval=5, duration=60):
        """継続監視"""
        self.log(f"🔍 継続監視開始 (間隔: {interval}秒, 期間: {duration}秒)")
        
        snapshots = []
        start = time.time()
        
        while time.time() - start < duration:
            snapshot = self.get_snapshot()
            snapshots.append(snapshot)
            
            # ステータス表示
            print(f"\n⏰ {snapshot['timestamp']}")
            print(f"CPU: {snapshot['cpu']['cpu_percent']:.1f}% {snapshot['cpu']['status']}")
            print(f"メモリ: {snapshot['memory']['percent']:.1f}% {snapshot['memory']['status']}")
            print(f"ディスク: {snapshot['disk']['percent']:.1f}% {snapshot['disk']['status']}")
            
            if snapshot['alerts']:
                print(f"⚠️ アラート: {len(snapshot['alerts'])}件")
                for alert in snapshot['alerts']:
                    print(f"   - {alert}")
            
            time.sleep(interval)
        
        # レポート保存
        report_file = f"/root/logs/monitor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(snapshots, f, indent=2)
        
        self.log(f"📄 監視レポート: {report_file}")
        
        return snapshots
    
    def quick_check(self):
        """クイックチェック"""
        print("=" * 60)
        print("👁️ システムクイックチェック")
        print("=" * 60)
        
        snapshot = self.get_snapshot()
        
        print(f"\n⏰ {snapshot['timestamp']}")
        print("\n💻 CPU")
        print(f"  使用率: {snapshot['cpu']['cpu_percent']:.1f}% {snapshot['cpu']['status']}")
        print(f"  負荷: {snapshot['cpu']['load_average']:.2f}")
        print(f"  コア数: {snapshot['cpu']['cpu_count']}")
        
        print("\n💾 メモリ")
        print(f"  使用率: {snapshot['memory']['percent']:.1f}% {snapshot['memory']['status']}")
        print(f"  使用量: {snapshot['memory']['used_gb']:.1f}GB / {snapshot['memory']['total_gb']:.1f}GB")
        print(f"  空き: {snapshot['memory']['available_gb']:.1f}GB")
        
        print("\n💿 ディスク")
        print(f"  使用率: {snapshot['disk']['percent']:.1f}% {snapshot['disk']['status']}")
        print(f"  使用量: {snapshot['disk']['used_gb']:.1f}GB / {snapshot['disk']['total_gb']:.1f}GB")
        print(f"  空き: {snapshot['disk']['free_gb']:.1f}GB")
        
        print("\n🌐 ネットワーク")
        print(f"  送信: {snapshot['network']['bytes_sent_mb']:.1f}MB")
        print(f"  受信: {snapshot['network']['bytes_recv_mb']:.1f}MB")
        
        print("\n⚙️ プロセス")
        print(f"  総数: {snapshot['processes']['total']}")
        if snapshot['processes']['high_cpu']:
            print(f"  CPU高負荷: {len(snapshot['processes']['high_cpu'])}個")
        if snapshot['processes']['high_memory']:
            print(f"  メモリ大量消費: {len(snapshot['processes']['high_memory'])}個")
        
        if snapshot['alerts']:
            print(f"\n⚠️ アラート ({len(snapshot['alerts'])}件):")
            for alert in snapshot['alerts']:
                print(f"  - {alert}")
        else:
            print("\n✅ 異常なし")
        
        print("=" * 60)
        
        return snapshot

if __name__ == "__main__":
    import sys
    
    monitor = SystemMonitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        duration = int(sys.argv[3]) if len(sys.argv) > 3 else 60
        monitor.monitor_continuous(interval, duration)
    else:
        monitor.quick_check()

