#!/usr/bin/env python3
"""
Phase 9: システム全体の高速化システム
- メモリ使用量最適化
- レスポンス時間改善
- リアルタイム監視・調整
- 自動最適化実行
"""

import os
import sys
import time
import psutil
import json
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
import logging
import gc
import resource

class Phase9PerformanceOptimizer:
    def __init__(self):
        self.vault_dir = Path("/root/.mana_vault")
        self.tools_dir = Path("/root/trinity_workspace/tools")
        self.config_file = self.vault_dir / "phase9_performance_config.json"
        
        # ログ設定
        self.setup_logging()
        
        # 設定読み込み
        self.config = self.load_config()
        
        # パフォーマンス履歴
        self.performance_history = []
        self.optimization_running = False
        
        # 最適化ターゲット
        self.targets = {
            "memory_usage": 70.0,  # 70%以下
            "cpu_usage": 80.0,     # 80%以下
            "response_time": 1.0,  # 1秒以下
            "disk_io": 50.0,       # 50MB/s以下
            "network_latency": 100  # 100ms以下
        }

    def setup_logging(self):
        """ログ設定"""
        log_file = self.vault_dir / "phase9_performance.log"
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # コンソール出力も追加
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def load_config(self):
        """設定ファイル読み込み"""
        default_config = {
            "optimization": {
                "enabled": True,
                "interval_seconds": 30,
                "aggressive_mode": False,
                "memory_cleanup_threshold": 80.0,
                "cpu_optimization_threshold": 85.0
            },
            "monitoring": {
                "enabled": True,
                "metrics_retention_days": 7,
                "alert_thresholds": {
                    "memory": 90.0,
                    "cpu": 95.0,
                    "disk": 95.0
                }
            },
            "auto_optimization": {
                "enabled": True,
                "learning_enabled": True,
                "prediction_window_minutes": 60
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # デフォルト設定とマージ
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                self.logger.error(f"設定ファイル読み込みエラー: {e}")
                return default_config
        else:
            self.save_config(default_config)
            return default_config

    def save_config(self, config=None):
        """設定ファイル保存"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.logger.info("設定ファイルを保存しました")
        except Exception as e:
            self.logger.error(f"設定ファイル保存エラー: {e}")

    def get_system_metrics(self):
        """システムメトリクス取得"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available = memory.available / (1024**3)  # GB
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # ネットワークI/O
            network = psutil.net_io_counters()
            
            # プロセス数
            process_count = len(psutil.pids())
            
            # ロードアベレージ
            load_avg = os.getloadavg()  # type: ignore[attr-defined]
            
            # レスポンス時間測定
            response_time = self.measure_response_time()
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_available_gb": memory_available,
                "disk_percent": disk_percent,
                "process_count": process_count,
                "load_avg_1min": load_avg[0],
                "load_avg_5min": load_avg[1],
                "load_avg_15min": load_avg[2],
                "response_time_ms": response_time,
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"メトリクス取得エラー: {e}")
            return None

    def measure_response_time(self):
        """レスポンス時間測定"""
        try:
            start_time = time.time()
            
            # 簡単なシステムコールでレスポンス時間測定
            subprocess.run(['true'], capture_output=True, timeout=1)
            
            end_time = time.time()
            return (end_time - start_time) * 1000  # ミリ秒
            
        except Exception as e:
            self.logger.error(f"レスポンス時間測定エラー: {e}")
            return 999.0

    def optimize_memory(self):
        """メモリ最適化"""
        try:
            self.logger.info("メモリ最適化を開始")
            
            # ガベージコレクション実行
            collected = gc.collect()
            self.logger.info(f"ガベージコレクション: {collected}オブジェクト回収")
            
            # 不要なプロセス終了
            self.terminate_unnecessary_processes()
            
            # メモリキャッシュクリア
            self.clear_memory_caches()
            
            # システムメモリ最適化
            self.optimize_system_memory()
            
            self.logger.info("メモリ最適化完了")
            return True
            
        except Exception as e:
            self.logger.error(f"メモリ最適化エラー: {e}")
            return False

    def terminate_unnecessary_processes(self):
        """不要なプロセス終了"""
        try:
            unnecessary_patterns = [
                'zombie', 'defunct', 'orphaned'
            ]
            
            for proc in psutil.process_iter(['pid', 'name', 'status']):
                try:
                    if proc.info['status'] in ['zombie', 'defunct']:
                        self.logger.info(f"不要プロセス終了: PID {proc.info['pid']}")
                        proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
        except Exception as e:
            self.logger.error(f"不要プロセス終了エラー: {e}")

    def clear_memory_caches(self):
        """メモリキャッシュクリア"""
        try:
            # システムキャッシュクリア
            subprocess.run(['sync'], check=True)
            subprocess.run(['echo', '3'], stdout=open('/proc/sys/vm/drop_caches', 'w'), check=True)
            self.logger.info("システムキャッシュクリア完了")
            
        except Exception as e:
            self.logger.error(f"キャッシュクリアエラー: {e}")

    def optimize_system_memory(self):
        """システムメモリ最適化"""
        try:
            # メモリオーバーコミット設定
            with open('/proc/sys/vm/overcommit_memory', 'w') as f:
                f.write('1')
            
            # スワップ使用量最適化
            with open('/proc/sys/vm/swappiness', 'w') as f:
                f.write('10')
            
            self.logger.info("システムメモリ設定最適化完了")
            
        except Exception as e:
            self.logger.error(f"システムメモリ最適化エラー: {e}")

    def optimize_cpu(self):
        """CPU最適化"""
        try:
            self.logger.info("CPU最適化を開始")
            
            # CPU周波数最適化
            self.optimize_cpu_frequency()
            
            # プロセス優先度調整
            self.adjust_process_priorities()
            
            # CPU使用率制限
            self.limit_cpu_usage()
            
            self.logger.info("CPU最適化完了")
            return True
            
        except Exception as e:
            self.logger.error(f"CPU最適化エラー: {e}")
            return False

    def optimize_cpu_frequency(self):
        """CPU周波数最適化"""
        try:
            # CPU governor設定
            cpu_count = psutil.cpu_count()
            for i in range(cpu_count):  # type: ignore
                governor_file = f'/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_governor'
                if os.path.exists(governor_file):
                    with open(governor_file, 'w') as f:
                        f.write('ondemand')
            
            self.logger.info("CPU周波数最適化完了")
            
        except Exception as e:
            self.logger.error(f"CPU周波数最適化エラー: {e}")

    def adjust_process_priorities(self):
        """プロセス優先度調整"""
        try:
            # 重要でないプロセスの優先度を下げる
            for proc in psutil.process_iter(['pid', 'name', 'nice']):
                try:
                    if proc.info['name'] in ['chrome', 'firefox', 'thunderbird']:
                        proc.nice(19)  # 最低優先度
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
        except Exception as e:
            self.logger.error(f"プロセス優先度調整エラー: {e}")

    def limit_cpu_usage(self):
        """CPU使用率制限"""
        try:
            # cgroups設定（可能な場合）
            if os.path.exists('/sys/fs/cgroup'):
                # CPU使用率制限設定
                pass
                
        except Exception as e:
            self.logger.error(f"CPU使用率制限エラー: {e}")

    def optimize_network(self):
        """ネットワーク最適化"""
        try:
            self.logger.info("ネットワーク最適化を開始")
            
            # TCP設定最適化
            self.optimize_tcp_settings()
            
            # ネットワークバッファ最適化
            self.optimize_network_buffers()
            
            self.logger.info("ネットワーク最適化完了")
            return True
            
        except Exception as e:
            self.logger.error(f"ネットワーク最適化エラー: {e}")
            return False

    def optimize_tcp_settings(self):
        """TCP設定最適化"""
        try:
            tcp_settings = {
                '/proc/sys/net/core/rmem_max': '16777216',
                '/proc/sys/net/core/wmem_max': '16777216',
                '/proc/sys/net/ipv4/tcp_rmem': '4096 65536 16777216',
                '/proc/sys/net/ipv4/tcp_wmem': '4096 65536 16777216',
                '/proc/sys/net/ipv4/tcp_congestion_control': 'bbr'
            }
            
            for setting, value in tcp_settings.items():
                if os.path.exists(setting):
                    with open(setting, 'w') as f:
                        f.write(value)
            
            self.logger.info("TCP設定最適化完了")
            
        except Exception as e:
            self.logger.error(f"TCP設定最適化エラー: {e}")

    def optimize_network_buffers(self):
        """ネットワークバッファ最適化"""
        try:
            buffer_settings = {
                '/proc/sys/net/core/netdev_max_backlog': '5000',
                '/proc/sys/net/core/netdev_budget': '600',
                '/proc/sys/net/core/netdev_budget_usecs': '5000'
            }
            
            for setting, value in buffer_settings.items():
                if os.path.exists(setting):
                    with open(setting, 'w') as f:
                        f.write(value)
            
            self.logger.info("ネットワークバッファ最適化完了")
            
        except Exception as e:
            self.logger.error(f"ネットワークバッファ最適化エラー: {e}")

    def run_optimization_cycle(self):
        """最適化サイクル実行"""
        try:
            self.logger.info("=== Phase 9: パフォーマンス最適化サイクル開始 ===")
            
            # 現在のメトリクス取得
            metrics = self.get_system_metrics()
            if not metrics:
                return False
            
            # 履歴に追加
            self.performance_history.append(metrics)
            
            # 履歴保持（最新100件）
            if len(self.performance_history) > 100:
                self.performance_history = self.performance_history[-100:]
            
            # 最適化判定
            optimizations_needed = []
            
            if metrics['memory_percent'] > self.targets['memory_usage']:
                optimizations_needed.append('memory')
            
            if metrics['cpu_percent'] > self.targets['cpu_usage']:
                optimizations_needed.append('cpu')
            
            if metrics['response_time_ms'] > self.targets['response_time'] * 1000:
                optimizations_needed.append('response')
            
            # 最適化実行
            for optimization in optimizations_needed:
                if optimization == 'memory':
                    self.optimize_memory()
                elif optimization == 'cpu':
                    self.optimize_cpu()
                elif optimization == 'response':
                    self.optimize_network()
            
            # 結果レポート生成
            self.generate_performance_report(metrics, optimizations_needed)
            
            self.logger.info("=== Phase 9: パフォーマンス最適化サイクル完了 ===")
            return True
            
        except Exception as e:
            self.logger.error(f"最適化サイクルエラー: {e}")
            return False

    def generate_performance_report(self, metrics, optimizations):
        """パフォーマンスレポート生成"""
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics,
                "optimizations_applied": optimizations,
                "targets": self.targets,
                "performance_score": self.calculate_performance_score(metrics)
            }
            
            # レポート保存
            report_file = self.vault_dir / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"パフォーマンスレポート生成: {report_file}")
            return report
            
        except Exception as e:
            self.logger.error(f"レポート生成エラー: {e}")
            return None

    def calculate_performance_score(self, metrics):
        """パフォーマンススコア計算"""
        try:
            score = 100.0
            
            # メモリ使用率スコア
            if metrics['memory_percent'] > 90:
                score -= 30
            elif metrics['memory_percent'] > 80:
                score -= 20
            elif metrics['memory_percent'] > 70:
                score -= 10
            
            # CPU使用率スコア
            if metrics['cpu_percent'] > 95:
                score -= 25
            elif metrics['cpu_percent'] > 85:
                score -= 15
            elif metrics['cpu_percent'] > 75:
                score -= 5
            
            # レスポンス時間スコア
            if metrics['response_time_ms'] > 5000:
                score -= 20
            elif metrics['response_time_ms'] > 2000:
                score -= 10
            elif metrics['response_time_ms'] > 1000:
                score -= 5
            
            return max(0, min(100, score))
            
        except Exception as e:
            self.logger.error(f"スコア計算エラー: {e}")
            return 0

    def run_continuous_optimization(self):
        """継続最適化実行"""
        self.logger.info("Phase 9: 継続パフォーマンス最適化を開始")
        self.optimization_running = True
        
        try:
            while self.optimization_running:
                self.run_optimization_cycle()
                
                # 設定された間隔で待機
                interval = self.config['optimization']['interval_seconds']
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("最適化を停止します")
            self.optimization_running = False
        except Exception as e:
            self.logger.error(f"継続最適化エラー: {e}")
        finally:
            self.optimization_running = False

if __name__ == "__main__":
    optimizer = Phase9PerformanceOptimizer()
    
    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        optimizer.run_continuous_optimization()
    else:
        optimizer.run_optimization_cycle()
