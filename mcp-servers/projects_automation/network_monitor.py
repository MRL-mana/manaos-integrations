#!/usr/bin/env python3
"""
🌐 Network Monitor - ネットワーク監視＆ヘルスチェック
"""

import concurrent.futures
import requests
import socket
import time

class NetworkMonitor:
    def __init__(self, max_workers=10):
        self.max_workers = max_workers
    
    def check_http(self, url, timeout=5):
        """HTTPチェック"""
        try:
            start = time.time()
            response = requests.get(url, timeout=timeout)
            elapsed = time.time() - start
            
            return {
                "url": url,
                "status": "🟢 オンライン",
                "code": response.status_code,
                "time": f"{elapsed:.2f}s",
                "success": True
            }
        except requests.RequestException:
            return {"url": url, "status": "🔴 オフライン", "success": False}
    
    def check_port(self, host, port, timeout=3):
        """ポートチェック"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            return {
                "host": host,
                "port": port,
                "status": "🟢 オープン" if result == 0 else "🔴 クローズド",
                "success": result == 0
            }
        except Exception:
            return {"host": host, "port": port, "status": "🔴 エラー", "success": False}
    
    def monitor_services(self):
        """サービス監視"""
        services = [
            {"name": "Trinity GPU API", "url": "http://localhost:5009/trinity/health"},
            {"name": "Mana Screen Sharing", "url": "http://localhost:5008/health"},
            {"name": "Turbo Dashboard", "url": "http://localhost:8888/api/status"},
        ]
        
        ports = [
            {"name": "SSH", "host": "localhost", "port": 22},
            {"name": "HTTP", "host": "localhost", "port": 80},
            {"name": "HTTPS", "host": "localhost", "port": 443},
        ]
        
        print("=" * 60)
        print("🌐 サービス監視")
        print("=" * 60)
        
        # HTTP監視
        print("\n🌐 Webサービス:")
        tasks = [(self.check_http, (s["url"],), {}) for s in services]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(func, *args, **kwargs) for func, args, kwargs in tasks]
            
            for future, service in zip(concurrent.futures.as_completed(futures), services):
                result = future.result()
                print(f"{result['status']} {service['name']}")
                if result.get("success"):
                    print(f"    応答時間: {result['time']}")
        
        # ポート監視
        print("\n🔌 ポート:")
        tasks = [(self.check_port, (p["host"], p["port"]), {}) for p in ports]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(func, *args, **kwargs) for func, args, kwargs in tasks]
            
            for future, port_info in zip(concurrent.futures.as_completed(futures), ports):
                result = future.result()
                print(f"{result['status']} {port_info['name']} (:{port_info['port']})")
        
        print("=" * 60)

if __name__ == "__main__":
    monitor = NetworkMonitor()
    monitor.monitor_services()
