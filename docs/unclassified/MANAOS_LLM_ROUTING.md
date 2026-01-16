# 🧠 ManaOS × Cursor × ローカルLLM 統合設計

**"難易度ルーティング"で2段構成を実現**

---

## 🎯 設計思想

```
Cursor = 実装・編集の司令塔
ローカルLLM = 常駐コーディング脳（補完/チャット/リファクタ/レビュー）
ManaOS = 仕事を回す実行基盤（RAG、ログ、タスク、通知、n8n、etc）
```

**2段構成**:
- **常駐：7B〜14B coder（速度担当）**
- **高精度：20B〜32B coder（難問担当）**

**ManaOS側で「難しそうなら賢い方に振る」**ってルールにできる。

---

## 🏗️ アーキテクチャ

```
┌─────────────────┐
│     Cursor      │ ← 実装・編集の司令塔
└────────┬────────┘
         │
         │ OpenAI互換API
         │
┌────────▼─────────────────────────────────────┐
│         ManaOS LLM Router                     │
│  ┌──────────────────────────────────────┐    │
│  │  難易度判定エンジン                   │    │
│  │  - プロンプト解析                     │    │
│  │  - コンテキスト長チェック             │    │
│  │  - 複雑度スコア計算                   │    │
│  └──────────┬───────────────────────────┘    │
│             │                                 │
│    ┌────────▼────────┐                       │
│    │  ルーティング    │                       │
│    └────────┬────────┘                       │
│             │                                 │
│    ┌────────┴────────┐                       │
│    │                 │                       │
│ ┌──▼──┐        ┌───▼───┐                   │
│ │軽量  │        │高精度  │                   │
│ │7B-14B│        │20B-32B│                   │
│ └──┬──┘        └───┬───┘                   │
└────┼───────────────┼───────────────────────┘
     │               │
     │               │
┌────▼───┐     ┌─────▼─────┐
│ LM     │     │ LM Studio │
│ Studio │     │ / Ollama  │
│ 7B     │     │ 32B       │
└────────┘     └───────────┘
```

---

## 🔧 実装設計

### 1. 難易度判定エンジン

**判定基準**:

1. **プロンプト長**
   - < 500文字 → 軽量モデル
   - 500-2000文字 → 中量モデル
   - > 2000文字 → 高精度モデル

2. **コンテキスト長**
   - < 2048トークン → 軽量モデル
   - 2048-4096トークン → 中量モデル
   - > 4096トークン → 高精度モデル

3. **キーワード検出**
   - 「設計」「アーキテクチャ」「複雑」→ 高精度モデル
   - 「補完」「修正」「リファクタ」→ 軽量モデル

4. **複雑度スコア**
   - 関数数、クラス数、依存関係数から計算
   - スコア < 10 → 軽量モデル
   - スコア 10-30 → 中量モデル
   - スコア > 30 → 高精度モデル

---

### 2. ルーティングロジック

```python
def route_request(prompt: str, context: dict) -> str:
    """
    リクエストを適切なモデルにルーティング
    
    Returns:
        モデル名（例: "Qwen2.5-Coder-7B-Instruct"）
    """
    # 難易度判定
    difficulty_score = calculate_difficulty(prompt, context)
    
    # ルーティング
    if difficulty_score < 10:
        return "Qwen2.5-Coder-7B-Instruct"  # 軽量
    elif difficulty_score < 30:
        return "Qwen2.5-Coder-14B-Instruct"  # 中量
    else:
        return "Qwen2.5-Coder-32B-Instruct"  # 高精度
```

---

### 3. ManaOS統合API

**エンドポイント**: `POST /api/llm/route`

**リクエスト**:
```json
{
  "prompt": "ユーザーのプロンプト",
  "context": {
    "file_path": "path/to/file.py",
    "code_context": "関連コード",
    "task_type": "implementation|review|refactor"
  },
  "preferences": {
    "prefer_speed": true,
    "prefer_quality": false
  }
}
```

**レスポンス**:
```json
{
  "model": "Qwen2.5-Coder-7B-Instruct",
  "difficulty_score": 5,
  "reasoning": "プロンプトが短く、単純な実装タスクのため軽量モデルを選択",
  "response": "モデルの応答"
}
```

---

## 📋 実装手順

### ステップ1：難易度判定エンジンの実装

**ファイル**: `llm_difficulty_analyzer.py`

```python
class DifficultyAnalyzer:
    """プロンプトの難易度を分析"""
    
    def calculate_difficulty(self, prompt: str, context: dict) -> float:
        """
        難易度スコアを計算（0-100）
        
        Returns:
            難易度スコア
        """
        score = 0.0
        
        # プロンプト長によるスコア
        prompt_length_score = min(len(prompt) / 100, 30)
        score += prompt_length_score
        
        # コンテキスト長によるスコア
        context_length = context.get("code_context", "")
        context_length_score = min(len(context_length) / 200, 30)
        score += context_length_score
        
        # キーワード検出によるスコア
        keywords_score = self._detect_keywords(prompt)
        score += keywords_score
        
        # 複雑度によるスコア
        complexity_score = self._calculate_complexity(context)
        score += complexity_score
        
        return min(score, 100)
    
    def _detect_keywords(self, prompt: str) -> float:
        """キーワード検出"""
        high_difficulty_keywords = [
            "設計", "アーキテクチャ", "複雑", "最適化",
            "refactor", "architecture", "design", "optimize"
        ]
        
        low_difficulty_keywords = [
            "補完", "修正", "リファクタ", "バグ",
            "complete", "fix", "refactor", "bug"
        ]
        
        prompt_lower = prompt.lower()
        
        high_count = sum(1 for kw in high_difficulty_keywords if kw in prompt_lower)
        low_count = sum(1 for kw in low_difficulty_keywords if kw in prompt_lower)
        
        return (high_count * 10) - (low_count * 5)
    
    def _calculate_complexity(self, context: dict) -> float:
        """コードの複雑度を計算"""
        code_context = context.get("code_context", "")
        
        # 関数数
        function_count = code_context.count("def ")
        
        # クラス数
        class_count = code_context.count("class ")
        
        # 依存関係数（import数）
        import_count = code_context.count("import ")
        
        complexity = (function_count * 2) + (class_count * 3) + (import_count * 1)
        
        return min(complexity, 40)
```

---

### ステップ2：ルーティングロジックの実装

**ファイル**: `llm_router_enhanced.py`

```python
from llm_difficulty_analyzer import DifficultyAnalyzer

class EnhancedLLMRouter:
    """難易度ルーティング対応のLLMルーター"""
    
    def __init__(self):
        self.analyzer = DifficultyAnalyzer()
        self.models = {
            "light": "Qwen2.5-Coder-7B-Instruct",
            "medium": "Qwen2.5-Coder-14B-Instruct",
            "heavy": "Qwen2.5-Coder-32B-Instruct"
        }
    
    def route(self, prompt: str, context: dict, preferences: dict = None) -> dict:
        """
        リクエストをルーティング
        
        Returns:
            {
                "model": "モデル名",
                "difficulty_score": スコア,
                "reasoning": "理由",
                "response": "応答"
            }
        """
        # 難易度判定
        difficulty_score = self.analyzer.calculate_difficulty(prompt, context)
        
        # ユーザー設定を考慮
        prefer_speed = preferences.get("prefer_speed", False) if preferences else False
        prefer_quality = preferences.get("prefer_quality", False) if preferences else False
        
        # ルーティング
        if prefer_speed or difficulty_score < 10:
            model = self.models["light"]
            reasoning = "プロンプトが短く、単純なタスクのため軽量モデルを選択"
        elif prefer_quality or difficulty_score > 30:
            model = self.models["heavy"]
            reasoning = "プロンプトが複雑で、高品質な応答が必要なため高精度モデルを選択"
        else:
            model = self.models["medium"]
            reasoning = "中程度の複雑度のため中量モデルを選択"
        
        # LLM呼び出し
        response = self._call_llm(model, prompt, context)
        
        return {
            "model": model,
            "difficulty_score": difficulty_score,
            "reasoning": reasoning,
            "response": response
        }
    
    def _call_llm(self, model: str, prompt: str, context: dict) -> str:
        """LLMを呼び出し"""
        # OpenAI互換API経由で呼び出し
        import requests
        
        # LM Studio/Ollamaのエンドポイント
        base_url = "http://localhost:1234/v1"
        
        response = requests.post(
            f"{base_url}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a helpful coding assistant."},
                    {"role": "user", "content": prompt}
                ]
            }
        )
        
        return response.json()["choices"][0]["message"]["content"]
```

---

### ステップ3：ManaOS統合APIの実装

**ファイル**: `manaos_llm_routing_api.py`

```python
from flask import Flask, request, jsonify
from llm_router_enhanced import EnhancedLLMRouter

app = Flask(__name__)

router = EnhancedLLMRouter()

@app.route("/api/llm/route", methods=["POST"])
def route_llm_request():
    """LLMリクエストをルーティング"""
    data = request.json
    
    prompt = data.get("prompt", "")
    context = data.get("context", {})
    preferences = data.get("preferences", {})
    
    result = router.route(prompt, context, preferences)
    
    return jsonify(result)
```

---

## 🔄 Cursor統合

### Cursor側の設定

**設定ファイル**: `cursor_llm_routing.json`

```json
{
  "routing_enabled": true,
  "routing_endpoint": "http://localhost:9500/api/llm/route",
  "default_model": "Qwen2.5-Coder-7B-Instruct",
  "preferences": {
    "prefer_speed": true,
    "prefer_quality": false
  }
}
```

### Cursor拡張機能（オプション）

Cursorの設定で、ManaOSルーター経由でLLMを呼び出すように設定：

```json
{
  "cursor.llm.customModels": [
    {
      "name": "ManaOS-Router",
      "provider": "openai-compatible",
      "baseUrl": "http://localhost:9500/api/llm/route",
      "apiKey": "manaos"
    }
  ]
}
```

---

## 📊 監視とログ

### ルーティングログ

**ファイル**: `llm_routing_logs.json`

```json
{
  "timestamp": "2025-01-28T12:00:00Z",
  "prompt_length": 150,
  "difficulty_score": 5,
  "selected_model": "Qwen2.5-Coder-7B-Instruct",
  "response_time_ms": 250,
  "user_satisfaction": "high"
}
```

### メトリクス

- **ルーティング精度**: 適切なモデルが選択された割合
- **レスポンス時間**: モデル別の平均レスポンス時間
- **ユーザー満足度**: ユーザーフィードバックから計算

---

## 🎯 運用ルール

### ルール1：自動ルーティング

- **デフォルト**: 難易度判定で自動ルーティング
- **オーバーライド**: ユーザーが明示的にモデルを指定可能

### ルール2：フォールバック

- **軽量モデル失敗時**: 中量モデルに自動フォールバック
- **中量モデル失敗時**: 高精度モデルに自動フォールバック

### ルール3：キャッシュ

- **同じプロンプト**: キャッシュから返却（ManaOSのRAG機能を活用）
- **類似プロンプト**: 類似度が高い場合はキャッシュを提案

---

## 📝 まとめ

**ManaOS統合設計**:

1. ✅ **難易度判定エンジン**: プロンプトの難易度を自動判定
2. ✅ **ルーティングロジック**: 難易度に応じて適切なモデルを選択
3. ✅ **ManaOS統合API**: `/api/llm/route`エンドポイントでルーティング
4. ✅ **Cursor統合**: CursorからManaOSルーター経由でLLM呼び出し
5. ✅ **監視とログ**: ルーティング精度とパフォーマンスを監視

**これで"難しそうなら賢い方に振る"が実現！🔥**

---

## 🔗 関連ファイル

- `CURSOR_LOCAL_LLM_SETUP.md` - 接続設定手順
- `CURSOR_MODEL_RECOMMENDATIONS.md` - モデル選定ガイド
- `CURSOR_PROMPT_TEMPLATES.md` - プロンプトテンプレート集
- `llm_routing.py` - 既存のLLMルーティング実装
- `llm_routing_config.yaml` - LLMルーティング設定



















