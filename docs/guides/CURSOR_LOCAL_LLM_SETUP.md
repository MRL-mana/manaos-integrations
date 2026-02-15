# 🚀 Cursor × ローカルLLM 接続完全ガイド

**マナ仕様：母艦ローカルLLM常駐前提の最短ルート**

---

## 🎯 ゴール設計

```
Cursor = 実装・編集の司令塔
ローカルLLM = 常駐コーディング脳（補完/チャット/リファクタ/レビュー）
ManaOS = 仕事を回す実行基盤（RAG、ログ、タスク、通知、n8n、etc）
```

**つまり👇**
- コードを書く場所：**Cursor**
- 考える人：**ローカルLLM**
- 実行＆運用：**ManaOS**

---

## 📋 構成は2択（マナ向け推奨順）

### A) いちばんラク：**LM Studio（OpenAI互換サーバー）** ⭐推奨

**特徴**:
- WindowsでGUIぽちぽちで立つ
- **OpenAI互換のURL**が出せる（Cursorが繋ぎやすい）
- 設定が簡単で迷わない

**おすすめ**：まずはこれで"接続成功"まで最短で到達

### B) ガチ運用：**Ollama（ローカル常駐）**

**特徴**:
- 軽い、速い、管理楽
- モデル切替もCLIで簡単
- ただしCursor側の繋ぎ方は環境によって当たり外れある（※OpenAI互換プロキシ噛ませると勝ち）

**おすすめ**：Aで動いたらBに移行（これが事故らない）

---

## 🔧 手順1：LM StudioでローカルLLMを立てる

### ステップ1-1：LM Studioのインストール

1. **LM Studioをダウンロード**
   - https://lmstudio.ai/ からWindows版をダウンロード
   - インストール（デフォルト設定でOK）

### ステップ1-2：モデルをダウンロード

1. **LM Studioを起動**
2. **「Search」タブ**でモデルを検索
3. **推奨モデル（常駐用）**をダウンロード：
   - `Qwen2.5-Coder-7B-Instruct`（軽量・コード特化）
   - `DeepSeek-Coder-6.7B-Instruct`（軽量・コード特化）
   - `Qwen2.5-Coder-14B-Instruct`（中量・高品質）

**注意**：RTX 5080なら7B〜14Bで"ヌルヌル運用"が正義

### ステップ1-3：サーバーを起動

1. **「Server」タブ**に移動
2. **「Select a model to load」**で先ほどダウンロードしたモデルを選択
   - 例：`Qwen2.5-Coder-7B-Instruct`
3. **「Start Server」**をクリック
4. **「OpenAI Compatible」**のエンドポイントを確認
   - 通常は `http://127.0.0.1:1234/v1` になる
5. **「Server is running」**が表示されればOK

### ステップ1-4：接続確認（オプション）

PowerShellで確認：

```powershell
# エンドポイント確認
curl http://127.0.0.1:1234/v1/models

# チャットテスト
curl http://127.0.0.1:1234/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "model": "Qwen2.5-Coder-7B-Instruct",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

---

## 🔧 手順2：CursorにローカルLLMを登録

### ステップ2-1：Cursorの設定を開く

1. **Cursorを起動**
2. **`Ctrl + ,`** で設定を開く
   - または `File → Preferences → Settings`

### ステップ2-2：LLM設定を開く

1. 設定の検索バーで **「LLM」** または **「Model」** を検索
2. **「Cursor Settings: LLM」** または **「Model」** を開く

### ステップ2-3：カスタムLLMを追加

**方法A：UIから設定（Cursor最新版）**

1. **「Add Custom Model」** または **「+」** ボタンをクリック
2. 以下の情報を入力：
   - **Provider**: `OpenAI Compatible` または `Custom`
   - **Base URL**: `http://127.0.0.1:1234/v1`
   - **API Key**: `lm-studio`（適当でOK、LM Studioは空でも通る場合あり）
   - **Model Name**: `Qwen2.5-Coder-7B-Instruct`（ダウンロードしたモデル名）

**方法B：設定ファイルから直接編集**

1. **設定ファイルの場所**を確認：
   ```
   %APPDATA%\Cursor\User\settings.json
   ```
2. 以下の設定を追加：

```json
{
  "cursor.general.enableLocalLLM": true,
  "cursor.llm.customModels": [
    {
      "name": "Qwen2.5-Coder-7B-Instruct",
      "provider": "openai-compatible",
      "baseUrl": "http://127.0.0.1:1234/v1",
      "apiKey": "lm-studio"
    }
  ],
  "cursor.llm.defaultModel": "Qwen2.5-Coder-7B-Instruct"
}
```

### ステップ2-4：Cursorを再起動

1. **Cursorを完全に終了**
2. **再起動**
3. 設定が反映されているか確認

---

## 🔧 手順3：接続テスト

### ステップ3-1：Cursorでチャットを開く

1. **`Ctrl + L`** でチャットを開く
2. 簡単な質問を入力：
   ```
   こんにちは！接続できていますか？
   ```
3. ローカルLLMから応答が返ってくれば成功！

### ステップ3-2：コード補完をテスト

1. 新しいファイルを作成（例：`test.py`）
2. コードを書いてみる：
   ```python
   def hello():
       # ここでCtrl+Spaceで補完が効くか確認
   ```
3. ローカルLLMからの補完が表示されれば成功！

---

## 🔧 手順4：Ollamaを使う場合（LM Studioの代替）

### ステップ4-1：Ollamaをインストール

1. **Ollamaをダウンロード**
   - https://ollama.ai/ からWindows版をダウンロード
   - インストール（デフォルト設定でOK）

### ステップ4-2：モデルをダウンロード

PowerShellで実行：

```powershell
# 常駐用（軽量・コード特化）
ollama pull qwen2.5-coder:7b

# または中量版
ollama pull qwen2.5-coder:14b
```

### ステップ4-3：OpenAI互換プロキシを立てる（重要）

Ollamaは直接OpenAI互換ではないので、プロキシが必要。

**方法A：ollama-openai-proxyを使う（推奨）**

```powershell
# ollama-openai-proxyをインストール
pip install ollama-openai-proxy

# プロキシを起動（ポート1234でOpenAI互換APIを提供）
ollama-openai-proxy --port 1234
```

**方法B：litellmを使う**

```powershell
# litellmをインストール
pip install litellm

# プロキシを起動
litellm --model ollama/qwen2.5-coder:7b --port 1234
```

### ステップ4-4：Cursorに登録

LM Studioと同じ手順で、以下の設定を追加：

```json
{
  "cursor.llm.customModels": [
    {
      "name": "qwen2.5-coder:7b",
      "provider": "openai-compatible",
      "baseUrl": "http://127.0.0.1:1234/v1",
      "apiKey": "ollama"
    }
  ]
}
```

---

## 🎯 モデル選び（RTX 5080前提）

### 常駐用（7B〜14B）⭐推奨

| モデル | VRAM | 速度 | 用途 |
|--------|------|------|------|
| **Qwen2.5-Coder-7B** | ~4GB | ⚡⚡⚡ | コード補完・軽量チャット |
| **DeepSeek-Coder-6.7B** | ~4GB | ⚡⚡⚡ | コード補完・軽量チャット |
| **Qwen2.5-Coder-14B** | ~8GB | ⚡⚡ | コード生成・中規模チャット |

**推奨**：まずは **Qwen2.5-Coder-7B** で"ヌルヌル運用"を確認

### 高精度用（20B〜32B）

| モデル | VRAM | 速度 | 用途 |
|--------|------|------|------|
| **Qwen2.5-Coder-32B** | ~20GB | ⚡ | 複雑なコード生成・設計 |
| **DeepSeek-Coder-33B** | ~20GB | ⚡ | 複雑なコード生成・設計 |

**推奨**：常駐は7B〜14B、重いタスクは32Bを"必要時のみ"呼ぶ

---

## 🚨 つまずきポイント先回り

### ❌ Cursorが接続できない

**原因1：Base URLが間違っている**
- ✅ 確認：`http://127.0.0.1:1234/v1` の `/v1` が付いているか
- ✅ 修正：必ず `/v1` を付ける

**原因2：Firewallでローカル遮断**
- ✅ 確認：Windows Firewallで `localhost:1234` が許可されているか
- ✅ 修正：一時的にFirewallを無効化してテスト

**原因3：LM Studio/Ollamaが起動していない**
- ✅ 確認：LM Studioの「Server」タブで「Server is running」が表示されているか
- ✅ 修正：サーバーを起動

### ❌ 遅い

**原因1：モデルが重すぎる**
- ✅ 確認：VRAM使用量を確認（タスクマネージャー）
- ✅ 修正：7B〜14Bに変更

**原因2：Context長すぎ**
- ✅ 確認：Cursorの設定で `max_tokens` を確認
- ✅ 修正：2048以下に設定

**原因3：量子化が重い**
- ✅ 確認：モデルの量子化レベル（Q4/Q8）
- ✅ 修正：Q4に変更（軽量化）

### ❌ 回答が薄い

**原因1：汎用モデルを使っている**
- ✅ 確認：モデル名に「Coder」が含まれているか
- ✅ 修正：Coder系モデルに変更

**原因2：プロンプトが不十分**
- ✅ 確認：プロンプトテンプレートを使用しているか
- ✅ 修正：後述のテンプレートを使用

### ❌ 長文で迷子

**原因1：出力フォーマットが固定されていない**
- ✅ 確認：プロンプトに出力フォーマットを指定しているか
- ✅ 修正：後述のテンプレートを使用

---

## 📝 次のステップ

接続成功したら、次は以下を実装：

1. ✅ **モデル最適化**（常駐用/高精度用の2段構成）
2. ✅ **ManaOS統合**（難易度ルーティング）
3. ✅ **運用ルール確立**（プロンプトテンプレート化）

---

## 🔗 関連ファイル

- `CURSOR_PROMPT_TEMPLATES.md` - プロンプトテンプレート集
- `CURSOR_MODEL_RECOMMENDATIONS.md` - モデル選定ガイド
- `MANAOS_LLM_ROUTING.md` - ManaOS統合設計

---

**これで接続成功まで到達！次は運用ルールを詰めよう🔥**



















