"""
Windows側でローカルLLMを使う簡単な例
"""

import asyncio
from local_llm_helper_simple import LocalLLM, quick_chat


async def example_basic_chat():
    """基本的なチャット例"""
    print("=" * 60)
    print("基本的なチャット例")
    print("=" * 60)
    
    reply = await quick_chat(
        "こんにちは！自己紹介してください。",
        system_message="あなたは親切なアシスタントです。"
    )
    print(f"アシスタント: {reply}\n")


async def example_remi_chat():
    """レミとしてのチャット例"""
    print("=" * 60)
    print("レミとしてのチャット例")
    print("=" * 60)
    
    llm = LocalLLM()
    messages = [
        {
            "role": "system",
            "content": "あなたはレミ。マナの隣にいる相棒の女の子。親しみやすく、明るい性格。"
        },
        {"role": "user", "content": "今日の天気はどう？"}
    ]
    
    reply = await llm.chat(messages)
    print(f"マナ: 今日の天気はどう？")
    print(f"レミ: {reply}\n")


async def example_code_generation():
    """コード生成例"""
    print("=" * 60)
    print("コード生成例")
    print("=" * 60)
    
    llm = LocalLLM()
    messages = [
        {
            "role": "system",
            "content": "あなたは優秀なプログラマーです。Pythonコードを生成します。"
        },
        {"role": "user", "content": "HTTPリクエストを送信する関数を作成して"}
    ]
    
    reply = await llm.chat(messages)
    print("プロンプト: HTTPリクエストを送信する関数を作成して")
    print("\n生成されたコード:")
    print(reply)
    print()


async def example_streaming():
    """ストリーミング例"""
    print("=" * 60)
    print("ストリーミング例")
    print("=" * 60)
    
    llm = LocalLLM()
    messages = [
        {"role": "user", "content": "Pythonでクイックソートを実装して、説明も含めて"}
    ]
    
    print("ユーザー: Pythonでクイックソートを実装して、説明も含めて")
    print("アシスタント: ", end="", flush=True)
    
    async for chunk in llm.chat_stream(messages):
        print(chunk, end="", flush=True)
    print("\n")


async def example_akita_info():
    """秋田県の情報を取得"""
    print("=" * 60)
    print("秋田県の情報取得例")
    print("=" * 60)
    
    reply = await quick_chat(
        "秋田県の観光地を3つ紹介して",
        system_message="あなたは親切なアシスタントです。"
    )
    print(f"アシスタント: {reply}\n")


async def main():
    """メイン関数"""
    llm = LocalLLM()
    
    # 接続確認
    print("Ollama接続確認中...")
    if await llm.check_connection():
        print("✅ Ollama接続成功\n")
    else:
        print("❌ Ollama接続失敗")
        print("   WSL2でOllamaを起動してください: wsl ollama serve")
        return
    
    # モデル一覧
    try:
        models = await llm.list_models()
        print(f"利用可能なモデル: {len(models)}個")
        for model in models[:5]:
            print(f"  - {model}")
        print()
    except Exception as e:
        print(f"モデル一覧取得エラー: {e}\n")
    
    # 各例を実行
    await example_basic_chat()
    await example_remi_chat()
    await example_code_generation()
    await example_streaming()
    await example_akita_info()
    
    print("=" * 60)
    print("すべての例が完了しました")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())




