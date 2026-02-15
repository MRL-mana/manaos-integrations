# LFM 2.5 クイックスタートガイド

**Liquid AI LFM 2.5**をManaOSで使うための最短ガイドです。

---

## 🚀 5分で始める

### 1. セットアップ（1回だけ）

```powershell
# PowerShellで実行
.\setup_lfm25.ps1
```

または手動で：

```bash
# OllamaにLFM 2.5を追加（Modelfileを使用）
ollama create lfm2.5:1.2b -f Modelfile.lfm25
```

### 2. 基本的な使い方

```python
from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType

client = AlwaysReadyLLMClient()

# 超軽量・超高速チャット
response = client.chat(
    "こんにちは！",
    model=ModelType.ULTRA_LIGHT,  # LFM 2.5
    task_type=TaskType.CONVERSATION
)

print(response.response)
```

### 3. 軽量会話（オフライン会話・下書き・整理）

```python
# 軽量会話タスクタイプを使用
response = client.chat(
    "今日のタスクを整理してください",
    model=ModelType.ULTRA_LIGHT,
    task_type=TaskType.LIGHTWEIGHT_CONVERSATION
)
```

---

## 📚 使用例

### 例1: オフライン会話

```python
response = client.chat(
    "今日の天気について話しましょう",
    model=ModelType.ULTRA_LIGHT,
    task_type=TaskType.LIGHTWEIGHT_CONVERSATION
)
```

### 例2: 下書き作成

```python
response = client.chat(
    "ブログ記事の下書きを作成してください。テーマは「AIの未来」です。",
    model=ModelType.ULTRA_LIGHT,
    task_type=TaskType.LIGHTWEIGHT_CONVERSATION
)
```

### 例3: テキスト整理

```python
response = client.chat(
    "以下のメモを整理してください：\n- タスク1\n- タスク2\n- タスク3",
    model=ModelType.ULTRA_LIGHT,
    task_type=TaskType.LIGHTWEIGHT_CONVERSATION
)
```

### 例4: LLMルーティング経由

```python
from llm_routing import LLMRouter

router = LLMRouter()

# conversationタスク（自動的にLFM 2.5が優先される）
result = router.route(
    task_type="conversation",
    prompt="こんにちは、今日はいい天気ですね。"
)

# lightweight_conversationタスク（常駐軽量LLM専用）
result = router.route(
    task_type="lightweight_conversation",
    prompt="メモを整理してください"
)
```

### 例5: ManaOSコアAPI経由

```python
from manaos_core_api import ManaOSCoreAPI

manaos = ManaOSCoreAPI()

# LLM呼び出し（lightweight_conversation対応）
result = manaos.act("llm_call", {
    "task_type": "lightweight_conversation",
    "prompt": "今日のタスクを整理してください"
})

# LFM 2.5専用呼び出し
result = manaos.act("lfm25_call", {
    "message": "こんにちは！",
    "task_type": "lightweight_conversation"
})
```

### 例6: API経由（HTTP）

```bash
# LFM 2.5チャット
curl -X POST http://127.0.0.1:9502/api/lfm25/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "こんにちは！",
    "task_type": "conversation"
  }'

# LFM 2.5軽量会話
curl -X POST http://127.0.0.1:9502/api/lfm25/lightweight \
  -H "Content-Type: application/json" \
  -d '{
    "message": "今日のタスクを整理してください"
  }'

# LFM 2.5状態確認
curl http://127.0.0.1:9502/api/lfm25/status
```

---

## 🧪 テスト実行

```bash
# 統合テスト
python test_lfm25_integration.py

# 使用例実行
python lfm25_usage_examples.py
```

---

## 📖 詳細ドキュメント

- `LFM25_INTEGRATION.md` - 完全統合ガイド
- `LFM25_DEEP_ANALYSIS.md` - 深層分析
- `README_LLM_ROUTING.md` - LLMルーティングシステム

---

**最終更新**: 2025-01-28

