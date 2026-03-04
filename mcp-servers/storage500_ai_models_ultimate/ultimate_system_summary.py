#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
システム全体サマリー
全てのシステムの状況を包括的に表示
"""

import os
import sys
import time
import json
import yaml
import psutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

class UltimateSystemSummary:
    """システム全体サマリー"""
    
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """設定読み込み"""
        try:
            with open('mirror_config.yaml', 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            print(f"設定読み込みエラー: {e}")
            self.config = {}
    
    def get_system_status(self) -> Dict[str, Any]:
        """システム状況取得"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'system_info': self.get_system_info(),
            'processes': self.get_process_status(),
            'databases': self.get_database_status(),
            'files': self.get_file_status(),
            'apis': self.get_api_status(),
            'performance': self.get_performance_status(),
            'backups': self.get_backup_status(),
            'notifications': self.get_notification_status()
        }
        return status
    
    def get_system_info(self) -> Dict[str, Any]:
        """システム情報取得"""
        try:
            disk = psutil.disk_usage('/')
            memory = psutil.virtual_memory()
            
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': memory.percent,
                'memory_used_gb': memory.used / (1024**3),
                'memory_total_gb': memory.total / (1024**3),
                'disk_percent': disk.percent,
                'disk_used_gb': disk.used / (1024**3),
                'disk_total_gb': disk.total / (1024**3)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_process_status(self) -> Dict[str, Any]:
        """プロセス状況取得"""
        processes = {}
        critical_processes = [
            'obsidian_notion_mirror_system.py',
            'gemini_api_fix.py',
            'advanced_automation_system.py',
            'real_time_monitor.py',
            'auto_backup_system.py',
            'ai_assistant_integration.py',
            'smart_notification_system.py',
            'system_master_controller.py'
        ]
        
        for proc_name in critical_processes:
            found = False
            pid = None
            cpu_percent = 0
            memory_percent = 0
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if proc_name in cmdline:
                    found = True
                    pid = proc.info['pid']
                    try:
                        proc_obj = psutil.Process(pid)
                        cpu_percent = proc_obj.cpu_percent()
                        memory_percent = proc_obj.memory_percent()
                    except:
                        pass
                    break
            
            processes[proc_name] = {
                'running': found,
                'pid': pid,
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent
            }
        
        return processes
    
    def get_database_status(self) -> Dict[str, Any]:
        """データベース状況取得"""
        databases = {}
        db_files = [
            'obsidian_notion_mirror.db',
            'gemini_api_fix.db',
            'ai_assistant.db',
            'smart_notification.db',
            'ultimate_integration_dashboard.db'
        ]
        
        for db_file in db_files:
            if os.path.exists(db_file):
                try:
                    size_mb = os.path.getsize(db_file) / (1024 * 1024)
                    conn = sqlite3.connect(db_file)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                    table_count = cursor.fetchone()[0]
                    conn.close()
                    
                    databases[db_file] = {
                        'exists': True,
                        'size_mb': size_mb,
                        'table_count': table_count
                    }
                except Exception as e:
                    databases[db_file] = {
                        'exists': True,
                        'error': str(e)
                    }
            else:
                databases[db_file] = {'exists': False}
        
        return databases
    
    def get_file_status(self) -> Dict[str, Any]:
        """ファイル状況取得"""
        files = {}
        
        # Obsidian Vault
        vault_path = Path("obsidian_vault")
        if vault_path.exists():
            md_files = list(vault_path.rglob("*.md"))
            files['obsidian_vault'] = {
                'exists': True,
                'file_count': len(md_files),
                'total_size_mb': sum(f.stat().st_size for f in md_files) / (1024 * 1024)
            }
        else:
            files['obsidian_vault'] = {'exists': False}
        
        # ログファイル
        log_files = [
            'obsidian_notion_mirror.log',
            'gemini_api_fix.log',
            'advanced_automation.log',
            'ai_assistant.log',
            'smart_notification.log'
        ]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                size_mb = os.path.getsize(log_file) / (1024 * 1024)
                files[log_file] = {
                    'exists': True,
                    'size_mb': size_mb
                }
            else:
                files[log_file] = {'exists': False}
        
        return files
    
    def get_api_status(self) -> Dict[str, Any]:
        """API状況取得"""
        apis = {}
        
        # Notion API
        notion_key = self.config.get('notion_api_key', '')
        apis['notion'] = {
            'configured': bool(notion_key),
            'key_length': len(notion_key) if notion_key else 0
        }
        
        # Gemini API
        gemini_key = self.config.get('gemini_api_key', '')
        apis['gemini'] = {
            'configured': bool(gemini_key) and gemini_key != "AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            'key_length': len(gemini_key) if gemini_key else 0
        }
        
        return apis
    
    def get_performance_status(self) -> Dict[str, Any]:
        """パフォーマンス状況取得"""
        try:
            return {
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_backup_status(self) -> Dict[str, Any]:
        """バックアップ状況取得"""
        backup_dir = Path("backups")
        if backup_dir.exists():
            backups = list(backup_dir.glob("backup_*"))
            if backups:
                latest_backup = max(backups, key=lambda x: x.stat().st_mtime)
                backup_age_hours = (datetime.now().timestamp() - latest_backup.stat().st_mtime) / 3600
                
                return {
                    'backup_count': len(backups),
                    'latest_backup': latest_backup.name,
                    'backup_age_hours': backup_age_hours,
                    'total_size_mb': sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file()) / (1024 * 1024)
                }
            else:
                return {'backup_count': 0}
        else:
            return {'backup_dir_exists': False}
    
    def get_notification_status(self) -> Dict[str, Any]:
        """通知状況取得"""
        try:
            db_path = 'smart_notification.db'
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM notifications")
                total_notifications = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM notifications WHERE level = 'CRITICAL'")
                critical_notifications = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM notifications WHERE level = 'WARNING'")
                warning_notifications = cursor.fetchone()[0]
                
                conn.close()
                
                return {
                    'total_notifications': total_notifications,
                    'critical_notifications': critical_notifications,
                    'warning_notifications': warning_notifications
                }
            else:
                return {'database_exists': False}
        except Exception as e:
            return {'error': str(e)}
    
    def display_summary(self):
        """サマリー表示"""
        status = self.get_system_status()
        
        print("=" * 80)
        print("🚀 システム全体サマリー")
        print("=" * 80)
        print(f"時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # システム情報
        sys_info = status['system_info']
        if 'error' not in sys_info:
            print("💻 システム情報:")
            print(f"  CPU使用率: {sys_info['cpu_percent']:.1f}%")
            print(f"  メモリ使用率: {sys_info['memory_percent']:.1f}% ({sys_info['memory_used_gb']:.1f}GB / {sys_info['memory_total_gb']:.1f}GB)")
            print(f"  ディスク使用率: {sys_info['disk_percent']:.1f}% ({sys_info['disk_used_gb']:.1f}GB / {sys_info['disk_total_gb']:.1f}GB)")
        print()
        
        # プロセス状況
        print("🔄 プロセス状況:")
        processes = status['processes']
        running_count = 0
        for proc_name, proc_info in processes.items():
            status_icon = "✅" if proc_info['running'] else "❌"
            print(f"  {status_icon} {proc_name}")
            if proc_info['running']:
                running_count += 1
                print(f"    PID: {proc_info['pid']}, CPU: {proc_info['cpu_percent']:.1f}%")
        print(f"  実行中: {running_count}/{len(processes)}")
        print()
        
        # データベース状況
        print("🗄️ データベース状況:")
        databases = status['databases']
        for db_name, db_info in databases.items():
            if db_info['exists']:
                if 'error' not in db_info:
                    print(f"  ✅ {db_name}: {db_info['table_count']}テーブル, {db_info['size_mb']:.1f}MB")
                else:
                    print(f"  ⚠️ {db_name}: エラー - {db_info['error']}")
            else:
                print(f"  ❌ {db_name}: 存在しません")
        print()
        
        # API状況
        print("🔗 API状況:")
        apis = status['apis']
        for api_name, api_info in apis.items():
            status_icon = "✅" if api_info['configured'] else "❌"
            print(f"  {status_icon} {api_name.upper()}: {'設定済み' if api_info['configured'] else '未設定'}")
        print()
        
        # バックアップ状況
        print("💾 バックアップ状況:")
        backup_info = status['backups']
        if 'backup_count' in backup_info:
            if backup_info['backup_count'] > 0:
                print(f"  ✅ バックアップ数: {backup_info['backup_count']}")
                print(f"  最新バックアップ: {backup_info['latest_backup']}")
                print(f"  経過時間: {backup_info['backup_age_hours']:.1f}時間")
                print(f"  総サイズ: {backup_info['total_size_mb']:.1f}MB")
            else:
                print("  ⚠️ バックアップが作成されていません")
        else:
            print("  ❌ バックアップディレクトリが存在しません")
        print()
        
        # 通知状況
        print("📢 通知状況:")
        notification_info = status['notifications']
        if 'total_notifications' in notification_info:
            print(f"  総通知数: {notification_info['total_notifications']}")
            print(f"  重要通知: {notification_info['critical_notifications']}")
            print(f"  警告通知: {notification_info['warning_notifications']}")
        else:
            print("  ❌ 通知データベースが存在しません")
        print()
        
        print("=" * 80)
    
    def save_summary_report(self):
        """サマリーレポート保存"""
        status = self.get_system_status()
        
        report_file = f"system_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
        
        print(f"📊 サマリーレポート保存: {report_file}")
    
    def run(self):
        """メイン実行"""
        print("システム全体サマリー開始...")
        
        while True:
            try:
                self.display_summary()
                
                command = input("\nコマンド (refresh/save/quit): ").strip().lower()
                
                if command == 'refresh':
                    continue
                elif command == 'save':
                    self.save_summary_report()
                elif command == 'quit':
                    break
                else:
                    print("無効なコマンドです")
                    
            except KeyboardInterrupt:
                print("\nサマリーシステムを終了します...")
                break
            except Exception as e:
                print(f"エラーが発生しました: {e}")
                time.sleep(5)

def main():
    """メイン関数"""
    summary = UltimateSystemSummary()
    summary.run()

if __name__ == "__main__":
    main() 