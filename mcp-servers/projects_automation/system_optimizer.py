#!/usr/bin/env python3
"""
🚀 システム最適化エンジン
メモリ、ディスク、プロセスを自動最適化
"""

import os
import psutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
import json

class SystemOptimizer:
    def __init__(self):
        self.results = []
        self.log_file = "/root/logs/system_optimizer.log"
        Path("/root/logs").mkdir(exist_ok=True)
    
    def log(self, msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {msg}"
        print(log_msg)
        with open(self.log_file, 'a') as f:
            f.write(log_msg + "\n")
    
    # メモリ最適化
    def optimize_memory(self):
        """メモリ最適化"""
        self.log("=" * 60)
        self.log("💾 メモリ最適化開始")
        
        before = psutil.virtual_memory()
        self.log(f"最適化前: {before.percent}% 使用 ({before.used / 1024**3:.1f}GB / {before.total / 1024**3:.1f}GB)")
        
        actions = []
        
        # 1. ページキャッシュクリア
        try:
            subprocess.run("sync", shell=True, check=True)
            subprocess.run("echo 3 > /proc/sys/vm/drop_caches", shell=True, check=True)
            actions.append("✅ ページキャッシュクリア")
        except subprocess.SubprocessError:
            actions.append("❌ ページキャッシュクリア失敗")
        
        # 2. スワップクリア
        try:
            subprocess.run("swapoff -a && swapon -a", shell=True, check=True)
            actions.append("✅ スワップクリア")
        except subprocess.SubprocessError:
            actions.append("⚠️ スワップなし/スキップ")
        
        # 3. 不要なプロセス特定
        heavy_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
            try:
                if proc.info['memory_percent'] > 5.0:
                    heavy_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'memory': f"{proc.info['memory_percent']:.1f}%"
                    })
            except Exception:
                pass
        
        after = psutil.virtual_memory()
        freed = before.used - after.used
        
        self.log(f"最適化後: {after.percent}% 使用 ({after.used / 1024**3:.1f}GB / {after.total / 1024**3:.1f}GB)")
        self.log(f"解放量: {freed / 1024**3:.2f}GB")
        
        for action in actions:
            self.log(f"  {action}")
        
        if heavy_processes:
            self.log(f"⚠️ メモリ大量消費プロセス({len(heavy_processes)}個):")
            for p in heavy_processes[:5]:
                self.log(f"   PID {p['pid']}: {p['name']} ({p['memory']})")
        
        return {
            "before": before.percent,
            "after": after.percent,
            "freed_gb": freed / 1024**3,
            "heavy_processes": heavy_processes
        }
    
    # ディスク最適化
    def optimize_disk(self):
        """ディスク最適化"""
        self.log("=" * 60)
        self.log("💿 ディスク最適化開始")
        
        actions = []
        freed_total = 0
        
        # 1. 古いログ削除
        log_dirs = ['/var/log', '/root/logs', '/tmp']
        for log_dir in log_dirs:
            if os.path.exists(log_dir):
                try:
                    result = subprocess.run(
                        f"find {log_dir} -type f -name '*.log' -mtime +7 -exec rm -f {{}} \\;",
                        shell=True, capture_output=True
                    )
                    actions.append(f"✅ {log_dir}: 7日以上前のログ削除")
                except subprocess.SubprocessError:
                    pass
        
        # 2. パッケージキャッシュクリア
        try:
            result = subprocess.run("apt-get clean", shell=True, capture_output=True)
            actions.append("✅ aptキャッシュクリア")
        except subprocess.SubprocessError:
            pass
        
        # 3. tmpファイルクリア
        try:
            subprocess.run("find /tmp -type f -atime +7 -delete", shell=True)
            actions.append("✅ /tmp: 7日以上前のファイル削除")
        except subprocess.SubprocessError:
            pass
        
        # 4. サムネイルキャッシュクリア
        try:
            subprocess.run("rm -rf /root/.cache/thumbnails/*", shell=True)
            actions.append("✅ サムネイルキャッシュクリア")
        except subprocess.SubprocessError:
            pass
        
        # ディスク使用状況
        disk = psutil.disk_usage('/')
        
        self.log(f"ディスク使用: {disk.percent}% ({disk.used / 1024**3:.1f}GB / {disk.total / 1024**3:.1f}GB)")
        self.log(f"空き容量: {disk.free / 1024**3:.1f}GB")
        
        for action in actions:
            self.log(f"  {action}")
        
        # 大きいディレクトリトップ5
        self.log("📊 大きいディレクトリ:")
        try:
            result = subprocess.run(
                "du -sh /root/* 2>/dev/null | sort -hr | head -5",
                shell=True, capture_output=True, text=True
            )
            for line in result.stdout.strip().split('\n'):
                self.log(f"   {line}")
        except subprocess.SubprocessError:
            pass
        
        return {
            "disk_percent": disk.percent,
            "free_gb": disk.free / 1024**3,
            "actions": actions
        }
    
    # プロセス最適化
    def optimize_processes(self):
        """プロセス最適化"""
        self.log("=" * 60)
        self.log("⚙️ プロセス最適化開始")
        
        # CPU使用率の高いプロセス
        high_cpu = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                cpu = proc.info['cpu_percent']
                if cpu > 50.0:
                    high_cpu.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu': cpu,
                        'memory': proc.info['memory_percent']
                    })
            except Exception:
                pass
        
        # ゾンビプロセス
        zombies = []
        for proc in psutil.process_iter(['pid', 'name', 'status']):
            try:
                if proc.info['status'] == psutil.STATUS_ZOMBIE:
                    zombies.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name']
                    })
            except Exception:
                pass
        
        total_procs = len(list(psutil.process_iter()))
        
        self.log(f"総プロセス数: {total_procs}")
        
        if high_cpu:
            self.log(f"⚠️ CPU高負荷プロセス({len(high_cpu)}個):")
            for p in high_cpu[:5]:
                self.log(f"   PID {p['pid']}: {p['name']} (CPU: {p['cpu']:.1f}%, MEM: {p['memory']:.1f}%)")
        
        if zombies:
            self.log(f"⚠️ ゾンビプロセス({len(zombies)}個):")
            for z in zombies:
                self.log(f"   PID {z['pid']}: {z['name']}")
        
        return {
            "total_processes": total_procs,
            "high_cpu": high_cpu,
            "zombies": zombies
        }
    
    # フル最適化
    def full_optimize(self):
        """フル最適化実行"""
        self.log("🚀 システム最適化開始")
        self.log(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        start = time.time()
        
        results = {
            "memory": self.optimize_memory(),
            "disk": self.optimize_disk(),
            "processes": self.optimize_processes()
        }
        
        elapsed = time.time() - start
        
        self.log("=" * 60)
        self.log(f"✅ 最適化完了 ({elapsed:.2f}秒)")
        self.log("=" * 60)
        
        # レポート保存
        report_file = f"/root/logs/optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "elapsed": elapsed,
                "results": results
            }, f, indent=2)
        
        self.log(f"📄 レポート: {report_file}")
        
        return results

if __name__ == "__main__":
    optimizer = SystemOptimizer()
    optimizer.full_optimize()
