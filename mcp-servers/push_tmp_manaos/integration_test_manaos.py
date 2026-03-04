"""
ManaOS統合テストスクリプト
既存ManaOSサービスとの統合と動作確認
"""

import sys
import io
import os
import requests
import json
from pathlib import Path
from datetime import datetime

try:
    from manaos_integrations._paths import UNIFIED_API_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import UNIFIED_API_PORT  # type: ignore
    except Exception:  # pragma: no cover
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9502"))

# Windowsでの文字エンコーディング問題を回避
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ManaOS既存サービスのエンドポイント
MANAOS_SERVICES = {
    "command_hub": os.getenv("COMMAND_HUB_URL", "http://127.0.0.1:9404"),
    "enhanced_api": os.getenv("ENHANCED_API_URL", "http://127.0.0.1:9406"),
    "monitoring": os.getenv("MONITORING_URL", "http://127.0.0.1:9407"),
    "ocr_api": os.getenv("OCR_API_URL", "http://127.0.0.1:9409"),
    "gallery_api": os.getenv("GALLERY_API_URL", "http://127.0.0.1:5559"),
    "task_executor": os.getenv("TASK_EXECUTOR_URL", "http://127.0.0.1:5176"),
    "unified_portal": os.getenv("UNIFIED_PORTAL_URL", "http://127.0.0.1:9408")
}

# 統合システムのエンドポイント
INTEGRATION_SERVICES = {
    "unified_api": os.getenv("MANAOS_INTEGRATION_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}"),
    "realtime_dashboard": os.getenv("REALTIME_DASHBOARD_URL", "http://127.0.0.1:9600"),
    "master_control": os.getenv("MASTER_CONTROL_URL", "http://127.0.0.1:9700")
}


def check_service(url: str, timeout: int = 5) -> tuple[bool, str]:
    """
    サービスの状態をチェック
    
    Args:
        url: サービスURL
        timeout: タイムアウト（秒）
        
    Returns:
        (利用可能かどうか, ステータスメッセージ)
    """
    try:
        response = requests.get(f"{url}/health", timeout=timeout)
        if response.status_code == 200:
            return True, "オンライン"
        else:
            return False, f"HTTP {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "接続不可"
    except requests.exceptions.Timeout:
        return False, "タイムアウト"
    except Exception as e:
        return False, f"エラー: {str(e)[:50]}"


def test_manaos_integration():
    """ManaOS既存サービスとの統合テスト"""
    print("=" * 70)
    print("ManaOS既存サービス統合テスト")
    print("=" * 70)
    print()
    
    results = {}
    
    for service_name, url in MANAOS_SERVICES.items():
        print(f"チェック中: {service_name} ({url})...", end=" ")
        available, status = check_service(url)
        results[service_name] = {
            "url": url,
            "available": available,
            "status": status
        }
        
        if available:
            print(f"✓ {status}")
        else:
            print(f"✗ {status}")
    
    return results


def test_integration_systems():
    """統合システムのテスト"""
    print("\n" + "=" * 70)
    print("統合システムテスト")
    print("=" * 70)
    print()
    
    results = {}
    
    for service_name, url in INTEGRATION_SERVICES.items():
        print(f"チェック中: {service_name} ({url})...", end=" ")
        available, status = check_service(url)
        results[service_name] = {
            "url": url,
            "available": available,
            "status": status
        }
        
        if available:
            print(f"✓ {status}")
        else:
            print(f"✗ {status}")
    
    return results


def test_integration_modules():
    """統合モジュールのインポートテスト"""
    print("\n" + "=" * 70)
    print("統合モジュールインポートテスト")
    print("=" * 70)
    print()
    
    modules = [
        "comfyui_integration",
        "google_drive_integration",
        "civitai_integration",
        "langchain_integration",
        "mem0_integration",
        "obsidian_integration",
        "crewai_integration",
        "workflow_automation",
        "ai_agent_autonomous",
        "predictive_maintenance",
        "auto_optimization",
        "learning_system",
        "multimodal_integration",
        "distributed_execution",
        "security_monitor",
        "notification_system",
        "backup_recovery",
        "performance_analytics",
        "cost_optimization",
        "streaming_processing",
        "batch_processing",
        "database_integration",
        "cloud_integration"
    ]
    
    results = {}
    
    for module_name in modules:
        print(f"インポート中: {module_name}...", end=" ")
        try:
            __import__(module_name)
            results[module_name] = {"status": "成功", "error": None}
            print("[OK]")
        except ImportError as e:
            results[module_name] = {"status": "失敗", "error": str(e)}
            print(f"[NG] {str(e)[:50]}")
        except Exception as e:
            results[module_name] = {"status": "エラー", "error": str(e)}
            print(f"[NG] {str(e)[:50]}")
    
    return results


def test_manaos_service_bridge():
    """ManaOSサービスブリッジのテスト"""
    print("\n" + "=" * 70)
    print("ManaOSサービスブリッジテスト")
    print("=" * 70)
    print()
    
    try:
        from manaos_service_bridge import ManaOSServiceBridge
        
        bridge = ManaOSServiceBridge()
        status = bridge.get_integration_status()
        
        print("統合状態:")
        print(json.dumps(status, indent=2, ensure_ascii=False))
        
        return {"status": "成功", "data": status}
    except Exception as e:
        print(f"[NG] エラー: {e}")
        return {"status": "失敗", "error": str(e)}


def test_ultimate_integration():
    """究極統合システムのテスト"""
    print("\n" + "=" * 70)
    print("究極統合システムテスト")
    print("=" * 70)
    print()
    
    try:
        from ultimate_integration import UltimateIntegration
        
        system = UltimateIntegration()
        status = system.get_comprehensive_status()
        
        print("包括的な状態:")
        print(f"  基本統合システム: {len(status.get('integrations', {}))}個")
        print(f"  高度機能: {len(status.get('advanced_features', {}))}個")
        
        online_basic = sum(1 for v in status.get('integrations', {}).values() if v)
        print(f"  オンライン基本システム: {online_basic}個")
        
        return {"status": "成功", "data": status}
    except Exception as e:
        print(f"[NG] エラー: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "失敗", "error": str(e)}


def generate_test_report(
    manaos_results: dict,
    integration_results: dict,
    module_results: dict,
    bridge_result: dict,
    ultimate_result: dict
):
    """テストレポートを生成"""
    report_path = Path("Reports") / f"ManaOS統合テストレポート_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    report_content = f"""# ManaOS統合テストレポート

**作成日**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 テスト結果サマリー

### ManaOS既存サービス

"""
    
    online_count = sum(1 for r in manaos_results.values() if r["available"])
    total_count = len(manaos_results)
    
    report_content += f"**オンライン**: {online_count}/{total_count}サービス\n\n"
    
    for service_name, result in manaos_results.items():
        status_icon = "✓" if result["available"] else "✗"
        report_content += f"- {status_icon} **{service_name}** ({result['url']}): {result['status']}\n"
    
    report_content += "\n### 統合システム\n\n"
    
    online_integration = sum(1 for r in integration_results.values() if r["available"])
    total_integration = len(integration_results)
    
    report_content += f"**オンライン**: {online_integration}/{total_integration}サービス\n\n"
    
    for service_name, result in integration_results.items():
        status_icon = "✓" if result["available"] else "✗"
        report_content += f"- {status_icon} **{service_name}** ({result['url']}): {result['status']}\n"
    
    report_content += "\n### 統合モジュール\n\n"
    
    success_modules = sum(1 for r in module_results.values() if r["status"] == "成功")
    total_modules = len(module_results)
    
    report_content += f"**成功**: {success_modules}/{total_modules}モジュール\n\n"
    
    for module_name, result in module_results.items():
        status_icon = "✓" if result["status"] == "成功" else "✗"
        report_content += f"- {status_icon} **{module_name}**: {result['status']}"
        if result.get("error"):
            error_msg = result['error'][:50].replace('\n', ' ')
            report_content += f" ({error_msg})"
        report_content += "\n"
    
    report_content += "\n### ManaOSサービスブリッジ\n\n"
    report_content += f"**状態**: {bridge_result.get('status', '不明')}\n\n"
    
    report_content += "\n### 究極統合システム\n\n"
    report_content += f"**状態**: {ultimate_result.get('status', '不明')}\n\n"
    
    report_content += "\n## 📝 まとめ\n\n"
    
    total_online = online_count + online_integration
    total_services = total_count + total_integration
    
    report_content += f"""
- **ManaOS既存サービス**: {online_count}/{total_count}オンライン
- **統合システム**: {online_integration}/{total_integration}オンライン
- **統合モジュール**: {success_modules}/{total_modules}成功
- **総合**: {total_online}/{total_services}サービスオンライン

## 🎯 推奨アクション

"""
    
    if online_count < total_count:
        report_content += "1. ManaOS既存サービスを起動してください\n"
    
    if online_integration < total_integration:
        report_content += "2. 統合システムを起動してください\n"
    
    if success_modules < total_modules:
        report_content += "3. 不足している依存関係をインストールしてください\n"
    
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_content, encoding='utf-8')
    
    print(f"\nテストレポートを保存しました: {report_path}")


def main():
    """メイン関数"""
    print("=" * 70)
    print("ManaOS統合テスト - 完全動作確認")
    print("=" * 70)
    print()
    
    # 1. ManaOS既存サービステスト
    manaos_results = test_manaos_integration()
    
    # 2. 統合システムテスト
    integration_results = test_integration_systems()
    
    # 3. 統合モジュールテスト
    module_results = test_integration_modules()
    
    # 4. ManaOSサービスブリッジテスト
    bridge_result = test_manaos_service_bridge()
    
    # 5. 究極統合システムテスト
    ultimate_result = test_ultimate_integration()
    
    # 6. レポート生成
    generate_test_report(
        manaos_results,
        integration_results,
        module_results,
        bridge_result,
        ultimate_result
    )
    
    # 7. サマリー表示
    print("\n" + "=" * 70)
    print("テスト結果サマリー")
    print("=" * 70)
    
    online_manaos = sum(1 for r in manaos_results.values() if r["available"])
    online_integration = sum(1 for r in integration_results.values() if r["available"])
    success_modules = sum(1 for r in module_results.values() if r["status"] == "成功")
    
    print(f"\nManaOS既存サービス: {online_manaos}/{len(manaos_results)}オンライン")
    print(f"統合システム: {online_integration}/{len(integration_results)}オンライン")
    print(f"統合モジュール: {success_modules}/{len(module_results)}成功")
    
    if bridge_result.get("status") == "成功":
        print("ManaOSサービスブリッジ: [OK] 動作中")
    else:
        print(f"ManaOSサービスブリッジ: [NG] {bridge_result.get('error', '不明')}")
    
    if ultimate_result.get("status") == "成功":
        print("究極統合システム: [OK] 動作中")
    else:
        print(f"究極統合システム: [NG] {ultimate_result.get('error', '不明')}")
    
    print("\nテスト完了！")


if __name__ == "__main__":
    main()

