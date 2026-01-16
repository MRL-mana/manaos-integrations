#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SearXNG + ローカルLLM統合の使用例
"""

from searxng_llm_integration import (
    SearXNGLLMIntegration,
    search_for_ollama,
    create_searxng_tool_for_ollama
)


def example_1_simple_search_with_llm():
    """例1: シンプルな検索 + LLM要約"""
    print("=" * 60)
    print("例1: 検索 + LLM要約")
    print("=" * 60)
    
    integration = SearXNGLLMIntegration(
        searxng_url="http://localhost:8080",
        ollama_url="http://localhost:11434",
        model_name="qwen2.5:7b"
    )
    
    # 検索 + LLM要約
    result = integration.search_with_llm(
        query="Pythonの最新バージョン",
        use_llm=True,
        max_results=5
    )
    
    print("\n📋 検索結果:")
    for item in result.get("results", [])[:3]:
        print(f"- {item['title']}")
        print(f"  {item['url']}")
    
    if result.get("llm_summary"):
        print("\n🤖 LLM要約:")
        print(result["llm_summary"])


def example_2_rag_context():
    """例2: RAG用コンテキスト生成"""
    print("\n" + "=" * 60)
    print("例2: RAG用コンテキスト生成")
    print("=" * 60)
    
    integration = SearXNGLLMIntegration()
    
    # RAG用コンテキストを生成
    context = integration.create_rag_context(
        query="Pythonの最新機能",
        max_results=5,
        include_urls=True
    )
    
    print("\n📚 RAGコンテキスト:")
    print(context[:500] + "...")


def example_3_training_data_collection():
    """例3: 学習データ収集"""
    print("\n" + "=" * 60)
    print("例3: 学習データ収集")
    print("=" * 60)
    
    integration = SearXNGLLMIntegration()
    
    # 学習用クエリリスト
    queries = [
        "Pythonの基本構文",
        "機械学習の基礎",
        "深層学習の仕組み"
    ]
    
    # データ収集
    training_data = integration.collect_training_data(
        queries=queries,
        output_file="data/training_data.json"
    )
    
    print(f"\n✅ 収集したデータ: {len(training_data)}件")
    for i, data in enumerate(training_data, 1):
        print(f"{i}. {data['query']}: {len(data['results'])}件の結果")


def example_4_ollama_function_calling():
    """例4: Ollama関数呼び出し（準備）"""
    print("\n" + "=" * 60)
    print("例4: Ollama関数呼び出し用ツール定義")
    print("=" * 60)
    
    # ツール定義を取得
    tool_def = create_searxng_tool_for_ollama()
    
    print("\n🔧 ツール定義:")
    import json
    print(json.dumps(tool_def, indent=2, ensure_ascii=False))
    
    print("\n💡 使用方法:")
    print("""
    import requests
    
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "qwen2.5:7b",
            "messages": [
                {"role": "user", "content": "Pythonの最新情報を調べて"}
            ],
            "tools": [tool_def],
            "tool_choice": "auto"
        }
    )
    """)


def example_5_smart_query():
    """例5: 検索が必要か判断してから実行"""
    print("\n" + "=" * 60)
    print("例5: スマートクエリ（検索判断付き）")
    print("=" * 60)
    
    integration = SearXNGLLMIntegration()
    
    queries = [
        "こんにちは",  # 検索不要
        "Pythonの最新バージョン",  # 検索必要
        "1+1は？"  # 検索不要
    ]
    
    for query in queries:
        print(f"\n質問: {query}")
        
        # 簡単な判断（実際はLLMに判断させる）
        needs_search = any(keyword in query for keyword in ["最新", "最近", "現在", "2024", "2025"])
        
        if needs_search:
            print("  → 検索を実行します")
            context = integration.create_rag_context(query, max_results=3)
            print(f"  → コンテキスト生成完了 ({len(context)}文字)")
        else:
            print("  → 検索不要（通常の回答で対応可能）")


def example_6_knowledge_base_expansion():
    """例6: 知識ベース拡張"""
    print("\n" + "=" * 60)
    print("例6: 知識ベース拡張")
    print("=" * 60)
    
    integration = SearXNGLLMIntegration()
    
    topics = [
        "Python 3.12の新機能",
        "機械学習の最新手法"
    ]
    
    for topic in topics:
        print(f"\n📖 トピック: {topic}")
        
        # RAGコンテキストを生成
        context = integration.create_rag_context(topic, max_results=5)
        
        # ここでベクトルDBに保存する想定
        print(f"  → コンテキスト生成完了")
        print(f"  → ベクトルDBに保存する準備完了 ({len(context)}文字)")
        
        # 実際の保存処理は以下をコメントアウトして使用
        # vectorstore.add_texts([context], metadatas=[{"source": "web_search", "topic": topic}])


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SearXNG + ローカルLLM統合 使用例")
    print("=" * 60)
    
    try:
        example_1_simple_search_with_llm()
        example_2_rag_context()
        example_3_training_data_collection()
        example_4_ollama_function_calling()
        example_5_smart_query()
        example_6_knowledge_base_expansion()
        
        print("\n" + "=" * 60)
        print("✅ すべての例を実行しました")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

















