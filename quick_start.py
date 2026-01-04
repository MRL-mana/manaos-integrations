"""
ManaOS統合システム - クイックスタートスクリプト
簡単に統合システムを使い始めるためのヘルパースクリプト
"""

import sys
from pathlib import Path

# モジュールパスを追加
sys.path.insert(0, str(Path(__file__).parent))

from unified_api_server import initialize_integrations, app
from workflow_automation import WorkflowAutomation, create_default_workflows
from enhanced_civitai_downloader import EnhancedCivitaiDownloader
from manaos_service_bridge import ManaOSServiceBridge


def print_banner():
    """バナーを表示"""
    print("=" * 60)
    print("ManaOS統合システム - クイックスタート")
    print("=" * 60)
    print()


def print_menu():
    """メニューを表示"""
    print("利用可能な機能:")
    print("  1. 統合APIサーバーを起動")
    print("  2. ワークフロー自動化をテスト")
    print("  3. 拡張CivitAIダウンローダーを使用")
    print("  4. ManaOSサービスブリッジをテスト")
    print("  5. すべての統合システムをテスト")
    print("  6. 統合状態を確認")
    print("  0. 終了")
    print()


def start_api_server():
    """統合APIサーバーを起動"""
    print("\n統合APIサーバーを起動中...")
    print("ブラウザで http://localhost:9500/health にアクセスしてください")
    print("Ctrl+Cで停止")
    print()
    
    initialize_integrations()
    app.run(host="0.0.0.0", port=9500, debug=True)


def test_workflow_automation():
    """ワークフロー自動化をテスト"""
    print("\nワークフロー自動化をテスト中...")
    
    automation = WorkflowAutomation()
    create_default_workflows(automation)
    
    print(f"登録済みワークフロー: {list(automation.workflows.keys())}")
    
    # サンプルワークフローを実行
    if "generate_and_backup" in automation.workflows:
        print("\n画像生成ワークフローを実行中...")
        result = automation.execute_workflow("generate_and_backup", {
            "prompt": "a beautiful landscape",
            "width": 512,
            "height": 512
        })
        print(f"結果: {result}")


def use_enhanced_downloader():
    """拡張CivitAIダウンローダーを使用"""
    print("\n拡張CivitAIダウンローダー")
    print("=" * 60)
    
    model_id = input("モデルIDを入力（Enterでスキップ）: ").strip()
    search_query = input("検索クエリを入力（Enterでスキップ）: ").strip()
    
    downloader = EnhancedCivitaiDownloader()
    
    if model_id:
        result = downloader.download_with_enhancements(
            model_id=model_id,
            backup_to_drive=False,
            create_note=True,
            save_to_memory=True
        )
        print(f"\n結果: {result}")
    elif search_query:
        results = downloader.search_and_download(query=search_query)
        print(f"\nダウンロード完了: {len(results)}件")
    else:
        print("モデルIDまたは検索クエリを入力してください。")


def test_service_bridge():
    """ManaOSサービスブリッジをテスト"""
    print("\nManaOSサービスブリッジをテスト中...")
    
    bridge = ManaOSServiceBridge()
    status = bridge.get_integration_status()
    
    print("\n統合状態:")
    import json
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    # 画像生成ワークフローテスト
    print("\n画像生成ワークフローを実行中...")
    result = bridge.integrate_image_generation_workflow(
        prompt="a beautiful landscape"
    )
    print(f"結果: {result}")


def test_all_integrations():
    """すべての統合システムをテスト"""
    print("\nすべての統合システムをテスト中...")
    
    from test_all_integrations import main as test_main
    test_main()


def check_integration_status():
    """統合状態を確認"""
    print("\n統合状態を確認中...")
    
    bridge = ManaOSServiceBridge()
    status = bridge.get_integration_status()
    
    import json
    print(json.dumps(status, indent=2, ensure_ascii=False))


def main():
    """メイン関数"""
    print_banner()
    
    while True:
        print_menu()
        choice = input("選択してください (0-6): ").strip()
        
        if choice == "0":
            print("\n終了します。")
            break
        elif choice == "1":
            start_api_server()
        elif choice == "2":
            test_workflow_automation()
        elif choice == "3":
            use_enhanced_downloader()
        elif choice == "4":
            test_service_bridge()
        elif choice == "5":
            test_all_integrations()
        elif choice == "6":
            check_integration_status()
        else:
            print("無効な選択です。")
        
        print("\n" + "-" * 60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n終了します。")
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()




















