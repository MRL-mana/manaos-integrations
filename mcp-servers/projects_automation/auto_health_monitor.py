#!/usr/bin/env python3
"""
ManaOS Auto Health Monitor & Self-Healing System
自動ヘルスチェックと自己修復システム
"""

import requests
import subprocess
import psutil
import time
import json
import logging
from datetime import datetime
from typing import Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutoHealthMonitor:
    def __init__(self):
        # 監視対象のサービス
        self.services = {
            'manaos_v3_orchestrator': {
                'port': 9200,
                'endpoint': 'http://localhost:9200/health',
                'restart_cmd': 'docker restart manaos-orchestrator',
                'critical': True
            },
            'manaos_v3_intention': {
                'port': 9201,
                'endpoint': 'http://localhost:9201/health',
                'restart_cmd': 'docker restart manaos-intention',
                'critical': True
            },
            'manaos_v3_policy': {
                'port': 9202,
                'endpoint': 'http://localhost:9202/health',
                'restart_cmd': 'docker restart manaos-policy',
                'critical': True
            },
            'manaos_v3_actuator': {
                'port': 9203,
                'endpoint': 'http://localhost:9203/health',
                'restart_cmd': 'docker restart manaos-actuator',
                'critical': True
            },
            'trinity_secretary': {
                'port': 8087,
                'endpoint': 'http://localhost:8087/',
                'restart_cmd': 'systemctl restart trinity_secretary || python3 /root/simple_trinity_test.py &',
                'critical': False
            },
            'trinity_google_services': {
                'port': 8097,
                'endpoint': 'http://localhost:8097/api/status',
                'restart_cmd': 'systemctl restart trinity_google || python3 /root/trinity_google_services.py &',
                'critical': False
            },
            'command_center': {
                'port': 10000,
                'endpoint': 'http://localhost:10000/',
                'restart_cmd': 'systemctl restart manaos_command_center || python3 /root/manaos_command_center.py &',
                'critical': True
            },
            'postgres_main': {
                'port': 5432,
                'endpoint': None,
                'restart_cmd': 'docker restart postgres',
                'critical': True
            },
            'redis_main': {
                'port': 6379,
                'endpoint': None,
                'restart_cmd': 'docker restart redis',
                'critical': True
            },
        }
        
        self.health_log = []
        self.recovery_actions = []
        
    def check_port(self, port: int) -> bool:
        """ポートが開いているか確認"""
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and conn.laddr and conn.laddr.port == port:
                return True
        return False
    
    def check_endpoint(self, url: str, timeout: int = 5) -> Dict:
        """HTTPエンドポイントをチェック"""
        try:
            response = requests.get(url, timeout=timeout)
            return {
                'status': 'healthy' if response.status_code == 200 else 'degraded',
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds()
            }
        except requests.exceptions.ConnectionError:
            return {'status': 'down', 'error': 'Connection refused'}
        except requests.exceptions.Timeout:
            return {'status': 'timeout', 'error': 'Request timeout'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def check_service(self, service_name: str, service_config: Dict) -> Dict:
        """個別サービスをチェック"""
        result = {
            'service': service_name,
            'timestamp': datetime.now().isoformat(),
            'port': service_config['port'],
            'critical': service_config['critical']
        }
        
        # ポートチェック
        port_open = self.check_port(service_config['port'])
        result['port_open'] = port_open
        
        # エンドポイントチェック（存在する場合）
        if service_config.get('endpoint'):
            endpoint_result = self.check_endpoint(service_config['endpoint'])
            result.update(endpoint_result)
        else:
            result['status'] = 'healthy' if port_open else 'down'
        
        return result
    
    def restart_service(self, service_name: str, restart_cmd: str) -> bool:
        """サービスを再起動"""
        logger.warning(f"🔄 サービス再起動を試行: {service_name}")
        
        try:
            result = subprocess.run(
                restart_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"✅ 再起動成功: {service_name}")
                self.recovery_actions.append({
                    'service': service_name,
                    'action': 'restart',
                    'timestamp': datetime.now().isoformat(),
                    'success': True
                })
                return True
            else:
                logger.error(f"❌ 再起動失敗: {service_name} - {result.stderr}")
                self.recovery_actions.append({
                    'service': service_name,
                    'action': 'restart',
                    'timestamp': datetime.now().isoformat(),
                    'success': False,
                    'error': result.stderr
                })
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️  再起動タイムアウト: {service_name}")
            return False
        except Exception as e:
            logger.error(f"❌ 再起動エラー: {service_name} - {e}")
            return False
    
    def run_health_check(self) -> Dict:
        """全サービスのヘルスチェックを実行"""
        logger.info("🏥 ヘルスチェック開始...")
        
        results = {}
        unhealthy_services = []
        critical_down = []
        
        for service_name, service_config in self.services.items():
            result = self.check_service(service_name, service_config)
            results[service_name] = result
            
            # 不健全なサービスを記録
            if result['status'] not in ['healthy']:
                unhealthy_services.append(service_name)
                
                if result['critical']:
                    critical_down.append(service_name)
                
                logger.warning(f"⚠️  不健全: {service_name} - {result['status']}")
        
        # サマリー
        total_services = len(self.services)
        healthy_count = sum(1 for r in results.values() if r['status'] == 'healthy')
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_services': total_services,
            'healthy': healthy_count,
            'unhealthy': len(unhealthy_services),
            'critical_down': len(critical_down),
            'overall_status': 'healthy' if healthy_count == total_services else 
                            ('critical' if critical_down else 'degraded')
        }
        
        return {
            'summary': summary,
            'services': results,
            'unhealthy_services': unhealthy_services,
            'critical_down': critical_down
        }
    
    def auto_heal(self, health_report: Dict) -> Dict:
        """自動修復を実行"""
        if not health_report['unhealthy_services']:
            logger.info("✅ 全サービスが正常です")
            return {'healed': [], 'failed': []}
        
        logger.info(f"🔧 自動修復開始 - {len(health_report['unhealthy_services'])}個のサービス")
        
        healed = []
        failed = []
        
        for service_name in health_report['unhealthy_services']:
            service_config = self.services[service_name]
            
            # 再起動を試行
            if self.restart_service(service_name, service_config['restart_cmd']):
                # 再起動後の確認
                time.sleep(5)
                recheck = self.check_service(service_name, service_config)
                
                if recheck['status'] == 'healthy':
                    healed.append(service_name)
                    logger.info(f"✅ 修復成功: {service_name}")
                else:
                    failed.append(service_name)
                    logger.error(f"❌ 修復失敗: {service_name}")
            else:
                failed.append(service_name)
        
        return {'healed': healed, 'failed': failed}
    
    def get_system_metrics(self) -> Dict:
        """システムメトリクスを取得"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu_percent': round(cpu_percent, 2),
            'memory_percent': round(memory.percent, 2),
            'memory_used_gb': round(memory.used / (1024**3), 2),
            'disk_percent': round(disk.percent, 2),
            'disk_used_gb': round(disk.used / (1024**3), 2),
            'process_count': len(psutil.pids()),
            'uptime_seconds': time.time() - psutil.boot_time()
        }
    
    def generate_report(self, health_report: Dict, healing_result: Dict) -> Dict:
        """総合レポートを生成"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'health_check': health_report,
            'auto_healing': healing_result,
            'system_metrics': self.get_system_metrics(),
            'recovery_actions': self.recovery_actions
        }
        
        # レポート保存（1時間に1回のみ）
        current_hour = datetime.now().strftime('%Y%m%d_%H')
        report_file = f"/root/logs/health_report_{current_hour}.json"
        
        # 既存のファイルがある場合は上書き、なければ新規作成
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📄 レポート保存: {report_file}")
        
        return report
    
    def monitor_loop(self, interval: int = 300):
        """継続的な監視ループ（完全停止）"""
        logger.info("🚨 ヘルスモニター完全停止 - ディスク容量不足")
        logger.info("⚠️ 監視ループを停止しました")
        return  # 完全停止

def main():
    monitor = AutoHealthMonitor()
    
    # 単発実行
    print("\n" + "="*60)
    print("🏥 ManaOS Auto Health Monitor")
    print("="*60 + "\n")
    
    # ヘルスチェック
    health_report = monitor.run_health_check()
    
    print("\n📊 ヘルスチェック結果:")
    print(f"  - 総サービス数: {health_report['summary']['total_services']}")
    print(f"  - 正常: {health_report['summary']['healthy']}")
    print(f"  - 問題あり: {health_report['summary']['unhealthy']}")
    print(f"  - 総合ステータス: {health_report['summary']['overall_status'].upper()}")
    
    # 自動修復
    if health_report['unhealthy_services']:
        print("\n🔧 自動修復実行中...")
        healing_result = monitor.auto_heal(health_report)
        
        print("\n✅ 修復完了:")
        print(f"  - 成功: {len(healing_result['healed'])}個")
        print(f"  - 失敗: {len(healing_result['failed'])}個")
        
        if healing_result['healed']:
            print(f"\n  修復成功: {', '.join(healing_result['healed'])}")
        if healing_result['failed']:
            print(f"\n  修復失敗: {', '.join(healing_result['failed'])}")
    
    # レポート生成
    report = monitor.generate_report(health_report, healing_result if health_report['unhealthy_services'] else {'healed': [], 'failed': []})
    
    print("\n📄 詳細レポート: /root/logs/health_report_*.json")
    print("="*60 + "\n")

if __name__ == '__main__':
    import sys
    
    if '--daemon' in sys.argv:
        # デーモンモードで実行
        monitor = AutoHealthMonitor()
        monitor.monitor_loop(interval=300)  # 5分ごと
    else:
        # 単発実行
        main()


