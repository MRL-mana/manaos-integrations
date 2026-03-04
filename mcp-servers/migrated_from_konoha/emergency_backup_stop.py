#!/usr/bin/env python3
"""
バックアップシステム緊急停止スクリプト
重複しているバックアップシステムを停止
"""

import subprocess
import os
import signal
import psutil
import json
from datetime import datetime

def stop_backup_processes():
    """バックアップ関連プロセスを停止"""
    
    stopped_processes = []
    
    # バックアップ関連のプロセス名
    backup_keywords = [
        'backup', 'automated_backup', 'unified_backup', 
        'auto_health_monitor', 'health_monitor'
    ]
    
    print("🛑 バックアップ関連プロセスの停止開始...")
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            proc_info = proc.info
            cmdline = ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else ''
            
            # バックアップ関連プロセスを検出
            if any(keyword in cmdline.lower() for keyword in backup_keywords):
                print(f"🔍 発見: PID {proc_info['pid']} - {cmdline[:100]}...")
                
                try:
                    # プロセスを停止
                    proc.terminate()
                    proc.wait(timeout=5)
                    stopped_processes.append({
                        'pid': proc_info['pid'],
                        'name': proc_info['name'],
                        'cmdline': cmdline,
                        'stopped_at': datetime.now().isoformat()
                    })
                    print(f"✅ 停止完了: PID {proc_info['pid']}")
                    
                except psutil.TimeoutExpired:
                    # 強制終了
                    proc.kill()
                    stopped_processes.append({
                        'pid': proc_info['pid'],
                        'name': proc_info['name'],
                        'cmdline': cmdline,
                        'stopped_at': datetime.now().isoformat(),
                        'force_killed': True
                    })
                    print(f"💀 強制終了: PID {proc_info['pid']}")
                    
                except Exception as e:
                    print(f"❌ 停止失敗: PID {proc_info['pid']} - {e}")
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # 結果レポート
    report = {
        'timestamp': datetime.now().isoformat(),
        'action': 'backup_processes_stop',
        'stopped_count': len(stopped_processes),
        'stopped_processes': stopped_processes
    }
    
    report_file = f"/root/trinity_workspace/backup_stop_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📊 停止完了:")
    print(f"  - 停止したプロセス数: {len(stopped_processes)}個")
    print(f"  - レポート: {report_file}")
    
    return stopped_processes

def disable_cron_backups():
    """cronジョブのバックアップを無効化"""
    
    print("\n🛑 cronジョブのバックアップ無効化...")
    
    try:
        # 現在のcrontabを取得
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        
        if result.returncode == 0:
            cron_lines = result.stdout.split('\n')
            
            # バックアップ関連のcronジョブをコメントアウト
            modified_lines = []
            disabled_count = 0
            
            for line in cron_lines:
                if any(keyword in line.lower() for keyword in ['backup', 'health_monitor']):
                    if not line.strip().startswith('#'):
                        modified_lines.append(f"# DISABLED: {line}")
                        disabled_count += 1
                        print(f"🚫 無効化: {line}")
                    else:
                        modified_lines.append(line)
                else:
                    modified_lines.append(line)
            
            # 新しいcrontabを設定
            new_crontab = '\n'.join(modified_lines)
            subprocess.run(['crontab', '-'], input=new_crontab, text=True)
            
            print(f"✅ cronジョブ無効化完了: {disabled_count}個")
            
        else:
            print("ℹ️  crontabが見つかりません")
            
    except Exception as e:
        print(f"❌ cron無効化エラー: {e}")

def main():
    """メイン実行"""
    print("🚨 バックアップシステム緊急停止開始")
    print("=" * 50)
    
    # プロセス停止
    stopped = stop_backup_processes()
    
    # cron無効化
    disable_cron_backups()
    
    print("\n✅ 緊急停止完了!")
    print("=" * 50)

if __name__ == "__main__":
    main()
