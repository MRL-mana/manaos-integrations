# 🚀 常時起動LLM完全ガイド

**Gen-Zトーンでぶっちゃけ解説するよ👇**

---

## 🎯 概要

**常時起動LLM = 「必要な時に即レスかつ安く回す」が肝**

このガイドでは、ManaOS環境で常時起動LLMを構築する方法を完全解説します。

---

## 📦 スタック構成

```
Docker Compose
  ├ ollama          ← ローカルLLMサーバー（常時起動）
  ├ redis           ← キャッシュ & キューイング
  ├ n8n             ← ワークフロー自動化
  ├ traefik         ← SSL & リバースプロキシ
  └ prometheus      ← メトリクス収集（オプション）
```

---

## 🛠️ セットアップ手順

### 1. Docker Compose起動

```bash
# 環境変数設定（.envファイル作成）
cat > .env << EOF
N8N_USER=admin
N8N_PASSWORD=your_secure_password
DOMAIN=your-domain.com
ACME_EMAIL=your-email@example.com
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin
EOF

# 起動
docker-compose -f docker-compose.always-ready-llm.yml up -d

# ログ確認
docker-compose -f docker-compose.always-ready-llm.yml logs -f ollama
```

### 2. Ollamaモデルインストール

```bash
# 軽量モデル（常時起動推奨）
docker exec ollama-always-ready ollama pull llama3.2:3b

# 中型モデル（必要時ロード）
docker exec ollama-always-ready ollama pull qwen2.5:14b

# 大型モデル（重いタスク用）
docker exec ollama-always-ready ollama pull qwen2.5:32b
```

### 3. n8nワークフローインポート

1. n8nにアクセス: `http://localhost:5678`
2. ワークフロー → インポート
3. `n8n_workflows/always_ready_llm_workflow.json` をインポート
4. Webhook URLをコピー

---

## 🧠 モデル選択戦略

### 軽量モデル（常時ロード推奨）

| モデル | 用途 | メモリ | 速度 |
|--------|------|--------|------|
| `llama3.2:3b` | 会話・意図分類 | ~2GB | ⚡⚡⚡ |
| `llama3.2:1b` | フィルタ・軽量タスク | ~1GB | ⚡⚡⚡⚡ |

### 中型モデル（必要時ロード）

| モデル | 用途 | メモリ | 速度 |
|--------|------|--------|------|
| `qwen2.5:14b` | 自動処理・コード生成 | ~8GB | ⚡⚡ |
| `qwen2.5:7b` | バランス型 | ~4GB | ⚡⚡⚡ |

### 大型モデル（重いタスク用）

| モデル | 用途 | メモリ | 速度 |
|--------|------|--------|------|
| `qwen2.5:32b` | 高品質生成・推論 | ~20GB | ⚡ |
| `qwen2.5:72b` | 最高品質・複雑な判断 | ~45GB | 🐌 |

---

## 🔥 キャッシュ戦略

### Redisキャッシュ設定

```yaml
# llm_routing_config.yaml に追加
cache:
  enabled: true
  redis_host: "localhost"
  redis_port: 6379
  ttl_hours: 24
  cache_patterns:
    - "conversation:*"  # 会話は24時間キャッシュ
    - "reasoning:*"     # 推論は12時間キャッシュ
    - "automation:*"    # 自動処理は6時間キャッシュ
```

### キャッシュヒット率向上Tips

1. **プロンプト正規化**: 空白・改行を統一
2. **モデル別キャッシュ**: モデル名もキーに含める
3. **TTL最適化**: 用途別にTTLを調整
4. **キャッシュウォーミング**: よく使うプロンプトを事前キャッシュ

---

## 🎛️ n8nワークフロー活用

### 基本フロー

```
Webhook受信
  ↓
キャッシュチェック
  ↓
  ├ ヒット → 即返却
  └ ミス → Ollama生成 → キャッシュ保存 → 返却
```

### 高度なフロー例

1. **負荷分散**: 複数モデルに分散
2. **フォールバック**: プライマリ失敗時に自動切り替え
3. **レート制限**: n8nのRate Limitノードで制御
4. **キューイング**: Redis Queueで順次処理

---

## 📊 監視 & メトリクス

### Prometheusメトリクス

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'ollama'
    static_configs:
      - targets: ['ollama:11434']
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
```

### Grafanaダッシュボード

- Ollama: モデル使用率、レスポンス時間
- Redis: キャッシュヒット率、メモリ使用量
- n8n: ワークフロー実行数、エラー率

---

## 💡 コスト最適化Tips

### 1. 動的モデルロード

```yaml
# Ollama設定
OLLAMA_KEEP_ALIVE=5m        # 5分間保持
OLLAMA_MAX_LOADED_MODELS=2   # 最大2モデル同時ロード
```

### 2. キャッシュ活用

- 同じ問い合わせはキャッシュから返す
- キャッシュヒット率80%以上を目標

### 3. モデル選択最適化

- 軽量タスク → 軽量モデル
- 重いタスク → 大型モデル（必要時のみ）

### 4. バッチ処理

- 複数リクエストをまとめて処理
- n8nのバッチノードで実装

---

## 🧨 トラップ回避

### 🔥 メモリ枯渇

**対策**:
- `OLLAMA_MAX_LOADED_MODELS=2` で制限
- 未使用モデルは自動アンロード（5分後）
- Redisの `maxmemory-policy=allkeys-lru` で自動削除

### 🔥 負荷バースト

**対策**:
- n8nのRate Limitノードで制御
- Redis Queueでキューイング
- 同時リクエスト数を制限

### 🔥 コスト爆上げ

**対策**:
- キャッシュ戦略でモデル呼び出し削減
- 軽量モデルを優先使用
- バッチ処理で効率化

---

## 🚀 実装例

### Pythonから呼び出し

#### n8n Webhook経由（推奨：キャッシュ自動対応）

```python
import requests

def call_llm(message: str, model: str = "llama3.2:3b", use_cache: bool = True):
    """n8n Webhook経由でLLM呼び出し（キャッシュ自動対応）"""
    webhook_url = "http://localhost:5678/webhook/llm-chat"
    
    response = requests.post(webhook_url, json={
        "message": message,
        "model": model,
        "use_cache": use_cache
    })
    
    return response.json()

# 使用例
result = call_llm("こんにちは！", model="llama3.2:3b")
print(result["response"])
print(f"キャッシュヒット: {result.get('cached', False)}")
```

#### 統合APIサーバー経由（直接キャッシュ制御）

```python
import requests

def call_llm_with_cache(message: str, model: str = "llama3.2:3b"):
    """統合APIサーバー経由でLLM呼び出し（キャッシュ手動制御）"""
    import hashlib
    import json
    
    # キャッシュキー生成
    cache_key = f"llm:{hashlib.sha256((message + model).encode()).hexdigest()}"
    
    # キャッシュチェック
    cache_response = requests.get(
        "http://localhost:9500/api/cache/get",
        params={"key": cache_key}
    )
    
    if cache_response.json().get("found"):
        print("キャッシュヒット！")
        return cache_response.json()["data"]
    
    # Ollamaで生成
    ollama_response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": message,
            "stream": False
        }
    )
    
    result = {
        "response": ollama_response.json()["response"],
        "model": model,
        "cached": False
    }
    
    # キャッシュに保存
    requests.post(
        "http://localhost:9500/api/cache/set",
        json={
            "key": cache_key,
            "value": result,
            "ttl_seconds": 86400  # 24時間
        }
    )
    
    return result

# 使用例
result = call_llm_with_cache("こんにちは！")
print(result["response"])
```

### 直接Ollama呼び出し（キャッシュなし）

```python
import requests

def call_ollama_direct(message: str, model: str = "llama3.2:3b"):
    """Ollama直接呼び出し"""
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": model,
        "prompt": message,
        "stream": False
    })
    
    return response.json()["response"]

# 使用例
result = call_ollama_direct("こんにちは！")
print(result)
```

---

## 📝 まとめ

**常時起動LLMの肝**:

1. ✅ **軽量モデルを常駐** → 即レス
2. ✅ **キャッシュ戦略** → コスト削減
3. ✅ **動的ロード** → メモリ効率
4. ✅ **n8n統合** → 自動化
5. ✅ **監視** → 最適化

**まなぶ向け推奨構成**:

- 常時起動: `llama3.2:3b`（会話・意図分類）
- 必要時ロード: `qwen2.5:14b`（自動処理・コード生成）
- 重いタスク: `qwen2.5:32b`（高品質生成）

この構成で、**爆速 & 安定 & コスパ最強**の常時起動LLMが完成！🔥

---

## 🔗 関連ファイル

- `docker-compose.always-ready-llm.yml` - Docker Compose設定
- `n8n_workflows/always_ready_llm_workflow.json` - n8nワークフロー
- `llm_routing_config.yaml` - LLMルーティング設定
- `llm_redis_cache.py` - Redisキャッシュ実装
- `always_ready_llm_client.py` - Pythonクライアントライブラリ
- `llm_load_balancer.py` - 負荷分散システム
- `llm_performance_monitor.py` - パフォーマンス監視
- `deploy_always_ready_llm.sh` - 自動デプロイスクリプト
- `examples/llm_usage_examples.py` - 使用例集
- `ALWAYS_READY_LLM_README.md` - パッケージREADME

---

## 🎉 完成した機能

✅ **完全なDocker Composeスタック**
✅ **Pythonクライアントライブラリ**
✅ **負荷分散・フォールバックシステム**
✅ **パフォーマンス監視**
✅ **自動デプロイスクリプト**
✅ **10種類の使用例**

**これで常時起動LLMシステムが完全に使える状態になりました！🔥**

---

**質問あったら気軽に聞いて👍🔥**

