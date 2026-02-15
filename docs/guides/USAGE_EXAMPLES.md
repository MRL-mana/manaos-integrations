# 🚀 Brave Search API & Base AI API 活用例

## 📋 概要

統合したBrave Search APIとBase AI APIを活用した実用的なスクリプトと使用例です。

---

## 🎨 1. AI支援付き画像生成

### `generate_with_ai_assistance.py`

画像生成時にBrave Search APIとBase AI APIを活用してプロンプトを改善します。

**機能:**
- ✅ Brave Search APIで最新のプロンプトトレンドを検索
- ✅ Base AI APIでプロンプトを自動改善
- ✅ ManaOS Core API経由で画像生成

**使用方法:**
```bash
python generate_with_ai_assistance.py
```

**実行例:**
```
[検索] 最新のプロンプトトレンドを検索しますか？ (y/n): y
  [検索] 'stable diffusion prompt ideas 2024' を検索中...
  [検索] 5件の結果を取得
    1. Top 10 Stable Diffusion Prompts for 2024
    2. Best AI Art Prompts Collection
    ...

[AI] プロンプトを改善中...
  [AI] プロンプト改善完了
```

---

## ✨ 2. スマートプロンプト生成ツール

### `smart_prompt_generator.py`

Brave Search APIとBase AI APIを活用して高品質なプロンプトを生成します。

**機能:**
- ✅ モード1: 新規プロンプト生成（検索 + AI生成）
- ✅ モード2: 既存プロンプト改善（AI改善）
- ✅ モード3: 参考資料検索のみ

**使用方法:**
```bash
python smart_prompt_generator.py
```

**実行例:**
```
モードを選択してください:
  1. 新規プロンプト生成（検索 + AI生成）
  2. 既存プロンプト改善（AI改善）
  3. 参考資料検索のみ

モード (1-3): 1

テーマを入力してください: cute gyaru girl
スタイル（オプション）: anime style

[検索] 'cute gyaru girl anime style stable diffusion prompt' を検索中...
[検索] 5件の結果を取得
  1. Gyaru Style Character Design Guide
  2. Anime Girl Prompt Collection
  ...

[AI] プロンプト生成中...
[AI] プロンプト生成完了

======================================================================
生成されたプロンプト:
======================================================================
cute gyaru girl, anime style, colorful hair, trendy fashion, 
kawaii expression, high quality, detailed, masterpiece, 8k
======================================================================
```

---

## 🔍 3. Brave Search API活用例

### Pythonコード例

```python
from manaos_core_api import ManaOSCoreAPI

manaos = ManaOSCoreAPI()

# 検索実行
result = manaos.act("brave_search", {
    "query": "stable diffusion prompt ideas",
    "count": 10,
    "search_lang": "jp",
    "country": "JP"
})

# 結果を処理
if result.get("status") == "success":
    for item in result["results"]:
        print(f"タイトル: {item['title']}")
        print(f"URL: {item['url']}")
        print(f"説明: {item.get('description', '')}")
```

### REST API例

```bash
# GETリクエスト
curl "http://127.0.0.1:9510/api/brave/search?query=Python&count=10"

# POSTリクエスト
curl -X POST http://127.0.0.1:9510/api/brave/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "stable diffusion prompts",
    "count": 10,
    "search_lang": "jp"
  }'
```

---

## 🤖 4. Base AI API活用例

### Pythonコード例

```python
from manaos_core_api import ManaOSCoreAPI

manaos = ManaOSCoreAPI()

# チャット実行（無料のAI API）
result = manaos.act("base_ai_chat", {
    "prompt": "画像生成プロンプトを改善してください: cute girl",
    "use_free": True
})

# 結果を処理
if result.get("result") and result["result"].get("response"):
    improved_prompt = result["result"]["response"]
    print(f"改善されたプロンプト: {improved_prompt}")
```

### REST API例

```bash
# POSTリクエスト
curl -X POST http://127.0.0.1:9510/api/base-ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "画像生成プロンプトを改善してください: cute girl",
    "use_free": true,
    "temperature": 0.7
  }'
```

---

## 🎯 5. 統合活用例

### プロンプト生成パイプライン

```python
from manaos_core_api import ManaOSCoreAPI

manaos = ManaOSCoreAPI()

# Step 1: 参考資料を検索
search_result = manaos.act("brave_search", {
    "query": "anime girl prompt ideas",
    "count": 5
})

# Step 2: AIでプロンプト生成
prompt = "cute anime girl"
improved = manaos.act("base_ai_chat", {
    "prompt": f"以下のプロンプトを改善してください: {prompt}",
    "use_free": True
})

# Step 3: 画像生成
image_result = manaos.act("generate_image", {
    "prompt": improved["result"]["response"],
    "model_id": "runwayml/stable-diffusion-v1-5"
})
```

---

## 📊 6. MCP Server経由（Cursorから）

### Brave Search

```
brave_search(query="stable diffusion prompts", count=10)
brave_search_simple(query="anime girl", count=5)
```

### Base AI Chat

```
base_ai_chat(prompt="画像生成プロンプトを改善してください: cute girl", use_free=True)
```

---

## 🛠️ 7. カスタマイズ例

### プロンプト改善関数

```python
def improve_prompt(prompt: str, style: str = "") -> str:
    """プロンプトを改善"""
    from manaos_core_api import ManaOSCoreAPI
    
    manaos = ManaOSCoreAPI()
    
    improvement_prompt = f"""以下の画像生成プロンプトを改善してください。
スタイル: {style if style else "指定なし"}

元のプロンプト: {prompt}

改善されたプロンプトのみを返してください:"""
    
    result = manaos.act("base_ai_chat", {
        "prompt": improvement_prompt,
        "use_free": True
    })
    
    if result.get("result") and result["result"].get("response"):
        return result["result"]["response"].strip()
    
    return prompt
```

### トレンド検索関数

```python
def search_trending_prompts(topic: str) -> list:
    """最新のプロンプトトレンドを検索"""
    from manaos_core_api import ManaOSCoreAPI
    
    manaos = ManaOSCoreAPI()
    
    result = manaos.act("brave_search", {
        "query": f"{topic} stable diffusion prompt 2024",
        "count": 10,
        "search_lang": "jp"
    })
    
    if result.get("status") == "success":
        return result.get("results", [])
    
    return []
```

---

## 🎉 まとめ

統合したBrave Search APIとBase AI APIを活用することで：

1. ✅ **プロンプト生成の自動化**: AI支援で高品質なプロンプトを生成
2. ✅ **トレンド調査の効率化**: Brave Searchで最新情報を取得
3. ✅ **ワークフローの改善**: 検索 → 生成 → 改善のパイプライン構築

**どんどん活用していきましょう！** 🚀

