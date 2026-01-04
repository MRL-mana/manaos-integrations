#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS クイック動作確認スクリプト
"""

import httpx
import json
from typing import Dict, Any

SERVICES = [
    {"name": "Intent Router", "port": 5100},
    {"name": "Task Planner", "port": 5101},
    {"name": "Task Critic", "port": 5102},
    {"name": "RAG Memory", "port": 5103},
    {"name": "Task Queue", "port": 5104},
    {"name": "UI Operations", "port": 5105},
    {"name": "Unified Orchestrator", "port": 5106},
    {"name": "Executor Enhanced", "port": 5107},
    {"name": "Portal Integration", "port": 5108},
    {"name": "Content Generation", "port": 5109},
    {"name": "LLM Optimization", "port": 5110},
    {"name": "System Status API", "port": 5112},
    {"name": "Crash Snapshot", "port": 5113},
    {"name": "Slack Integration", "port": 5114},
    {"name": "Web Voice Interface", "port": 5115},
    {"name": "Portal Voice Integration", "port": 5116},
    {"name": "Revenue Tracker", "port": 5117},
    {"name": "Product Automation", "port": 5118},
    {"name": "Payment Integration", "port": 5119},
]

def check_service(port: int, timeout: float = 2.0) -> Dict[str, Any]:
    """サービスヘルスチェック"""
    try:
        response = httpx.get(
            f"http://localhost:{port}/health",
            timeout=timeout
        )
        if response.status_code == 200:
            return {
                "status": "healthy",
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "data": response.json()
            }
        else:
            return {
                "status": "unhealthy",
                "response_time_ms": None,
                "error": f"HTTP {response.status_code}"
            }
    except httpx.ConnectError:
        return {
            "status": "down",
            "response_time_ms": None,
            "error": "Connection refused"
        }
    except httpx.TimeoutException:
        return {
            "status": "timeout",
            "response_time_ms": None,
            "error": "Request timeout"
        }
    except Exception as e:
        return {
            "status": "error",
            "response_time_ms": None,
            "error": str(e)
        }

def main():
    print("\n" + "=" * 80)
    print("ManaOS クイック動作確認")
    print("=" * 80 + "\n")
    
    results = []
    healthy_count = 0
    
    for service in SERVICES:
        print(f"Checking {service['name']} (Port: {service['port']})...", end=" ")
        result = check_service(service["port"])
        results.append({
            "name": service["name"],
            "port": service["port"],
            **result
        })
        
        if result["status"] == "healthy":
            print(f"[OK] ({result['response_time_ms']:.0f}ms)")
            healthy_count += 1
        else:
            print(f"[{result['status'].upper()}]")
            if result.get("error"):
                print(f"   Error: {result['error']}")
    
    print("\n" + "=" * 80)
    print("Result Summary")
    print("=" * 80)
    print(f"Total Services: {len(SERVICES)}")
    print(f"Healthy: {healthy_count}")
    print(f"Unhealthy: {len(SERVICES) - healthy_count}")
    print(f"Success Rate: {healthy_count / len(SERVICES) * 100:.1f}%")
    
    if healthy_count == len(SERVICES):
        print("\n[SUCCESS] All services are running!")
    elif healthy_count > 0:
        print(f"\n[WARNING] {len(SERVICES) - healthy_count} services are not running")
        print("   Start: .\\start_all_services.ps1")
    else:
        print("\n[ERROR] No services are running")
        print("   Start: .\\start_all_services.ps1")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

