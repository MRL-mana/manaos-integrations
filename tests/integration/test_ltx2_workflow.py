"""
LTX-2ワークフロー構造の動作確認スクリプト
修正後のワークフローが正しく構築されるか確認
"""

import sys
import json
from pathlib import Path
import io
import pytest

# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

def test_workflow_structure():
    """ワークフロー構造のテスト"""
    try:
        from ltx2_video_integration import LTX2VideoIntegration
    except ImportError:
        try:
            from ltx2.ltx2_video_integration import LTX2VideoIntegration
        except Exception as exc:
            pytest.skip(f"LTX-2 integration module unavailable: {exc}")

    print("=" * 60)
    print("LTX-2 ワークフロー構造テスト")
    print("=" * 60)
    print()
    
    ltx2 = LTX2VideoIntegration()
    
    # テスト用のパラメータ
    test_image_path = "test_image.png"  # 実際の画像パスに置き換える必要がある
    
    print("[1] 1パス生成ワークフローの作成...")
    try:
        workflow = ltx2.create_ltx2_workflow(
            start_image_path=test_image_path,
            prompt="a beautiful landscape, mountains, sunset",
            negative_prompt="blurry, low quality",
            video_length_seconds=5,
            width=512,
            height=512,
            use_two_pass=False,
            use_nag=True,
            use_res2s_sampler=True,
            model_name="ltx-2-19b-distilled.safetensors"
        )
        
        print("   ✅ 1パス生成ワークフローが作成されました")
        print(f"   ノード数: {len(workflow)}")
        
        # 主要なノードタイプを確認
        node_types = {}
        for node_id, node_data in workflow.items():
            node_type = node_data.get("class_type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        print("\n   使用されているノードタイプ:")
        for node_type, count in sorted(node_types.items()):
            print(f"     - {node_type}: {count}")
        
        # 必須ノードの確認
        required_nodes = [
            "LoadImage",
            "CheckpointLoaderSimple",
            "LTXVGemmaCLIPModelLoader",
            "LTXVAudioVAELoader",
            "CLIPTextEncode",
            "LTXVConditioning",
            "LTXVPreprocess",
            "LTXVEmptyLatentAudio",
            "LTXVImgToVideoInplace",
            "KSampler",
            "LTXVSeparateAVLatent",
            "LTXVSpatioTemporalTiledVAEDecode",
            "LTXVAudioVAEDecode",
            "CreateVideo",
            "SaveVideo"
        ]
        
        print("\n   必須ノードの確認:")
        missing_nodes = []
        for required_node in required_nodes:
            if required_node in node_types:
                print(f"     ✅ {required_node}")
            else:
                print(f"     ❌ {required_node} (見つかりません)")
                missing_nodes.append(required_node)
        
        if missing_nodes:
            print(f"\n   ⚠️  不足しているノード: {', '.join(missing_nodes)}")
        else:
            print("\n   ✅ すべての必須ノードが含まれています")
        
        # ワークフローをJSONファイルに保存（デバッグ用）
        debug_file = Path("ltx2_workflow_debug.json")
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(workflow, f, indent=2, ensure_ascii=False)
        print(f"\n   📄 デバッグ用ワークフローを保存しました: {debug_file}")
        
    except Exception as e:
        print(f"   ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"1-pass workflow creation failed: {e}")
    
    print()
    print("[2] 2段階生成（アップスケール）ワークフローの作成...")
    try:
        workflow_2pass = ltx2.create_ltx2_workflow(
            start_image_path=test_image_path,
            prompt="a beautiful landscape, mountains, sunset",
            negative_prompt="blurry, low quality",
            video_length_seconds=5,
            width=512,
            height=512,
            use_two_pass=True,
            use_nag=True,
            use_res2s_sampler=True,
            model_name="ltx-2-19b-distilled.safetensors",
            pass1_width=512,
            pass1_height=512,
            pass2_width=1024,
            pass2_height=1024
        )
        
        print("   ✅ 2段階生成ワークフローが作成されました")
        print(f"   ノード数: {len(workflow_2pass)}")
        
        # アップスケール関連のノードを確認
        node_types_2pass = {}
        for node_id, node_data in workflow_2pass.items():
            node_type = node_data.get("class_type", "unknown")
            node_types_2pass[node_type] = node_types_2pass.get(node_type, 0) + 1
        
        if "LatentUpscaleModelLoader" in node_types_2pass:
            print("   ✅ アップスケールモデルローダーが含まれています")
        else:
            print("   ⚠️  アップスケールモデルローダーが見つかりません")
        
        if "LTXVLatentUpsampler" in node_types_2pass:
            print("   ✅ 潜在空間アップサンプラーが含まれています")
        else:
            print("   ⚠️  潜在空間アップサンプラーが見つかりません")
        
        # ワークフローをJSONファイルに保存（デバッグ用）
        debug_file_2pass = Path("ltx2_workflow_2pass_debug.json")
        with open(debug_file_2pass, 'w', encoding='utf-8') as f:
            json.dump(workflow_2pass, f, indent=2, ensure_ascii=False)
        print(f"   📄 デバッグ用ワークフローを保存しました: {debug_file_2pass}")
        
    except Exception as e:
        print(f"   ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"2-pass workflow creation failed: {e}")
    
    print()
    print("[3] ComfyUI接続確認...")
    if ltx2.is_available():
        print("   ✅ ComfyUIに接続できました")
        print("   💡 実際の動画生成を試す準備ができています")
    else:
        print("   ⚠️  ComfyUIに接続できません")
        print("   ComfyUIが起動しているか確認してください: http://127.0.0.1:8188")
    
    print()
    print("=" * 60)
    print("テスト完了")
    print("=" * 60)
    print()
    print("次のステップ:")
    print("1. ComfyUIを起動")
    print("2. 必要なモデルファイルが配置されているか確認")
    print("3. 実際の動画生成を試行: python generate_mana_mufufu_ltx2_video.py")
    
    assert True
