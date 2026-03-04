#!/usr/bin/env python3
"""
パフォーマンス分析システム
システムパフォーマンスの分析、ボトルネック検出、最適化提案
"""

import psutil
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """パフォーマンス分析システム"""
    
    def __init__(self, base_path: str = "/root"):
        self.base_path = Path(base_path)
        self.config_path = self.base_path / ".performance_config.json"
        self.report_path = self.base_path / "performance_report.json"
        
        self.default_config = {
            "enabled": True,
            "monitoring_duration": 60,  # 秒
            "thresholds": {
                "cpu_high": 80,
                "memory_high": 85,
                "disk_io_high": 1000,  # MB/s
                "network_high": 1000   # MB/s
            },
            "checks": {
                "cpu": True,
                "memory": True,
                "disk": True,
                "network": True,
                "processes": True,
                "system_load": True
            }
        }
        
        self.config = self.load_config()
        
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
    
    def monitor_cpu(self, duration: int = 60) -> Dict:
        """CPU監視"""
        logger.info(f"📊 CPU監視中... ({duration}秒)")
        
        samples = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            load_avg = psutil.getloadavg()
            
            samples.append({
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": sum(cpu_percent) / len(cpu_percent),
                "cpu_per_core": cpu_percent,
                "cpu_count": cpu_count,
                "cpu_freq_mhz": cpu_freq.current if cpu_freq else 0,
                "load_avg_1m": load_avg[0],
                "load_avg_5m": load_avg[1],
                "load_avg_15m": load_avg[2]
            })
        
        # 統計計算
        avg_cpu = sum(s["cpu_percent"] for s in samples) / len(samples)
        max_cpu = max(s["cpu_percent"] for s in samples)
        min_cpu = min(s["cpu_percent"] for s in samples)
        
        return {
            "samples": samples,
            "statistics": {
                "avg": round(avg_cpu, 2),
                "max": round(max_cpu, 2),
                "min": round(min_cpu, 2),
                "duration": duration
            },
            "issues": self._check_cpu_issues(avg_cpu, max_cpu)
        }
    
    def monitor_memory(self, duration: int = 60) -> Dict:
        """メモリ監視"""
        logger.info(f"📊 メモリ監視中... ({duration}秒)")
        
        samples = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            samples.append({
                "timestamp": datetime.now().isoformat(),
                "memory_percent": memory.percent,
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "swap_percent": swap.percent,
                "swap_used_gb": round(swap.used / (1024**3), 2)
            })
            
            time.sleep(1)
        
        # 統計計算
        avg_memory = sum(s["memory_percent"] for s in samples) / len(samples)
        max_memory = max(s["memory_percent"] for s in samples)
        
        return {
            "samples": samples,
            "statistics": {
                "avg": round(avg_memory, 2),
                "max": round(max_memory, 2),
                "duration": duration
            },
            "issues": self._check_memory_issues(avg_memory, max_memory)
        }
    
    def monitor_disk(self, duration: int = 60) -> Dict:
        """ディスク監視"""
        logger.info(f"📊 ディスク監視中... ({duration}秒)")
        
        samples = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            disk_usage = psutil.disk_usage(self.base_path)
            disk_io = psutil.disk_io_counters()
            
            samples.append({
                "timestamp": datetime.now().isoformat(),
                "disk_percent": disk_usage.percent,
                "disk_used_gb": round(disk_usage.used / (1024**3), 2),
                "disk_free_gb": round(disk_usage.free / (1024**3), 2),
                "read_bytes_mb": round(disk_io.read_bytes / (1024**2), 2),
                "write_bytes_mb": round(disk_io.write_bytes / (1024**2), 2)
            })
            
            time.sleep(1)
        
        # 統計計算
        avg_disk = sum(s["disk_percent"] for s in samples) / len(samples)
        max_disk = max(s["disk_percent"] for s in samples)
        
        return {
            "samples": samples,
            "statistics": {
                "avg": round(avg_disk, 2),
                "max": round(max_disk, 2),
                "duration": duration
            },
            "issues": self._check_disk_issues(avg_disk, max_disk)
        }
    
    def monitor_network(self, duration: int = 60) -> Dict:
        """ネットワーク監視"""
        logger.info(f"📊 ネットワーク監視中... ({duration}秒)")
        
        samples = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            net_io = psutil.net_io_counters()
            
            samples.append({
                "timestamp": datetime.now().isoformat(),
                "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
                "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errors_in": net_io.errin,
                "errors_out": net_io.errout
            })
            
            time.sleep(1)
        
        return {
            "samples": samples,
            "statistics": {
                "duration": duration,
                "total_sent_mb": samples[-1]["bytes_sent_mb"],
                "total_recv_mb": samples[-1]["bytes_recv_mb"]
            },
            "issues": self._check_network_issues(samples)
        }
    
    def analyze_processes(self) -> Dict:
        """プロセス分析"""
        logger.info("📊 プロセス分析中...")
        
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                proc_info = proc.info
                processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # CPU使用率でソート
        cpu_top = sorted(processes, key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)[:10]
        
        # メモリ使用率でソート
        memory_top = sorted(processes, key=lambda x: x.get('memory_percent', 0) or 0, reverse=True)[:10]
        
        return {
            "total_processes": len(processes),
            "cpu_top_10": cpu_top,
            "memory_top_10": memory_top,
            "issues": self._check_process_issues(processes)
        }
    
    def _check_cpu_issues(self, avg: float, max: float) -> List[Dict]:
        """CPU問題チェック"""
        issues = []
        threshold = self.config["thresholds"]["cpu_high"]
        
        if avg > threshold:
            issues.append({
                "severity": "high",
                "message": f"CPU平均使用率が高いです: {avg:.1f}% (閾値: {threshold}%)",
                "recommendation": "CPU使用率の高いプロセスを確認してください"
            })
        
        if max > threshold:
            issues.append({
                "severity": "medium",
                "message": f"CPU最大使用率が高いです: {max:.1f}%",
                "recommendation": "CPU使用率のピークを確認してください"
            })
        
        return issues
    
    def _check_memory_issues(self, avg: float, max: float) -> List[Dict]:
        """メモリ問題チェック"""
        issues = []
        threshold = self.config["thresholds"]["memory_high"]
        
        if avg > threshold:
            issues.append({
                "severity": "high",
                "message": f"メモリ平均使用率が高いです: {avg:.1f}% (閾値: {threshold}%)",
                "recommendation": "メモリ使用量の多いプロセスを確認してください"
            })
        
        if max > threshold:
            issues.append({
                "severity": "medium",
                "message": f"メモリ最大使用率が高いです: {max:.1f}%",
                "recommendation": "メモリリークの可能性を確認してください"
            })
        
        return issues
    
    def _check_disk_issues(self, avg: float, max: float) -> List[Dict]:
        """ディスク問題チェック"""
        issues = []
        threshold = 90
        
        if avg > threshold:
            issues.append({
                "severity": "critical",
                "message": f"ディスク使用率が高いです: {avg:.1f}%",
                "recommendation": "不要なファイルを削除してください"
            })
        
        if max > threshold:
            issues.append({
                "severity": "high",
                "message": f"ディスク使用率のピークが高いです: {max:.1f}%",
                "recommendation": "ディスク容量を増やすことを検討してください"
            })
        
        return issues
    
    def _check_network_issues(self, samples: List[Dict]) -> List[Dict]:
        """ネットワーク問題チェック"""
        issues = []
        
        # エラー率チェック
        total_errors = samples[-1]["errors_in"] + samples[-1]["errors_out"]
        if total_errors > 100:
            issues.append({
                "severity": "medium",
                "message": f"ネットワークエラーが検出されました: {total_errors}件",
                "recommendation": "ネットワーク設定を確認してください"
            })
        
        return issues
    
    def _check_process_issues(self, processes: List[Dict]) -> List[Dict]:
        """プロセス問題チェック"""
        issues = []
        
        # ゾンビプロセスチェック
        zombie_count = sum(1 for p in processes if p.get('status') == 'zombie')
        if zombie_count > 0:
            issues.append({
                "severity": "high",
                "message": f"ゾンビプロセスが検出されました: {zombie_count}個",
                "recommendation": "ゾンビプロセスをクリーンアップしてください"
            })
        
        # プロセス数チェック
        if len(processes) > 1000:
            issues.append({
                "severity": "medium",
                "message": f"プロセス数が多いです: {len(processes)}個",
                "recommendation": "不要なプロセスを終了してください"
            })
        
        return issues
    
    def run_full_analysis(self) -> Dict:
        """フル分析実行"""
        logger.info("=" * 60)
        logger.info("📊 パフォーマンス分析開始")
        logger.info("=" * 60)
        
        duration = self.config["monitoring_duration"]
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "duration": duration,
            "cpu": {},
            "memory": {},
            "disk": {},
            "network": {},
            "processes": {},
            "all_issues": [],
            "performance_score": 100
        }
        
        # CPU分析
        if self.config["checks"]["cpu"]:
            report["cpu"] = self.monitor_cpu(duration)
            report["all_issues"].extend(report["cpu"]["issues"])
        
        # メモリ分析
        if self.config["checks"]["memory"]:
            report["memory"] = self.monitor_memory(duration)
            report["all_issues"].extend(report["memory"]["issues"])
        
        # ディスク分析
        if self.config["checks"]["disk"]:
            report["disk"] = self.monitor_disk(duration)
            report["all_issues"].extend(report["disk"]["issues"])
        
        # ネットワーク分析
        if self.config["checks"]["network"]:
            report["network"] = self.monitor_network(duration)
            report["all_issues"].extend(report["network"]["issues"])
        
        # プロセス分析
        if self.config["checks"]["processes"]:
            report["processes"] = self.analyze_processes()
            report["all_issues"].extend(report["processes"]["issues"])
        
        # パフォーマンススコア計算
        report["performance_score"] = self.calculate_performance_score(report["all_issues"])
        
        # レポート保存
        with open(self.report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info("=" * 60)
        logger.info("✅ パフォーマンス分析完了")
        logger.info(f"   問題数: {len(report['all_issues'])}")
        logger.info(f"   パフォーマンススコア: {report['performance_score']}/100")
        logger.info("=" * 60)
        
        return report
    
    def calculate_performance_score(self, issues: List[Dict]) -> int:
        """パフォーマンススコア計算"""
        score = 100
        
        for issue in issues:
            severity = issue["severity"]
            if severity == "critical":
                score -= 20
            elif severity == "high":
                score -= 10
            elif severity == "medium":
                score -= 5
            elif severity == "low":
                score -= 2
        
        return max(0, score)


def main():
    """メイン実行"""
    analyzer = PerformanceAnalyzer()
    
    print("=" * 60)
    print("📊 パフォーマンス分析システム")
    print("=" * 60)
    
    print("\n📊 監視設定:")
    print(f"  監視時間: {analyzer.config['monitoring_duration']}秒")
    print(f"  CPU閾値: {analyzer.config['thresholds']['cpu_high']}%")
    print(f"  メモリ閾値: {analyzer.config['thresholds']['memory_high']}%")
    
    print("\n実行する操作を選択:")
    print("  1. フル分析実行")
    print("  2. CPU分析のみ")
    print("  3. メモリ分析のみ")
    print("  4. ディスク分析のみ")
    print("  5. プロセス分析のみ")
    print("  0. 終了")
    
    choice = input("\n選択 (0-5): ").strip()
    
    if choice == "1":
        print("\n📊 フル分析実行中...")
        report = analyzer.run_full_analysis()
        
        print("\n📊 分析結果:")
        print(f"  問題数: {len(report['all_issues'])}")
        print(f"  パフォーマンススコア: {report['performance_score']}/100")
        
        if report['all_issues']:
            print("\n⚠️  発見された問題:")
            for issue in report['all_issues'][:5]:
                print(f"    [{issue['severity'].upper()}] {issue['message']}")
    
    elif choice == "2":
        print("\n📊 CPU分析中...")
        result = analyzer.monitor_cpu(10)
        print(f"✅ 完了: 平均 {result['statistics']['avg']:.1f}%")
    
    elif choice == "3":
        print("\n📊 メモリ分析中...")
        result = analyzer.monitor_memory(10)
        print(f"✅ 完了: 平均 {result['statistics']['avg']:.1f}%")
    
    elif choice == "4":
        print("\n📊 ディスク分析中...")
        result = analyzer.monitor_disk(10)
        print(f"✅ 完了: 平均 {result['statistics']['avg']:.1f}%")
    
    elif choice == "5":
        print("\n📊 プロセス分析中...")
        result = analyzer.analyze_processes()
        print(f"✅ 完了: {result['total_processes']}個のプロセス")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

