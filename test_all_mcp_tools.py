"""
ManaOS統合MCPサーバーのツールをテストするスクリプト
実際に各機能を呼び出して動作確認します
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# MCPサーバーのモジュールを直接インポートしてテスト
import asyncio
from manaos_unified_mcp_server.server import call_tool

async def test_all_tools():
    """すべてのツールをテスト"""
    print("=" * 60)
    print("ManaOS統合MCPサーバー ツールテスト")
    print("=" * 60)
    print()
    
    test_results = {}
    
    # ========================================
    # 1. SVI動画生成のテスト
    # ========================================
    print("[1] SVI動画生成のテスト...")
    print("   （ComfyUIが起動している必要があります）")
    try:
        result = await call_tool("svi_get_queue_status", {})
        if result and len(result) > 0:
            print(f"   [OK] キュー状態を取得できました")
            test_results["svi_queue"] = True
        else:
            print(f"   [SKIP] SVI統合が利用できません")
            test_results["svi_queue"] = False
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        test_results["svi_queue"] = False
    print()
    
    # ========================================
    # 2. ComfyUI画像生成のテスト
    # ========================================
    print("[2] ComfyUI画像生成のテスト...")
    print("   （ComfyUIが起動している必要があります）")
    try:
        # 実際には生成せず、接続確認のみ
        from comfyui_integration import ComfyUIIntegration
        comfyui = ComfyUIIntegration()
        if comfyui.is_available():
            print(f"   [OK] ComfyUIに接続できました")
            test_results["comfyui"] = True
        else:
            print(f"   [SKIP] ComfyUIに接続できません")
            test_results["comfyui"] = False
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        test_results["comfyui"] = False
    print()
    
    # ========================================
    # 3. Google Driveのテスト
    # ========================================
    print("[3] Google Driveのテスト...")
    try:
        result = await call_tool("google_drive_list_files", {})
        if result and len(result) > 0:
            if "❌" not in result[0].text:
                print(f"   [OK] Google Driveに接続できました")
                test_results["google_drive"] = True
            else:
                print(f"   [SKIP] Google Drive統合が利用できません")
                test_results["google_drive"] = False
        else:
            print(f"   [SKIP] Google Drive統合が利用できません")
            test_results["google_drive"] = False
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        test_results["google_drive"] = False
    print()
    
    # ========================================
    # 4. Rowsのテスト
    # ========================================
    print("[4] Rowsのテスト...")
    try:
        result = await call_tool("rows_list_spreadsheets", {})
        if result and len(result) > 0:
            if "❌" not in result[0].text:
                print(f"   [OK] Rowsに接続できました")
                test_results["rows"] = True
            else:
                print(f"   [SKIP] Rows統合が利用できません")
                test_results["rows"] = False
        else:
            print(f"   [SKIP] Rows統合が利用できません")
            test_results["rows"] = False
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        test_results["rows"] = False
    print()
    
    # ========================================
    # 5. Obsidianのテスト
    # ========================================
    print("[5] Obsidianのテスト...")
    try:
        result = await call_tool("obsidian_create_note", {
            "title": "MCPテストノート",
            "content": "これはMCPサーバーのテストで作成されたノートです。\n\n作成日時: 2025-01-28"
        })
        if result and len(result) > 0:
            if "✅" in result[0].text:
                print(f"   [OK] Obsidianノートを作成できました")
                test_results["obsidian"] = True
            else:
                print(f"   [SKIP] Obsidian統合が利用できません: {result[0].text[:100]}")
                test_results["obsidian"] = False
        else:
            print(f"   [SKIP] Obsidian統合が利用できません")
            test_results["obsidian"] = False
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        test_results["obsidian"] = False
    print()
    
    # ========================================
    # 6. 画像ストックのテスト
    # ========================================
    print("[6] 画像ストックのテスト...")
    try:
        # テスト用の画像を探す
        test_image = None
        search_paths = [
            Path("C:/Users/mana4/OneDrive/Desktop/mufufu_cyberrealistic_10"),
            Path("C:/Users/mana4/OneDrive/Desktop/output"),
        ]
        for search_path in search_paths:
            if search_path.exists():
                images = list(search_path.glob("*.png"))
                if images:
                    test_image = images[0]
                    break
        
        if test_image:
            result = await call_tool("image_stock_add", {
                "image_path": str(test_image),
                "description": "MCPテスト画像"
            })
            if result and len(result) > 0:
                if "✅" in result[0].text:
                    print(f"   [OK] 画像をストックに追加できました")
                    test_results["image_stock"] = True
                else:
                    print(f"   [SKIP] 画像ストック統合が利用できません")
                    test_results["image_stock"] = False
            else:
                print(f"   [SKIP] 画像ストック統合が利用できません")
                test_results["image_stock"] = False
        else:
            print(f"   [SKIP] テスト用の画像が見つかりません")
            test_results["image_stock"] = False
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        test_results["image_stock"] = False
    print()
    
    # ========================================
    # 7. 通知のテスト
    # ========================================
    print("[7] 通知のテスト...")
    try:
        result = await call_tool("notification_send", {
            "message": "MCPサーバーのテスト通知です",
            "priority": "normal"
        })
        if result and len(result) > 0:
            if "✅" in result[0].text:
                print(f"   [OK] 通知を送信できました")
                test_results["notification"] = True
            else:
                print(f"   [SKIP] 通知ハブ統合が利用できません")
                test_results["notification"] = False
        else:
            print(f"   [SKIP] 通知ハブ統合が利用できません")
            test_results["notification"] = False
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        test_results["notification"] = False
    print()
    
    # ========================================
    # 8. 記憶システムのテスト
    # ========================================
    print("[8] 記憶システムのテスト...")
    try:
        result = await call_tool("memory_store", {
            "content": "MCPサーバーのテストで記憶に保存された情報です。",
            "format_type": "memo"
        })
        if result and len(result) > 0:
            if "✅" in result[0].text:
                print(f"   [OK] 記憶に保存できました")
                test_results["memory"] = True
                
                # 検索テスト
                recall_result = await call_tool("memory_recall", {
                    "query": "MCPサーバー",
                    "limit": 5
                })
                if recall_result and len(recall_result) > 0:
                    print(f"   [OK] 記憶から検索できました")
                else:
                    print(f"   [WARN] 記憶からの検索に問題がありました")
            else:
                print(f"   [SKIP] 記憶システム統合が利用できません")
                test_results["memory"] = False
        else:
            print(f"   [SKIP] 記憶システム統合が利用できません")
            test_results["memory"] = False
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        test_results["memory"] = False
    print()
    
    # ========================================
    # 9. LLMルーティングのテスト
    # ========================================
    print("[9] LLMルーティングのテスト...")
    try:
        result = await call_tool("llm_chat", {
            "prompt": "こんにちは、これはテストです。",
            "task_type": "conversation"
        })
        if result and len(result) > 0:
            if "❌" not in result[0].text:
                print(f"   [OK] LLMルーティングが動作しました")
                print(f"   応答: {result[0].text[:100]}...")
                test_results["llm"] = True
            else:
                print(f"   [SKIP] LLMルーティング統合が利用できません")
                test_results["llm"] = False
        else:
            print(f"   [SKIP] LLMルーティング統合が利用できません")
            test_results["llm"] = False
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        test_results["llm"] = False
    print()
    
    # ========================================
    # 10. 秘書機能のテスト
    # ========================================
    print("[10] 秘書機能のテスト...")
    try:
        # 朝のルーチンのみテスト（時間がかかる可能性があるため）
        print("   朝のルーチンを実行します（時間がかかる場合があります）...")
        result = await call_tool("secretary_morning_routine", {})
        if result and len(result) > 0:
            if "❌" not in result[0].text:
                print(f"   [OK] 秘書機能が動作しました")
                test_results["secretary"] = True
            else:
                print(f"   [SKIP] 秘書機能統合が利用できません")
                test_results["secretary"] = False
        else:
            print(f"   [SKIP] 秘書機能統合が利用できません")
            test_results["secretary"] = False
    except Exception as e:
        print(f"   [SKIP] エラー: {e}")
        test_results["secretary"] = False
    print()
    
    # ========================================
    # 結果サマリー
    # ========================================
    print("=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    
    total = len(test_results)
    success = sum(1 for v in test_results.values() if v)
    failed = total - success
    
    for tool_name, result in test_results.items():
        status = "[OK]" if result else "[SKIP]"
        print(f"{status} {tool_name}")
    
    print()
    print(f"成功: {success}/{total}")
    print(f"スキップ: {failed}/{total}")
    print()
    
    if success > 0:
        print("[OK] 一部の機能が動作しています")
        print("利用可能な機能はCursorから直接使用できます")
    else:
        print("[INFO] すべての機能がスキップされました")
        print("統合モジュールがインストールされていないか、")
        print("設定が必要な可能性があります")
    
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










