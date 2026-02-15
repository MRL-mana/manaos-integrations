# SearXNG統合セットアップガイド

ローカルLLMに「実質無制限」でWeb検索させるためのSearXNG統合のセットアップ手順です。

## 📋 概要

SearXNGは複数の検索エンジンをまとめて結果を返す「メタ検索エンジン」で、セルフホスト可能です。これをManaOSに統合することで、ローカルLLMが制限なくWeb検索できるようになります。

### 主な特徴

- ✅ **実質無制限**: 自分のサーバーが耐える限り検索可能
- ✅ **キャッシュ機能**: 同じ検索は再利用（レート制限回避）
- ✅ **複数エンジン**: Google、Bing、DuckDuckGoなどを統合
- ✅ **プライバシー重視**: 検索履歴を外部に送信しない

## 🚀 セットアップ手順

### 1. SearXNGの起動（Docker）

```bash
# Docker Composeで起動
docker-compose -f docker-compose.searxng.yml up -d

# 起動確認（http://127.0.0.1:8080 にアクセス）
curl http://127.0.0.1:8080
```

### 2. 環境変数の設定（オプション）

`.env`ファイルに以下を追加（必要に応じて）：

```env
# SearXNG設定
SEARXNG_BASE_URL=http://127.0.0.1:8080

# キャッシュ設定（オプション）
SEARXNG_CACHE_DIR=./data/searxng_cache
SEARXNG_CACHE_TTL=3600  # キャッシュ有効期限（秒）
```

### 3. Python依存関係のインストール

```bash
pip install httpx
```

## 📖 使い方

### A) MCPサーバー経由（Cursorから直接使用）

CursorのMCPサーバーから直接検索ツールを呼び出せます：

```
web_search(query="Pythonの最新情報", max_results=5)
```

### B) ManaOS標準API経由

```python
import manaos_integrations.manaos_core_api as manaos

# Web検索を実行
result = manaos.act("web_search", {
    "query": "Pythonの最新情報",
    "max_results": 10,
    "language": "ja"
})

print(f"検索結果: {result['count']}件")
for item in result['results']:
    print(f"- {item['title']}: {item['url']}")
```

### C) 統合クラスを直接使用

```python
from searxng_integration import SearXNGIntegration

# 統合クラスの初期化
searxng = SearXNGIntegration(
    base_url="http://127.0.0.1:8080",
    enable_cache=True,
    cache_ttl=3600
)

# 検索実行
result = searxng.search(
    query="Pythonの最新情報",
    max_results=10,
    language="ja"
)

# シンプルな検索（結果のみ）
results = searxng.search_simple("Python", max_results=5)
```

## 🔧 高度な設定

### キャッシュの管理

```python
from searxng_integration import SearXNGIntegration

searxng = SearXNGIntegration()

# キャッシュをクリア（全削除）
searxng.clear_cache()

# 7日以上古いキャッシュのみ削除
searxng.clear_cache(older_than_days=7)
```

### 検索エンジンの選択

```python
# 特定の検索エンジンのみ使用
result = searxng.search(
    query="Python",
    engines=["google", "bing"],  # GoogleとBingのみ使用
    max_results=10
)
```

### カテゴリフィルタ

```python
# 画像検索のみ
result = searxng.search(
    query="Python",
    categories=["images"],
    max_results=10
)
```

### 時間範囲フィルタ

```python
# 過去1週間の結果のみ
result = searxng.search(
    query="Python",
    time_range="week",
    max_results=10
)
```

## 🔍 利用可能なツール

### MCPサーバー経由

1. **`web_search`**: 詳細な検索結果を返す
   - `query`: 検索クエリ（必須）
   - `max_results`: 最大結果数（デフォルト: 10）
   - `language`: 言語コード（デフォルト: "ja"）
   - `categories`: 検索カテゴリ（例: ["general", "images"]）
   - `time_range`: 時間範囲（"day", "week", "month", "year"）

2. **`web_search_simple`**: シンプルな検索（結果のみ）
   - `query`: 検索クエリ（必須）
   - `max_results`: 最大結果数（デフォルト: 5）

### ManaOS標準API経由

- **`web_search`** / **`search_web`**: Web検索アクション

## 📊 状態確認

```python
from searxng_integration import SearXNGIntegration

searxng = SearXNGIntegration()
status = searxng.get_status()

print(f"利用可能: {status['available']}")
print(f"キャッシュファイル数: {status['cache']['cache_files']}")
print(f"キャッシュサイズ: {status['cache']['cache_size_mb']}MB")
print(f"利用可能な検索エンジン: {status['available_engines']}個")
```

## 🛠️ トラブルシューティング

### SearXNGに接続できない

1. Dockerコンテナが起動しているか確認：
   ```bash
   docker ps | grep searxng
   ```

2. ポート8080が使用可能か確認：
   ```bash
   curl http://127.0.0.1:8080
   ```

3. 環境変数`SEARXNG_BASE_URL`が正しく設定されているか確認

### 検索結果が返ってこない

1. SearXNGのログを確認：
   ```bash
   docker logs searxng
   ```

2. 検索エンジンが利用可能か確認：
   ```python
   searxng = SearXNGIntegration()
   engines = searxng.get_engines()
   print(engines)
   ```

### キャッシュが大きくなりすぎた

```python
# 古いキャッシュを削除
searxng.clear_cache(older_than_days=7)
```

## 🔐 セキュリティとプライバシー

- SearXNGは検索クエリを外部に送信しますが、検索履歴は保存しません
- キャッシュはローカルに保存されます（`data/searxng_cache/`）
- 必要に応じてキャッシュディレクトリを`.gitignore`に追加してください

## 📚 参考リンク

- [SearXNG公式ドキュメント](https://docs.searxng.org/)
- [SearXNG GitHub](https://github.com/searxng/searxng)
- [Open WebUI + SearXNG統合](https://docs.openwebui.com/)

## 🎯 次のステップ

1. **Open WebUIとの統合**: Open WebUIのWeb Search機能にSearXNGを設定
2. **n8nワークフロー連携**: n8nからSearXNG検索を呼び出すワークフローを作成
3. **LLM自動検索**: LLMが自動的にWeb検索を実行する機能を追加

## 💡 使用例

### LLMと組み合わせた検索

```python
import manaos_integrations.manaos_core_api as manaos

# 1. LLMに質問
llm_result = manaos.act("llm_call", {
    "task_type": "conversation",
    "prompt": "Pythonの最新バージョンについて調べて"
})

# 2. LLMの回答に基づいて検索
search_result = manaos.act("web_search", {
    "query": "Python最新バージョン 2024",
    "max_results": 5
})

# 3. 検索結果をLLMに要約させる
summary_result = manaos.act("llm_call", {
    "task_type": "reasoning",
    "prompt": f"以下の検索結果を要約してください:\n{search_result}"
})
```

### n8nワークフロー連携

n8nワークフローからManaOS APIを呼び出して検索：

```json
{
  "action": "web_search",
  "query": "{{ $json.query }}",
  "max_results": 10
}
```

















