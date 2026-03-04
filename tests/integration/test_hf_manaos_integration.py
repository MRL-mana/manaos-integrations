"""
Hugging Face統合テスト（ManaOS統合版）
"""

import sys
from pathlib import Path

# ManaOS統合APIをインポート
sys.path.insert(0, str(Path(__file__).parent))
from manaos_core_api import get_manaos_api


def test_hf_integration():
    """Hugging Face統合のテスト"""
    print("=" * 60)
    print("Hugging Face統合テスト（ManaOS統合版）")
    print("=" * 60)
    
    # Hugging Face Helperを直接テスト（画像生成をスキップ）
    try:
        from huggingface_helper import HuggingFaceHelper
        helper = HuggingFaceHelper()
        
        print("\n[0] Hugging Face Helper直接テスト")
        print("-" * 60)
        results = helper.search_models("stable diffusion", task="text-to-image", limit=3)
        print(f"✓ {len(results)}件のモデルが見つかりました")
        for i, model in enumerate(results, 1):
            print(f"  {i}. {model['id']} ({model['downloads']:,} downloads)")
        
    except Exception as e:
        print(f"✗ Hugging Face Helperテストエラー: {e}")
        return
    
    api = get_manaos_api()
    
    # 1. モデル検索テスト
    print("\n[1] モデル検索テスト")
    print("-" * 60)
    result = api.act("search_models", {
        "query": "stable diffusion",
        "task": "text-to-image",
        "limit": 5
    })
    
    if "error" in result:
        print(f"✗ エラー: {result['error']}")
    else:
        models = result.get("models", [])
        print(f"✓ {len(models)}件のモデルが見つかりました")
        for i, model in enumerate(models[:3], 1):
            print(f"  {i}. {model['id']} ({model['downloads']:,} downloads)")
    
    # 2. モデル情報取得テスト
    print("\n[2] モデル情報取得テスト")
    print("-" * 60)
    result = api.act("get_model_info", {
        "model_id": "runwayml/stable-diffusion-v1-5"
    })
    
    if "error" in result:
        print(f"✗ エラー: {result['error']}")
    else:
        info = result.get("model_info", {})
        if info:
            print(f"✓ モデル情報を取得しました")
            print(f"  モデルID: {info.get('id')}")
            print(f"  ダウンロード数: {info.get('downloads', 0):,}")
            print(f"  いいね数: {info.get('likes', 0):,}")
        else:
            print("✗ モデル情報が取得できませんでした")
    
    # 3. 画像生成テスト（オプション - 時間がかかるためコメントアウト）
    print("\n[3] 画像生成テスト（スキップ - 時間がかかるため）")
    print("-" * 60)
    print("画像生成をテストする場合は、以下のコードのコメントを外してください:")
    print("""
    result = api.act("generate_image", {
        "prompt": "a beautiful landscape with mountains and a lake, sunset, highly detailed, 4k",
        "negative_prompt": "blurry, low quality, distorted",
        "width": 512,
        "height": 512,
        "num_inference_steps": 30,
        "model_id": "runwayml/stable-diffusion-v1-5"
    })
    
    if "error" in result:
        print(f"✗ エラー: {result['error']}")
    else:
        if result.get("success"):
            print(f"✓ {result.get('count', 0)}枚の画像を生成しました")
            for img in result.get("images", []):
                print(f"  - {img['path']}")
        else:
            print(f"✗ 生成失敗: {result.get('error')}")
    """)
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)


