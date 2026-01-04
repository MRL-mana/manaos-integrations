# manaOS Readiness仕様書
**作成日**: 2025-12-28  
**目的**: 初期化完了の定義と運用ゲートの明確化

---

## エンドポイント仕様

### `/health` - プロセス生存チェック

**目的**: プロセスが生きているかだけを確認（軽量）

**仕様**:
- **常に即200を返す**（重い処理は一切しない）
- プロセス生存のみを確認
- タイムアウト: 1秒以内

**レスポンス例**:
```json
{
  "status": "alive",
  "timestamp": "2025-12-28T22:30:00.000000"
}
```

---

### `/ready` - 初期化完了チェック

**目的**: すべての必須チェックが完了しているか確認

**仕様**:
- **200**: 初期化完了（すべての必須チェックがOK）
- **503**: 初期化中（必須チェックが未完了）
- **500**: 初期化エラー

**必須チェック**:
1. `memory_db`: 記憶DB接続OK
2. `obsidian_path`: Obsidianパス確認OK
3. `notification_hub`: 通知ハブ初期化OK
4. `llm_routing`: LLMルーティングのモデル最低1つ起動OK
5. `image_stock`: 画像ストックDB/フォルダアクセスOK

**レスポンス例（200 - ready）**:
```json
{
  "status": "ready",
  "integrations": {
    "llm_routing": true,
    "memory_unified": true,
    "notification_hub": true,
    "secretary": true,
    "image_stock": true
  },
  "initialization": {
    "completed": ["llm_routing", "memory_unified", ...],
    "failed": []
  },
  "readiness_checks": {
    "memory_db": {
      "status": "ok",
      "message": "記憶DB接続OK"
    },
    "obsidian_path": {
      "status": "ok",
      "message": "Obsidianパス確認OK"
    },
    "notification_hub": {
      "status": "ok",
      "message": "通知ハブ初期化OK"
    },
    "llm_routing": {
      "status": "ok",
      "message": "LLMルーティングOK（5モデル利用可能）"
    },
    "image_stock": {
      "status": "ok",
      "message": "画像ストックアクセスOK"
    }
  }
}
```

**レスポンス例（503 - starting）**:
```json
{
  "status": "starting",
  "pending": ["llm_routing"],
  "completed": ["memory_unified", "notification_hub"],
  "failed": [],
  "readiness_checks": {
    "memory_db": {
      "status": "ok",
      "message": "記憶DB接続OK"
    },
    "llm_routing": {
      "status": "error",
      "message": "Ollama API接続エラー: HTTP 500"
    }
  }
}
```

---

### `/status` - 初期化進捗ステータス

**目的**: 初期化の詳細な進捗情報を取得

**仕様**:
- **常に200を返す**（進捗情報を返す）
- 初期化中でも詳細情報を返す

**レスポンス例**:
```json
{
  "status": "starting",
  "initialization": {
    "pending": ["llm_routing"],
    "completed": ["memory_unified", "notification_hub"],
    "failed": [],
    "progress": {
      "total": 13,
      "completed": 12,
      "failed": 0,
      "pending": 1
    }
  },
  "readiness_checks": {
    "memory_db": {
      "status": "ok",
      "message": "記憶DB接続OK"
    },
    "llm_routing": {
      "status": "error",
      "message": "Ollama API接続エラー"
    }
  },
  "check_summary": {
    "ok": 4,
    "warning": 0,
    "error": 1,
    "not_available": 0
  },
  "ready": false
}
```

---

## 初期化完了の定義

### 必須チェック（5項目）

1. **記憶DB接続OK** (`memory_db`)
   - 統一記憶システムが初期化されている
   - 簡単な読み書きテストが成功

2. **Obsidianパス確認OK** (`obsidian_path`)
   - Obsidian統合が初期化されている
   - Vaultパスが存在し、読み書き可能

3. **通知ハブ初期化OK** (`notification_hub`)
   - 通知ハブが初期化されている
   - キュー投入が可能

4. **LLMルーティングOK** (`llm_routing`)
   - LLMルーティングが初期化されている
   - Ollama APIに接続可能
   - 最低1つのモデルがインストールされている

5. **画像ストックアクセスOK** (`image_stock`)
   - 画像ストックが初期化されている
   - ストックディレクトリが存在し、書き込み可能

### 完了条件

**すべての必須チェックが`status: "ok"`の場合、`/ready`は200を返す。**

---

## テスト仕様（ポーリング）

### 推奨テストフロー

1. **`/health`チェック**（1秒タイムアウト）
   - プロセス生存を確認

2. **`/ready`ポーリング**（最大60秒、2秒間隔）
   - 503は正常（初期化中）
   - 200でGO（初期化完了）
   - タイムアウトした場合は失敗

3. **各機能テスト**
   - `/ready`が200になってから実行
   - 通知、remember/recall、routing、画像ストック等

### ポーリング実装例

```python
def wait_for_ready(max_wait: int = 60, poll_interval: int = 2) -> bool:
    start_time = time.time()
    while time.time() - start_time < max_wait:
        response = requests.get(f"{BASE_URL}/ready", timeout=5)
        if response.status_code == 200:
            return True
        elif response.status_code == 503:
            # 初期化中（正常）
            time.sleep(poll_interval)
            continue
        else:
            # エラー
            return False
    return False  # タイムアウト
```

---

## 運用ルール

### `/health`と`/ready`の使い分け

- **`/health`**: プロセス生存のみ（ロードバランサー、監視ツール用）
- **`/ready`**: 初期化完了確認（テスト、デプロイ確認用）
- **`/status`**: 詳細な進捗確認（デバッグ、運用確認用）

### 判定基準

- **「初期化中に失敗」を防ぐ**: テストは必ず`/ready`が200になってから実行
- **「たまに失敗するOS」を防ぐ**: 初期化完了の定義を明確にする
- **「運用できる」状態**: 毎回同じ手順で合格する

---

**仕様完了**: 2025-12-28













