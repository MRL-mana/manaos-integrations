"""
Remi実演デモ
実際にレミと会話してみる
"""

import httpx
import asyncio
import json

REMI_API = "http://127.0.0.1:9407"


async def chat_with_remi():
    """レミと会話"""
    print("=" * 60)
    print("Remi実演デモ")
    print("=" * 60)
    print("\nレミと会話してみましょう。")
    print("（'exit'で終了）\n")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            try:
                # ユーザー入力
                user_input = input("マナ: ").strip()
                
                if user_input.lower() in ['exit', 'quit', '終了']:
                    print("\nレミ: またね、マナ！")
                    break
                
                if not user_input:
                    continue
                
                # レミに送信
                print("（レミが考えてる...）")
                response = await client.post(
                    f"{REMI_API}/remi/speech/input",
                    json={"text": user_input, "source": "demo"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    remi_text = data.get("text", "...")
                    print(f"レミ: {remi_text}\n")
                else:
                    print(f"エラー: {response.status_code}\n")
                    
            except KeyboardInterrupt:
                print("\n\nレミ: またね、マナ！")
                break
            except Exception as e:
                print(f"エラー: {e}\n")


async def analyze_x_post():
    """Xポスト解析デモ"""
    print("\n" + "=" * 60)
    print("Xポスト解析デモ")
    print("=" * 60)
    
    test_post = input("\nXポストを入力（またはEnterでサンプル）: ").strip()
    if not test_post:
        test_post = "今日は良い天気ですね。散歩に行きたいです。"
        print(f"サンプル: {test_post}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("\n（レミが解析してる...）")
        response = await client.post(
            f"{REMI_API}/remi/x/analyze",
            json={"post_text": test_post}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("\n" + "-" * 60)
            print("レミの解析結果")
            print("-" * 60)
            print(f"\n要約:")
            print(f"  {data.get('summary', 'N/A')}")
            print(f"\n論点:")
            print(f"  {data.get('point', 'N/A')}")
            print(f"\n返信案:")
            print(f"  {data.get('reply_suggestion', 'N/A')}")
        else:
            print(f"エラー: {response.status_code}")


async def main():
    """メイン"""
    print("\nRemi実演デモ")
    print("=" * 60)
    print("1. レミと会話")
    print("2. Xポスト解析")
    print("3. 終了")
    print("=" * 60)
    
    choice = input("\n選択 (1-3): ").strip()
    
    if choice == "1":
        await chat_with_remi()
    elif choice == "2":
        await analyze_x_post()
    else:
        print("終了します。")


if __name__ == "__main__":
    asyncio.run(main())






