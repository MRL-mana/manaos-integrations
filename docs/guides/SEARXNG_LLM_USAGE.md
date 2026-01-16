# SearXNG + ローカルLLM統合ガイド

ローカルLLMや学習系でSearXNG検索を使う方法を説明します。

## 🎯 用途別の使い方

### 1. Ollama + SearXNG（関数呼び出し）

Ollamaの関数呼び出し機能を使って検索：

```python
from searxng_llm_integration import search_for_ollama, create_searxng_tool_for_ollama
import requests

# ツール定義を取得
tool_def = create_searxng_tool_for_ollama()

# Ollamaにツールを登録して使用
response = requests.post(
    "http://localhost:11434/api/chat",
    json={
        "model": "qwen2.5:7b",
        "messages": [
            {
                "role": "user",
                "content": "Pythonの最新バージョンについて調べて"
            }
        ],
        "tools": [tool_def],
        "tool_choice": "auto"
    }
)
```

### 2. LangChain + SearXNG（エージェント）

LangChainエージェントに検索ツールを追加：

```python
from searxng_llm_integration import SearXNGLLMIntegration
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate

# 統合クラスを初期化
integration = SearXNGLLMIntegration(
    searxng_url="http://localhost:8080",
    ollama_url="http://localhost:11434",
    model_name="qwen2.5:7b"
)

# 検索ツールを取得
search_tool = integration.get_langchain_tool()

# エージェントを作成
tools = [search_tool]
prompt = PromptTemplate.from_template("""
あなたはWeb検索ができるアシスタントです。
必要に応じてweb_searchツールを使用して最新情報を検索してください。

質問: {input}
""")

agent = create_react_agent(integration.llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 実行
result = executor.invoke({"input": "Pythonの最新バージョンは？"})
print(result["output"])
```

### 3. RAGシステムに統合

検索結果をRAGのコンテキストとして使用：

```python
from searxng_llm_integration import SearXNGLLMIntegration
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate

# 統合クラスを初期化
integration = SearXNGLLMIntegration()

# RAG用コンテキストを生成
query = "Pythonの最新情報"
context = integration.create_rag_context(query, max_results=5)

# LLMに質問
llm = Ollama(model="qwen2.5:7b")
prompt = f"""以下の情報を基に質問に回答してください。

コンテキスト:
{context}

質問: {query}

回答:"""

response = llm.invoke(prompt)
print(response)
```

### 4. LLMで検索結果を要約

検索結果をLLMで自動要約：

```python
from searxng_llm_integration import SearXNGLLMIntegration

integration = SearXNGLLMIntegration()

# 検索 + LLM要約
result = integration.search_with_llm(
    query="Pythonの最新情報",
    use_llm=True,
    max_results=5
)

print("検索結果:")
for item in result["results"]:
    print(f"- {item['title']}: {item['url']}")

print("\nLLM要約:")
print(result.get("llm_summary", ""))
```

### 5. 学習データ収集

検索結果を学習データとして収集：

```python
from searxng_llm_integration import SearXNGLLMIntegration

integration = SearXNGLLMIntegration()

# 複数のクエリでデータ収集
queries = [
    "Pythonの最新機能",
    "機械学習の最新トレンド",
    "LLMの最新研究"
]

training_data = integration.collect_training_data(
    queries=queries,
    output_file="data/training_data.json"
)

print(f"収集したデータ: {len(training_data)}件")
```

## 🔧 ManaOS標準API経由で使う

```python
import manaos_integrations.manaos_core_api as manaos

# 1. 検索
search_result = manaos.act("web_search", {
    "query": "Python最新情報",
    "max_results": 5
})

# 2. LLMで要約
summary = manaos.act("llm_call", {
    "task_type": "reasoning",
    "prompt": f"以下の検索結果を要約してください:\n{search_result}"
})
```

## 📚 実用例

### 例1: 最新情報を常に取得するLLM

```python
from searxng_llm_integration import SearXNGLLMIntegration
from langchain_community.llms import Ollama

integration = SearXNGLLMIntegration()
llm = Ollama(model="qwen2.5:7b")

def ask_with_search(question: str):
    """検索付きで質問に答える"""
    # 検索実行
    context = integration.create_rag_context(question, max_results=3)
    
    # LLMに質問
    prompt = f"""以下の情報を基に質問に回答してください。

最新情報:
{context}

質問: {question}

回答（最新情報を踏まえて）:"""
    
    return llm.invoke(prompt)

# 使用例
answer = ask_with_search("Pythonの最新バージョンは？")
print(answer)
```

### 例2: 知識ベース構築

```python
from searxng_llm_integration import SearXNGLLMIntegration

integration = SearXNGLLMIntegration()

# トピックごとにデータ収集
topics = [
    "Python 3.12の新機能",
    "機械学習の最新手法",
    "LLMのfine-tuning方法"
]

for topic in topics:
    # 検索結果をRAGコンテキストとして保存
    context = integration.create_rag_context(topic, max_results=10)
    
    # ベクトルDBに保存（例）
    # vector_db.add_document(context, metadata={"topic": topic})
    
    print(f"✅ {topic}のデータを収集しました")
```

### 例3: 自動リサーチアシスタント

```python
from searxng_llm_integration import SearXNGLLMIntegration

integration = SearXNGLLMIntegration()

def research_topic(topic: str):
    """トピックについて自動リサーチ"""
    # 複数の角度から検索
    queries = [
        f"{topic}とは",
        f"{topic}の最新情報",
        f"{topic}の使い方"
    ]
    
    all_results = []
    for query in queries:
        result = integration.search_with_llm(query, max_results=3)
        all_results.append(result)
    
    # 結果を統合
    summary = integration.search_with_llm(
        f"{topic}について包括的に説明してください",
        max_results=10
    )
    
    return {
        "topic": topic,
        "detailed_results": all_results,
        "summary": summary.get("llm_summary", "")
    }

# 使用例
research = research_topic("RAGシステム")
print(research["summary"])
```

## 🎓 学習系での活用

### ファインチューニング用データ収集

```python
from searxng_llm_integration import SearXNGLLMIntegration

integration = SearXNGLLMIntegration()

# 学習用クエリリスト
training_queries = [
    "Pythonの基本構文",
    "機械学習の基礎",
    "深層学習の仕組み"
]

# データ収集
training_data = integration.collect_training_data(
    queries=training_queries,
    output_file="data/finetuning_data.json"
)

# 収集したデータをファインチューニング用に変換
# （必要に応じてフォーマット変換）
```

### 知識ベース拡張

```python
# RAGシステムの知識ベースに検索結果を追加
from searxng_llm_integration import SearXNGLLMIntegration

integration = SearXNGLLMIntegration()

def expand_knowledge_base(topic: str):
    """知識ベースを拡張"""
    # 検索結果を取得
    context = integration.create_rag_context(topic, max_results=10)
    
    # ベクトルDBに追加（例: ChromaDB）
    # vectorstore.add_texts([context], metadatas=[{"source": "web_search", "topic": topic}])
    
    return context

# 使用例
knowledge = expand_knowledge_base("Pythonの最新機能")
```

## 🔗 統合ポイント

### LLMルーティングシステムとの統合

```python
from llm_routing import LLMRouter
from searxng_llm_integration import SearXNGLLMIntegration

router = LLMRouter()
integration = SearXNGLLMIntegration()

# 検索が必要な場合に自動検索
def smart_query(user_query: str):
    # LLMに検索が必要か判断させる
    needs_search = router.route(
        task_type="reasoning",
        prompt=f"この質問に答えるには最新情報が必要ですか？: {user_query}"
    )
    
    if "必要" in needs_search.get("response", ""):
        # 検索実行
        context = integration.create_rag_context(user_query)
        # LLMで回答生成
        return router.route(
            task_type="reasoning",
            prompt=f"以下の情報を基に回答してください:\n{context}\n\n質問: {user_query}"
        )
    else:
        # 通常の回答
        return router.route(task_type="conversation", prompt=user_query)
```

## 📝 まとめ

SearXNG統合により、ローカルLLMで以下が可能になります：

- ✅ **最新情報の取得**: 常に最新のWeb情報を取得
- ✅ **事実確認**: 検索結果でLLMの回答を検証
- ✅ **知識ベース拡張**: RAGシステムにWeb情報を追加
- ✅ **学習データ収集**: ファインチューニング用データの自動収集
- ✅ **自動リサーチ**: トピックについて自動的に情報収集

詳細は各統合モジュールのドキュメントを参照してください。

















