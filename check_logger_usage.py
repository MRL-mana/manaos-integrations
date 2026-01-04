#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS ログ管理使用状況確認スクリプト
"""

from pathlib import Path

# 主要サービスリスト
SERVICES = [
    "intent_router.py",
    "task_planner.py",
    "task_critic.py",
    "rag_memory_enhanced.py",
    "task_queue_system.py",
    "ui_operations_api.py",
    "unified_orchestrator.py",
    "task_executor_enhanced.py",
    "portal_integration_api.py",
    "content_generation_loop.py",
    "llm_optimization.py",
    "system_status_api.py",
    "crash_snapshot.py",
    "slack_integration.py",
    "web_voice_interface.py",
    "portal_voice_integration.py",
    "revenue_tracker.py",
    "product_automation.py",
    "payment_integration.py",
    "ssot_api.py",
    "unified_api_server.py"
]

def check_logger_usage():
    """ログ管理モジュールの使用状況を確認"""
    script_dir = Path(__file__).parent
    
    results = {
        "using_manaos_logger": [],
        "using_unified_logger": [],
        "using_standard_logging": [],
        "not_using": [],
        "not_found": []
    }
    
    for service in SERVICES:
        service_path = script_dir / service
        
        if not service_path.exists():
            results["not_found"].append(service)
            continue
        
        try:
            with open(service_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # ログ管理モジュールの使用確認
            if "manaos_logger" in content or "ManaOSLogger" in content:
                results["using_manaos_logger"].append(service)
            elif "unified_logger" in content or "UnifiedLogger" in content:
                results["using_unified_logger"].append(service)
            elif "import logging" in content or "from logging import" in content:
                results["using_standard_logging"].append(service)
            else:
                results["not_using"].append(service)
        except Exception as e:
            print(f"エラー: {service} の読み込みに失敗: {e}")
            results["not_found"].append(service)
    
    # 結果表示
    print("=" * 60)
    print("ManaOS ログ管理使用状況")
    print("=" * 60)
    
    print(f"\n[OK] manaos_logger使用: {len(results['using_manaos_logger'])}/{len(SERVICES)}")
    for service in results["using_manaos_logger"]:
        print(f"  - {service}")
    
    print(f"\n[OK] unified_logger使用: {len(results['using_unified_logger'])}/{len(SERVICES)}")
    for service in results["using_unified_logger"]:
        print(f"  - {service}")
    
    print(f"\n[WARN] 標準logging使用: {len(results['using_standard_logging'])}/{len(SERVICES)}")
    for service in results["using_standard_logging"]:
        print(f"  - {service}")
    
    print(f"\n[NG] ログ未使用: {len(results['not_using'])}/{len(SERVICES)}")
    for service in results["not_using"]:
        print(f"  - {service}")
    
    if results["not_found"]:
        print(f"\n[WARN] ファイル未検出: {len(results['not_found'])}")
        for service in results["not_found"]:
            print(f"  - {service}")
    
    print("\n" + "=" * 60)
    total_using = len(results['using_manaos_logger']) + len(results['using_unified_logger'])
    print(f"統一ロガー使用率: {total_using}/{len(SERVICES)} ({total_using/len(SERVICES)*100:.1f}%)")
    print("=" * 60)
    
    return results

if __name__ == "__main__":
    check_logger_usage()

