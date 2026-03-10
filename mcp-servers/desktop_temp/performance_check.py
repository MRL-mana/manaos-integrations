"""
新PC（母艦）性能チェックツール
システムのパフォーマンスを包括的にチェックします
"""

import platform
import psutil
import sys
import time
from datetime import datetime
import json
import subprocess
from typing import Dict, List, Optional

try:
    import GPUtil
    HAS_GPUTIL = True
except ImportError:
    HAS_GPUTIL = False

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class PerformanceChecker:
    """システム性能チェッカー"""
    
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
    
    def print_header(self, title: str):
        """セクションヘッダーを表示"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)
    
    def check_system_info(self) -> Dict:
        """システム基本情報を取得"""
        self.print_header("システム基本情報")
        
        info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "architecture": platform.architecture()[0],
            "python_version": sys.version.split()[0]
        }
        
        for key, value in info.items():
            print(f"{key:20s}: {value}")
        
        return info
    
    def check_cpu(self) -> Dict:
        """CPU性能をチェック"""
        self.print_header("CPU性能")
        
        cpu_count_physical = psutil.cpu_count(logical=False)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        cpu_percent_avg = sum(cpu_percent) / len(cpu_percent)
        
        print(f"物理CPUコア数    : {cpu_count_physical}")
        print(f"論理CPUコア数    : {cpu_count_logical}")
        if cpu_freq:
            print(f"現在の周波数    : {cpu_freq.current:.2f} MHz")
            print(f"最小周波数      : {cpu_freq.min:.2f} MHz")
            print(f"最大周波数      : {cpu_freq.max:.2f} MHz")
        print(f"CPU使用率（平均）: {cpu_percent_avg:.1f}%")
        print(f"CPU使用率（各コア）:")
        for i, percent in enumerate(cpu_percent):
            bar = "█" * int(percent / 2)
            print(f"  コア {i+1:2d}: {percent:5.1f}% {bar}")
        
        # CPUベンチマーク（簡単な計算テスト）
        print("\nCPUベンチマーク実行中...")
        start = time.time()
        result = sum(i * i for i in range(10000000))
        cpu_bench_time = time.time() - start
        print(f"計算テスト時間   : {cpu_bench_time:.3f}秒 (1000万回の二乗計算)")
        
        cpu_info = {
            "physical_cores": cpu_count_physical,
            "logical_cores": cpu_count_logical,
            "frequency": {
                "current": cpu_freq.current if cpu_freq else None,
                "min": cpu_freq.min if cpu_freq else None,
                "max": cpu_freq.max if cpu_freq else None
            },
            "usage_percent": cpu_percent_avg,
            "usage_per_core": cpu_percent,
            "benchmark_time": cpu_bench_time
        }
        
        return cpu_info
    
    def check_memory(self) -> Dict:
        """メモリ性能をチェック"""
        self.print_header("メモリ（RAM）情報")
        
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        print(f"総メモリ容量     : {mem.total / (1024**3):.2f} GB")
        print(f"使用可能メモリ   : {mem.available / (1024**3):.2f} GB")
        print(f"使用中メモリ     : {mem.used / (1024**3):.2f} GB")
        print(f"メモリ使用率     : {mem.percent:.1f}%")
        print(f"空きメモリ       : {mem.free / (1024**3):.2f} GB")
        
        print(f"\nスワップ（仮想メモリ）:")
        print(f"総スワップ容量   : {swap.total / (1024**3):.2f} GB")
        print(f"使用中スワップ   : {swap.used / (1024**3):.2f} GB")
        print(f"スワップ使用率   : {swap.percent:.1f}%")
        
        # メモリベンチマーク（メモリアクセステスト）
        print("\nメモリベンチマーク実行中...")
        start = time.time()
        test_data = [0] * (100 * 1024 * 1024)  # 100MB
        for i in range(len(test_data)):
            test_data[i] = i
        mem_bench_time = time.time() - start
        del test_data
        print(f"メモリアクセステスト: {mem_bench_time:.3f}秒 (100MB書き込み)")
        
        mem_info = {
            "total_gb": mem.total / (1024**3),
            "available_gb": mem.available / (1024**3),
            "used_gb": mem.used / (1024**3),
            "free_gb": mem.free / (1024**3),
            "percent": mem.percent,
            "swap_total_gb": swap.total / (1024**3),
            "swap_used_gb": swap.used / (1024**3),
            "swap_percent": swap.percent,
            "benchmark_time": mem_bench_time
        }
        
        return mem_info
    
    def check_disk(self) -> Dict:
        """ディスク性能をチェック"""
        self.print_header("ディスク情報")
        
        disk_info = {}
        partitions = psutil.disk_partitions()
        
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                print(f"\nパーティション: {partition.device}")
                print(f"  マウントポイント: {partition.mountpoint}")
                print(f"  ファイルシステム: {partition.fstype}")
                print(f"  総容量          : {usage.total / (1024**3):.2f} GB")
                print(f"  使用中          : {usage.used / (1024**3):.2f} GB")
                print(f"  空き容量        : {usage.free / (1024**3):.2f} GB")
                print(f"  使用率          : {usage.percent:.1f}%")
                
                disk_info[partition.mountpoint] = {
                    "device": partition.device,
                    "fstype": partition.fstype,
                    "total_gb": usage.total / (1024**3),
                    "used_gb": usage.used / (1024**3),
                    "free_gb": usage.free / (1024**3),
                    "percent": usage.percent
                }
            except PermissionError:
                print(f"\nパーティション: {partition.device} (アクセス権限なし)")
        
        # ディスクI/O統計
        print("\nディスクI/O統計:")
        io = psutil.disk_io_counters()
        if io:
            print(f"読み込み回数    : {io.read_count:,}")
            print(f"書き込み回数    : {io.write_count:,}")
            print(f"読み込みバイト  : {io.read_bytes / (1024**3):.2f} GB")
            print(f"書き込みバイト  : {io.write_bytes / (1024**3):.2f} GB")
            disk_info["io_stats"] = {
                "read_count": io.read_count,
                "write_count": io.write_count,
                "read_bytes_gb": io.read_bytes / (1024**3),
                "write_bytes_gb": io.write_bytes / (1024**3)
            }
        
        return disk_info
    
    def check_network(self) -> Dict:
        """ネットワーク性能をチェック"""
        self.print_header("ネットワーク情報")
        
        net_info = {}
        
        # ネットワークインターフェース
        print("ネットワークインターフェース:")
        net_if_addrs = psutil.net_if_addrs()
        net_if_stats = psutil.net_if_stats()
        
        for interface_name, addresses in net_if_addrs.items():
            stats = net_if_stats.get(interface_name)
            print(f"\n{interface_name}:")
            if stats:
                print(f"  状態          : {'有効' if stats.isup else '無効'}")
                print(f"  速度          : {stats.speed} Mbps" if stats.speed > 0 else "  速度          : 不明")
                print(f"  MTU           : {stats.mtu}")
            
            for addr in addresses:
                if addr.family == 2:  # IPv4
                    print(f"  IPv4アドレス  : {addr.address}")
                    if addr.netmask:
                        print(f"  サブネット    : {addr.netmask}")
                elif addr.family == 23:  # IPv6
                    print(f"  IPv6アドレス  : {addr.address}")
        
        # ネットワークI/O統計
        print("\nネットワークI/O統計:")
        net_io = psutil.net_io_counters()
        if net_io:
            print(f"送信バイト      : {net_io.bytes_sent / (1024**3):.2f} GB")
            print(f"受信バイト      : {net_io.bytes_recv / (1024**3):.2f} GB")
            print(f"送信パケット    : {net_io.packets_sent:,}")
            print(f"受信パケット    : {net_io.packets_recv:,}")
            net_info["io_stats"] = {
                "bytes_sent_gb": net_io.bytes_sent / (1024**3),
                "bytes_recv_gb": net_io.bytes_recv / (1024**3),
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        
        return net_info
    
    def check_gpu(self) -> Optional[Dict]:
        """GPU性能をチェック"""
        self.print_header("GPU情報")
        
        gpu_info = {}
        
        # NVIDIA GPU (nvidia-smi)
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu", 
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("NVIDIA GPU:")
                lines = result.stdout.strip().split('\n')
                for i, line in enumerate(lines):
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 6:
                        print(f"\n  GPU {i}:")
                        print(f"    名前          : {parts[0]}")
                        print(f"    総VRAM        : {parts[1]} MB")
                        print(f"    使用VRAM      : {parts[2]} MB")
                        print(f"    空きVRAM      : {parts[3]} MB")
                        print(f"    温度          : {parts[4]} °C")
                        print(f"    使用率        : {parts[5]}%")
                        gpu_info[f"gpu_{i}"] = {
                            "name": parts[0],
                            "memory_total_mb": int(parts[1]),
                            "memory_used_mb": int(parts[2]),
                            "memory_free_mb": int(parts[3]),
                            "temperature": int(parts[4]),
                            "utilization": int(parts[5])
                        }
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass
        
        # GPUtilライブラリ
        if HAS_GPUTIL:
            try:
                gpus = GPUtil.getGPUs()  # type: ignore[possibly-unbound]
                if gpus:
                    print("\nGPUtilライブラリによる情報:")
                    for gpu in gpus:
                        print(f"\n  GPU {gpu.id}: {gpu.name}")
                        print(f"    総VRAM        : {gpu.memoryTotal} MB")
                        print(f"    使用VRAM      : {gpu.memoryUsed} MB")
                        print(f"    空きVRAM      : {gpu.memoryFree} MB")
                        print(f"    使用率        : {gpu.load * 100:.1f}%")
                        print(f"    温度          : {gpu.temperature} °C")
            except Exception as e:
                print(f"GPUtilエラー: {e}")
        
        # PyTorch CUDA
        if HAS_TORCH and torch.cuda.is_available():  # type: ignore[possibly-unbound]
            print("\nPyTorch CUDA情報:")
            print(f"  CUDA利用可能  : はい")
            print(f"  CUDAバージョン: {torch.version.cuda}")  # type: ignore[possibly-unbound]
            print(f"  cuDNNバージョン: {torch.backends.cudnn.version()}")  # type: ignore[possibly-unbound]
            print(f"  GPU数          : {torch.cuda.device_count()}")  # type: ignore[possibly-unbound]
            for i in range(torch.cuda.device_count()):  # type: ignore[possibly-unbound]
                print(f"\n  GPU {i}: {torch.cuda.get_device_name(i)}")  # type: ignore[possibly-unbound]
                props = torch.cuda.get_device_properties(i)  # type: ignore[possibly-unbound]
                print(f"    総メモリ      : {props.total_memory / (1024**3):.2f} GB")
                print(f"    マルチプロセッサ数: {props.multi_processor_count}")
                print(f"    計算能力      : {props.major}.{props.minor}")
                gpu_info[f"pytorch_gpu_{i}"] = {
                    "name": torch.cuda.get_device_name(i),  # type: ignore[possibly-unbound]
                    "total_memory_gb": props.total_memory / (1024**3),
                    "multi_processor_count": props.multi_processor_count,
                    "compute_capability": f"{props.major}.{props.minor}"
                }
        elif HAS_TORCH:
            print("PyTorch CUDA: 利用不可")
        
        if not gpu_info:
            print("GPU情報が見つかりませんでした")
            return None
        
        return gpu_info
    
    def check_processes(self) -> Dict:
        """プロセス情報をチェック"""
        self.print_header("プロセス情報")
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                if pinfo['cpu_percent'] is not None and pinfo['cpu_percent'] > 0:
                    processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # CPU使用率でソート
        processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
        
        print("CPU使用率上位10プロセス:")
        print(f"{'PID':<8} {'名前':<30} {'CPU%':<8} {'メモリ%':<8}")
        print("-" * 60)
        for proc in processes[:10]:
            print(f"{proc['pid']:<8} {proc['name']:<30} {proc['cpu_percent'] or 0:<8.1f} {proc['memory_percent'] or 0:<8.1f}")
        
        # メモリ使用率でソート
        processes.sort(key=lambda x: x['memory_percent'] or 0, reverse=True)
        
        print("\nメモリ使用率上位10プロセス:")
        print(f"{'PID':<8} {'名前':<30} {'CPU%':<8} {'メモリ%':<8}")
        print("-" * 60)
        for proc in processes[:10]:
            print(f"{proc['pid']:<8} {proc['name']:<30} {proc['cpu_percent'] or 0:<8.1f} {proc['memory_percent'] or 0:<8.1f}")
        
        return {
            "total_processes": len(processes),
            "top_cpu": processes[:10] if processes else [],
            "top_memory": processes[:10] if processes else []
        }
    
    def generate_report(self) -> Dict:
        """レポートを生成"""
        self.print_header("性能チェックレポート生成")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "system_info": self.results.get("system_info", {}),
            "cpu": self.results.get("cpu", {}),
            "memory": self.results.get("memory", {}),
            "disk": self.results.get("disk", {}),
            "network": self.results.get("network", {}),
            "gpu": self.results.get("gpu"),
            "processes": self.results.get("processes", {}),
            "check_duration": time.time() - self.start_time
        }
        
        return report
    
    def save_report(self, report: Dict, filename: str = "performance_report.json"):
        """レポートをJSONファイルに保存"""
        filepath = f".cursor/{filename}"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\nレポートを保存しました: {filepath}")
    
    def run_all_checks(self, save_report: bool = True):
        """すべてのチェックを実行"""
        print("\n" + "=" * 70)
        print("  新PC（母艦）性能チェックツール")
        print("=" * 70)
        print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            self.results["system_info"] = self.check_system_info()
            self.results["cpu"] = self.check_cpu()
            self.results["memory"] = self.check_memory()
            self.results["disk"] = self.check_disk()
            self.results["network"] = self.check_network()
            self.results["gpu"] = self.check_gpu()
            self.results["processes"] = self.check_processes()
            
            report = self.generate_report()
            
            if save_report:
                self.save_report(report)
            
            elapsed_time = time.time() - self.start_time
            print("\n" + "=" * 70)
            print(f"性能チェック完了 (所要時間: {elapsed_time:.2f}秒)")
            print("=" * 70)
            
            return report
            
        except Exception as e:
            print(f"\nエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """メイン関数"""
    checker = PerformanceChecker()
    checker.run_all_checks()


if __name__ == "__main__":
    main()













































