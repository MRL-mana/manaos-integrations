# LLMモデルアップグレードガイド

**現在のモデル**: `llama3.2:3b`（軽量・高速）  
**推奨アップグレード**: `qwen2.5:14b`（バランス型・高品質）

---

## 🎯 推奨モデル

### 1. qwen2.5:14b（推奨）

**特徴**:
- ✅ **バランス型**: 性能と速度のバランスが良い
- ✅ **高品質生成**: より正確な応答
- ✅ **ツール使用得意**: コード生成・データ処理に強い
- ✅ **メモリ**: 約8GB（中程度）

**用途**: 会話・タグ推定・コード生成・データ処理

### 2. qwen2.5:7b（軽量版）

**特徴**:
- ✅ **軽量**: 約4GB（軽量）
- ✅ **高速**: レスポンスが速い
- ✅ **性能向上**: llama3.2:3bより高性能

**用途**: 会話・軽量タスク

### 3. llama3.1:8b（バランス型）

**特徴**:
- ✅ **バランス型**: 性能と速度のバランス
- ✅ **安定性**: 高い安定性

**用途**: 会話・タスク実行

---

## 📋 モデル比較

| モデル | サイズ | 性能 | 速度 | 推奨用途 |
|--------|--------|------|------|---------|
| llama3.2:3b（現在） | 約2GB | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 会話・軽量タスク |
| qwen2.5:7b | 約4GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 会話・軽量タスク |
| qwen2.5:14b（推奨） | 約8GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 会話・高品質生成・ツール使用 |
| llama3.1:8b | 約5GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 会話・タスク実行 |

---

## 🚀 アップグレード手順

### Step 1: モデルをインストール

```powershell
# qwen2.5:14bをインストール（推奨）
ollama pull qwen2.5:14b

# または、軽量版（qwen2.5:7b）
ollama pull qwen2.5:7b
```

### Step 2: Slack Integrationの設定変更

**ファイル**: `slack_integration.py`

**変更前**:
```python
response = LLM_CLIENT.chat(
    text,
    model=ModelType.LIGHT,  # llama3.2:3b
    task_type=TaskType.CONVERSATION
)
```

**変更後**:
```python
response = LLM_CLIENT.chat(
    text,
    model=ModelType.MEDIUM,  # qwen2.5:14b
    task_type=TaskType.CONVERSATION
)
```

**または、直接指定**:
```python
response = LLM_CLIENT.chat(
    text,
    model="qwen2.5:14b",  # 直接指定
    task_type=TaskType.CONVERSATION
)
```

### Step 3: File Secretaryの設定変更

**ファイル**: `file_secretary_organizer.py`

**変更前**:
```python
def __init__(self, db: FileSecretaryDB, ollama_url: str = "http://localhost:11434", model: str = "llama3.2:3b"):
```

**変更後**:
```python
def __init__(self, db: FileSecretaryDB, ollama_url: str = "http://localhost:11434", model: str = "qwen2.5:14b"):
```

### Step 4: always_ready_llm_clientの設定変更（オプション）

**ファイル**: `always_ready_llm_client.py`

**変更前**:
```python
class ModelType(Enum):
    LIGHT = "llama3.2:3b"      # 軽量・高速
    MEDIUM = "qwen2.5:14b"     # バランス型
```

**変更後**（既に設定済み）:
```python
class ModelType(Enum):
    LIGHT = "llama3.2:3b"      # 軽量・高速
    MEDIUM = "qwen2.5:14b"     # バランス型 ← 既に設定済み
```

### Step 5: サービスを再起動

```powershell
# Slack Integrationを再起動
Get-Process python | Where-Object { $_.CommandLine -like "*slack_integration.py*" } | Stop-Process
python slack_integration.py

# File Secretaryを再起動（必要に応じて）
```

---

## 🧪 テスト方法

### 1. モデルがインストールされているか確認

```powershell
ollama list
```

### 2. モデルを直接テスト

```powershell
ollama run qwen2.5:14b "こんにちは、今日はいい天気ですね。"
```

### 3. Slack Integrationでテスト

Slackでメッセージを送信して、応答の品質を確認

### 4. File Secretaryでテスト

ファイルを整理して、タグ推定の精度を確認

---

## 💡 パフォーマンス比較

### llama3.2:3b（現在）

- **レスポンス時間**: 1-3秒
- **メモリ使用量**: 約2GB
- **精度**: ⭐⭐⭐（会話・タグ推定には十分）

### qwen2.5:14b（推奨）

- **レスポンス時間**: 2-5秒
- **メモリ使用量**: 約8GB
- **精度**: ⭐⭐⭐⭐⭐（より正確な応答）

---

## 🎯 推奨設定

### パフォーマンス重視

**設定**: `qwen2.5:14b`  
**用途**: 会話・タグ推定・コード生成  
**メリット**: より正確な応答・ツール使用得意

### 速度重視

**設定**: `qwen2.5:7b`  
**用途**: 会話・軽量タスク  
**メリット**: 高速・軽量・性能向上

### バランス型

**設定**: `llama3.1:8b`  
**用途**: 会話・タスク実行  
**メリット**: バランス・安定性

---

## 📝 注意事項

1. **メモリ使用量**: より高性能なモデルはメモリを多く使用します
2. **レスポンス時間**: モデルが大きいほどレスポンス時間が長くなります
3. **インストール時間**: モデルのダウンロードに時間がかかります

---

## 🎉 結論

**推奨アップグレード**: `qwen2.5:14b`

- ✅ バランス型（性能と速度）
- ✅ 高品質生成
- ✅ ツール使用得意
- ✅ 会話・タグ推定に最適

**現在の`llama3.2:3b`でも十分動作していますが、`qwen2.5:14b`にアップグレードするとより正確な応答が期待できます！** 🚀

