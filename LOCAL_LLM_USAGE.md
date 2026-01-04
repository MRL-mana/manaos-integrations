# ローカルLLMの使い方（Cursorチャットから）

## 🚀 すぐに使う

### 基本的な使い方

```python
from local_llm_helper import ask

# 質問する
answer = ask("Pythonでリストをソートする方法を教えて", model="llama3.2:3b")
print(answer)
```

### 会話形式で使う

```python
from local_llm_helper import chat

# 会話履歴付き
result = chat(
    model="qwen3:4b",
    messages=[
        {"role": "user", "content": "こんにちは"},
        {"role": "assistant", "content": "こんにちは！何かお手伝いできることはありますか？"},
        {"role": "user", "content": "Pythonのリスト内包表記を教えて"}
    ]
)
print(result["message"]["content"])
```

---

## 📋 利用可能な関数

### `ask(question, model="qwen3:4b")`
最も簡単な質問関数

```python
from local_llm_helper import ask

answer = ask("PythonでHello Worldを出力するコードを書いて", model="llama3.2:3b")
```

### `chat(model, message, messages, stream, timeout)`
会話形式で使う関数

```python
from local_llm_helper import chat

result = chat(
    model="qwen3:4b",
    message="こんにちは"
)
```

### `generate(model, prompt, stream, timeout)`
テキスト生成用

```python
from local_llm_helper import generate

result = generate(
    model="qwen3:4b",
    prompt="Pythonで関数を定義する方法："
)
```

### `list_models()`
インストール済みモデル一覧

```python
from local_llm_helper import list_models

models = list_models()
print(models)
```

### `check_status()`
Ollamaの状態確認

```python
from local_llm_helper import check_status

status = check_status()
print(status)
```

---

## 🎯 推奨モデル

### 軽量・高速（推奨）
- `llama3.2:3b` - 最も軽量、高速応答
- `qwen3:4b` - バランス型

### 中型（高品質）
- `qwen2.5:14b` - より高品質な回答
- `llama3.1:8b` - バランス型

### 大型（最高品質）
- `qwen2.5:32b` - 高品質な生成
- `llama3.1:70b` - 最高品質（時間がかかる）

### コード生成専用
- `deepseek-coder:6.7b` - コード生成に特化
- `qwen2.5-coder:32b` - 高品質なコード生成

---

## 💡 使用例

### 例1: コード生成

```python
from local_llm_helper import ask

code = ask("Pythonでクイックソートを実装して", model="deepseek-coder:6.7b")
print(code)
```

### 例2: 説明を求める

```python
from local_llm_helper import ask

explanation = ask("Pythonのデコレータについて説明して", model="qwen2.5:14b")
print(explanation)
```

### 例3: 会話を続ける

```python
from local_llm_helper import chat

# 1回目の質問
result1 = chat(model="qwen3:4b", message="Pythonのリストとは？")
print(result1["message"]["content"])

# 2回目の質問（会話履歴付き）
result2 = chat(
    model="qwen3:4b",
    messages=[
        {"role": "user", "content": "Pythonのリストとは？"},
        {"role": "assistant", "content": result1["message"]["content"]},
        {"role": "user", "content": "タプルとの違いは？"}
    ]
)
print(result2["message"]["content"])
```

---

## 🔧 Cursorチャットから使う

Cursorのチャットで「ローカルLLMで〇〇について聞いて」と指示すれば、自動的に呼び出します。

例：
- 「ローカルLLMでPythonのデコレータについて説明してもらって」
- 「ローカルLLMでコードレビューしてもらって」
- 「ローカルLLMで〇〇について聞いて、llama3.2:3bを使って」

---

## 📊 状態確認

```python
from local_llm_helper import check_status

status = check_status()
print(f"状態: {status['status']}")
print(f"利用可能なモデル数: {len(status['available_models'])}")
print(f"実行中のモデル: {status['running_models']}")
```

---

## ⚠️ 注意事項

1. **タイムアウト**: モデルのロードに時間がかかる場合があります（特に大型モデル）
2. **メモリ**: 大型モデルは多くのメモリを使用します
3. **初回起動**: モデルの初回ロードには時間がかかります

---

## 🎉 まとめ

**最も簡単な使い方：**

```python
from local_llm_helper import ask
answer = ask("質問内容", model="llama3.2:3b")
print(answer)
```

これだけでローカルLLMを使えます！

