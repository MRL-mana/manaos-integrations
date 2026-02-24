#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS 設定ファイル検証使用状況確認スクリプト
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

def check_config_validator_usage():
    """設定ファイル検証モジュールの使用状況を確認"""
    script_dir = Path(__file__).parent
    
    results = {
        "using": [],
        "not_using": [],
        "not_found": [],
        "has_config_file": []
    }
    
    for service in SERVICES:
        service_path = script_dir / service
        
        if not service_path.exists():
            results["not_found"].append(service)
            continue
        
        try:
            with open(service_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 設定ファイル検証モジュールの使用確認
            if "manaos_config_validator" in content or "ConfigValidator" in content:
                results["using"].append(service)
            else:
                results["not_using"].append(service)
            
            # 設定ファイルの存在確認
            service_name = service.replace('.py', '')
            config_files = [
                f"{service_name}_config.json",
                f"{service_name}.json"
            ]
            for config_file in config_files:
                if (script_dir / config_file).exists():
                    results["has_config_file"].append((service, config_file))
                    break
        except Exception as e:
            print(f"エラー: {service} の読み込みに失敗: {e}")
            results["not_found"].append(service)
    
    # 結果表示
    print("=" * 60)
    print("ManaOS 設定ファイル検証使用状況")
    print("=" * 60)
    
    print(f"\n[OK] 使用中: {len(results['using'])}/{len(SERVICES)}")
    for service in results["using"]:
        print(f"  - {service}")
    
    print(f"\n[NG] 未使用: {len(results['not_using'])}/{len(SERVICES)}")
    for service in results["not_using"]:
        print(f"  - {service}")
    
    if results["not_found"]:
        print(f"\n[WARN] ファイル未検出: {len(results['not_found'])}")
        for service in results["not_found"]:
            print(f"  - {service}")
    
    print(f"\n[INFO] 設定ファイルあり: {len(results['has_config_file'])}")
    for service, config_file in results["has_config_file"]:
        print(f"  - {service}: {config_file}")
    
    print("\n" + "=" * 60)
    print(f"使用率: {len(results['using'])}/{len(SERVICES)} ({len(results['using'])/len(SERVICES)*100:.1f}%)")
    print("=" * 60)
    
    return results

if __name__ == "__main__":
    check_config_validator_usage()

