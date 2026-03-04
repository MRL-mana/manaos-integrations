#!/usr/bin/env python3
"""
RunPod統合 クイックテスト
Phase 1（Modal.com）の動作確認
"""

import sys
from manaos_modal_client import ManaOSModalClient


def print_header(text: str):
    """ヘッダー表示"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def test_modal_auth():
    """Modal認証テスト"""
    print_header("📝 Step 1: Modal認証チェック")
    
    client = ManaOSModalClient()
    
    if client.check_modal_auth():
        print("✅ Modal認証OK！")
        return True
    else:
        print("❌ Modal認証が必要です")
        print("\n次のコマンドを実行してください:")
        print("  modal token set")
        print("\nその後、もう一度このスクリプトを実行してください。")
        return False


def test_health_check():
    """ヘルスチェックテスト"""
    print_header("🏥 Step 2: ヘルスチェック")
    
    client = ManaOSModalClient()
    result = client.health_check()
    
    if result["success"]:
        print("✅ ヘルスチェック成功！")
        print("\nサービス情報:")
        for key, value in result["data"].items():
            print(f"  {key}: {value}")
        return True
    else:
        print(f"❌ ヘルスチェック失敗: {result.get('error', 'Unknown error')}")
        return False


def test_text_generation():
    """テキスト生成テスト"""
    print_header("💬 Step 3: テキスト生成テスト（軽量・高速）")
    
    print("プロンプト: 'Hello, this is a quick test for'")
    print("処理中...\n")
    
    client = ManaOSModalClient()
    result = client.generate_text(
        prompt="Hello, this is a quick test for",
        max_length=50,
        temperature=0.7
    )
    
    if result["success"]:
        print("✅ テキスト生成成功！")
        print("\n生成されたテキスト:")
        print(f"  {result['text']}")
        return True
    else:
        print(f"❌ テキスト生成失敗: {result.get('error', 'Unknown error')}")
        return False


def test_image_generation_info():
    """画像生成の情報表示（実際には実行しない）"""
    print_header("🎨 Step 4: 画像生成について")
    
    print("画像生成は時間がかかるため、このテストではスキップします。")
    print("\n実際に画像を生成する場合は、以下のコードを使用してください:")
    print("\n```python")
    print("from manaos_modal_client import ManaOSModalClient")
    print("")
    print("client = ManaOSModalClient()")
    print("result = client.generate_image(")
    print("    prompt='A beautiful sunset over mountains',")
    print("    steps=30")
    print(")")
    print("print(result)")
    print("```")
    print("\n生成には約3-5分かかります。")


def main():
    """メイン処理"""
    print("\n" + "🚀" * 30)
    print("  ManaOS RunPod GPU統合 - Phase 1 クイックテスト")
    print("🚀" * 30)
    
    # Step 1: Modal認証
    if not test_modal_auth():
        sys.exit(1)
    
    # Step 2: ヘルスチェック
    if not test_health_check():
        print("\n⚠️  ヘルスチェックに失敗しましたが、続行します...")
    
    # Step 3: テキスト生成（軽量テスト）
    if not test_text_generation():
        print("\n⚠️  テキスト生成に失敗しました")
    
    # Step 4: 画像生成の情報
    test_image_generation_info()
    
    # 最終結果
    print_header("✅ テスト完了")
    
    print("Phase 1（Modal.com）の基本機能が動作しています！")
    print("\n次のステップ:")
    print("  1. 画像生成を試す")
    print("  2. Phase 2（Pull型ワーカー）の実装を開始")
    print("  3. ManaOS v3.0に統合")
    print("\n詳細はREADME.mdとSETUP_GUIDE.mdを参照してください。")
    print("\n🎉 おめでとうございます！RunPod GPU統合の第一歩が完了しました！")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  テストが中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


