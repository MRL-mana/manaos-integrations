# 🚀 難易度ルーティング クイックスタート

## ✅ セットアップ完了

- ✅ LM Studioサーバー: 起動中
- ✅ 利用可能なモデル: 4つ
- ✅ 設定ファイル: 作成済み
- ✅ LLMルーティングAPI: 起動中（または起動準備完了）

---

## 🎯 使い方

### 1. API経由で使用

```python
import requests

response = requests.post(
  "http://127.0.0.1:9502/api/llm/route",
    json={
        "prompt": "このコードを最適化してください",
        "context": {
            "code_context": "def hello():\n    print('hello')"
        }
    }
)

result = response.json()
print(f"選択されたモデル: {result['model']}")
print(f"難易度スコア: {result['difficulty_score']}")
print(f"応答: {result['response']}")
```

### 2. Pythonから直接使用

```python
from llm_router_enhanced import EnhancedLLMRouter

router = EnhancedLLMRouter()

result = router.route(
    prompt="このコードを最適化してください",
    context={"code_context": "..."}
)

print(f"モデル: {result['model']}")
print(f"難易度: {result['difficulty_level']}")
print(f"応答: {result['response']}")
```

### 3. Cursorから使用（MCP経由）

CursorのMCP設定に `llm_routing_mcp_server` を追加すると、Cursorから直接使用できます。

---

## 📊 難易度ルーティングの仕組み

### 難易度スコア（0-100）

| スコア範囲 | レベル | 使用モデル | 用途 |
|-----------|--------|-----------|------|
| 0-20 | 低 | qwen2.5-coder-7b-instruct | コード補完、簡単な修正 |
| 20-50 | 中 | qwen2.5-coder-7b-instruct | コード生成、リファクタリング |
| 50-100 | 高 | qwen2.5-coder-7b-instruct | アーキテクチャ設計、最適化 |

### 難易度の計算要素

1. **プロンプト長**（最大30点）
2. **コンテキスト長**（最大30点）
3. **キーワード検出**（最大20点）
4. **コード複雑度**（最大20点）

---

## 🔧 設定のカスタマイズ

設定ファイル: `llm_routing_config_lm_studio.yaml`

### 難易度の閾値を変更

```yaml
difficulty_routing:
  low:
    threshold_max: 20  # この値を変更
  medium:
    threshold_min: 20
    threshold_max: 50  # この値を変更
  high:
    threshold_min: 50  # この値を変更
```

### モデルを変更

```yaml
difficulty_routing:
  low:
    models:
      primary: "qwen2.5-coder-7b-instruct"  # モデル名を変更
      fallback:
        - "nvidia/nemotron-3-nano"
```

---

## 📈 パフォーマンスモニタリング

### 統計情報の確認

```powershell
python llm_routing_stats.py
```

### ログの確認

```powershell
python llm_routing_logger.py
```

---

## 🎉 これで完了！

難易度に応じた自動モデル選択と複数モデルの使い分けが可能になりました！

**詳細ガイド**: `DIFFICULTY_ROUTING_GUIDE.md` を参照してください。



















