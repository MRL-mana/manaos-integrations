"""
LLMルーティングシステム 監視ダッシュボード
リアルタイムでサービス状態を監視
"""

import requests
import time
import json
from datetime import datetime
from typing import Dict, Any, List
from collections import deque
import os

from _paths import LM_STUDIO_PORT, UNIFIED_API_PORT

# APIエンドポイント
UNIFIED_API_URL = os.getenv(
    "MANAOS_INTEGRATION_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}"
).rstrip("/")
ROUTING_API_URL = UNIFIED_API_URL
LM_STUDIO_URL = os.getenv(
    "LM_STUDIO_URL", f"http://127.0.0.1:{LM_STUDIO_PORT}/v1"
).rstrip("/")

# 監視履歴（最新100件）
monitoring_history = deque(maxlen=100)


class ServiceMonitor:
    """サービス監視クラス"""
    
    def __init__(self):
        self.services = {
            "lm_studio": {
                "name": "LM Studioサーバー",
                "url": f"{LM_STUDIO_URL}/models",
                "status": "unknown",
                "last_check": None,
                "response_time_ms": 0
            },
            "llm_routing_api": {
                "name": "LLMルーティング（Unified API）",
                "url": f"{ROUTING_API_URL}/api/llm/health",
                "status": "unknown",
                "last_check": None,
                "response_time_ms": 0
            },
            "unified_api": {
                "name": "統合APIサーバー",
                "url": f"{UNIFIED_API_URL}/health",
                "status": "unknown",
                "last_check": None,
                "response_time_ms": 0
            }
        }
    
    def check_service(self, service_key: str) -> Dict[str, Any]:
        """サービスをチェック"""
        service = self.services[service_key]
        
        try:
            start_time = time.time()
            response = requests.get(service["url"], timeout=3)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                service["status"] = "healthy"
                service["response_time_ms"] = response_time_ms
                service["last_check"] = datetime.now().isoformat()
                
                # 追加情報を取得
                try:
                    data = response.json()
                    return {
                        "status": "healthy",
                        "response_time_ms": response_time_ms,
                        "data": data
                    }
                except Exception:
                    return {
                        "status": "healthy",
                        "response_time_ms": response_time_ms
                    }
            else:
                service["status"] = "unhealthy"
                service["response_time_ms"] = response_time_ms
                service["last_check"] = datetime.now().isoformat()
                return {
                    "status": "unhealthy",
                    "response_time_ms": response_time_ms,
                    "http_status": response.status_code
                }
        
        except requests.exceptions.Timeout:
            service["status"] = "timeout"
            service["last_check"] = datetime.now().isoformat()
            return {
                "status": "timeout",
                "response_time_ms": 3000
            }
        
        except Exception as e:
            service["status"] = "error"
            service["last_check"] = datetime.now().isoformat()
            return {
                "status": "error",
                "error": str(e)
            }
    
    def check_all_services(self) -> Dict[str, Any]:
        """すべてのサービスをチェック"""
        results = {}
        
        for service_key in self.services.keys():
            results[service_key] = self.check_service(service_key)
            time.sleep(0.5)  # リクエスト間隔
        
        return results
    
    def get_status_summary(self) -> Dict[str, Any]:
        """ステータスサマリーを取得"""
        healthy_count = sum(1 for s in self.services.values() if s["status"] == "healthy")
        total_count = len(self.services)
        
        return {
            "total_services": total_count,
            "healthy_services": healthy_count,
            "unhealthy_services": total_count - healthy_count,
            "health_percentage": (healthy_count / total_count * 100) if total_count > 0 else 0,
            "services": {
                key: {
                    "name": service["name"],
                    "status": service["status"],
                    "last_check": service["last_check"],
                    "response_time_ms": service["response_time_ms"]
                }
                for key, service in self.services.items()
            }
        }


def print_dashboard(monitor: ServiceMonitor):
    """ダッシュボードを表示"""
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("=" * 70)
    print("  LLMルーティングシステム 監視ダッシュボード")
    print("=" * 70)
    print(f"  更新時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # サービス状態
    summary = monitor.get_status_summary()
    
    print(f"📊 全体ステータス:")
    print(f"  健康なサービス: {summary['healthy_services']}/{summary['total_services']}")
    print(f"  健全性: {summary['health_percentage']:.1f}%")
    print()
    
    # 各サービスの詳細
    print("🔍 サービス詳細:")
    for key, service_info in summary["services"].items():
        status_icon = "✅" if service_info["status"] == "healthy" else "❌"
        status_color = "healthy" if service_info["status"] == "healthy" else "unhealthy"
        
        print(f"  {status_icon} {service_info['name']}")
        print(f"     ステータス: {service_info['status']}")
        if service_info["response_time_ms"] > 0:
            print(f"     レスポンス時間: {service_info['response_time_ms']}ms")
        if service_info["last_check"]:
            print(f"     最終チェック: {service_info['last_check']}")
        print()
    
    print("=" * 70)
    print("  更新中... (Ctrl+Cで終了)")
    print("=" * 70)


def main():
    """メイン関数"""
    monitor = ServiceMonitor()
    
    print("LLMルーティングシステム 監視ダッシュボードを起動します...")
    print("Ctrl+Cで終了")
    print()
    
    try:
        while True:
            monitor.check_all_services()
            print_dashboard(monitor)
            time.sleep(5)  # 5秒ごとに更新
    
    except KeyboardInterrupt:
        print("\n監視を終了します...")


if __name__ == "__main__":
    main()



















