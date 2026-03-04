#!/usr/bin/env python3
"""
🖥️ ManaOS System Inspector
ManaOSシステム全体の状況を把握・分析

機能:
- 全サービスの死活監視
- システムメトリクス取得
- 健全性スコア計算
- 推奨事項自動生成
- リアルタイムアラート
"""

import os
import asyncio
import logging
import json
import sqlite3
import psutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ManaOSSystemInspector:
    """ManaOSシステム状況把握"""
    
    def __init__(self):
        # エンドポイント
        self.manaos_orchestrator = "http://localhost:9200"
        self.command_center = "http://localhost:10000"
        self.unified_monitor_db = "/root/manaos_unified_metrics.db"
        
        # 監視対象サービス
        self.services = {
            'manaos_v3_orchestrator': {
                'port': 9200, 
                'name': 'Remi（司令）',
                'critical': True
            },
            'manaos_v3_intention': {
                'port': 9201, 
                'name': 'Intention Detector',
                'critical': True
            },
            'manaos_v3_policy': {
                'port': 9202, 
                'name': 'Policy Engine',
                'critical': True
            },
            'manaos_v3_actuator': {
                'port': 9203, 
                'name': 'Actuator',
                'critical': True
            },
            'manaos_v3_ingestor': {
                'port': 9204, 
                'name': 'Ingestor',
                'critical': False
            },
            'manaos_v3_insight': {
                'port': 9205, 
                'name': 'Insight',
                'critical': False
            },
            'trinity_master': {
                'port': 8087, 
                'name': 'Trinity Master',
                'critical': False
            },
            'ai_learning': {
                'port': 8600, 
                'name': 'AI Learning System',
                'critical': False
            },
        }
        
        logger.info("🖥️ ManaOS System Inspector initialized")
    
    async def get_full_system_status(self) -> Dict[str, Any]:
        """システム全体の状況を取得"""
        logger.info("🔍 Collecting full system status...")
        
        status = {
            'timestamp': datetime.now().isoformat(),
            'overall_health': 'unknown',
            'health_score': 0,
            'system_metrics': await self._get_system_metrics(),
            'services': await self._check_all_services(),
            'recent_issues': await self._get_recent_issues(),
            'performance': await self._get_performance_stats(),
            'recommendations': []
        }
        
        # 総合健全性スコア計算
        health_score = self._calculate_health_score(status)
        status['health_score'] = health_score
        status['overall_health'] = self._get_health_label(health_score)
        
        # 推奨事項生成
        status['recommendations'] = self._generate_recommendations(status)
        
        logger.info(f"✅ System status collected - Health: {health_score}/100")
        
        return status
    
    async def _get_system_metrics(self) -> Dict:
        """システムメトリクス取得"""
        logger.info("  📊 Getting system metrics...")
        
        try:
            # まずDBから最新データを取得
            if Path(self.unified_monitor_db).exists():
                conn = sqlite3.connect(self.unified_monitor_db)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM system_metrics 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''')
                
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return {
                        'timestamp': row[1],
                        'cpu_percent': round(row[2], 1),
                        'memory_percent': round(row[3], 1),
                        'memory_used_gb': round(row[4], 1),
                        'disk_percent': round(row[5], 1),
                        'process_count': row[6],
                        'load_avg': round(row[7], 2)
                    }
        except Exception as e:
            logger.warning(f"  ⚠️ DB metrics failed: {e}")
        
        # フォールバック：psutilで直接取得
        try:
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': round(psutil.cpu_percent(interval=1), 1),
                'memory_percent': round(mem.percent, 1),
                'memory_used_gb': round(mem.used / 1024**3, 1),
                'disk_percent': round(disk.percent, 1),
                'process_count': len(psutil.pids()),
                'load_avg': round(os.getloadavg()[0], 2)
            }
        except Exception as e:
            logger.error(f"  ❌ Metrics collection failed: {e}")
            return {}
    
    async def _check_all_services(self) -> Dict[str, Dict]:
        """全サービスの死活確認"""
        logger.info("  🔧 Checking all services...")
        
        results = {}
        
        async with httpx.AsyncClient(timeout=5) as client:
            for service_id, service_info in self.services.items():
                try:
                    # /health エンドポイントを試す
                    url = f"http://localhost:{service_info['port']}/health"
                    start_time = datetime.now()
                    
                    try:
                        response = await client.get(url)
                        status_code = response.status_code
                    except requests.RequestException:
                        # /health がなければ / で試す
                        url = f"http://localhost:{service_info['port']}/"
                        response = await client.get(url)
                        status_code = response.status_code
                    
                    response_time = (datetime.now() - start_time).total_seconds() * 1000
                    
                    results[service_id] = {
                        'name': service_info['name'],
                        'port': service_info['port'],
                        'status': 'online' if status_code == 200 else 'degraded',
                        'response_time_ms': round(response_time, 1),
                        'critical': service_info.get('critical', False)
                    }
                    
                except Exception as e:
                    results[service_id] = {
                        'name': service_info['name'],
                        'port': service_info['port'],
                        'status': 'offline',
                        'response_time_ms': None,
                        'critical': service_info.get('critical', False),
                        'error': str(e)
                    }
        
        online_count = sum(1 for s in results.values() if s['status'] == 'online')
        logger.info(f"    ✅ Services: {online_count}/{len(results)} online")
        
        return results
    
    async def _get_recent_issues(self) -> List[Dict]:
        """最近の問題を取得"""
        logger.info("  ⚠️ Checking recent issues...")
        
        issues = []
        
        if not Path(self.unified_monitor_db).exists():
            return issues
        
        try:
            conn = sqlite3.connect(self.unified_monitor_db)
            cursor = conn.cursor()
            
            # 過去24時間の健全性チェック
            cursor.execute('''
                SELECT timestamp, status, issues 
                FROM health_checks 
                WHERE timestamp > datetime('now', '-24 hours')
                AND status IN ('warning', 'critical')
                ORDER BY timestamp DESC
                LIMIT 10
            ''')
            
            rows = cursor.fetchall()
            
            for row in rows:
                try:
                    issues.append({
                        'timestamp': row[0],
                        'severity': row[1],
                        'details': json.loads(row[2]) if row[2] else []
                    })
                except Exception:
                    continue
            
            conn.close()
            
            logger.info(f"    ⚠️ Found {len(issues)} recent issues")
            
        except Exception as e:
            logger.warning(f"  ⚠️ Issues retrieval failed: {e}")
        
        return issues
    
    async def _get_performance_stats(self) -> Dict:
        """パフォーマンス統計（過去1時間）"""
        logger.info("  📈 Getting performance stats...")
        
        if not Path(self.unified_monitor_db).exists():
            return {}
        
        try:
            conn = sqlite3.connect(self.unified_monitor_db)
            cursor = conn.cursor()
            
            # 過去1時間の平均・最大値
            cursor.execute('''
                SELECT 
                    AVG(cpu_percent) as avg_cpu,
                    AVG(memory_percent) as avg_mem,
                    AVG(disk_percent) as avg_disk,
                    MAX(cpu_percent) as max_cpu,
                    MAX(memory_percent) as max_mem,
                    COUNT(*) as data_points
                FROM system_metrics
                WHERE timestamp > datetime('now', '-1 hour')
            ''')
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[5] > 0:  # data_points > 0
                return {
                    'avg_cpu': round(row[0], 1),
                    'avg_memory': round(row[1], 1),
                    'avg_disk': round(row[2], 1),
                    'max_cpu': round(row[3], 1),
                    'max_memory': round(row[4], 1),
                    'data_points': row[5]
                }
        except Exception as e:
            logger.warning(f"  ⚠️ Performance stats failed: {e}")
        
        return {}
    
    def _calculate_health_score(self, status: Dict) -> int:
        """健全性スコア計算（0-100）"""
        score = 100
        
        metrics = status.get('system_metrics', {})
        services = status.get('services', {})
        
        # CPU使用率（Noneチェック）
        cpu = metrics.get('cpu_percent', 0)
        if cpu is not None and cpu > 90:
            score -= 20
        elif cpu is not None and cpu > 70:
            score -= 10
        elif cpu is not None and cpu > 50:
            score -= 5
        
        # メモリ使用率（Noneチェック）
        memory = metrics.get('memory_percent', 0)
        if memory is not None and memory > 90:
            score -= 20
        elif memory is not None and memory > 75:
            score -= 10
        elif memory is not None and memory > 60:
            score -= 5
        
        # ディスク使用率（Noneチェック）
        disk = metrics.get('disk_percent', 0)
        if disk is not None and disk > 95:
            score -= 25
        elif disk is not None and disk > 85:
            score -= 15
        elif disk is not None and disk > 75:
            score -= 8
        
        # サービス状態
        offline_critical = sum(
            1 for s in services.values() 
            if s['status'] == 'offline' and s.get('critical', False)
        )
        offline_normal = sum(
            1 for s in services.values() 
            if s['status'] == 'offline' and not s.get('critical', False)
        )
        
        score -= offline_critical * 15  # 重要サービス
        score -= offline_normal * 5     # 通常サービス
        
        # 最近の問題
        issues = status.get('recent_issues', [])
        critical_issues = sum(1 for i in issues if i.get('severity') == 'critical')
        warning_issues = sum(1 for i in issues if i.get('severity') == 'warning')
        
        score -= critical_issues * 5
        score -= warning_issues * 2
        
        return max(0, min(100, score))
    
    def _get_health_label(self, score: int) -> str:
        """健全性ラベル"""
        if score >= 90:
            return '🟢 優良'
        elif score >= 70:
            return '🟡 注意'
        elif score >= 50:
            return '🟠 警告'
        else:
            return '🔴 深刻'
    
    def _generate_recommendations(self, status: Dict) -> List[str]:
        """推奨事項生成"""
        recommendations = []
        
        metrics = status.get('system_metrics', {})
        services = status.get('services', {})
        
        # CPU（Noneチェック）
        cpu = metrics.get('cpu_percent', 0) or 0
        if cpu > 85:
            recommendations.append('🔴 CPU使用率が非常に高いです。不要なプロセスを停止してください')
        elif cpu > 70:
            recommendations.append('💡 CPU使用率が高めです。負荷の高いタスクを確認してください')
        
        # メモリ（Noneチェック）
        memory = metrics.get('memory_percent', 0) or 0
        if memory > 85:
            recommendations.append('🔴 メモリ使用率が非常に高いです。メモリリークの可能性があります')
        elif memory > 75:
            recommendations.append('💡 メモリ使用率が高めです。キャッシュクリアを推奨します')
        
        # ディスク（Noneチェック）
        disk = metrics.get('disk_percent', 0) or 0
        if disk > 90:
            recommendations.append('🔴 ディスク容量が逼迫しています。緊急でクリーンアップが必要です')
        elif disk > 85:
            recommendations.append('⚠️ ディスク容量が不足しています。古いログやバックアップを削除してください')
        elif disk > 75:
            recommendations.append('💡 ディスク容量に余裕がなくなってきました。定期的なクリーンアップを推奨します')
        
        # オフラインサービス（重要）
        offline_critical = [
            s['name'] for s in services.values() 
            if s['status'] == 'offline' and s.get('critical', False)
        ]
        if offline_critical:
            recommendations.append(
                f'🔴 重要サービスがオフラインです: {", ".join(offline_critical)}。すぐに再起動してください'
            )
        
        # オフラインサービス（通常）
        offline_normal = [
            s['name'] for s in services.values() 
            if s['status'] == 'offline' and not s.get('critical', False)
        ]
        if offline_normal:
            recommendations.append(
                f'⚠️ サービスがオフラインです: {", ".join(offline_normal)}。必要に応じて再起動してください'
            )
        
        # 応答速度が遅いサービス（Noneチェック）
        slow_services = [
            s['name'] for s in services.values() 
            if s.get('response_time_ms') is not None and s.get('response_time_ms', 0) > 1000
        ]
        if slow_services:
            recommendations.append(
                f'💡 応答が遅いサービスがあります: {", ".join(slow_services)}。負荷を確認してください'
            )
        
        # 推奨事項がない場合
        if not recommendations:
            recommendations.append('✅ システムは正常に動作しています。問題はありません')
        
        return recommendations
    
    async def get_service_details(self, service_id: str) -> Dict[str, Any]:
        """特定サービスの詳細情報を取得"""
        if service_id not in self.services:
            return {'error': 'Service not found'}
        
        service_info = self.services[service_id]
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # ヘルスチェック
                url = f"http://localhost:{service_info['port']}/health"
                response = await client.get(url)
                
                return {
                    'service_id': service_id,
                    'name': service_info['name'],
                    'port': service_info['port'],
                    'status': 'online' if response.status_code == 200 else 'degraded',
                    'health_data': response.json() if response.status_code == 200 else {}
                }
        except Exception as e:
            return {
                'service_id': service_id,
                'name': service_info['name'],
                'port': service_info['port'],
                'status': 'offline',
                'error': str(e)
            }


# テスト用
async def test_inspector():
    """システムインスペクターのテスト"""
    inspector = ManaOSSystemInspector()
    
    print("\n" + "="*60)
    print("ManaOS System Inspector - Test")
    print("="*60)
    
    status = await inspector.get_full_system_status()
    
    print(f"\n{status['overall_health']} 健全性スコア: {status['health_score']}/100")
    
    print("\n📊 システムメトリクス:")
    metrics = status['system_metrics']
    print(f"  CPU: {metrics.get('cpu_percent', 0)}%")
    print(f"  RAM: {metrics.get('memory_percent', 0)}% ({metrics.get('memory_used_gb', 0)} GB)")
    print(f"  Disk: {metrics.get('disk_percent', 0)}%")
    print(f"  Processes: {metrics.get('process_count', 0)}")
    
    print("\n🔧 サービス:")
    services = status['services']
    for svc_id, svc_info in services.items():
        status_emoji = '✅' if svc_info['status'] == 'online' else '❌'
        print(f"  {status_emoji} {svc_info['name']}: {svc_info['status']}")
    
    print("\n💡 推奨事項:")
    for rec in status['recommendations']:
        print(f"  {rec}")


if __name__ == '__main__':
    asyncio.run(test_inspector())

