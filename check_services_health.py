"""
ManaOSサービスヘルスチェックスクリプト
起動後の全サービスの生存確認を行う
"""
import requests
import time
from typing import Dict, List, Tuple

# チェック対象のサービス
SERVICES = [
    {"name": "MRL Memory", "port": 5103, "url": "http://127.0.0.1:5103/health"},
    {"name": "Learning System", "port": 5104, "url": "http://127.0.0.1:5104/health"},
    {"name": "LLM Routing", "port": 5111, "url": "http://127.0.0.1:5111/health"},
    {"name": "Unified API", "port": 9500, "url": "http://127.0.0.1:9500/health"},
]

def check_service(service: Dict) -> Tuple[bool, str]:
    """
    単一サービスのヘルスチェック
    
    Returns:
        (成功フラグ, レスポンス詳細またはエラーメッセージ)
    """
    try:
        response = requests.get(service["url"], timeout=5)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"HTTP {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused"
    except Exception as e:
        return False, str(e)

def check_all_services(retry_count: int = 3, retry_delay: int = 2) -> bool:
    """
    全サービスのヘルスチェック（リトライ機能付き）
    
    Args:
        retry_count: リトライ回数
        retry_delay: リトライ間隔（秒）
    
    Returns:
        全サービスが正常ならTrue
    """
    print("\n" + "=" * 60)
    print("🔍 ManaOSサービスヘルスチェック")
    print("=" * 60)
    
    all_healthy = True
    
    for attempt in range(retry_count):
        if attempt > 0:
            print(f"\n⏳ リトライ {attempt}/{retry_count - 1}... ({retry_delay}秒待機)")
            time.sleep(retry_delay)
        
        attempt_results = []
        for service in SERVICES:
            success, detail = check_service(service)
            attempt_results.append((service, success, detail))
            
            status_icon = "✅" if success else "❌"
            status_text = "OK" if success else "ERROR"
            print(f"{status_icon} {service['name']:20} (port {service['port']}): {status_text}")
            if not success:
                print(f"   └─ {detail}")
        
        # すべて成功したら終了
        if all(result[1] for result in attempt_results):
            all_healthy = True
            break
        else:
            all_healthy = False
    
    print("=" * 60)
    if all_healthy:
        print("✅ すべてのサービスが正常稼働中")
    else:
        print("⚠️ 一部のサービスが応答しません")
        print("   対処: タスク \"ManaOS: すべてのサービスを起動\" を再実行してください")
    print("=" * 60 + "\n")
    
    return all_healthy

if __name__ == "__main__":
    import sys
    success = check_all_services()
    sys.exit(0 if success else 1)
