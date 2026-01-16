#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LM Studioモデルを自動確認し、不足している場合は案内"""

import sys
import requests
import time

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_and_recommend_models():
    """モデルを確認し、不足している場合は推奨"""
    print("=" * 60)
    print("LM Studio モデル自動確認")
    print("=" * 60)
    
    # 必要なモデル（優先順位順）
    required_models = {
        "qwen2.5-coder-14b-instruct": {
            "priority": 1,
            "size": "約8GB",
            "description": "高精度モデル（推奨）"
        },
        "qwen2.5-coder-32b-instruct": {
            "priority": 2,
            "size": "約20GB",
            "description": "最高精度モデル（オプション）"
        },
        "openai/gpt-oss-20b": {
            "priority": 3,
            "size": "約40GB",
            "description": "高精度モデル（オプション）"
        }
    }
    
    try:
        # LM Studio APIからモデル一覧を取得
        r = requests.get('http://localhost:1234/v1/models', timeout=5)
        if r.status_code == 200:
            models_data = r.json().get('data', [])
            available_models = [model.get('id', '') for model in models_data]
            
            print(f"\n利用可能なモデル数: {len(available_models)}")
            print("\n利用可能なモデル:")
            for model in available_models:
                print(f"  ✓ {model}")
            
            print("\n必要なモデルの確認:")
            missing_models = []
            for model_name, model_info in required_models.items():
                # 部分一致で確認
                found = False
                matched_model = None
                for available in available_models:
                    if model_name.lower() in available.lower() or available.lower() in model_name.lower():
                        found = True
                        matched_model = available
                        break
                
                if found:
                    print(f"  ✓ {model_name} (利用可能: {matched_model})")
                else:
                    print(f"  ✗ {model_name} (未ダウンロード)")
                    missing_models.append((model_name, model_info))
            
            if missing_models:
                print("\n" + "=" * 60)
                print("推奨: 以下のモデルをダウンロードしてください")
                print("=" * 60)
                
                for model_name, model_info in missing_models:
                    priority = model_info["priority"]
                    size = model_info["size"]
                    description = model_info["description"]
                    
                    print(f"\n【優先度{priority}】{description}:")
                    print(f"  - {model_name}")
                    print(f"  - サイズ: {size}")
                    print(f"  ダウンロード方法:")
                    print(f"    1. LM Studioを起動")
                    print(f"    2. 「Search」タブを開く")
                    print(f"    3. \"{model_name}\" を検索")
                    print(f"    4. モデルを選択して「Download」をクリック")
            else:
                print("\n✓ 必要なモデルはすべて利用可能です！")
                print("  現在の設定で最高の精度が得られます。")
            
            # 推奨モデルを表示
            print("\n" + "=" * 60)
            print("現在の推奨設定")
            print("=" * 60)
            print("使用中のモデル: qwen2.5-coder-14b-instruct")
            print("精度: 高精度（十分な精度が得られています）")
            print("\nより高い精度が必要な場合:")
            print("  - qwen2.5-coder-32b-instruct をダウンロード")
            print("  - 環境変数: MANA_OCR_USE_LARGE_MODEL=1 を設定")
            
        else:
            print(f"✗ LM Studio APIエラー: HTTP {r.status_code}")
            print("  LM Studioのサーバーが起動しているか確認してください")
            
    except requests.exceptions.ConnectionError:
        print("✗ LM Studioサーバーに接続できません")
        print("  LM Studioの「Server」タブで「Start Server」をクリックしてください")
    except Exception as e:
        print(f"✗ エラー: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    check_and_recommend_models()
