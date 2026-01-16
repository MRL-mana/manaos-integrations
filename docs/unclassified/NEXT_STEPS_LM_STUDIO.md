# 🚀 LM Studio 次のステップ

## ✅ インストール完了

LM Studio バージョン 0.3.36 がインストール済みです！

---

## 📋 サーバー起動手順

LM Studioが起動したら、以下の手順でサーバーを開始してください：

### ステップ1: モデルをダウンロード（初回のみ）

1. LM Studioの「**Search**」タブをクリック
2. 推奨モデルを検索：
   - **Qwen2.5-Coder-7B-Instruct**（軽量・高速・コーディング特化）
   - **DeepSeek-Coder-6.7B-Instruct**（コーディング特化）
3. モデル名をクリックして「**Download**」をクリック
4. ダウンロード完了まで待機（数GB〜数十GB、時間がかかります）

### ステップ2: サーバーを起動

1. LM Studioの上部タブから「**Server**」をクリック
2. ダウンロードしたモデルを選択
3. 設定を確認：
   - **Context Length**: 4096 または 8192（デフォルトでOK）
   - **Threads**: 自動（CPUコア数に応じて）
4. 「**Start Server**」ボタンをクリック
5. サーバーが起動すると、以下のような表示が確認できます：
   - `Server running on http://localhost:1234`
   - `OpenAI Compatible API` が有効になっている

---

## ✅ 起動確認

サーバーが起動したら、以下で確認できます：

```powershell
# すべてのサービスを確認
.\check_running_status.ps1

# または直接確認
Invoke-WebRequest -Uri "http://localhost:1234/v1/models" -Method GET
```

**期待される結果：**
- ✅ LM Studioサーバー: 起動中
- ✅ LLMルーティングAPI: 起動中 (`http://localhost:9501`)
- ✅ 統合APIサーバー: 起動中 (`http://localhost:9500`)

---

## 🎯 完全運用開始

すべてのサービスが起動したら：

### 1. CursorでローカルLLMを使用

Cursorの設定で既に `http://localhost:1234/v1` が設定済みです。
- Cursorの設定を開く
- モデルを選択して使用開始

### 2. MCPサーバー経由でLLMルーティングを使用

CursorのMCP設定で `llm_routing_mcp_server` が有効です。
- ツール経由でLLMルーティング機能を使用可能
- 難易度に応じて自動的に適切なモデルを選択

### 3. API経由でLLMルーティングを使用

- `http://localhost:9501/api/llm/route` でルーティングAPIを使用
- `http://localhost:9500/api/llm/route` で統合API経由でも使用可能

---

## 🔧 トラブルシューティング

### サーバーが起動しない場合
- LM Studioの「Server」タブでエラーメッセージを確認
- ポート1234が他のアプリケーションで使用されていないか確認
- LM Studioを再起動して再試行

### モデルがダウンロードできない場合
- インターネット接続を確認
- 十分なディスク容量があるか確認（モデルは数GB〜数十GB必要）
- Hugging Faceのアカウントが必要な場合があります（通常は不要）

### 接続できない場合
- ファイアウォールでローカル接続がブロックされていないか確認
- `http://localhost:1234/v1/models` にブラウザでアクセスして確認

---

## 📝 推奨モデル一覧

### 常駐用（軽量・高速）
- **Qwen2.5-Coder-7B-Instruct**（推奨）
- **DeepSeek-Coder-6.7B-Instruct**

### 高精度用（重いけど賢い）
- **Qwen2.5-Coder-14B-Instruct**（VRAMに余裕がある場合）
- **DeepSeek-Coder-33B-Instruct**（VRAMに十分な余裕がある場合）

---

**LM Studioサーバーを起動すれば完全運用開始です！🎉**



















