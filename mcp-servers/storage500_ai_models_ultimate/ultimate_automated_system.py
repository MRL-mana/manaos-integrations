#!/usr/bin/env python3
"""
究極の全自動システム管理ツール
セキュリティ + システム統合 + ストレージ最適化 + Google Drive を統合
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

class UltimateAutomatedSystem:
    def __init__(self):
        self.logger = self._setup_logging()
        self.config = {
            'automation': {
                'security_check_interval_hours': 6,
                'system_monitoring_interval_minutes': 5,
                'storage_optimization_interval_hours': 12,
                'backup_interval_hours': 24,
                'cleanup_interval_hours': 12
            },
            'storage': {
                'local_storage_path': '/mnt/storage',
                'google_drive_path': '/mnt/google-drive',
                'disk_warning_threshold': 80,
                'disk_critical_threshold': 90
            },
            'services': {
                'docker_containers': ['sd-webui-cpu', 'n8n'],
                'python_services': [
                    'dashboard.py', 'api_dashboard.py', 'mrl_unified_dashboard.py',
                    'mcp_receive_claude_improved.py', 'mcp_receive_luna.py'
                ]
            },
            'notifications': {
                'slack_enabled': True,
                'discord_enabled': True,
                'email_enabled': False
            }
        }
        self.system_active = False
        self.stats = {
            'security_checks': 0,
            'system_restarts': 0,
            'storage_optimizations': 0,
            'backups_created': 0,
            'cleanups_performed': 0
        }
    
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ultimate_automated_system.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def check_system_health(self):
        """システム全体の健全性をチェック"""
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'disk_usage': self.get_disk_usage(),
            'memory_usage': psutil.virtual_memory().percent,
            'cpu_usage': psutil.cpu_percent(),
            'services_status': self.check_services_status(),
            'security_status': self.check_security_status(),
            'storage_status': self.check_storage_status(),
            'issues': [],
            'recommendations': []
        }
        
        # 問題を検出
        if health_report['disk_usage']['percent'] > self.config['storage']['disk_critical_threshold']:
            health_report['issues'].append("ディスク使用率が危険レベルです")
            health_report['recommendations'].append("緊急ストレージ最適化を実行してください")
        
        if health_report['memory_usage'] > 80:
            health_report['issues'].append("メモリ使用率が高いです")
            health_report['recommendations'].append("メモリ使用量の多いプロセスを確認してください")
        
        if health_report['cpu_usage'] > 80:
            health_report['issues'].append("CPU使用率が高いです")
            health_report['recommendations'].append("CPU負荷の高いプロセスを確認してください")
        
        return health_report
    
    def get_disk_usage(self):
        """ディスク使用率を取得"""
        disk_usage = psutil.disk_usage('/')
        return {
            'total': disk_usage.total,
            'used': disk_usage.used,
            'free': disk_usage.free,
            'percent': disk_usage.percent
        }
    
    def check_services_status(self):
        """サービス状況をチェック"""
        services_status = {}
        
        # Dockerコンテナ
        for container in self.config['services']['docker_containers']:
            try:
                result = subprocess.run(['docker', 'ps', '--filter', f'name={container}', '--format', '{{.Status}}'], capture_output=True, text=True)
                services_status[container] = 'running' if result.stdout.strip() else 'stopped'
            except Exception:
                services_status[container] = 'unknown'
        
        # Pythonサービス
        for service in self.config['services']['python_services']:
            found = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['cmdline'] and any(service in cmd for cmd in proc.info['cmdline']):
                        services_status[service] = 'running'
                        found = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not found:
                services_status[service] = 'stopped'
        
        return services_status
    
    def check_security_status(self):
        """セキュリティ状況をチェック"""
        security_status = {}
        
        # ファイアウォール
        try:
            result = subprocess.run(['ufw', 'status'], capture_output=True, text=True)
            security_status['firewall'] = 'active' if 'Status: active' in result.stdout else 'inactive'
        except Exception:
            security_status['firewall'] = 'unknown'
        
        # fail2ban
        try:
            result = subprocess.run(['fail2ban-client', 'status'], capture_output=True, text=True)
            security_status['fail2ban'] = 'active' if result.returncode == 0 else 'inactive'
        except Exception:
            security_status['fail2ban'] = 'unknown'
        
        return security_status
    
    def check_storage_status(self):
        """ストレージ状況をチェック"""
        storage_status = {}
        
        # ローカルストレージ
        if os.path.exists(self.config['storage']['local_storage_path']):
            disk_usage = psutil.disk_usage(self.config['storage']['local_storage_path'])
            storage_status['local_storage'] = {
                'available': True,
                'free_gb': disk_usage.free / (1024*1024*1024),
                'percent': disk_usage.percent
            }
        else:
            storage_status['local_storage'] = {'available': False}
        
        # Google Drive
        if os.path.exists(self.config['storage']['google_drive_path']):
            disk_usage = psutil.disk_usage(self.config['storage']['google_drive_path'])
            storage_status['google_drive'] = {
                'available': True,
                'free_gb': disk_usage.free / (1024*1024*1024),
                'percent': disk_usage.percent
            }
        else:
            storage_status['google_drive'] = {'available': False}
        
        return storage_status
    
    def auto_fix_issues(self):
        """問題を自動修正"""
        fixes_applied = []
        
        # ディスク容量問題の修正
        disk_usage = self.get_disk_usage()
        if disk_usage['percent'] > self.config['storage']['disk_warning_threshold']:
            fixes_applied.extend(self.emergency_storage_cleanup())
        
        # サービス停止の修正
        services_status = self.check_services_status()
        for service, status in services_status.items():
            if status == 'stopped':
                if self.restart_service(service):
                    fixes_applied.append(f"サービス {service} を再起動しました")
        
        return fixes_applied
    
    def emergency_storage_cleanup(self):
        """緊急ストレージクリーンアップ"""
        fixes = []
        
        try:
            # 大きなファイルを検索して移動
            large_files = []
            for root, dirs, files in os.walk('.'):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size > 100 * 1024 * 1024:  # 100MB以上
                            large_files.append((file_path, file_size))
                    except Exception:
                        pass
            
            # 大きなファイルを追加ストレージに移動
            for file_path, file_size in large_files[:5]:  # 最大5個まで
                try:
                    storage_path = os.path.join(self.config['storage']['local_storage_path'], 'moved_files', os.path.basename(file_path))
                    os.makedirs(os.path.dirname(storage_path), exist_ok=True)
                    import shutil
                    shutil.move(file_path, storage_path)
                    fixes.append(f"大きなファイルを移動: {os.path.basename(file_path)} ({file_size / (1024*1024):.1f} MB)")
                except Exception as e:
                    self.logger.error(f"ファイル移動エラー {file_path}: {e}")
            
            # Dockerクリーンアップ
            try:
                subprocess.run(['docker', 'system', 'prune', '-f'], capture_output=True)
                fixes.append("Dockerクリーンアップを実行")
            except Exception as e:
                self.logger.error(f"Dockerクリーンアップエラー: {e}")
            
        except Exception as e:
            self.logger.error(f"緊急ストレージクリーンアップエラー: {e}")
        
        return fixes
    
    def restart_service(self, service_name):
        """サービスを再起動"""
        try:
            if service_name in self.config['services']['docker_containers']:
                result = subprocess.run(['docker', 'restart', service_name], capture_output=True, text=True)
                return result.returncode == 0
            elif service_name in self.config['services']['python_services']:
                # Pythonサービスを再起動
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if proc.info['cmdline'] and any(service_name in cmd for cmd in proc.info['cmdline']):
                            proc.terminate()
                            proc.wait(timeout=10)
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                        continue
                
                # サービスを再起動
                if service_name == 'dashboard.py':
                    subprocess.Popen(['streamlit', 'run', 'dashboard.py', '--server.port', '8503', '--server.address', '0.0.0.0', '--server.headless', 'true'])
                elif service_name == 'api_dashboard.py':
                    subprocess.Popen(['streamlit', 'run', 'api_dashboard.py', '--server.port', '8504', '--server.address', '0.0.0.0', '--server.headless', 'true'])
                elif service_name == 'mrl_unified_dashboard.py':
                    subprocess.Popen(['streamlit', 'run', 'mrl_unified_dashboard.py', '--server.port', '8506', '--server.address', '0.0.0.0', '--server.headless', 'true'])
                
                return True
            else:
                return False
        except Exception as e:
            self.logger.error(f"サービス再起動エラー {service_name}: {e}")
            return False
    
    def perform_security_check(self):
        """セキュリティチェックを実行"""
        try:
            if os.path.exists('security_enhancement_tool.py'):
                result = subprocess.run(['python3', 'security_enhancement_tool.py'], capture_output=True, text=True)
                if result.returncode == 0:
                    self.stats['security_checks'] += 1
                    self.logger.info("セキュリティチェック完了")
                    return True
            return False
        except Exception as e:
            self.logger.error(f"セキュリティチェックエラー: {e}")
            return False
    
    def perform_system_monitoring(self):
        """システム監視を実行"""
        try:
            health_report = self.check_system_health()
            fixes = self.auto_fix_issues()
            
            if fixes:
                self.stats['system_restarts'] += len([f for f in fixes if '再起動' in f])
                self.logger.info(f"自動修正を適用: {fixes}")
            
            # レポートを保存
            with open('system_health_report.json', 'w') as f:
                json.dump(health_report, f, indent=2, ensure_ascii=False)
            
            return health_report
        except Exception as e:
            self.logger.error(f"システム監視エラー: {e}")
            return None
    
    def perform_storage_optimization(self):
        """ストレージ最適化を実行"""
        try:
            if os.path.exists('comprehensive_storage_optimizer.py'):
                result = subprocess.run(['python3', 'comprehensive_storage_optimizer.py'], capture_output=True, text=True)
                if result.returncode == 0:
                    self.stats['storage_optimizations'] += 1
                    self.logger.info("ストレージ最適化完了")
                    return True
            return False
        except Exception as e:
            self.logger.error(f"ストレージ最適化エラー: {e}")
            return False
    
    def perform_backup(self):
        """バックアップを実行"""
        try:
            backup_name = f"system_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = os.path.join(self.config['storage']['local_storage_path'], 'backups', backup_name)
            
            os.makedirs(backup_path, exist_ok=True)
            
            # 重要なファイルをバックアップ
            important_files = ['*.py', '*.json', '*.md', '*.sh', '*.conf']
            
            for pattern in important_files:
                import glob
                for file_path in glob.glob(pattern):
                    try:
                        rel_path = os.path.relpath(file_path, '.')
                        dest_path = os.path.join(backup_path, rel_path)
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        import shutil
                        shutil.copy2(file_path, dest_path)
                    except Exception as e:
                        self.logger.error(f"バックアップエラー {file_path}: {e}")
            
            self.stats['backups_created'] += 1
            self.logger.info(f"バックアップ作成完了: {backup_name}")
            return True
        except Exception as e:
            self.logger.error(f"バックアップエラー: {e}")
            return False
    
    def perform_cleanup(self):
        """クリーンアップを実行"""
        try:
            cleaned_items = []
            
            # 古いログファイルを削除
            for file in os.listdir('.'):
                if file.endswith('.log') and os.path.getmtime(file) < (datetime.now() - timedelta(days=7)).timestamp():
                    try:
                        os.remove(file)
                        cleaned_items.append(f"古いログファイル: {file}")
                    except Exception:
                        pass
            
            # 一時ファイルを削除
            temp_patterns = ['*.tmp', '*.temp', '*.cache']
            for pattern in temp_patterns:
                import glob
                for temp_file in glob.glob(pattern):
                    try:
                        os.remove(temp_file)
                        cleaned_items.append(f"一時ファイル: {temp_file}")
                    except Exception:
                        pass
            
            self.stats['cleanups_performed'] += 1
            self.logger.info(f"クリーンアップ完了: {len(cleaned_items)} アイテム削除")
            return True
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")
            return False
    
    def send_notification(self, message):
        """通知を送信"""
        try:
            # Slack通知
            if self.config['notifications']['slack_enabled']:
                self.send_slack_notification(message)
            
            # Discord通知
            if self.config['notifications']['discord_enabled']:
                self.send_discord_notification(message)
        
        except Exception as e:
            self.logger.error(f"通知送信エラー: {e}")
    
    def send_slack_notification(self, message):
        """Slack通知を送信"""
        try:
            if os.path.exists('slack_config.json'):
                with open('slack_config.json', 'r') as f:
                    slack_config = json.load(f)
                
                webhook_url = slack_config.get('webhook_url')
                if webhook_url:
                    payload = {
                        'text': f"🤖 全自動システム通知: {message}",
                        'username': 'Ultimate Automated System'
                    }
                    response = requests.post(webhook_url, json=payload)
                    if response.status_code == 200:
                        self.logger.info("Slack通知を送信しました")
        except Exception as e:
            self.logger.error(f"Slack通知エラー: {e}")
    
    def send_discord_notification(self, message):
        """Discord通知を送信"""
        try:
            if os.path.exists('discord_config.json'):
                with open('discord_config.json', 'r') as f:
                    discord_config = json.load(f)
                
                webhook_url = discord_config.get('webhook_url')
                if webhook_url:
                    payload = {
                        'content': f"🤖 全自動システム通知: {message}",
                        'username': 'Ultimate Automated System'
                    }
                    response = requests.post(webhook_url, json=payload)
                    if response.status_code == 204:
                        self.logger.info("Discord通知を送信しました")
        except Exception as e:
            self.logger.error(f"Discord通知エラー: {e}")
    
    def setup_automated_schedule(self):
        """自動化スケジュールを設定"""
        try:
            # セキュリティチェック
            schedule.every(self.config['automation']['security_check_interval_hours']).hours.do(self.perform_security_check)
            
            # システム監視
            schedule.every(self.config['automation']['system_monitoring_interval_minutes']).minutes.do(self.perform_system_monitoring)
            
            # ストレージ最適化
            schedule.every(self.config['automation']['storage_optimization_interval_hours']).hours.do(self.perform_storage_optimization)
            
            # バックアップ
            schedule.every(self.config['automation']['backup_interval_hours']).hours.do(self.perform_backup)
            
            # クリーンアップ
            schedule.every(self.config['automation']['cleanup_interval_hours']).hours.do(self.perform_cleanup)
            
            self.logger.info("自動化スケジュールを設定しました")
            return True
        except Exception as e:
            self.logger.error(f"自動化スケジュール設定エラー: {e}")
            return False
    
    def start_ultimate_system(self):
        """究極の全自動システムを開始"""
        self.logger.info("究極の全自動システムを開始します...")
        
        # 自動化スケジュールを設定
        if not self.setup_automated_schedule():
            self.logger.error("自動化スケジュールの設定に失敗しました")
            return False
        
        # 初回実行
        self.perform_security_check()
        self.perform_system_monitoring()
        self.perform_storage_optimization()
        self.perform_backup()
        self.perform_cleanup()
        
        # スケジュールループを開始
        def schedule_loop():
            while self.system_active:
                try:
                    schedule.run_pending()
                    time.sleep(60)  # 1分ごとにチェック
                except Exception as e:
                    self.logger.error(f"スケジュールループエラー: {e}")
                    time.sleep(60)
        
        # スケジュールスレッドを開始
        schedule_thread = threading.Thread(target=schedule_loop, daemon=True)
        schedule_thread.start()
        
        self.system_active = True
        self.logger.info("究極の全自動システムが開始されました")
        
        # 開始通知を送信
        self.send_notification("究極の全自動システムが開始されました 🚀")
        
        return True
    
    def stop_ultimate_system(self):
        """究極の全自動システムを停止"""
        self.logger.info("究極の全自動システムを停止します...")
        self.system_active = False
        schedule.clear()
        self.logger.info("究極の全自動システムが停止されました")
        self.send_notification("究極の全自動システムが停止されました ⏹️")
    
    def get_system_stats(self):
        """システム統計を取得"""
        return {
            'system_active': self.system_active,
            'stats': self.stats,
            'next_security_check': schedule.next_run(),
            'next_backup': schedule.next_run(),
            'system_health': self.check_system_health()
        }

def main():
    ultimate_system = UltimateAutomatedSystem()
    
    print("=== 究極の全自動システム管理ツール ===")
    print("1. 究極の全自動システムを開始")
    print("2. システム状況を確認")
    print("3. 手動セキュリティチェック")
    print("4. 手動ストレージ最適化")
    print("5. 手動バックアップ")
    print("6. 究極の全自動システムを停止")
    print("7. 終了")
    
    while True:
        try:
            choice = input("\n選択してください (1-7): ").strip()
            
            if choice == '1':
                if ultimate_system.start_ultimate_system():
                    print("✅ 究極の全自動システムが開始されました")
                else:
                    print("❌ 究極の全自動システムの開始に失敗しました")
            
            elif choice == '2':
                stats = ultimate_system.get_system_stats()
                print(f"\n=== システム状況 ===")
                print(f"システム状態: {'✅ アクティブ' if stats['system_active'] else '❌ 停止'}")
                print(f"セキュリティチェック回数: {stats['stats']['security_checks']}")
                print(f"システム再起動回数: {stats['stats']['system_restarts']}")
                print(f"ストレージ最適化回数: {stats['stats']['storage_optimizations']}")
                print(f"バックアップ作成回数: {stats['stats']['backups_created']}")
                print(f"クリーンアップ実行回数: {stats['stats']['cleanups_performed']}")
                
                health = stats['system_health']
                print(f"ディスク使用率: {health['disk_usage']['percent']:.1f}%")
                print(f"メモリ使用率: {health['memory_usage']:.1f}%")
                print(f"CPU使用率: {health['cpu_usage']:.1f}%")
            
            elif choice == '3':
                if ultimate_system.perform_security_check():
                    print("✅ セキュリティチェックを実行しました")
                else:
                    print("❌ セキュリティチェックに失敗しました")
            
            elif choice == '4':
                if ultimate_system.perform_storage_optimization():
                    print("✅ ストレージ最適化を実行しました")
                else:
                    print("❌ ストレージ最適化に失敗しました")
            
            elif choice == '5':
                if ultimate_system.perform_backup():
                    print("✅ バックアップを実行しました")
                else:
                    print("❌ バックアップに失敗しました")
            
            elif choice == '6':
                ultimate_system.stop_ultimate_system()
                print("✅ 究極の全自動システムを停止しました")
            
            elif choice == '7':
                print("終了します...")
                break
            
            else:
                print("無効な選択です。1-7を選択してください。")
        
        except KeyboardInterrupt:
            print("\n終了します...")
            break
        except Exception as e:
            print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main() 