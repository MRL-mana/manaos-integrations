#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 ManaOS 新システム一括起動スクリプト
すべての新システムを起動・統合
"""

import os
import sys
import asyncio
from pathlib import Path

# Windows環境でのエンコーディング問題を回避
if sys.platform == "win32":
    import io
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from manaos_logger import get_logger

logger = get_logger(__name__)


async def initialize_all_systems():
    """すべての新システムを初期化"""
    systems_status = {}
    
    print("=" * 70)
    print("🚀 ManaOS 新システム一括起動")
    print("=" * 70)
    print()
    
    # 1. GPU最適化システム
    print("[1/9] GPU最適化システムを初期化中...")
    try:
        from gpu_optimizer import get_gpu_optimizer
        optimizer = get_gpu_optimizer()
        await optimizer.initialize()
        systems_status["gpu_optimizer"] = "✅ 起動済み"
        print("   ✅ GPU最適化システム起動完了")
    except Exception as e:
        systems_status["gpu_optimizer"] = f"❌ エラー: {e}"
        print(f"   ❌ GPU最適化システム起動エラー: {e}")
    
    # 2. GPU並列実行システム
    print("[2/9] GPU並列実行システムを初期化中...")
    try:
        from gpu_parallel_executor import get_parallel_executor
        executor = get_parallel_executor(max_parallel=4)
        systems_status["gpu_parallel_executor"] = "✅ 起動済み"
        print("   ✅ GPU並列実行システム起動完了")
    except Exception as e:
        systems_status["gpu_parallel_executor"] = f"❌ エラー: {e}"
        print(f"   ❌ GPU並列実行システム起動エラー: {e}")
    
    # 3. Prometheusメトリクス
    print("[3/9] Prometheusメトリクスを初期化中...")
    try:
        from prometheus_integration import get_prometheus_metrics
        metrics = get_prometheus_metrics()
        if metrics:
            systems_status["prometheus_metrics"] = "✅ 起動済み"
            print("   ✅ Prometheusメトリクス起動完了")
        else:
            systems_status["prometheus_metrics"] = "⚠️ 利用不可（prometheus_client未インストール）"
            print("   ⚠️ Prometheusメトリクスは利用できません（prometheus_client未インストール）")
    except Exception as e:
        systems_status["prometheus_metrics"] = f"❌ エラー: {e}"
        print(f"   ❌ Prometheusメトリクス起動エラー: {e}")
    
    # 4. アラートシステム
    print("[4/9] アラートシステムを初期化中...")
    try:
        from alert_system import get_alert_system
        alert_system = get_alert_system()
        systems_status["alert_system"] = "✅ 起動済み"
        print("   ✅ アラートシステム起動完了")
    except Exception as e:
        systems_status["alert_system"] = f"❌ エラー: {e}"
        print(f"   ❌ アラートシステム起動エラー: {e}")
    
    # 5. パフォーマンス監視
    print("[5/9] パフォーマンス監視を初期化中...")
    try:
        from performance_monitor import get_performance_monitor
        monitor = get_performance_monitor()
        await monitor.start_monitoring(interval=10)
        systems_status["performance_monitor"] = "✅ 起動済み（監視中）"
        print("   ✅ パフォーマンス監視起動完了（10秒間隔で監視中）")
    except Exception as e:
        systems_status["performance_monitor"] = f"❌ エラー: {e}"
        print(f"   ❌ パフォーマンス監視起動エラー: {e}")
    
    # 6. 自動バックアップシステム
    print("[6/9] 自動バックアップシステムを初期化中...")
    try:
        from auto_backup_system import get_backup_system
        backup_system = get_backup_system()
        backup_system.start_scheduled_backups("02:00")
        systems_status["backup_system"] = "✅ 起動済み（毎日02:00にバックアップ）"
        print("   ✅ 自動バックアップシステム起動完了（毎日02:00にバックアップ）")
    except Exception as e:
        systems_status["backup_system"] = f"❌ エラー: {e}"
        print(f"   ❌ 自動バックアップシステム起動エラー: {e}")
    
    # 7. インテリジェントキャッシュ
    print("[7/9] インテリジェントキャッシュを初期化中...")
    try:
        from intelligent_cache import get_cache
        cache = get_cache(max_size=1000, default_ttl=3600)
        systems_status["cache"] = "✅ 起動済み"
        print("   ✅ インテリジェントキャッシュ起動完了")
    except Exception as e:
        systems_status["cache"] = f"❌ エラー: {e}"
        print(f"   ❌ インテリジェントキャッシュ起動エラー: {e}")
    
    # 8. 設定検証システム
    print("[8/9] 設定検証システムを初期化中...")
    try:
        from config_validator_enhanced import get_config_validator
        validator = get_config_validator()
        validation_results = validator.validate_all_configs()
        error_count = sum(1 for _, (is_valid, _) in validation_results.items() if not is_valid)
        if error_count == 0:
            systems_status["config_validator"] = "✅ 起動済み（すべての設定ファイルが正常）"
            print("   ✅ 設定検証システム起動完了（すべての設定ファイルが正常）")
        else:
            systems_status["config_validator"] = f"⚠️ 起動済み（{error_count}個の設定ファイルにエラー）"
            print(f"   ⚠️ 設定検証システム起動完了（{error_count}個の設定ファイルにエラー）")
    except Exception as e:
        systems_status["config_validator"] = f"❌ エラー: {e}"
        print(f"   ❌ 設定検証システム起動エラー: {e}")
    
    # 9. メトリクス収集システム
    print("[9/9] メトリクス収集システムを初期化中...")
    try:
        from metrics_collector import get_metrics_collector
        collector = get_metrics_collector()
        collector.collect_system_metrics()
        systems_status["metrics_collector"] = "✅ 起動済み"
        print("   ✅ メトリクス収集システム起動完了")
    except Exception as e:
        systems_status["metrics_collector"] = f"❌ エラー: {e}"
        print(f"   ❌ メトリクス収集システム起動エラー: {e}")
    
    print()
    print("=" * 70)
    print("📊 起動状況サマリー")
    print("=" * 70)
    
    for system_name, status in systems_status.items():
        print(f"  {system_name}: {status}")
    
    print()
    print("=" * 70)
    print("✅ 新システムの起動が完了しました")
    print("=" * 70)
    
    return systems_status


if __name__ == "__main__":
    try:
        asyncio.run(initialize_all_systems())
    except KeyboardInterrupt:
        print("\n\n起動を中断しました")
    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()








