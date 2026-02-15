# MRL Memory System 使用ガイド

## 概要

MRL Memory Systemは、短期記憶（FWPKM）と長期記憶（RAG）を統合した記憶システムです。現在、正常に動作しています。

## 現在の状態

- ✅ APIサーバー: 動作中（ポート5105）
- ✅ 書き込み: 有効（sampledモード）
- ✅ 認証: 有効
- ✅ 統合: ManaOS Core API、LLMルーティングと統合済み

## 使用方法

### 1. API直接使用

```python
import requests
import os
from pathlib import Path

# APIキーを読み込む
api_key = None
env_path = Path(".env")
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("MRL_MEMORY_API_KEY="):
            api_key = line.split("=", 1)[1].strip()
            break

base_url = "http://127.0.0.1:5105"
headers = {"Content-Type": "application/json"}
if api_key:
    headers["X-API-Key"] = api_key

# テキストを処理してメモリに保存
response = requests.post(
    f"{base_url}/api/memory/process",
    json={
        "text": "プロジェクトXの開始日は2024年2月1日です。",
        "source": "test",
        "enable_rehearsal": True,
        "enable_promotion": False
    },
    headers=headers,
    timeout=5
)

# メモリから検索
response = requests.post(
    f"{base_url}/api/memory/search",
    json={
        "query": "プロジェクトX",
        "limit": 5
    },
    headers=headers,
    timeout=5
)

# LLMコンテキストを取得
response = requests.post(
    f"{base_url}/api/memory/context",
    json={
        "query": "プロジェクトXについて",
        "limit": 3
    },
    headers=headers,
    timeout=5
)
```

### 2. ManaOS Core API経由

```python
from manaos_core_api import ManaOSCoreAPI

api = ManaOSCoreAPI()

# 記憶を保存
memory_entry = api.remember(
    input_data={
        "content": "今日の会議で、来週のリリース日を3月15日に決定しました。",
        "metadata": {"type": "meeting_note"}
    },
    format_type="mrl_memory"
)

# 記憶を検索
results = api.recall(
    query="リリース日",
    scope="all",
    limit=5
)
```

### 3. LLMルーティング統合（準備中）

```python
from mrl_memory_integration import MRLMemoryLLMIntegration
from llm_routing import LLMRouter

llm_router = LLMRouter()
mrl_integration = MRLMemoryLLMIntegration(llm_router=llm_router)

# メモリを活用したLLMルーティング
result = mrl_integration.route_with_memory(
    task_type="conversation",
    prompt="プロジェクトXの予算はいくらでしたか？",
    source="test",
    enable_memory=True
)
```

## 利用可能なエンドポイント

### `/health` (GET)
ヘルスチェック（認証不要）

### `/api/metrics` (GET)
メトリクス取得（認証必要）

### `/api/memory/process` (POST)
テキストを処理してメモリに保存

**リクエスト例:**
```json
{
  "text": "テキスト内容",
  "source": "source_name",
  "enable_rehearsal": true,
  "enable_promotion": false
}
```

### `/api/memory/search` (POST)
メモリから検索

**リクエスト例:**
```json
{
  "query": "検索クエリ",
  "limit": 10
}
```

### `/api/memory/context` (POST)
LLMコンテキストを取得

**リクエスト例:**
```json
{
  "query": "検索クエリ",
  "limit": 5
}
```

### `/api/memory/update_working` (POST)
Working Memoryを更新

### `/api/memory/promote` (POST)
メモリを昇格

## 設定

環境変数（`.env`ファイル）で設定可能:

- `MRL_MEMORY_API_KEY`: APIキー（認証用）
- `MRL_MEMORY_API_URL`: API URL（デフォルト: http://127.0.0.1:5105）
- `REQUIRE_AUTH`: 認証必須かどうか（デフォルト: 1）
- `RATE_LIMIT_PER_MIN`: レート制限（デフォルト: 60）
- `MAX_INPUT_CHARS`: 最大入力文字数（デフォルト: 200000）

## 状態確認

```bash
python check_mrl_memory_status.py
```

## 次のステップ

1. ✅ APIサーバーは動作中
2. ✅ ManaOS Core APIと統合済み
3. 🔄 LLMルーティング統合を強化（進行中）
4. 📝 実際の使用例を追加

## トラブルシューティング

### APIに接続できない
- ポート5105でサーバーが起動しているか確認
- `python check_mrl_memory_status.py`で状態確認

### 認証エラー
- `.env`ファイルに`MRL_MEMORY_API_KEY`が設定されているか確認
- リクエストヘッダーに`X-API-Key`を追加

### メモリが保存されない
- `Write Enabled`が1になっているか確認
- Rollout Managerの設定を確認（sampledモードの場合、10%の確率で保存）
