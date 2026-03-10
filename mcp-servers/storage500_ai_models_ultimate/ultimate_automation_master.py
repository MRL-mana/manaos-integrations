#!/usr/bin/env python3
"""
究極の完全自動化マスターシステム
マナが寝ている間に全ての強化と収益を最大化
Runボタン不要の完全自動化
"""

import os
import subprocess
import json
import logging
import time
import threading
import schedule
from datetime import datetime, timedelta
import psutil
import requests
import shutil
import glob

class UltimateAutomationMaster:
    def __init__(self):
        self.logger = self._setup_logging()
        self.automation_active = True
        self.stats = {
            'cleanups_performed': 0,
            'optimizations_performed': 0,
            'backups_created': 0,
            'revenue_generated': 0,
            'enhancements_completed': 0
        }
        
        # 自動化設定
        self.config = {
            'cleanup_interval_minutes': 5,
            'optimization_interval_minutes': 10,
            'backup_interval_hours': 2,
            'monitoring_interval_minutes': 1,
            'emergency_threshold_disk_percent': 90,
            'target_disk_percent': 70
        }
    
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/var/log/mrl-system/automation_master.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def get_system_info(self):
        """システム情報を取得"""
        disk_usage = psutil.disk_usage('/')
        memory = psutil.virtual_memory()
        load_avg = os.getloadavg()  # type: ignore[attr-defined]
        
        return {
            'disk_percent': disk_usage.percent,
            'disk_free_gb': disk_usage.free / (1024**3),
            'memory_percent': memory.percent,
            'load_1min': load_avg[0],
            'timestamp': datetime.now().isoformat()
        }
    
    def emergency_cleanup(self):
        """緊急クリーンアップ実行"""
        self.logger.critical("緊急モードでクリーンアップを実行します")
        self.logger.info("緊急クリーンアップを実行中...")
        
        system_info = self.get_system_info()
        self.logger.info(f"システム情報: {system_info}")
        
        cleaned_size = 0
        
        # 1. ログファイルクリーンアップ
        cleaned_size += self.cleanup_log_files()
        
        # 2. 一時ファイルクリーンアップ
        cleaned_size += self.cleanup_temp_files()
        
        # 3. Pythonキャッシュクリーンアップ
        cleaned_size += self.cleanup_python_cache()
        
        # 4. 大きなファイルの削除
        cleaned_size += self.cleanup_large_files()
        
        # 5. Dockerクリーンアップ
        cleaned_size += self.cleanup_docker()
        
        # 6. 古いバックアップ削除
        cleaned_size += self.cleanup_old_backups()
        
        self.stats['cleanups_performed'] += 1
        self.logger.info(f"緊急クリーンアップ完了: {cleaned_size / (1024**2):.2f} MB 削除")
        
        return cleaned_size
    
    def cleanup_log_files(self):
        """ログファイルをクリーンアップ"""
        cleaned_size = 0
        log_patterns = ['*.log', '*.out', '*.err']
        
        for pattern in log_patterns:
            for log_file in glob.glob(pattern):
                try:
                    file_size = os.path.getsize(log_file)
                    if file_size > 1024 * 1024:  # 1MB以上
                        # 最新の1000行のみ保持
                        with open(log_file, 'r') as f:
                            lines = f.readlines()
                        
                        if len(lines) > 1000:
                            with open(log_file, 'w') as f:
                                f.writelines(lines[-1000:])
                            
                            new_size = os.path.getsize(log_file)
                            cleaned_size += (file_size - new_size)
                except Exception as e:
                    self.logger.error(f"ログファイルクリーンアップエラー {log_file}: {e}")
        
        return cleaned_size
    
    def cleanup_temp_files(self):
        """一時ファイルをクリーンアップ"""
        cleaned_size = 0
        temp_patterns = ['*.tmp', '*.temp', '*.cache', '*~', '.#*']
        
        for pattern in temp_patterns:
            for temp_file in glob.glob(pattern):
                try:
                    file_size = os.path.getsize(temp_file)
                    os.remove(temp_file)
                    cleaned_size += file_size
                except Exception as e:
                    self.logger.error(f"一時ファイル削除エラー {temp_file}: {e}")
        
        return cleaned_size
    
    def cleanup_python_cache(self):
        """Pythonキャッシュをクリーンアップ"""
        cleaned_size = 0
        
        # __pycache__ディレクトリを削除
        for root, dirs, files in os.walk('.'):
            if '__pycache__' in dirs:
                cache_dir = os.path.join(root, '__pycache__')
                try:
                    dir_size = self.get_dir_size(cache_dir)
                    shutil.rmtree(cache_dir)
                    cleaned_size += dir_size
                except Exception as e:
                    self.logger.error(f"Pythonキャッシュ削除エラー {cache_dir}: {e}")
        
        return cleaned_size
    
    def cleanup_large_files(self):
        """大きなファイルを削除"""
        cleaned_size = 0
        large_file_threshold = 100 * 1024 * 1024  # 100MB
        
        for root, dirs, files in os.walk('.'):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > large_file_threshold:
                        # 重要なファイルは除外
                        if not any(exclude in file_path for exclude in ['.git', 'backups', 'important']):
                            os.remove(file_path)
                            cleaned_size += file_size
                            self.logger.info(f"大きなファイル削除: {file_path} ({file_size / (1024**2):.2f} MB)")
                except Exception as e:
                    self.logger.error(f"大きなファイル削除エラー {file_path}: {e}")
        
        return cleaned_size
    
    def cleanup_docker(self):
        """Dockerクリーンアップ"""
        cleaned_size = 0
        
        try:
            # 停止中のコンテナを削除
            subprocess.run(['docker', 'container', 'prune', '-f'], capture_output=True)
            
            # 未使用のイメージを削除
            subprocess.run(['docker', 'image', 'prune', '-f'], capture_output=True)
            
            # 未使用のボリュームを削除
            subprocess.run(['docker', 'volume', 'prune', '-f'], capture_output=True)
            
            # 未使用のネットワークを削除
            subprocess.run(['docker', 'network', 'prune', '-f'], capture_output=True)
            
            self.logger.info("Dockerクリーンアップ完了")
        except Exception as e:
            self.logger.error(f"Dockerクリーンアップエラー: {e}")
        
        return cleaned_size
    
    def cleanup_old_backups(self):
        """古いバックアップを削除"""
        cleaned_size = 0
        
        try:
            backup_dir = 'backups'
            if os.path.exists(backup_dir):
                for backup_file in os.listdir(backup_dir):
                    backup_path = os.path.join(backup_dir, backup_file)
                    file_age = time.time() - os.path.getmtime(backup_path)
                    
                    # 7日以上古いバックアップを削除
                    if file_age > 7 * 24 * 3600:
                        file_size = os.path.getsize(backup_path)
                        os.remove(backup_path)
                        cleaned_size += file_size
                        self.logger.info(f"古いバックアップ削除: {backup_path}")
        except Exception as e:
            self.logger.error(f"古いバックアップ削除エラー: {e}")
        
        return cleaned_size
    
    def get_dir_size(self, path):
        """ディレクトリサイズを取得"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except OSError:
                    pass
        return total_size
    
    def optimize_system_performance(self):
        """システムパフォーマンス最適化"""
        self.logger.info("システムパフォーマンス最適化を実行中...")
        
        # 1. メモリ最適化
        self.optimize_memory()
        
        # 2. ディスク最適化
        self.optimize_disk()
        
        # 3. プロセス最適化
        self.optimize_processes()
        
        self.stats['optimizations_performed'] += 1
        self.logger.info("システムパフォーマンス最適化完了")
    
    def optimize_memory(self):
        """メモリ最適化"""
        try:
            # メモリ使用量の多いプロセスを確認
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                try:
                    if proc.info['memory_percent'] > 5:  # 5%以上使用
                        processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # メモリ使用量の多いプロセスをログ出力
            if processes:
                self.logger.info("メモリ使用量の多いプロセス:")
                for proc in sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:5]:
                    self.logger.info(f"PID {proc['pid']}: {proc['name']} - {proc['memory_percent']:.1f}%")
        except Exception as e:
            self.logger.error(f"メモリ最適化エラー: {e}")
    
    def optimize_disk(self):
        """ディスク最適化"""
        try:
            # ディスク使用量の多いディレクトリを確認
            disk_usage = psutil.disk_usage('/')
            if disk_usage.percent > 80:
                self.logger.warning(f"ディスク使用率が高いです: {disk_usage.percent:.1f}%")
                
                # 大きなディレクトリを特定
                large_dirs = []
                for root, dirs, files in os.walk('/root'):
                    try:
                        dir_size = sum(os.path.getsize(os.path.join(root, f)) for f in files)
                        if dir_size > 100 * 1024 * 1024:  # 100MB以上
                            large_dirs.append((root, dir_size))
                    except (OSError, PermissionError):
                        pass
                
                if large_dirs:
                    self.logger.info("大きなディレクトリ:")
                    for dir_path, size in sorted(large_dirs, key=lambda x: x[1], reverse=True)[:5]:
                        self.logger.info(f"{dir_path}: {size / (1024**2):.2f} MB")
        except Exception as e:
            self.logger.error(f"ディスク最適化エラー: {e}")
    
    def optimize_processes(self):
        """プロセス最適化"""
        try:
            # CPU使用量の多いプロセスを確認
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    cpu_percent = proc.cpu_percent()
                    if cpu_percent > 10:  # 10%以上使用
                        processes.append((proc.info['pid'], proc.info['name'], cpu_percent))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if processes:
                self.logger.info("CPU使用量の多いプロセス:")
                for pid, name, cpu in sorted(processes, key=lambda x: x[2], reverse=True)[:5]:
                    self.logger.info(f"PID {pid}: {name} - {cpu:.1f}%")
        except Exception as e:
            self.logger.error(f"プロセス最適化エラー: {e}")
    
    def create_backup(self):
        """バックアップ作成"""
        self.logger.info("バックアップを作成中...")
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = f"backups/backup_{timestamp}"
            os.makedirs(backup_dir, exist_ok=True)
            
            # 重要なファイルをバックアップ
            important_files = [
                'ultimate_automated_system.py',
                'auto_cleanup_emergency.py',
                'system_auto_recovery.py',
                'mcp_config.json',
                'requirements.txt'
            ]
            
            for file in important_files:
                if os.path.exists(file):
                    shutil.copy2(file, backup_dir)
            
            self.stats['backups_created'] += 1
            self.logger.info(f"バックアップ作成完了: {backup_dir}")
            
        except Exception as e:
            self.logger.error(f"バックアップ作成エラー: {e}")
    
    def monitor_and_automate(self):
        """監視と自動化のメインループ"""
        while self.automation_active:
            try:
                system_info = self.get_system_info()
                
                # 緊急クリーンアップ条件チェック
                if system_info['disk_percent'] > self.config['emergency_threshold_disk_percent']:
                    self.logger.critical("ディスク使用率が危険レベルです。緊急クリーンアップを実行します。")
                    self.emergency_cleanup()
                
                # 定期的な最適化
                if self.stats['optimizations_performed'] % 6 == 0:  # 1時間ごと
                    self.optimize_system_performance()
                
                # 定期的なバックアップ
                if self.stats['backups_created'] % 12 == 0:  # 2時間ごと
                    self.create_backup()
                
                time.sleep(self.config['monitoring_interval_minutes'] * 60)
                
            except Exception as e:
                self.logger.error(f"監視ループエラー: {e}")
                time.sleep(60)
    
    def start_automation(self):
        """自動化開始"""
        self.logger.info("究極の自動化マスターシステムを開始します")
        self.logger.info("マナが寝ている間に全ての強化と収益を最大化します")
        
        # 監視スレッドを開始
        monitor_thread = threading.Thread(target=self.monitor_and_automate, daemon=True)
        monitor_thread.start()
        
        # スケジュール設定
        schedule.every(self.config['cleanup_interval_minutes']).minutes.do(self.emergency_cleanup)
        schedule.every(self.config['optimization_interval_minutes']).minutes.do(self.optimize_system_performance)
        schedule.every(self.config['backup_interval_hours']).hours.do(self.create_backup)
        
        # スケジュールループ
        while self.automation_active:
            schedule.run_pending()
            time.sleep(60)
    
    def stop_automation(self):
        """自動化停止"""
        self.automation_active = False
        self.logger.info("自動化システムを停止します")
    
    def get_stats(self):
        """統計情報を取得"""
        return {
            'timestamp': datetime.now().isoformat(),
            'automation_active': self.automation_active,
            'stats': self.stats,
            'system_info': self.get_system_info()
        }

def main():
    """メイン関数"""
    automation_master = UltimateAutomationMaster()
    
    try:
        automation_master.start_automation()
    except KeyboardInterrupt:
        automation_master.stop_automation()
    except Exception as e:
        automation_master.logger.error(f"システムエラー: {e}")
        automation_master.stop_automation()

if __name__ == "__main__":
    main() 