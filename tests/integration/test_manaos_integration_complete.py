#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 ManaOS統合システム完全テストスクリプト
全統合システムの動作確認とパフォーマンステスト
"""

import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Windowsでの文字エンコーディング問題を回避
if sys.platform == "win32":
    import io
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 統合システムのインポート
try:
    from manaos_integration_orchestrator import ManaOSIntegrationOrchestrator
    ORCHESTRATOR_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ ManaOS Integration Orchestratorのインポートに失敗: {e}")
    ORCHESTRATOR_AVAILABLE = False

try:
    from manaos_service_bridge import ManaOSServiceBridge
    SERVICE_BRIDGE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ ManaOS Service Bridgeのインポートに失敗: {e}")
    SERVICE_BRIDGE_AVAILABLE = False

try:
    from manaos_complete_integration import ManaOSCompleteIntegration
    COMPLETE_INTEGRATION_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ ManaOS Complete Integrationのインポートに失敗: {e}")
    COMPLETE_INTEGRATION_AVAILABLE = False

try:
    from unified_api_server_optimizer import get_optimizer
    OPTIMIZER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Unified API Server Optimizerのインポートに失敗: {e}")
    OPTIMIZER_AVAILABLE = False


def print_section(title: str):
    """セクションタイトルを表示"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(test_name: str, success: bool, details: str = ""):
    """テスト結果を表示"""
    icon = "✅" if success else "❌"
    print(f"{icon} {test_name}")
    if details:
        print(f"   {details}")


def test_orchestrator():
    """統合オーケストレーターのテスト"""
    print_section("統合オーケストレーター テスト")
    
    if not ORCHESTRATOR_AVAILABLE:
        print_result("統合オーケストレーター", False, "モジュールが利用できません")
        return False
    
    try:
        orchestrator = ManaOSIntegrationOrchestrator()
        print_result("統合オーケストレーター初期化", True)
        
        # 全サービスの状態をチェック
        print("\n全サービスの状態をチェック中...")
        services_status = orchestrator.check_all_services(use_parallel=True)
        
        summary = services_status.get("summary", {})
        print_result(
            "サービス状態チェック",
            True,
            f"総サービス数: {summary.get('total_services', 0)}, "
            f"利用可能: {summary.get('available_services', 0)}, "
            f"可用性: {summary.get('availability_rate', 0)*100:.1f}%"
        )
        
        # マナOSサービスの状態を表示
        print("\nマナOSサービス:")
        for service_id, service_status in services_status.get("manaos_services", {}).items():
            status_icon = "✅" if service_status.get("available", False) else "❌"
            print(f"  {status_icon} {service_status.get('name', service_id)} (ポート {service_status.get('port', 'N/A')})")
        
        # 統合システムの状態を表示
        print("\n統合システム:")
        for service_id, service_status in services_status.get("integration_services", {}).items():
            status_icon = "✅" if service_status.get("available", False) else "❌"
            print(f"  {status_icon} {service_status.get('name', service_id)} (ポート {service_status.get('port', 'N/A')})")
        
        # 包括的な状態を取得
        print("\n包括的な状態を取得中...")
        comprehensive_status = orchestrator.get_comprehensive_status()
        print_result("包括的な状態取得", True)
        
        return True
    except Exception as e:
        print_result("統合オーケストレーター", False, f"エラー: {e}")
        return False


def test_service_bridge():
    """サービスブリッジのテスト"""
    print_section("サービスブリッジ テスト")
    
    if not SERVICE_BRIDGE_AVAILABLE:
        print_result("サービスブリッジ", False, "モジュールが利用できません")
        return False
    
    try:
        bridge = ManaOSServiceBridge()
        print_result("サービスブリッジ初期化", True)
        
        # マナOSサービスの状態をチェック
        print("\nマナOSサービスの状態をチェック中...")
        services = bridge.check_manaos_services(use_parallel=True)
        
        available_count = sum(1 for s in services.values() if s)
        total_count = len(services)
        print_result(
            "マナOSサービスチェック",
            True,
            f"利用可能: {available_count}/{total_count}"
        )
        
        # 統合状態を取得
        print("\n統合状態を取得中...")
        integration_status = bridge.get_integration_status()
        print_result("統合状態取得", True)
        
        return True
    except Exception as e:
        print_result("サービスブリッジ", False, f"エラー: {e}")
        return False


def test_complete_integration():
    """完全統合システムのテスト"""
    print_section("完全統合システム テスト")
    
    if not COMPLETE_INTEGRATION_AVAILABLE:
        print_result("完全統合システム", False, "モジュールが利用できません")
        return False
    
    try:
        integration = ManaOSCompleteIntegration()
        print_result("完全統合システム初期化", True)
        
        # 完全統合状態を取得
        print("\n完全統合状態を取得中...")
        complete_status = integration.get_complete_status()
        print_result("完全統合状態取得", True)
        
        # 状態を表示
        print("\n統合状態:")
        print(f"  コア: {complete_status.get('core', {}).get('status', 'N/A')}")
        
        memory_learning = complete_status.get("memory_learning", {})
        if memory_learning:
            print(f"  記憶・学習系: {len(memory_learning)}個のシステム")
        
        personality_autonomy = complete_status.get("personality_autonomy_secretary", {})
        if personality_autonomy:
            print(f"  人格・自律・秘書系: 統合済み")
        
        return True
    except Exception as e:
        print_result("完全統合システム", False, f"エラー: {e}")
        return False


def test_optimizer():
    """最適化システムのテスト"""
    print_section("最適化システム テスト")
    
    if not OPTIMIZER_AVAILABLE:
        print_result("最適化システム", False, "モジュールが利用できません")
        return False
    
    try:
        optimizer = get_optimizer()
        print_result("最適化システム初期化", True)
        
        # キャッシュ統計を取得
        print("\nキャッシュ統計を取得中...")
        cache_stats = optimizer.get_cache_stats()
        print_result("キャッシュ統計取得", True)
        if cache_stats.get("available"):
            print(f"  キャッシュシステム: 利用可能")
        
        # パフォーマンス統計を取得
        print("\nパフォーマンス統計を取得中...")
        perf_stats = optimizer.get_performance_stats()
        print_result("パフォーマンス統計取得", True)
        
        return True
    except Exception as e:
        print_result("最適化システム", False, f"エラー: {e}")
        return False


def test_performance():
    """パフォーマンステスト"""
    print_section("パフォーマンステスト")
    
    if not ORCHESTRATOR_AVAILABLE:
        print_result("パフォーマンステスト", False, "統合オーケストレーターが利用できません")
        return False
    
    try:
        orchestrator = ManaOSIntegrationOrchestrator()
        
        # 並列チェックのパフォーマンステスト
        print("\n並列チェックのパフォーマンステスト...")
        start_time = time.time()
        services_status = orchestrator.check_all_services(use_parallel=True)
        parallel_time = time.time() - start_time
        
        print_result(
            "並列チェック",
            True,
            f"実行時間: {parallel_time:.3f}秒"
        )
        
        # 順次チェックのパフォーマンステスト
        print("\n順次チェックのパフォーマンステスト...")
        start_time = time.time()
        services_status = orchestrator.check_all_services(use_parallel=False)
        sequential_time = time.time() - start_time
        
        print_result(
            "順次チェック",
            True,
            f"実行時間: {sequential_time:.3f}秒"
        )
        
        # パフォーマンス改善率を計算
        if sequential_time > 0:
            improvement = ((sequential_time - parallel_time) / sequential_time) * 100
            print(f"\nパフォーマンス改善: {improvement:.1f}% 高速化")
        
        return True
    except Exception as e:
        print_result("パフォーマンステスト", False, f"エラー: {e}")
        return False


def main():
    """メイン関数"""
    print("=" * 60)
    print("  ManaOS統合システム完全テスト")
    print("=" * 60)
    print(f"テスト開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "orchestrator": test_orchestrator(),
        "service_bridge": test_service_bridge(),
        "complete_integration": test_complete_integration(),
        "optimizer": test_optimizer(),
        "performance": test_performance()
    }
    
    # 結果サマリー
    print_section("テスト結果サマリー")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)
    failed_tests = total_tests - passed_tests
    
    print(f"総テスト数: {total_tests}")
    print(f"成功: {passed_tests}")
    print(f"失敗: {failed_tests}")
    print(f"成功率: {passed_tests/total_tests*100:.1f}%")
    
    print("\n詳細:")
    for test_name, success in results.items():
        icon = "✅" if success else "❌"
        print(f"  {icon} {test_name}")
    
    # 結果をJSONファイルに保存
    result_file = Path("test_results.json")
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": passed_tests/total_tests*100
            }
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n結果を保存しました: {result_file}")
    
    return passed_tests == total_tests










