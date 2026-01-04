# 🚀 常時起動LLM クイックスタート

**推奨される最初のステップ**

---

## ✅ 現在の状態

テスト結果:
- ✅ Ollama: 起動中（30モデルインストール済み）
- ✅ n8n: 起動中
- ⚠️ Redis: 未起動（オプション）
- ⚠️ 統合API: 未起動（オプション）

**基本動作確認完了！** 直接Ollama呼び出しで動作確認済み。

---

## 🎯 次のステップ

### 1. 基本的な使い方（推奨）

```python
from always_ready_llm_client import quick_chat, ModelType

# 1行で呼び出し
response = quick_chat("こんにちは！", ModelType.LIGHT)
print(response)
```

### 2. 詳細な使い方

```python
from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType

# クライアント初期化
client = AlwaysReadyLLMClient()

# チャット
response = client.chat(
    "Pythonでクイックソートを実装してください",
    model=ModelType.MEDIUM,
    task_type=TaskType.AUTOMATION
)

print(f"レスポンス: {response.response}")
print(f"レイテンシ: {response.latency_ms:.2f}ms")
print(f"キャッシュ: {response.cached}")
```

### 3. 使用例を実行

```bash
python examples/llm_usage_examples.py
```

### 4. パフォーマンス監視開始

```bash
python llm_performance_monitor.py
```

---

## 🔧 オプション設定

### Redis起動（キャッシュ機能を使う場合）

```bash
# Docker Composeで起動
docker-compose -f docker-compose.always-ready-llm.yml up -d redis

# または、Windowsで直接起動
# Redisをインストールして起動
```

### n8nワークフロー設定（Webhook経由を使う場合）

1. http://localhost:5678 にアクセス
2. ワークフロー → インポート
3. `n8n_workflows/always_ready_llm_workflow.json` を選択
4. ワークフローを有効化

### 統合APIサーバー起動（キャッシュAPIを使う場合）

```bash
python unified_api_server.py
```

---

## 📊 利用可能なモデル

現在インストール済みモデル（30個）:
- `qwen3:4b`, `qwen3:30b`
- `qwen3-coder:30b`
- `llava:34b`
- `qwen3-vl:30b`
- その他多数

推奨モデル:
- **軽量**: `llama3.2:3b`（高速・会話用）
- **中型**: `qwen2.5:14b`（バランス型・コード生成）
- **大型**: `qwen2.5:32b`（高品質生成）

---

## 🎉 これで準備完了！

基本的な使い方は上記の通りです。詳細は以下を参照してください:

- `ALWAYS_READY_LLM_README.md` - 完全なドキュメント
- `ALWAYS_READY_LLM_GUIDE.md` - 詳細ガイド
- `examples/llm_usage_examples.py` - 10種類の使用例

**質問があったら気軽に聞いて👍**
