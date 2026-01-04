# ローカルLLM強化機能の使用箇所ガイド

## 📍 現在の使用箇所

### 1. ✅ RAGシステム（自動統合済み）

**ファイル**: `Systems/konoha_migration/server_projects/projects/automation/manaos_langchain_rag.py`

**使用されている機能:**
- ✅ **Qwen 3:4b** モデル（デフォルト）
- ✅ **プロンプト最適化**（自動適用）
- ✅ **キャッシュ機能**（自動適用）
- ✅ **メトリクス収集**（自動適用）

**使用例:**
```python
from manaos_langchain_rag import ManaOSLangChainRAG

# 初期化（自動的にキャッシュとメトリクスが有効化）
rag = ManaOSLangChainRAG()

# クエリ実行（自動的に最適化・キャッシュ・メトリクス記録）
result = rag.query("アルバイトと正社員の違いは？")
print(result['answer'])
```

**アクセス方法:**
- **直接使用**: Pythonスクリプトから直接インポート
- **API経由**: `rag_api_server.py` 経由でHTTP APIとして使用

---

### 2. ✅ Ollama統合API（プロンプト最適化統合済み）

**ファイル**: `Systems/konoha_migration/manaos_unified_system/api/ollama_integration.py`

**使用されている機能:**
- ✅ **Qwen 3:4b** モデル（デフォルト）
- ✅ **プロンプト最適化**（`optimize`パラメータで制御）

**APIエンドポイント:**
```
POST /api/ollama/chat
POST /api/ollama/generate
```

**使用例:**
```bash
# プロンプト最適化を有効化してチャット
curl -X POST http://localhost:5000/api/ollama/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:4b",
    "messages": [{"role": "user", "content": "短い質問"}],
    "optimize": true
  }'
```

**アクセス方法:**
- **Unified API Gateway**: `http://localhost:5000/api/ollama/chat`
- **直接API**: `http://localhost:11434/api/chat`（Ollama直接）

---

### 3. ✅ RAG API Server（RAGシステムを使用）

**ファイル**: `Systems/konoha_migration/server_projects/projects/automation/rag_api_server.py`

**使用されている機能:**
- ✅ RAGシステム経由で全ての機能が利用可能
- ✅ プロンプト最適化
- ✅ キャッシュ
- ✅ メトリクス収集

**APIエンドポイント:**
```
POST /api/rag/query
GET /api/rag/status
```

**使用例:**
```bash
curl -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "アルバイトと正社員の違いは？"}'
```

---

## 🎯 追加で使える場所

### 1. リトライ機能の使用

**ファイル**: `manaos_integrations/llm_retry.py`

**使用例:**
```python
from llm_retry import retry_with_backoff, RetryConfig
from manaos_langchain_rag import ManaOSLangChainRAG

rag = ManaOSLangChainRAG()

# リトライ設定
config = RetryConfig(max_retries=3, initial_delay=1.0)

# リトライ機能付きで実行
result = retry_with_backoff(
    lambda: rag.query("重要な質問"),
    config=config,
    fallback_func=lambda: {"answer": "フォールバック回答"}
)
```

**適用箇所:**
- エラーが発生しやすい処理
- ネットワーク経由のAPI呼び出し
- 外部サービスとの連携

---

### 2. バッチ処理の使用

**ファイル**: `manaos_integrations/llm_batch.py`

**使用例:**
```python
from llm_batch import BatchProcessor
from manaos_langchain_rag import ManaOSLangChainRAG

rag = ManaOSLangChainRAG()
processor = BatchProcessor(max_workers=4)

# 複数のクエリを並列処理
queries = [
    "アルバイトの定義は？",
    "正社員の定義は？",
    "パートの定義は？"
]

results = processor.process_batch(
    queries=queries,
    process_func=lambda q: rag.query(q),
    timeout=60.0
)

for result in results:
    print(f"質問: {result['query']}")
    print(f"回答: {result.get('answer', 'エラー')}")
```

**適用箇所:**
- 大量のクエリを処理する場合
- バッチ処理が必要なタスク
- 並列処理で高速化したい場合

---

### 3. キャッシュ統計の確認

**使用例:**
```python
from llm_cache import get_cache

cache = get_cache()
stats = cache.get_stats()

print(f"キャッシュヒット率: {stats['hit_rate']:.1%}")
print(f"総ヒット数: {stats['hits']}")
print(f"総ミス数: {stats['misses']}")
print(f"キャッシュファイル数: {stats['cache_files']}")
```

**適用箇所:**
- パフォーマンス監視
- キャッシュ効率の確認
- システム最適化

---

### 4. メトリクス統計の確認

**使用例:**
```python
from llm_metrics import get_metrics

metrics = get_metrics()
stats = metrics.get_stats()

print(f"総クエリ数: {stats['total_queries']}")
print(f"最適化率: {stats['optimization_rate']:.1%}")
print(f"キャッシュヒット率: {stats['cache_hit_rate']:.1%}")
print(f"平均応答時間: {stats['average_response_time']:.2f}秒")
print(f"平均プロンプト長: {stats['average_prompt_length']:.0f}文字")
```

**適用箇所:**
- システム監視
- パフォーマンス分析
- プロンプト最適化の効果測定

---

## 🔧 統合可能な場所

### 1. Unified API Gateway

**ファイル**: `Systems/konoha_migration/manaos_unified_system/services/unified_api_gateway.py`

**追加できる機能:**
- リトライ機能の統合
- バッチ処理エンドポイントの追加
- メトリクスAPIの追加

**例:**
```python
@app.route("/api/llm/batch", methods=["POST"])
def llm_batch():
    from llm_batch import BatchProcessor
    from manaos_langchain_rag import ManaOSLangChainRAG
    
    data = request.get_json()
    queries = data.get("queries", [])
    
    rag = ManaOSLangChainRAG()
    processor = BatchProcessor(max_workers=4)
    results = processor.process_batch(
        queries=queries,
        process_func=lambda q: rag.query(q)
    )
    
    return jsonify({"results": results})
```

---

### 2. n8nワークフロー

**使用可能な機能:**
- Ollama統合API経由でプロンプト最適化を使用
- バッチ処理で複数のクエリを処理
- メトリクスAPIで統計を取得

**n8nノード設定例:**
```json
{
  "name": "Ollama Chat (Optimized)",
  "type": "httpRequest",
  "parameters": {
    "url": "http://localhost:5000/api/ollama/chat",
    "method": "POST",
    "body": {
      "model": "qwen3:4b",
      "messages": [{"role": "user", "content": "{{ $json.message }}"}],
      "optimize": true
    }
  }
}
```

---

### 3. Telegram Bot

**ファイル**: `Systems/konoha_migration/server_projects/projects/automation/manaspec_telegram_bot.py`

**追加できる機能:**
- RAGシステムとの統合
- キャッシュ機能の活用
- メトリクス収集

---

### 4. ダッシュボード

**ファイル**: `Systems/konoha_migration/server_manaos_dashboard/manaos_dashboard/app.py`

**追加できる機能:**
- メトリクスの可視化
- キャッシュ統計の表示
- パフォーマンスグラフ

---

## 📊 機能別使用箇所まとめ

| 機能 | 現在の使用箇所 | 追加可能な場所 |
|---|---|---|
| **Qwen 3:4b** | ✅ RAGシステム<br>✅ Ollama統合API | - |
| **プロンプト最適化** | ✅ RAGシステム（自動）<br>✅ Ollama統合API（オプション） | n8nワークフロー<br>Telegram Bot |
| **キャッシュ** | ✅ RAGシステム（自動） | Unified API Gateway<br>Telegram Bot |
| **メトリクス** | ✅ RAGシステム（自動） | ダッシュボード<br>監視システム |
| **リトライ** | - | Unified API Gateway<br>Ollama統合API |
| **バッチ処理** | - | Unified API Gateway<br>n8nワークフロー |

---

## 🚀 すぐに使える例

### 1. Pythonスクリプトから使用

```python
from Systems.konoha_migration.server_projects.projects.automation.manaos_langchain_rag import ManaOSLangChainRAG

# 初期化（自動的に全ての機能が有効化）
rag = ManaOSLangChainRAG()

# クエリ実行
result = rag.query("質問内容")
print(result['answer'])

# メトリクス確認
if rag.metrics:
    stats = rag.metrics.get_stats()
    print(f"キャッシュヒット率: {stats['cache_hit_rate']:.1%}")
```

### 2. HTTP APIから使用

```bash
# RAG API
curl -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "質問内容"}'

# Ollama統合API（プロンプト最適化付き）
curl -X POST http://localhost:5000/api/ollama/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:4b",
    "messages": [{"role": "user", "content": "質問内容"}],
    "optimize": true
  }'
```

### 3. バッチ処理の使用

```python
from llm_batch import BatchProcessor
from manaos_langchain_rag import ManaOSLangChainRAG

rag = ManaOSLangChainRAG()
processor = BatchProcessor(max_workers=4)

queries = ["質問1", "質問2", "質問3"]
results = processor.process_batch(
    queries=queries,
    process_func=rag.query
)
```

---

## 📝 まとめ

**現在自動的に使用されている場所:**
1. ✅ **RAGシステム** - 全ての機能が自動統合済み
2. ✅ **Ollama統合API** - プロンプト最適化が統合済み

**追加で使える場所:**
1. 🔧 **Unified API Gateway** - リトライ・バッチ処理を追加可能
2. 🔧 **n8nワークフロー** - API経由で使用可能
3. 🔧 **Telegram Bot** - RAGシステムを統合可能
4. 🔧 **ダッシュボード** - メトリクスを可視化可能

**すぐに使える:**
- Pythonスクリプトから直接使用
- HTTP API経由で使用
- バッチ処理で大量のクエリを処理



