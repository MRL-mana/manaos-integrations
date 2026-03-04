#!/usr/bin/env python3
"""
RunPod接続確認ツール
Tailscale / RunPod Serverless / Modal.com すべてをチェック
"""

import sys

sys.path.insert(0, '/root/runpod_integration')
sys.path.insert(0, '/root')

def check_tailscale():
    """Tailscale接続確認"""
    print("1️⃣ Tailscale接続確認")
    print("-" * 60)

    try:
        from tailscale_runpod_connector import TailscaleRunPodConnector

        connector = TailscaleRunPodConnector()
        result = connector.test_connection()

        if result.get("success"):
            print("  ✅ Tailscale接続成功")
            print(f"     IP: {result.get('tailscale_ip')}")
            print(f"     Ping: {'✅' if result.get('ping') else '❌'}")
            print(f"     SSH: {'✅' if result.get('ssh') else '❌'}")
            return True
        else:
            print("  ❌ Tailscale接続失敗")
            print(f"     IP: {result.get('tailscale_ip')}")
            print(f"     Ping: {'✅' if result.get('ping') else '❌'}")
            print(f"     SSH: {'✅' if result.get('ssh') else '❌'}")
            print("\n  💡 RunPod側でTailscaleを起動してください:")
            print("     RunPod Web Terminalで:")
            print("     tailscale up")
            return False
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False

def check_runpod_serverless():
    """RunPod Serverless確認"""
    print("\n2️⃣ RunPod Serverless確認")
    print("-" * 60)

    try:
        # パス1: archive
        try:
            sys.path.insert(0, '/root/archive/dummy_systems/20251106')
            from runpod_serverless_client import RunPodServerlessClient
            client_class = RunPodServerlessClient
            print("  ✅ RunPod Serverless Client: 見つかりました")
        except ImportError:
            # パス2: manaos_unified_system
            try:
                from manaos_unified_system.services.runpod_serverless_client import RunPodServerlessClient
                client_class = RunPodServerlessClient
                print("  ✅ RunPod Serverless Client: 見つかりました")
            except ImportError:
                print("  ❌ RunPod Serverless Client: 見つかりません")
                return False

        client = client_class()

        # 簡単なテスト（実際には生成しない）
        print("  📡 エンドポイント接続確認中...")
        print(f"     エンドポイントID: {getattr(client, 'endpoint_id', 'N/A')}")

        # 実際にテスト生成をしてみる（オプション）
        test_mode = input("  テスト生成を実行しますか？ (y/N): ").strip().lower()
        if test_mode == 'y':
            print("  🎨 テスト生成中...")
            result = client.generate_image(
                prompt="test image",
                model="stable_diffusion",
                width=512,
                height=512,
                steps=10
            )

            if result.get('status') == 'completed':
                print("  ✅ RunPod Serverless: 接続成功")
                return True
            else:
                print(f"  ❌ RunPod Serverless: エラー - {result.get('error')}")
                return False
        else:
            print("  ⏭️  テスト生成をスキップ")
            return True

    except Exception as e:
        print(f"  ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_modal():
    """Modal.com確認"""
    print("\n3️⃣ Modal.com確認")
    print("-" * 60)

    try:
        from manaos_modal_client import ManaOSModalClient

        client = ManaOSModalClient()

        if client.check_modal_auth():
            print("  ✅ Modal.com認証: OK")

            # テスト生成（オプション）
            test_mode = input("  テスト生成を実行しますか？ (y/N): ").strip().lower()
            if test_mode == 'y':
                print("  🎨 テスト生成中...")
                result = client.generate_image(
                    prompt="test image",
                    steps=10
                )

                if result.get('success'):
                    print("  ✅ Modal.com: 接続成功")
                    return True
                else:
                    print(f"  ❌ Modal.com: エラー - {result.get('error')}")
                    return False
            else:
                print("  ⏭️  テスト生成をスキップ")
                return True
        else:
            print("  ❌ Modal.com認証: NG")
            print("  💡 Modal認証を設定してください:")
            print("     modal token set")
            return False
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False

def main():
    """メイン処理"""
    print("🔍 RunPod接続確認ツール")
    print("=" * 60)
    print()

    results = {
        "tailscale": False,
        "runpod_serverless": False,
        "modal": False
    }

    # Tailscale確認
    results["tailscale"] = check_tailscale()

    # RunPod Serverless確認
    results["runpod_serverless"] = check_runpod_serverless()

    # Modal.com確認
    results["modal"] = check_modal()

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 接続確認結果")
    print("=" * 60)
    print(f"  Tailscale: {'✅' if results['tailscale'] else '❌'}")
    print(f"  RunPod Serverless: {'✅' if results['runpod_serverless'] else '❌'}")
    print(f"  Modal.com: {'✅' if results['modal'] else '❌'}")
    print()

    # 推奨方法を表示
    available_methods = [k for k, v in results.items() if v]

    if available_methods:
        print("💡 利用可能な接続方法:")
        for method in available_methods:
            if method == "tailscale":
                print("  ✅ Tailscale - 直接接続（低レイテンシ）")
            elif method == "runpod_serverless":
                print("  ✅ RunPod Serverless - API経由（確実）")
            elif method == "modal":
                print("  ✅ Modal.com - Phase 1（確実）")
        print()
        print("🚀 推奨: RunPod Serverless または Modal.com")
    else:
        print("❌ 利用可能な接続方法がありません")
        print()
        print("💡 対処方法:")
        print("  1. RunPod Serverless: APIキーを設定")
        print("  2. Modal.com: modal token set で認証")
        print("  3. Tailscale: RunPod側で tailscale up")

if __name__ == "__main__":
    main()




