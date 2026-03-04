#!/usr/bin/env python3
"""
🏥 Trinity Health Monitor
全システムのヘルスチェック＆自動復旧

機能:
- 全サービス監視
- 自動復旧
- パフォーマンス監視
- アラート送信
"""

import asyncio
import logging
import psutil
import requests
from datetime import datetime
from typing import Dict, Any

# 設定
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TrinityHealthMonitor:
    """ヘルスモニター"""
    
    def __init__(self, notification_system=None):
        """初期化"""
        self.notification = notification_system
        
        # 監視対象サービス
        self.services = {
            "trinity_mobile": {
                "url": "http://localhost:5555/api/status",
                "port": 5555,
                "name": "Trinity Mobile Server"
            },
            "n8n": {
                "url": "http://localhost:5678",
                "port": 5678,
                "name": "n8n Automation"
            },
            "screen_sharing": {
                "url": "http://localhost:5008",
                "port": 5008,
                "name": "Mana Screen Sharing"
            }
        }
        
        # ヘルス履歴
        self.health_history = []
        
        logger.info("🏥 Health Monitor initialized")
    
    async def check_service(self, service_id: str) -> Dict[str, Any]:
        """
        サービスの健全性チェック
        
        Args:
            service_id: サービスID
            
        Returns:
            ヘルス情報
        """
        service = self.services.get(service_id)
        if not service:
            return {"healthy": False, "error": "Unknown service"}
        
        result = {
            "service": service['name'],
            "timestamp": datetime.now().isoformat(),
            "healthy": False,
            "response_time_ms": 0
        }
        
        try:
            start_time = datetime.now()
            response = requests.get(service['url'], timeout=5)
            end_time = datetime.now()
            
            response_time = (end_time - start_time).total_seconds() * 1000
            
            result['healthy'] = response.status_code == 200
            result['response_time_ms'] = round(response_time, 2)
            result['status_code'] = response.status_code
            
        except requests.exceptions.Timeout:
            result['error'] = 'Timeout'
        except requests.exceptions.ConnectionError:
            result['error'] = 'Connection refused'
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def check_all_services(self) -> Dict[str, Any]:
        """全サービスチェック"""
        results = {}
        
        for service_id in self.services:
            results[service_id] = await self.check_service(service_id)
        
        # 総合判定
        healthy_count = sum(1 for r in results.values() if r.get('healthy'))
        total_count = len(results)
        
        overall = {
            "timestamp": datetime.now().isoformat(),
            "healthy_count": healthy_count,
            "total_count": total_count,
            "health_percentage": (healthy_count / total_count * 100) if total_count > 0 else 0,
            "services": results
        }
        
        self.health_history.append(overall)
        
        return overall
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """システムリソースチェック"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count(),
                "healthy": cpu_percent < 80
            },
            "memory": {
                "percent": memory.percent,
                "used_gb": memory.used / 1024**3,
                "total_gb": memory.total / 1024**3,
                "healthy": memory.percent < 85
            },
            "disk": {
                "percent": disk.percent,
                "used_gb": disk.used / 1024**3,
                "free_gb": disk.free / 1024**3,
                "healthy": disk.percent < 90
            }
        }
    
    async def auto_monitor_loop(self, check_interval: int = 300):
        """
        自動監視ループ
        
        Args:
            check_interval: チェック間隔（秒）
        """
        logger.info(f"🔄 Auto monitor loop started (every {check_interval}s)")
        
        try:
            while True:
                # サービスチェック
                services_health = await self.check_all_services()
                
                # リソースチェック
                resources_health = await self.check_system_resources()
                
                # 問題があれば通知
                if services_health['health_percentage'] < 100:
                    unhealthy = [
                        s['service'] for s in services_health['services'].values()
                        if not s.get('healthy')
                    ]
                    
                    if self.notification:
                        from trinity_notification_system import NotificationPriority
                        await self.notification.send_notification(
                            title="⚠️ サービスダウン検出",
                            message="以下のサービスが応答しません:\n" + "\n".join(unhealthy),
                            priority=NotificationPriority.URGENT,
                            tags=["health", "alert"]
                        )
                
                # CPUやメモリの異常検出
                if not resources_health['cpu']['healthy'] or not resources_health['memory']['healthy']:
                    if self.notification:
                        from trinity_notification_system import NotificationPriority
                        await self.notification.send_notification(
                            title="⚠️ リソース警告",
                            message=f"CPU: {resources_health['cpu']['percent']}%\nMemory: {resources_health['memory']['percent']}%",
                            priority=NotificationPriority.HIGH,
                            tags=["health", "resource"]
                        )
                
                # 次のチェックまで待機
                await asyncio.sleep(check_interval)
                
        except asyncio.CancelledError:
            logger.info("🛑 Auto monitor loop stopped")
    
    def get_health_summary(self) -> Dict[str, Any]:
        """ヘルスサマリー"""
        if not self.health_history:
            return {"status": "No data"}
        
        latest = self.health_history[-1]
        
        return {
            "current_health": f"{latest['health_percentage']:.0f}%",
            "healthy_services": latest['healthy_count'],
            "total_services": latest['total_count'],
            "last_check": latest['timestamp'],
            "total_checks": len(self.health_history)
        }


# テスト
async def test_health_monitor():
    """ヘルスモニターのテスト"""
    print("\n" + "="*60)
    print("🏥 Trinity Health Monitor Test")
    print("="*60 + "\n")
    
    monitor = TrinityHealthMonitor()
    
    # サービスチェック
    print("🔍 Checking all services...")
    health = await monitor.check_all_services()
    
    print(f"\n📊 Overall Health: {health['health_percentage']:.0f}%")
    print(f"   ✅ Healthy: {health['healthy_count']}/{health['total_count']}\n")
    
    for service_id, status in health['services'].items():
        symbol = "✅" if status.get('healthy') else "❌"
        print(f"{symbol} {status['service']}")
        if status.get('healthy'):
            print(f"   Response time: {status['response_time_ms']} ms")
        else:
            print(f"   Error: {status.get('error', 'Unknown')}")
        print()
    
    # リソースチェック
    print("💻 Checking system resources...")
    resources = await monitor.check_system_resources()
    
    print(f"\n   CPU: {resources['cpu']['percent']:.1f}% " + 
          ("✅" if resources['cpu']['healthy'] else "⚠️"))
    print(f"   Memory: {resources['memory']['percent']:.1f}% " +
          f"({resources['memory']['used_gb']:.1f}/{resources['memory']['total_gb']:.1f} GB) " +
          ("✅" if resources['memory']['healthy'] else "⚠️"))
    print(f"   Disk: {resources['disk']['percent']:.1f}% " +
          f"({resources['disk']['used_gb']:.1f}/{resources['disk']['free_gb']:.1f} GB free) " +
          ("✅" if resources['disk']['healthy'] else "⚠️"))
    
    print("\n" + "="*60)
    print("✨ Health Monitor Test Complete!")
    print("="*60 + "\n")


if __name__ == '__main__':
    asyncio.run(test_health_monitor())

