# SearXNG統合 クイックスタート

## 🚀 最短5分で始める

### 1. SearXNGを起動

```bash
docker-compose -f docker-compose.searxng.yml up -d
```

### 2. 動作確認

ブラウザで http://localhost:8080 にアクセスしてSearXNGが起動していることを確認

### 3. Pythonで使う

```python
from searxng_integration import SearXNGIntegration

# 初期化
searxng = SearXNGIntegration()

# 検索
result = searxng.search("Python", max_results=5)

# 結果を表示
for item in result['results']:
    print(f"{item['title']}: {item['url']}")
```

### 4. Cursorから使う（MCP経由）

Cursorのチャットで：

```
web_search(query="Pythonの最新情報", max_results=5)
```

## 📝 よくある使い方

### ManaOS標準API経由

```python
import manaos_integrations.manaos_core_api as manaos

result = manaos.act("web_search", {
    "query": "Python最新情報",
    "max_results": 10
})
```

### LLMと組み合わせる

```python
# 1. 検索
search_result = manaos.act("web_search", {"query": "Python"})

# 2. LLMに要約させる
summary = manaos.act("llm_call", {
    "task_type": "reasoning",
    "prompt": f"以下の検索結果を要約: {search_result}"
})
```

## 🔧 トラブルシューティング

### SearXNGに接続できない

```bash
# Dockerコンテナの状態確認
docker ps | grep searxng

# ログ確認
docker logs searxng
```

### テスト実行

```bash
python test_searxng_integration.py
```

詳細は [SEARXNG_SETUP.md](./SEARXNG_SETUP.md) を参照してください。

















