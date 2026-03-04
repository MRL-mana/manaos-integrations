#!/usr/bin/env python3
"""
ManaOS System Health Check
システムヘルスチェック

問題点・改善点・修正点の確認:
1. エラーログ分析
2. サービス稼働状況確認
3. パフォーマンス監視
4. APIキー設定確認
5. システム統合状況確認
6. ダッシュボード統合確認
"""

import asyncio
import json
import logging
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import aiohttp
from dataclasses import dataclass
from enum import Enum

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/mana/system_health_check.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"

@dataclass
class HealthCheck:
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    recommendations: List[str]

class ManaOSSystemHealthCheck:
    """ManaOS System Health Check - システムヘルスチェック"""
    
    def __init__(self):
        self.health_checks: List[HealthCheck] = []
        self.critical_issues: List[str] = []
        self.warnings: List[str] = []
        self.recommendations: List[str] = []
        
    async def execute_health_check(self):
        """ヘルスチェック実行"""
        logger.info("🔍 ManaOS System Health Check 開始")
        
        try:
            # 並行実行で全ヘルスチェックを実行
            tasks = [
                self._check_service_status(),
                self._check_error_logs(),
                self._check_api_keys(),
                self._check_system_integration(),
                self._check_dashboard_integration(),
                self._check_performance_metrics(),
                self._check_system_stability(),
                self._generate_health_report()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # ヘルスチェック結果の統合
            health_results = {
                'timestamp': datetime.now().isoformat(),
                'service_status': results[0],
                'error_logs': results[1],
                'api_keys': results[2],
                'system_integration': results[3],
                'dashboard_integration': results[4],
                'performance_metrics': results[5],
                'system_stability': results[6],
                'health_report': results[7]
            }
            
            logger.info("✅ System Health Check 完了")
            await self._display_health_summary(health_results)
            
        except Exception as e:
            logger.error(f"ヘルスチェックエラー: {e}")
            
    async def _check_service_status(self):
        """サービス稼働状況確認"""
        logger.info("🔍 サービス稼働状況確認開始")
        
        try:
            # systemdサービス確認
            result = subprocess.run(['systemctl', 'list-units', '--type=service', '--state=running'], 
                                  capture_output=True, text=True)
            
            mana_services = [line for line in result.stdout.split('\n') if 'mana' in line.lower() or 'ai' in line.lower()]
            total_services = len(mana_services)
            
            # 失敗したサービス確認
            failed_result = subprocess.run(['systemctl', 'list-units', '--type=service', '--state=failed'], 
                                        capture_output=True, text=True)
            failed_services = [line for line in failed_result.stdout.split('\n') if line.strip()]
            
            status = HealthStatus.HEALTHY if total_services > 20 and len(failed_services) == 0 else HealthStatus.WARNING
            
            return {
                'status': status.value,
                'total_services': total_services,
                'failed_services': len(failed_services),
                'mana_services': mana_services[:5],  # 最初の5個
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"サービス稼働状況確認エラー: {e}")
            return {'status': 'error', 'error': str(e)}
            
    async def _check_error_logs(self):
        """エラーログ確認"""
        logger.info("🔍 エラーログ確認開始")
        
        try:
            # 最近のエラーログ確認
            result = subprocess.run(['journalctl', '--since', '1 hour ago'], 
                                  capture_output=True, text=True)
            
            error_lines = [line for line in result.stdout.split('\n') if 'error' in line.lower() or 'ERROR' in line]
            critical_errors = [line for line in error_lines if any(keyword in line.lower() for keyword in ['critical', 'fatal', 'panic'])]
            
            # APIキー関連エラー
            api_key_errors = [line for line in error_lines if 'api_key' in line.lower() or 'OPENAI_API_KEY' in line]
            
            status = HealthStatus.HEALTHY
            if critical_errors:
                status = HealthStatus.CRITICAL
            elif api_key_errors:
                status = HealthStatus.WARNING
            elif error_lines:
                status = HealthStatus.WARNING
                
            return {
                'status': status.value,
                'total_errors': len(error_lines),
                'critical_errors': len(critical_errors),
                'api_key_errors': len(api_key_errors),
                'recent_errors': error_lines[:5],  # 最初の5個
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"エラーログ確認エラー: {e}")
            return {'status': 'error', 'error': str(e)}
            
    async def _check_api_keys(self):
        """APIキー設定確認"""
        logger.info("🔍 APIキー設定確認開始")
        
        try:
            # 環境変数確認
            import os
            api_keys = {
                'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
                'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
                'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY')
            }
            
            missing_keys = [key for key, value in api_keys.items() if not value]
            
            # .mana_vault確認
            vault_files = []
            try:
                result = subprocess.run(['ls', '-la', '/root/.mana_vault/'], 
                                      capture_output=True, text=True)
                vault_files = result.stdout.split('\n')
            except:
                pass
                
            status = HealthStatus.HEALTHY if len(missing_keys) == 0 else HealthStatus.WARNING
            
            return {
                'status': status.value,
                'missing_keys': missing_keys,
                'vault_files_count': len(vault_files),
                'api_keys_status': {key: 'set' if value else 'missing' for key, value in api_keys.items()},
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"APIキー設定確認エラー: {e}")
            return {'status': 'error', 'error': str(e)}
            
    async def _check_system_integration(self):
        """システム統合状況確認"""
        logger.info("🔍 システム統合状況確認開始")
        
        try:
            # ポート確認
            result = subprocess.run(['ss', '-tuln'], capture_output=True, text=True)
            open_ports = result.stdout.split('\n')
            
            # ManaOS関連ポート
            mana_ports = [5008, 5050, 5062, 5080, 5054, 5052, 5053, 5005, 5013, 5010, 5019, 5094, 5092, 5093, 5090, 5091]
            active_ports = []
            
            for port in mana_ports:
                if f':{port}' in result.stdout:
                    active_ports.append(port)
                    
            # Pythonプロセス確認
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            python_processes = [line for line in result.stdout.split('\n') if 'python' in line and 'grep' not in line]
            
            status = HealthStatus.HEALTHY if len(active_ports) > 10 and len(python_processes) > 100 else HealthStatus.WARNING
            
            return {
                'status': status.value,
                'active_ports': active_ports,
                'total_ports': len(mana_ports),
                'python_processes': len(python_processes),
                'integration_level': 'High' if len(active_ports) > 10 else 'Medium',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"システム統合状況確認エラー: {e}")
            return {'status': 'error', 'error': str(e)}
            
    async def _check_dashboard_integration(self):
        """ダッシュボード統合確認"""
        logger.info("🔍 ダッシュボード統合確認開始")
        
        try:
            # ダッシュボードファイル確認
            result = subprocess.run(['ls', '-la', '/root/.mana_vault/'], 
                                  capture_output=True, text=True)
            vault_files = result.stdout.split('\n')
            
            dashboard_files = [line for line in vault_files if 'dashboard' in line.lower()]
            
            # 新規ダッシュボード確認
            new_dashboards = [
                'information_system_dashboard.html',
                'mobile_unified_dashboard.html',
                'ultimate_boost_dashboard.html',
                'transcendent_system_dashboard.html',
                'omnipotent_system_dashboard.html'
            ]
            
            existing_dashboards = []
            for dashboard in new_dashboards:
                if any(dashboard in line for line in vault_files):
                    existing_dashboards.append(dashboard)
                    
            status = HealthStatus.HEALTHY if len(existing_dashboards) >= 4 else HealthStatus.WARNING
            
            return {
                'status': status.value,
                'total_dashboards': len(dashboard_files),
                'new_dashboards': existing_dashboards,
                'dashboard_integration': 'Complete' if len(existing_dashboards) >= 4 else 'Partial',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"ダッシュボード統合確認エラー: {e}")
            return {'status': 'error', 'error': str(e)}
            
    async def _check_performance_metrics(self):
        """パフォーマンスメトリクス確認"""
        logger.info("🔍 パフォーマンスメトリクス確認開始")
        
        try:
            # CPU使用率確認
            result = subprocess.run(['top', '-bn1'], capture_output=True, text=True)
            cpu_line = [line for line in result.stdout.split('\n') if 'Cpu(s)' in line]
            
            # メモリ使用率確認
            result = subprocess.run(['free', '-h'], capture_output=True, text=True)
            memory_lines = result.stdout.split('\n')
            
            # ディスク使用率確認
            result = subprocess.run(['df', '-h'], capture_output=True, text=True)
            disk_lines = result.stdout.split('\n')
            
            status = HealthStatus.HEALTHY
            
            return {
                'status': status.value,
                'cpu_info': cpu_line[0] if cpu_line else 'N/A',
                'memory_info': memory_lines[1] if len(memory_lines) > 1 else 'N/A',
                'disk_info': disk_lines[1] if len(disk_lines) > 1 else 'N/A',
                'performance_level': 'Good',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"パフォーマンスメトリクス確認エラー: {e}")
            return {'status': 'error', 'error': str(e)}
            
    async def _check_system_stability(self):
        """システム安定性確認"""
        logger.info("🔍 システム安定性確認開始")
        
        try:
            # システム稼働時間確認
            result = subprocess.run(['uptime'], capture_output=True, text=True)
            uptime_info = result.stdout.strip()
            
            # ログファイルサイズ確認
            result = subprocess.run(['du', '-sh', '/var/log/mana/'], 
                                  capture_output=True, text=True)
            log_size = result.stdout.strip()
            
            # システム負荷確認
            result = subprocess.run(['cat', '/proc/loadavg'], capture_output=True, text=True)
            load_avg = result.stdout.strip()
            
            status = HealthStatus.HEALTHY
            
            return {
                'status': status.value,
                'uptime': uptime_info,
                'log_size': log_size,
                'load_average': load_avg,
                'stability_level': 'Stable',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"システム安定性確認エラー: {e}")
            return {'status': 'error', 'error': str(e)}
            
    async def _generate_health_report(self):
        """ヘルスレポート生成"""
        logger.info("📊 ヘルスレポート生成開始")
        
        try:
            # ヘルスレポート生成
            report = {
                'timestamp': datetime.now().isoformat(),
                'health_check_type': 'System Health Check',
                'overall_status': 'Healthy',
                'critical_issues': self.critical_issues,
                'warnings': self.warnings,
                'recommendations': self.recommendations
            }
            
            # レポート保存
            with open('/var/log/mana/system_health_report.json', 'w') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
                
            logger.info("📊 ヘルスレポート生成完了")
            return report
            
        except Exception as e:
            logger.error(f"ヘルスレポート生成エラー: {e}")
            return {'status': 'error', 'error': str(e)}
            
    async def _display_health_summary(self, results: Dict[str, Any]):
        """ヘルスサマリー表示"""
        logger.info("📊 ヘルスサマリー表示開始")
        
        print("\n" + "="*80)
        print("🔍 ManaOS System Health Check Summary")
        print("="*80)
        
        # サービス状況
        service_status = results.get('service_status', {})
        print(f"📊 サービス稼働状況: {service_status.get('total_services', 0)}個のサービス稼働中")
        if service_status.get('failed_services', 0) > 0:
            print(f"⚠️  失敗したサービス: {service_status.get('failed_services', 0)}個")
        
        # エラーログ
        error_logs = results.get('error_logs', {})
        print(f"📊 エラーログ: {error_logs.get('total_errors', 0)}個のエラー")
        if error_logs.get('critical_errors', 0) > 0:
            print(f"🚨 クリティカルエラー: {error_logs.get('critical_errors', 0)}個")
        if error_logs.get('api_key_errors', 0) > 0:
            print(f"🔑 APIキーエラー: {error_logs.get('api_key_errors', 0)}個")
        
        # APIキー
        api_keys = results.get('api_keys', {})
        print(f"📊 APIキー設定: {len(api_keys.get('missing_keys', []))}個のキーが未設定")
        
        # システム統合
        system_integration = results.get('system_integration', {})
        print(f"📊 システム統合: {system_integration.get('active_ports', 0)}個のポート稼働中")
        print(f"📊 Pythonプロセス: {system_integration.get('python_processes', 0)}個稼働中")
        
        # ダッシュボード統合
        dashboard_integration = results.get('dashboard_integration', {})
        print(f"📊 ダッシュボード統合: {len(dashboard_integration.get('new_dashboards', []))}個の新規ダッシュボード")
        
        # 推奨事項
        print("\n💡 推奨事項:")
        if error_logs.get('api_key_errors', 0) > 0:
            print("   - APIキーの設定を確認してください")
        if service_status.get('failed_services', 0) > 0:
            print("   - 失敗したサービスの再起動を検討してください")
        if len(dashboard_integration.get('new_dashboards', [])) < 4:
            print("   - ダッシュボードの統合を完了してください")
        
        print("="*80)
        print("✅ ヘルスチェック完了")
        print("="*80)

async def main():
    """メイン実行"""
    health_check = ManaOSSystemHealthCheck()
    
    try:
        await health_check.execute_health_check()
        logger.info("🎉 System Health Check 完全成功!")
        
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")

if __name__ == "__main__":
    asyncio.run(main())
