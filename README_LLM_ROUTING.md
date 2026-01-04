# LLMルーティングシステム

manaOSのLLMルーティングシステム（ロール別モデル + fallback + 監査ログ）

## 📋 概要

LLMルーティングシステムは、タスクタイプに応じて最適なモデルを自動選択し、fallback機能で安定性を確保します。

### 特徴

- ✅ **ロール別モデル**: 会話/推論/自動処理で異なるモデルを使用
- ✅ **Fallback機能**: Primary失敗時に自動的に代替モデルに切り替え
- ✅ **監査ログ**: 「なぜそのモデルになったか」を記録
- ✅ **標準API統合**: manaOS標準API（`manaos.act()`）から使用可能

## 🚀 使い方

### 基本的な使い方

```python
from manaos_integrations.llm_routing import LLMRouter

router = LLMRouter()

# 会話タスク
result = router.route(
    task_type="conversation",
    prompt="こんにちは、今日はいい天気ですね。"
)
print(result['response'])
```

### 標準API経由での使用

```python
import manaos_integrations.manaos_core_api as manaos

# LLM呼び出し
result = manaos.act("llm_call", {
    "task_type": "conversation",
    "prompt": "こんにちは"
})
```

## 📐 タスクタイプ

### 1. conversation（会話）

- **用途**: 日常対話、雑談、質問応答
- **Primary**: `llama3.2:3b`（軽量・高速）
- **Fallback**: `qwen2.5:7b`, `llama3.1:8b`
- **優先度**: レイテンシ（速度）

### 2. reasoning（推論）

- **用途**: 複雑な判断、分析、計画立案
- **Primary**: `qwen2.5:72b`（重い・強い）
- **Fallback**: `qwen2.5:32b`, `llama3.1:70b`
- **優先度**: 品質

### 3. automation（自動処理）

- **用途**: タスク実行、コード生成、データ処理
- **Primary**: `qwen2.5:14b`（ツール呼び出し得意）
- **Fallback**: `llama3.1:8b`, `mistral:7b`
- **優先度**: 安定性

## ⚙️ 設定

設定ファイル: `llm_routing_config.yaml`

```yaml
ollama_url: "http://localhost:11434"

routing:
  conversation:
    primary: "llama3.2:3b"
    fallback:
      - "qwen2.5:7b"
      - "llama3.1:8b"
    priority: "latency"
    max_tokens: 2048
    temperature: 0.7
```

## 📝 監査ログ

すべてのLLM呼び出しは監査ログに記録されます。

### ログ項目

- `request_id`: リクエストID
- `timestamp`: タイムスタンプ
- `routed_model`: 使用したモデル
- `task_type`: タスクタイプ
- `memory_refs`: 参照したノートID
- `tools_used`: 使用したツール
- `input_summary`: 入力の要約
- `output_summary`: 出力の要約
- `latency_ms`: レイテンシ（ミリ秒）
- `fallback_used`: fallbackが使われたか

### ログの取得

```python
router = LLMRouter()
logs = router.get_audit_logs(limit=100)
```

## 🧪 テスト

```bash
cd manaos_integrations
python test_llm_routing.py
```

## 🔧 トラブルシューティング

### モデルが利用できない場合

1. Ollamaが起動しているか確認
   ```bash
   # Windows
   Get-Process ollama
   
   # Linux/Mac
   systemctl status ollama
   ```

2. モデルがインストールされているか確認
   ```bash
   ollama list
   ```

3. モデルをインストール
   ```bash
   ollama pull llama3.2:3b
   ollama pull qwen2.5:7b
   ```

### Fallbackが動作しない場合

- 設定ファイル（`llm_routing_config.yaml`）を確認
- すべてのfallbackモデルがインストールされているか確認

## 📚 関連ドキュメント

- `ManaOS_Extension_Phase_CoreSpec.md` - 中核仕様書
- `ManaOS_Extension_Phase_Roadmap.md` - ロードマップ
- `manaos_core_api.py` - 標準API実装

---

**最終更新**: 2025-12-28


















