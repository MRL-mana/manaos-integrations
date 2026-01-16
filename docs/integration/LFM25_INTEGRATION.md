# LFM 2.5統合ガイド

**Liquid AI LFM 2.5**をManaOSに統合しました。これは「小型モデルの勝ち筋」を現実にしたモデルです。

---

## 🎯 LFM 2.5とは？

### 特徴

- **1.2Bパラメータ**（超小型）
- **GPT-3.5級の日本語スコア**
- **CPU前提で超高速**（GPU不要）
  - 入力：1万トークン/秒超
  - 出力：数百トークン/秒
- **日本語が「おまけ」じゃない**（最初から多言語を同等に扱う構造）

### なぜ「画期的」なのか？

1. **性能密度が異常**: 同じ1.2Bでも実質パラメータ効率が高い
2. **CPU前提で速い**: クラウド前提モデルでは出ない設計思想
3. **日本語が強い**: 日本語特化モデルより実使用で強い

---

## 🚀 セットアップ

### 1. OllamaでLFM 2.5をインストール

```bash
# OllamaにLFM 2.5を追加
ollama pull lfm2.5:1.2b
```

**注意**: 現在、LFM 2.5はOllama公式モデルライブラリにまだ追加されていない可能性があります。以下の方法で追加できます：

#### 方法1: Modelfileを使用（推奨）

```bash
# Modelfileを作成
cat > Modelfile << EOF
FROM liquidai/lfm2.5:1.2b
TEMPLATE """{{ .Prompt }}"""
PARAMETER temperature 0.8
PARAMETER top_p 0.9
PARAMETER top_k 40
EOF

# モデルを作成
ollama create lfm2.5:1.2b -f Modelfile
```

#### 方法2: 直接ダウンロード（Hugging Face経由）

```bash
# Hugging FaceからダウンロードしてOllamaに追加
# （詳細はLiquid AIの公式ドキュメントを参照）
```

### 2. LM Studioで使用する場合

LM StudioでLFM 2.5モデルをダウンロードし、モデル名を`lfm2.5:1.2b`に設定してください。

---

## 📐 使用方法

### 基本的な使い方

```python
from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType

client = AlwaysReadyLLMClient()

# LFM 2.5を使用（超軽量・超高速）
response = client.chat(
    "こんにちは！短く挨拶してください。",
    model=ModelType.ULTRA_LIGHT,  # LFM 2.5
    task_type=TaskType.CONVERSATION
)

print(response.response)
print(f"レイテンシ: {response.latency_ms:.2f}ms")
```

### 常駐軽量LLMとして使用（オフライン会話・下書き・整理）

```python
# lightweight_conversationタスクタイプを使用
response = client.chat(
    "今日のタスクを整理してください",
    model=ModelType.ULTRA_LIGHT,
    task_type=TaskType.LIGHTWEIGHT_CONVERSATION  # 専用タスクタイプ
)
```

### LLMルーティングシステム経由で使用

```python
from llm_routing import LLMRouter

router = LLMRouter()

# conversationタスク（自動的にLFM 2.5が優先される）
result = router.route(
    task_type="conversation",
    prompt="こんにちは、今日はいい天気ですね。"
)

# lightweight_conversationタスク（常駐軽量LLM専用）
result = router.route(
    task_type="lightweight_conversation",
    prompt="メモを整理してください"
)
```

---

## ⚙️ 設定

### LLMルーティング設定（`llm_routing_config.yaml`）

```yaml
routing:
  conversation:
    # LFM 2.5がprimary（最優先）
    primary: "lfm2.5:1.2b"
    fallback:
      - "llama3.2:3b"
      - "qwen2.5:7b"
    priority: "latency"
    max_tokens: 2048
    temperature: 0.7
  
  lightweight_conversation:
    # 常駐軽量LLM専用タスクタイプ
    primary: "lfm2.5:1.2b"
    fallback:
      - "llama3.2:3b"
      - "llama3.2:1b"
    priority: "latency"
    max_tokens: 1024
    temperature: 0.8
```

### タスクタイプの使い分け

| タスクタイプ | 用途 | Primaryモデル | 特徴 |
|------------|------|--------------|------|
| `conversation` | 日常対話、雑談、質問応答 | LFM 2.5 | 軽量・高速・レスポンス最優先 |
| `lightweight_conversation` | オフライン会話・下書き・整理 | LFM 2.5 | 常駐軽量LLM専用、CPU前提 |
| `reasoning` | 複雑な判断、分析、計画立案 | Qwen 2.5 72B | 重い・強い・品質最優先 |
| `automation` | タスク実行、コード生成 | Qwen 2.5 14B | ツール呼び出し得意 |

---

## 🎯 使用例

### 例1: オフライン会話

```python
from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType

client = AlwaysReadyLLMClient()

# オフラインで会話（LFM 2.5が自動選択）
response = client.chat(
    "今日の天気について話しましょう",
    model=ModelType.ULTRA_LIGHT,
    task_type=TaskType.LIGHTWEIGHT_CONVERSATION
)
```

### 例2: 下書き作成

```python
# 下書きをLFM 2.5で作成（高速）
response = client.chat(
    "ブログ記事の下書きを作成してください。テーマは「AIの未来」です。",
    model=ModelType.ULTRA_LIGHT,
    task_type=TaskType.LIGHTWEIGHT_CONVERSATION
)
```

### 例3: テキスト整理

```python
# メモを整理（LFM 2.5で高速処理）
response = client.chat(
    "以下のメモを整理してください：\n- タスク1\n- タスク2\n- タスク3",
    model=ModelType.ULTRA_LIGHT,
    task_type=TaskType.LIGHTWEIGHT_CONVERSATION
)
```

---

## 🔧 トラブルシューティング

### LFM 2.5が利用できない場合

1. **Ollamaが起動しているか確認**
   ```bash
   # Windows
   Get-Process ollama
   
   # Linux/Mac
   systemctl status ollama
   ```

2. **モデルがインストールされているか確認**
   ```bash
   ollama list | grep lfm
   ```

3. **モデルをインストール**
   ```bash
   ollama pull lfm2.5:1.2b
   ```

### Fallbackが動作する場合

LFM 2.5が利用できない場合、自動的にfallbackモデル（llama3.2:3b等）に切り替わります。これは正常な動作です。

---

## 📊 パフォーマンス

### 期待される性能

- **レイテンシ**: 100-300ms（CPU前提）
- **スループット**: 
  - 入力：1万トークン/秒超
  - 出力：数百トークン/秒
- **メモリ使用量**: 約2-4GB（CPU前提）

### ベンチマーク

- **日本語スコア**: GPT-3.5級
- **パラメータ**: 1.2B（超小型）
- **CPU使用率**: 中程度（常時起動可能）

---

## 🎉 まとめ

LFM 2.5は「自分のPCに住んでるAI」を現実にするモデルです。

**特徴**:
- ✅ 超軽量（1.2B）
- ✅ 超高速（CPU前提）
- ✅ 日本語が強い
- ✅ 常時起動可能

**用途**:
- オフライン会話
- 下書き作成
- テキスト整理
- メモ作成
- 軽量タスク

**ManaOSとの相性**:
- 常時起動 ✅
- 低コスト ✅
- ローカル主軸 ✅
- 役割分担AI ✅

---

**最終更新**: 2025-01-28
