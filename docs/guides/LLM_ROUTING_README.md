# 🧠 ManaOS LLMルーティングシステム

**難易度判定で自動的に最適なモデルを選択**

---

## 🎯 概要

プロンプトの難易度を自動判定して、適切なローカルLLMモデルにルーティングするシステム。

- **軽量タスク** → `Qwen2.5-Coder-7B-Instruct`（超高速）
- **中量タスク** → `Qwen2.5-Coder-14B-Instruct`（バランス型）
- **高難易度タスク** → `Qwen2.5-Coder-32B-Instruct`（高品質）

---

## 🚀 クイックスタート

### 1. 依存関係のインストール

```powershell
pip install flask flask-cors requests
```

### 2. APIサーバーを起動

```powershell
py -3.10 .\unified_api_server.py
```

（既定ポートは `9510`。変更する場合は `$env:PORT = "9510"` を設定）

### 3. テスト実行

```powershell
python test_llm_routing.py
```

---

## 📋 APIエンドポイント

### POST `/api/llm/route`

LLMリクエストをルーティングして実行

**リクエスト**:
```json
{
  "prompt": "この関数のタイポを修正して",
  "context": {
    "file_path": "path/to/file.py",
    "code_context": "def hello():\n    print('helo')",
    "task_type": "implementation"
  },
  "preferences": {
    "prefer_speed": true,
    "prefer_quality": false,
    "force_model": null
  }
}
```

**レスポンス**:
```json
{
  "model": "Qwen2.5-Coder-7B-Instruct",
  "difficulty_score": 5.0,
  "difficulty_level": "low",
  "reasoning": "プロンプトが短く、単純なタスクのため軽量モデルを選択",
  "response": "修正後のコード...",
  "response_time_ms": 250,
  "success": true
}
```

---

### POST `/api/llm/analyze`

プロンプトの難易度を分析（LLM呼び出しなし）

**リクエスト**:
```json
{
  "prompt": "このコードをリファクタリングして",
  "context": {
    "code_context": "def hello():\n    print('hello')"
  }
}
```

**レスポンス**:
```json
{
  "difficulty_score": 15.5,
  "difficulty_level": "medium",
  "recommended_model": "Qwen2.5-Coder-14B-Instruct"
}
```

---

### GET `/api/llm/models`

利用可能なモデル一覧を取得

**レスポンス**:
```json
{
  "models": [
    "Qwen2.5-Coder-7B-Instruct",
    "Qwen2.5-Coder-14B-Instruct",
    "Qwen2.5-Coder-32B-Instruct"
  ]
}
```

---

### GET `/api/llm/health`

ヘルスチェック

**レスポンス**:
```json
{
  "status": "ok",
  "llm_server": "lm_studio",
  "available_models": 3
}
```

---

## 🔧 設定

### 環境変数

- `LLM_SERVER`: 使用するLLMサーバー（`lm_studio` または `ollama`）
- `PORT`: Unified APIサーバーのポート（デフォルト: 9510）

### 設定ファイル

`cursor_llm_routing_config.json`:

```json
{
  "routing_enabled": true,
  "routing_endpoint": "http://127.0.0.1:9510/api/llm/route",
  "default_model": "Qwen2.5-Coder-7B-Instruct",
  "preferences": {
    "prefer_speed": true,
    "prefer_quality": false
  },
  "llm_server": "lm_studio",
  "lm_studio_url": "http://127.0.0.1:1234/v1",
  "ollama_url": "http://127.0.0.1:11434"
}
```

---

## 🧠 難易度判定の仕組み

### 判定基準

1. **プロンプト長**（最大30点）
   - < 500文字 → 軽量モデル
   - 500-2000文字 → 中量モデル
   - > 2000文字 → 高精度モデル

2. **コンテキスト長**（最大30点）
   - < 2048トークン → 軽量モデル
   - 2048-4096トークン → 中量モデル
   - > 4096トークン → 高精度モデル

3. **キーワード検出**（最大20点）
   - 「設計」「アーキテクチャ」「複雑」→ 高精度モデル
   - 「補完」「修正」「リファクタ」→ 軽量モデル

4. **コード複雑度**（最大20点）
   - 関数数、クラス数、依存関係数から計算

### スコアリング

- **0-10**: 軽量モデル（7B）
- **10-30**: 中量モデル（14B）
- **30以上**: 高精度モデル（32B）

---

## 💡 使用例

### Pythonから呼び出し

```python
import requests

# ルーティング実行
response = requests.post(
  "http://127.0.0.1:9510/api/llm/route",
    json={
        "prompt": "この関数のタイポを修正して",
        "context": {
            "code_context": "def hello():\n    print('helo')"
        },
        "preferences": {
            "prefer_speed": True
        }
    }
)

result = response.json()
print(f"選択モデル: {result['model']}")
print(f"応答: {result['response']}")
```

### Cursorから呼び出し

Cursorの設定で、ManaOSルーター経由でLLMを呼び出すように設定：

```json
{
  "cursor.llm.customModels": [
    {
      "name": "ManaOS-Router",
      "provider": "openai-compatible",
      "baseUrl": "http://127.0.0.1:9510/api/llm/route",
      "apiKey": "manaos"
    }
  ]
}
```

---

## 🚨 トラブルシューティング

### APIサーバーが起動しない

1. **ポートが使用中**
  - 別のポートを指定: `$env:PORT = "9510"`

2. **依存関係が不足**
   - `pip install flask flask-cors requests`

### LLM呼び出しが失敗する

1. **LM Studio/Ollamaが起動していない**
   - LM Studio: 「Server」タブで「Start Server」をクリック
   - Ollama: `ollama serve` を実行

2. **モデルがダウンロードされていない**
   - LM Studio: 「Search」タブでモデルをダウンロード
   - Ollama: `ollama pull qwen2.5-coder:7b`

### ルーティングが適切でない

1. **難易度スコアを確認**
   - `/api/llm/analyze` で難易度スコアを確認

2. **ユーザー設定を調整**
   - `prefer_speed` または `prefer_quality` を設定

---

## 📝 ファイル構成

- `llm_difficulty_analyzer.py` - 難易度判定エンジン
- `llm_router_enhanced.py` - ルーティングロジック
- `unified_api_server.py` - Unified APIサーバー（`/api/llm/*` を提供）
- `llm_routing_mcp_server/` - LLMルーティングMCPサーバー（現行）
- `manaos_llm_routing_api.py` - （レガシー）Flask APIサーバー（非推奨）
- `cursor_llm_routing_config.json` - 設定ファイル
- `test_llm_routing.py` - 統合テスト
- `start_llm_routing_api.ps1` - （レガシー）起動スクリプト

---

## 🔗 関連ドキュメント

- `CURSOR_LOCAL_LLM_SETUP.md` - Cursor接続設定
- `CURSOR_MODEL_RECOMMENDATIONS.md` - モデル選定ガイド
- `MANAOS_LLM_ROUTING.md` - 統合設計書

---

**これで"難しそうなら賢い方に振る"が実現！🔥**



















