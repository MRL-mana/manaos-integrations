# 🚀 難易度ルーティングと複数モデル使い分けガイド

## 🎯 概要

難易度に応じた自動モデル選択と複数モデルの使い分け機能を設定します。

### 機能

- ✅ **難易度分析**: プロンプトの難易度を自動分析
- ✅ **自動モデル選択**: 難易度に応じて最適なモデルを自動選択
- ✅ **複数モデル使い分け**: タスクタイプに応じて異なるモデルを使用
- ✅ **Fallback機能**: Primaryモデルが失敗した場合、自動的に代替モデルに切り替え
- ✅ **パフォーマンスモニタリング**: レスポンス時間や成功率を記録

---

## 📋 設定手順

### ステップ1: LM Studioサーバーの確認

LM Studioサーバーが起動していることを確認：

```powershell
Invoke-WebRequest -Uri "http://localhost:1234/v1/models" -Method GET
```

**期待される結果：**
- JSON形式でモデル一覧が表示される
- 複数のモデルが利用可能

### ステップ2: 設定ファイルの確認

設定ファイル `llm_routing_config_lm_studio.yaml` を確認：

```yaml
# 難易度別モデル設定
difficulty_routing:
  low:      # 低難易度（軽量・高速）
  medium:   # 中難易度（バランス型）
  high:     # 高難易度（高精度）
```

### ステップ3: LLMルーティングAPIの起動

```powershell
.\start_llm_routing_api.ps1
```

または、手動で起動：

```powershell
python manaos_llm_routing_api.py
```

### ステップ4: 動作確認

```powershell
.\test_llm_routing.py
```

---

## 🎯 難易度ルーティングの仕組み

### 難易度スコア（0-100）

難易度は以下の要素から計算されます：

1. **プロンプト長**（最大30点）
   - 短いプロンプト → 低難易度
   - 長いプロンプト → 高難易度

2. **コンテキスト長**（最大30点）
   - コンテキストが少ない → 低難易度
   - コンテキストが多い → 高難易度

3. **キーワード検出**（最大20点）
   - 高難易度キーワード: "設計", "アーキテクチャ", "最適化" など
   - 低難易度キーワード: "補完", "修正", "タイポ" など

4. **コード複雑度**（最大20点）
   - 関数数、クラス数、ネストの深さなど

### 難易度レベル

| レベル | スコア範囲 | 使用モデル | 用途 |
|--------|-----------|-----------|------|
| **低** | 0-20 | qwen2.5-coder-7b-instruct | コード補完、簡単な修正 |
| **中** | 20-50 | qwen2.5-coder-7b-instruct | コード生成、リファクタリング |
| **高** | 50-100 | qwen2.5-coder-7b-instruct（14B/32B推奨） | アーキテクチャ設計、最適化 |

---

## 🔧 使用方法

### API経由で使用

```python
import requests

# 難易度ルーティングを使用
response = requests.post(
    "http://localhost:9501/api/llm/route",
    json={
        "prompt": "このコードを最適化してください",
        "context": {
            "code_context": "..."
        }
    }
)

result = response.json()
print(f"選択されたモデル: {result['model']}")
print(f"難易度スコア: {result['difficulty_score']}")
print(f"難易度レベル: {result['difficulty_level']}")
print(f"応答: {result['response']}")
```

### Pythonから直接使用

```python
from llm_router_enhanced import EnhancedLLMRouter

router = EnhancedLLMRouter()

# 難易度ルーティング
result = router.route(
    prompt="このコードを最適化してください",
    context={
        "code_context": "..."
    },
    preferences={
        "prefer_speed": False,
        "prefer_quality": True
    }
)

print(f"選択されたモデル: {result['model']}")
print(f"難易度スコア: {result['difficulty_score']}")
print(f"応答: {result['response']}")
```

### Cursorから使用（MCP経由）

CursorのMCP設定に `llm_routing_mcp_server` を追加すると、Cursorから直接使用できます。

---

## 📊 タスクタイプ別ルーティング

### conversation（会話）

- **用途**: 日常対話、雑談、質問応答
- **モデル**: qwen2.5-coder-7b-instruct
- **優先度**: 速度

### coding（コーディング）

- **用途**: コード生成、リファクタリング、バグ修正
- **モデル**: qwen2.5-coder-7b-instruct
- **優先度**: バランス

### reasoning（推論）

- **用途**: 複雑な判断、分析、計画立案
- **モデル**: qwen2.5-coder-7b-instruct（14B/32B推奨）
- **優先度**: 品質

---

## 🔄 Fallback機能

Primaryモデルが失敗した場合、自動的にFallbackモデルに切り替えます。

**例：**
1. Primary: `qwen2.5-coder-7b-instruct` → 失敗
2. Fallback 1: `nvidia/nemotron-3-nano` → 成功

---

## 📈 パフォーマンスモニタリング

### 監査ログ

すべてのリクエストが監査ログに記録されます：

- リクエストID
- タイムスタンプ
- 選択されたモデル
- 難易度スコア
- レスポンス時間
- Fallback使用有無

### 統計情報の確認

```powershell
python llm_routing_stats.py
```

---

## 🎯 最適化のヒント

### 1. モデルの選択

- **軽量タスク**: 7Bモデルで十分
- **中規模タスク**: 7Bモデルで対応可能
- **高難易度タスク**: 14B/32Bモデルを推奨（利用可能な場合）

### 2. ユーザー設定の活用

```python
preferences = {
    "prefer_speed": True,    # 速度優先
    "prefer_quality": False, # 品質優先
    "force_model": None      # モデルを強制指定
}
```

### 3. コンテキストの最適化

- 必要最小限のコンテキストを提供
- 長すぎるコンテキストは難易度スコアを上げる

---

## 🔧 トラブルシューティング

### LLMルーティングAPIが起動しない

1. **ポート9501が使用中か確認**
   ```powershell
   Get-NetTCPConnection -LocalPort 9501
   ```

2. **LM Studioサーバーが起動しているか確認**
   ```powershell
   Invoke-WebRequest -Uri "http://localhost:1234/v1/models" -Method GET
   ```

### モデルが選択されない

1. **利用可能なモデルを確認**
   ```powershell
   Invoke-WebRequest -Uri "http://localhost:1234/v1/models" -Method GET
   ```

2. **設定ファイルのモデル名を確認**
   - モデル名が正確か確認
   - 大文字小文字を区別する場合があります

### 難易度スコアが期待と異なる

1. **キーワードを追加**
   - `llm_difficulty_analyzer.py` のキーワードリストを編集

2. **閾値を調整**
   - `llm_routing_config_lm_studio.yaml` の閾値を調整

---

## 📖 関連ファイル

- `llm_router_enhanced.py` - 難易度ルーティング実装
- `llm_difficulty_analyzer.py` - 難易度分析エンジン
- `manaos_llm_routing_api.py` - LLMルーティングAPI
- `llm_routing_config_lm_studio.yaml` - 設定ファイル

---

**難易度ルーティングと複数モデル使い分けを設定して、効率的にLLMを使用しましょう！🎉**



















