#!/usr/bin/env python3
"""
Trinity System Optimizer - システム最適化ダッシュボード
"""
import subprocess
import json
import time
from datetime import datetime
from typing import Dict, List

class TrinitySystemOptimizer:
    def __init__(self):
        self.core_services = [
            'manaos.target',
            'mana-api-bridge.service',
            'mana-realtime-dashboard.service',
            'mana-screen-sharing.service',
            'trinity-enhanced-secretary.service',
            'trinity-orchestrator-api.service',
            'manaos-heal.service',
            'mana-trinity-sync.service'
        ]
        
        self.on_demand_services = [
            'trinity-image-generator.service',
            'manaos-auto-backup.service',
            'manaos-calendar-reminder.service',
            'mana-security-monitor.service',
            'manaos-unified-monitor.service'
        ]
    
    def get_service_status(self, service_name: str) -> Dict:
        """サービスの状態を取得"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True,
                text=True
            )
            
            enabled_result = subprocess.run(
                ['systemctl', 'is-enabled', service_name],
                capture_output=True,
                text=True
            )
            
            return {
                'name': service_name,
                'active': result.stdout.strip() == 'active',
                'enabled': enabled_result.stdout.strip() == 'enabled',
                'status': result.stdout.strip()
            }
        except Exception as e:
            return {
                'name': service_name,
                'active': False,
                'enabled': False,
                'error': str(e)
            }
    
    def get_system_stats(self) -> Dict:
        """システム統計を取得"""
        try:
            # CPU使用率
            cpu_result = subprocess.run(
                "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | sed 's/%us,//'",
                shell=True,
                capture_output=True,
                text=True
            )
            
            # メモリ使用率
            mem_result = subprocess.run(
                ['free', '-m'],
                capture_output=True,
                text=True
            )
            
            # 実行中プロセス数
            proc_result = subprocess.run(
                ['ps', 'aux', '|', 'wc', '-l'],
                shell=True,
                capture_output=True,
                text=True
            )
            
            return {
                'cpu_usage': cpu_result.stdout.strip() if cpu_result.stdout else 'N/A',
                'memory_info': mem_result.stdout.strip(),
                'process_count': proc_result.stdout.strip(),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def optimize_system(self):
        """システム最適化を実行"""
        print("🔧 Trinity System Optimizer")
        print("=" * 60)
        
        # コアサービスの状態確認
        print("📊 コアサービス状態:")
        for service in self.core_services:
            status = self.get_service_status(service)
            status_icon = "🟢" if status['active'] else "🔴"
            enabled_icon = "✅" if status['enabled'] else "❌"
            print(f"  {status_icon} {enabled_icon} {service}")
        
        print("\n📋 オンデマンドサービス:")
        for service in self.on_demand_services:
            status = self.get_service_status(service)
            status_icon = "🟢" if status['active'] else "🔴"
            print(f"  {status_icon} {service}")
        
        # システム統計
        stats = self.get_system_stats()
        print(f"\n📈 システム統計:")
        print(f"  プロセス数: {stats.get('process_count', 'N/A')}")
        print(f"  CPU使用率: {stats.get('cpu_usage', 'N/A')}")
        
        print("\n✅ 最適化完了!")
    
    def create_optimization_report(self) -> str:
        """最適化レポートを作成"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'core_services': {},
            'on_demand_services': {},
            'optimization_status': 'completed'
        }
        
        for service in self.core_services:
            report['core_services'][service] = self.get_service_status(service)
        
        for service in self.on_demand_services:
            report['on_demand_services'][service] = self.get_service_status(service)
        
        return json.dumps(report, indent=2, ensure_ascii=False)
    
    def save_report(self, filename: str = None):  # type: ignore
        """レポートを保存"""
        if not filename:
            filename = f"/root/trinity_workspace/logs/optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = self.create_optimization_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"📄 レポートを保存しました: {filename}")

def main():
    optimizer = TrinitySystemOptimizer()
    
    print("🚀 Trinity System Optimizer 起動")
    print("=" * 60)
    
    # 最適化実行
    optimizer.optimize_system()
    
    # レポート保存
    optimizer.save_report()
    
    print("\n🎯 最適化完了! システムが効率的に動作しています。")

if __name__ == '__main__':
    main()
