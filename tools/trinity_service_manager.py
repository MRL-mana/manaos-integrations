#!/usr/bin/env python3
"""
Trinity Service Manager - オンデマンドサービス管理
"""
import subprocess
import sys
import shutil
import logging
import argparse
from typing import List, Dict

logger = logging.getLogger(__name__)

# systemctl が存在しない環境 (Windows) ではサービス操作を無効化
_SYSTEMCTL = shutil.which("systemctl")


def _systemctl_available() -> bool:
    """systemctl が使用可能かどうかを返す"""
    return _SYSTEMCTL is not None

class TrinityServiceManager:
    def __init__(self):
        self.on_demand_services = {
            'image-generator': 'trinity-image-generator.service',
            'auto-backup': 'manaos-auto-backup.service',
            'calendar-reminder': 'manaos-calendar-reminder.service',
            'security-monitor': 'mana-security-monitor.service',
            'unified-monitor': 'manaos-unified-monitor.service'
        }
    
    def start_service(self, service_name: str) -> bool:
        """サービスを起動"""
        if not _systemctl_available():
            logger.error("systemctl が見つかりません。Linux/systemd 環境でのみ利用可能です。")
            return False
        try:
            if service_name in self.on_demand_services:
                actual_service = self.on_demand_services[service_name]
            else:
                actual_service = service_name

            result = subprocess.run(  # type: ignore[call-arg]
                [_SYSTEMCTL, 'start', actual_service],  # type: ignore
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"✅ {service_name} を起動しました")
                return True
            else:
                logger.error("%s の起動に失敗: %s", service_name, result.stderr)
                return False
        except Exception as e:
            logger.error("start_service error: %s", e)
            return False

    def stop_service(self, service_name: str) -> bool:
        """サービスを停止"""
        if not _systemctl_available():
            logger.error("systemctl が見つかりません。Linux/systemd 環境でのみ利用可能です。")
            return False
        try:
            if service_name in self.on_demand_services:
                actual_service = self.on_demand_services[service_name]
            else:
                actual_service = service_name

            result = subprocess.run(  # type: ignore[call-arg]
                [_SYSTEMCTL, 'stop', actual_service],  # type: ignore
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"✅ {service_name} を停止しました")
                return True
            else:
                logger.error("%s の停止に失敗: %s", service_name, result.stderr)
                return False
        except Exception as e:
            logger.error("stop_service error: %s", e)
            return False

    def status_service(self, service_name: str) -> Dict:
        """サービスの状態を確認"""
        if not _systemctl_available():
            return {
                'name': service_name,
                'status': False,
                'error': 'systemctl unavailable (non-Linux environment)',
            }
        try:
            if service_name in self.on_demand_services:
                actual_service = self.on_demand_services[service_name]
            else:
                actual_service = service_name

            result = subprocess.run(  # type: ignore[call-arg]
                [_SYSTEMCTL, 'status', actual_service],  # type: ignore
            )
            
            return {
                'name': service_name,
                'actual_name': actual_service,
                'status': result.returncode == 0,
                'output': result.stdout
            }
        except Exception as e:
            return {
                'name': service_name,
                'error': str(e)
            }
    
    def list_services(self):
        """利用可能なサービス一覧を表示"""
        print("🚀 Trinity Service Manager")
        print("=" * 50)
        print("📋 オンデマンドサービス一覧:")
        for key, value in self.on_demand_services.items():
            status = self.status_service(key)
            status_text = "🟢 起動中" if status.get('status') else "🔴 停止中"
            print(f"  {key}: {value} - {status_text}")
        print("=" * 50)
    
    def auto_optimize(self):
        """自動最適化を実行"""
        print("🔧 自動最適化を実行中...")
        
        # 重要なサービスを起動
        important_services = ['manaos-heal', 'mana-trinity-sync']
        for service in important_services:
            self.start_service(service)
        
        print("✅ 自動最適化完了!")

def main():
    parser = argparse.ArgumentParser(description='Trinity Service Manager')
    parser.add_argument('action', choices=['start', 'stop', 'status', 'list', 'optimize'], 
                       help='実行するアクション')
    parser.add_argument('service', nargs='?', help='サービス名')
    
    args = parser.parse_args()
    manager = TrinityServiceManager()
    
    if args.action == 'list':
        manager.list_services()
    elif args.action == 'optimize':
        manager.auto_optimize()
    elif args.service:
        if args.action == 'start':
            manager.start_service(args.service)
        elif args.action == 'stop':
            manager.stop_service(args.service)
        elif args.action == 'status':
            status = manager.status_service(args.service)
            print(f"📊 {status['name']} の状態:")
            print(status.get('output', status.get('error', '不明')))
    else:
        print("❌ サービス名を指定してください")

if __name__ == '__main__':
    main()


















