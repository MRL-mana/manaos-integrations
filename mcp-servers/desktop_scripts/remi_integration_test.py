"""
Remi統合テスト
実際にOllamaと会話して動作確認
"""

import httpx
import asyncio
import json

REMI_API = "http://127.0.0.1:9407"


async def test_speech_input():
    """音声入力テスト（テキスト版）"""
    print("\n[テスト1] 音声入力（テキスト）")
    print("-" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{REMI_API}/remi/speech/input",
                json={
                    "text": "レミ、起動した？",
                    "source": "test"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"[OK] 成功")
                print(f"レミの返事: {data.get('text', 'N/A')}")
                print(f"感情: {data.get('emotion', 'N/A')}")
                return True
            else:
                print(f"[NG] 失敗: {response.status_code}")
                print(response.text)
                return False
    except Exception as e:
        print(f"[NG] エラー: {e}")
        return False


async def test_x_analyze():
    """X解析テスト"""
    print("\n[テスト2] Xポスト解析")
    print("-" * 60)
    
    test_post = "今日は良い天気ですね。散歩に行きたいです。"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{REMI_API}/remi/x/analyze",
                json={"post_text": test_post}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"[OK] 成功")
                print(f"要約: {data.get('summary', 'N/A')[:100]}...")
                print(f"論点: {data.get('point', 'N/A')[:100]}...")
                return True
            else:
                print(f"[NG] 失敗: {response.status_code}")
                return False
    except Exception as e:
        print(f"[NG] エラー: {e}")
        return False


async def test_websocket():
    """WebSocket接続テスト"""
    print("\n[テスト3] WebSocket接続")
    print("-" * 60)
    
    try:
        import websockets
        
        async with websockets.connect(f"ws://localhost:9407/remi/ws") as ws:
            # 接続確認
            print("[OK] WebSocket接続成功")
            
            # メッセージ送信
            await ws.send(json.dumps({
                "type": "speech_input",
                "text": "テスト"
            }))
            
            # 応答待ち
            response = await asyncio.wait_for(ws.recv(), timeout=10.0)
            data = json.loads(response)
            
            if data.get("type") == "remi_response":
                print(f"[OK] 応答受信: {data.get('text', 'N/A')[:50]}...")
                return True
            else:
                print(f"[NG] 予期しない応答: {data}")
                return False
                
    except ImportError:
        print("[SKIP] websocketsライブラリがインストールされていません")
        print("  インストール: pip install websockets")
        return None
    except Exception as e:
        print(f"[NG] エラー: {e}")
        return False


async def main():
    """メイン処理"""
    print("=" * 60)
    print("Remi統合テスト")
    print("=" * 60)
    
    results = []
    
    # テスト実行
    results.append(await test_speech_input())
    results.append(await test_x_analyze())
    ws_result = await test_websocket()
    if ws_result is not None:
        results.append(ws_result)
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果")
    print("=" * 60)
    
    passed = sum(1 for r in results if r is True)
    total = len(results)
    
    print(f"成功: {passed}/{total}")
    
    if passed == total:
        print("\n[SUCCESS] 全テスト成功！レミは正常に動作しています。")
    else:
        print("\n[WARNING] 一部テストが失敗しました。")
        print("Ollamaが起動しているか確認してください。")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)






