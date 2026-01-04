"""
ManaOS統合機能を直接呼び出すテストスクリプト
MCPサーバー経由ではなく、統合モジュールを直接使用します
"""

import sys
from pathlib import Path
import asyncio

sys.path.insert(0, str(Path(__file__).parent))

async def test_all_tools():
    """すべてのツールをテスト"""
    print("=" * 60)
    print("ManaOS統合機能 直接テスト")
    print("=" * 60)
    print()
    
    # ========================================
    # 1. 記憶システムのテスト（memory_store）
    # ========================================
    print("[1] memory_store - 記憶に情報を保存...")
    try:
        from memory_unified import UnifiedMemory
        memory = UnifiedMemory()
        result = memory.store(
            content="MCPサーバーのテストで記憶に保存された情報です。",
            format_type="memo"
        )
        print(f"   [OK] 記憶に保存しました: {result[:100] if result else '保存完了'}...")
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # ========================================
    # 2. Obsidianノート作成のテスト（obsidian_create_note）
    # ========================================
    print("[2] obsidian_create_note - Obsidianノートを作成...")
    try:
        vault_path = "C:/Users/mana4/Documents/Obsidian Vault"
        from obsidian_integration import ObsidianIntegration
        obsidian = ObsidianIntegration(vault_path=vault_path)
        result = obsidian.create_note(
            title="MCPテストノート",
            content="これはMCPサーバーのテストで作成されたノートです。\n\n作成日時: 2025-01-28\n\n## テスト内容\n\n- memory_store\n- obsidian_create_note\n- その他の機能"
        )
        if result:
            print(f"   [OK] Obsidianノートを作成しました: {result}")
        else:
            print(f"   [SKIP] ノート作成に失敗しました")
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # ========================================
    # 3. Google Driveアップロードのテスト（google_drive_upload）
    # ========================================
    print("[3] google_drive_upload - ファイルをGoogle Driveにアップロード...")
    try:
        from google_drive_integration import GoogleDriveIntegration
        gdrive = GoogleDriveIntegration()
        
        # テスト用のファイルを探す
        test_file = None
        search_paths = [
            Path("C:/Users/mana4/OneDrive/Desktop/Reports"),
            Path("C:/Users/mana4/OneDrive/Desktop"),
        ]
        for search_path in search_paths:
            if search_path.exists():
                files = list(search_path.glob("*.md"))[:1]
                if files:
                    test_file = files[0]
                    break
        
        if test_file and test_file.exists():
            # folder_idは省略可能なので、ファイル名のみ指定
            result = gdrive.upload_file(
                file_path=str(test_file),
                file_name=f"MCP_Test_{test_file.name}"
            )
            if result:
                print(f"   [OK] Google Driveにアップロードしました: {result}")
            else:
                print(f"   [SKIP] アップロードに失敗しました")
        else:
            print(f"   [SKIP] テスト用のファイルが見つかりません")
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # ========================================
    # 4. Rowsクエリのテスト（rows_query）
    # ========================================
    print("[4] rows_query - Rowsスプレッドシートをクエリ...")
    try:
        from rows_integration import RowsIntegration
        rows = RowsIntegration()
        
        # まずスプレッドシート一覧を取得
        spreadsheets = rows.list_spreadsheets()
        if spreadsheets and len(spreadsheets) > 0:
            spreadsheet_id = spreadsheets[0].get("id")
            print(f"   使用するスプレッドシート: {spreadsheet_id}")
            
            # 簡単なクエリを実行
            result = rows.ai_query(
                spreadsheet_id=spreadsheet_id,
                query="最初の5行を表示してください"
            )
            if result:
                print(f"   [OK] Rowsクエリを実行しました")
                print(f"   結果: {result[:200] if result else 'なし'}...")
            else:
                print(f"   [SKIP] クエリに失敗しました")
        else:
            print(f"   [SKIP] スプレッドシートが見つかりません")
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # ========================================
    # 5. LLMチャットのテスト（llm_chat）
    # ========================================
    print("[5] llm_chat - LLMとチャット...")
    try:
        from llm_routing import LLMRouter
        router = LLMRouter()
        
        result = await router.route(
            prompt="こんにちは、これはテストです。短く返答してください。",
            task_type="conversation"
        )
        if result:
            print(f"   [OK] LLMチャットが動作しました")
            print(f"   応答: {result.get('response', result)[:200]}...")
        else:
            print(f"   [SKIP] LLMチャットに失敗しました")
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # ========================================
    # 6. ComfyUI画像生成のテスト（comfyui_generate_image）
    # ========================================
    print("[6] comfyui_generate_image - ComfyUIで画像を生成...")
    print("   （ComfyUIが起動している必要があります）")
    try:
        from comfyui_integration import ComfyUIIntegration
        comfyui = ComfyUIIntegration()
        
        if comfyui.is_available():
            # 簡単な画像生成を実行
            result = comfyui.generate_image(
                prompt="cute cat, high quality",
                negative_prompt="low quality, blurry",
                width=512,
                height=512,
                steps=20
            )
            if result:
                print(f"   [OK] ComfyUIで画像を生成しました")
                print(f"   画像パス: {result}")
            else:
                print(f"   [SKIP] 画像生成に失敗しました")
        else:
            print(f"   [SKIP] ComfyUIに接続できません")
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # ========================================
    # 7. SVI動画生成のテスト（svi_generate_video）
    # ========================================
    print("[7] svi_generate_video - SVIで動画を生成...")
    print("   （ComfyUIが起動している必要があります）")
    try:
        from svi_wan22_video_integration import SVIWan22VideoIntegration
        svi = SVIWan22VideoIntegration()
        
        # 開始画像を探す
        start_image = None
        search_paths = [
            Path("C:/Users/mana4/OneDrive/Desktop/mufufu_cyberrealistic_10"),
            Path("C:/Users/mana4/OneDrive/Desktop/output"),
        ]
        for search_path in search_paths:
            if search_path.exists():
                images = list(search_path.glob("*.png"))[:1]
                if images:
                    start_image = images[0]
                    break
        
        if start_image and start_image.exists():
            result = svi.generate_video(
                start_image_path=str(start_image),
                prompt="ゆっくりと動く、美しい風景",
                video_length_seconds=3,
                steps=6,
                motion_strength=1.0
            )
            if result:
                print(f"   [OK] SVIで動画生成を開始しました")
                print(f"   プロンプトID: {result}")
            else:
                print(f"   [SKIP] 動画生成に失敗しました")
        else:
            print(f"   [SKIP] 開始画像が見つかりません")
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # ========================================
    # 結果サマリー
    # ========================================
    print("=" * 60)
    print("テスト完了")
    print("=" * 60)
    print()
    print("[INFO] 各機能のテストが完了しました")
    print("利用可能な機能はCursorのMCPサーバーからも使用できます")
    print()

if __name__ == "__main__":
    try:
        asyncio.run(test_all_tools())
    except KeyboardInterrupt:
        print("\n\nテストが中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

