# 🚀 常時起動LLM完全パッケージ

**「必要な時に即レスかつ安く回す」常時起動LLMシステム**

---

## 📦 パッケージ内容

### コアファイル

1. **`docker-compose.always-ready-llm.yml`** - Docker Compose設定
   - Ollama + Redis + n8n + Traefik の完全スタック

2. **`always_ready_llm_client.py`** - Pythonクライアントライブラリ
   - 簡単にLLMを呼び出せるクライアント
   - キャッシュ自動対応
   - フォールバック機能

3. **`llm_load_balancer.py`** - 負荷分散システム
   - 複数モデルへの分散
   - 自動フォールバック
   - ヘルスチェック

4. **`llm_performance_monitor.py`** - パフォーマンス監視
   - レイテンシ、スループット監視
   - キャッシュヒット率追跡
   - ダッシュボード表示

5. **`deploy_always_ready_llm.sh`** - 自動デプロイスクリプト
   - ワンコマンドでセットアップ完了

6. **`n8n_workflows/always_ready_llm_workflow.json`** - n8nワークフロー
   - Webhook経由LLM呼び出し
   - キャッシュ統合

7. **`examples/llm_usage_examples.py`** - 使用例集
   - 10種類の使用例

---

## 🚀 クイックスタート

### 1. デプロイ

```bash
# Linux/Mac
./deploy_always_ready_llm.sh

# Windows (PowerShell)
docker-compose -f docker-compose.always-ready-llm.yml up -d
```

### 2. モデルインストール

```bash
docker exec ollama-always-ready ollama pull llama3.2:3b
docker exec ollama-always-ready ollama pull qwen2.5:14b
```

### 3. 使用開始

```python
from always_ready_llm_client import quick_chat, ModelType

# 1行で呼び出し
response = quick_chat("こんにちは！", ModelType.LIGHT)
print(response)
```

---

## 📚 使い方

### 基本的な使い方

```python
from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType

# クライアント初期化
client = AlwaysReadyLLMClient()

# チャット
response = client.chat("こんにちは！", ModelType.LIGHT)
print(response.response)
print(f"レイテンシ: {response.latency_ms:.2f}ms")
print(f"キャッシュ: {response.cached}")
```

### バッチ処理

```python
messages = ["こんにちは", "今日の天気は？", "ありがとう"]
results = client.batch_chat(messages, ModelType.LIGHT)

for result in results:
    print(result.response)
```

### 負荷分散

```python
from llm_load_balancer import LLMLoadBalancer, ModelEndpoint, LoadBalanceStrategy

endpoints = [
    ModelEndpoint(model=ModelType.LIGHT, priority=1),
    ModelEndpoint(model=ModelType.MEDIUM, priority=2)
]

balancer = LLMLoadBalancer(
    endpoints=endpoints,
    strategy=LoadBalanceStrategy.ROUND_ROBIN
)

response = balancer.chat("こんにちは！")
```

### パフォーマンス監視

```python
from llm_performance_monitor import LLMPerformanceMonitor

monitor = LLMPerformanceMonitor(client)

# リクエスト実行
response = client.chat("テスト")
monitor.record("テスト", ModelType.LIGHT, TaskType.CONVERSATION, response=response)

# ダッシュボード表示
monitor.print_dashboard()
```

---

## 🎯 機能一覧

### ✅ 実装済み機能

- ✅ Docker Compose完全スタック
- ✅ Pythonクライアントライブラリ
- ✅ Redisキャッシュ統合
- ✅ n8nワークフロー統合
- ✅ 負荷分散・フォールバック
- ✅ パフォーマンス監視
- ✅ 自動デプロイスクリプト
- ✅ 使用例集

### 🔄 拡張可能機能

- 🔄 ストリーミング対応
- 🔄 レート制限
- 🔄 認証・認可
- 🔄 メトリクスエクスポート（Prometheus）
- 🔄 アラート通知

---

## 📊 アーキテクチャ

```
┌─────────────┐
│   Client    │
│  (Python)   │
└──────┬──────┘
       │
       ├──→ n8n Webhook ──→ Ollama ──→ LLM
       │         │
       │         └──→ Redis Cache
       │
       └──→ Direct Ollama (Fallback)
```

---

## 🔧 設定

### 環境変数

```bash
# .envファイル
N8N_USER=admin
N8N_PASSWORD=your_password
REDIS_HOST=redis
REDIS_PORT=6379
```

### モデル選択

| モデル | 用途 | メモリ | 速度 |
|--------|------|--------|------|
| `llama3.2:3b` | 会話・軽量タスク | ~2GB | ⚡⚡⚡ |
| `qwen2.5:14b` | 自動処理・コード生成 | ~8GB | ⚡⚡ |
| `qwen2.5:32b` | 高品質生成 | ~20GB | ⚡ |

---

## 📈 パフォーマンス

### 期待値

- **レイテンシ**: 100-500ms（キャッシュヒット時: <10ms）
- **スループット**: 10-50 req/s（モデル依存）
- **キャッシュヒット率**: 60-80%（用途依存）

### 最適化Tips

1. **キャッシュ活用**: 同じ問い合わせはキャッシュから返す
2. **モデル選択**: 軽量タスクには軽量モデルを使用
3. **バッチ処理**: 複数リクエストをまとめて処理
4. **負荷分散**: 複数モデルに分散して処理

---

## 🐛 トラブルシューティング

### Ollamaが起動しない

```bash
# ログ確認
docker logs ollama-always-ready

# 再起動
docker restart ollama-always-ready
```

### Redis接続エラー

```bash
# Redis確認
docker exec redis-cache redis-cli ping

# 再起動
docker restart redis-cache
```

### n8nワークフローが動かない

1. n8n UI (`http://localhost:5678`) にアクセス
2. ワークフローを有効化
3. Webhook URLを確認

---

## 📝 使用例

詳細な使用例は `examples/llm_usage_examples.py` を参照してください。

```bash
python examples/llm_usage_examples.py
```

---

## 🔗 関連ファイル

- `ALWAYS_READY_LLM_GUIDE.md` - 完全ガイド
- `docker-compose.always-ready-llm.yml` - Docker Compose設定
- `n8n_workflows/always_ready_llm_workflow.json` - n8nワークフロー
- `examples/llm_usage_examples.py` - 使用例集

---

## 📄 ライセンス

このプロジェクトはManaOS統合システムの一部です。

---

**質問があったら気軽に聞いて👍🔥**






















