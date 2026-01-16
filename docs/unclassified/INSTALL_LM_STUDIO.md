# LM Studio インストールガイド

## 📥 インストール手順

### ステップ1: LM Studioをダウンロード

1. **公式サイトにアクセス**
   - URL: https://lmstudio.ai/
   - または直接ダウンロード: https://lmstudio.ai/download

2. **Windows版をダウンロード**
   - 「Download for Windows」をクリック
   - インストーラー（`.exe`）をダウンロード

### ステップ2: インストール

1. ダウンロードしたインストーラーを実行
2. インストールウィザードに従って進む
3. 通常のインストール場所：
   - `C:\Users\<ユーザー名>\AppData\Local\Programs\LM Studio`
   - または `C:\Program Files\LM Studio`

### ステップ3: 初回起動と設定

1. **LM Studioを起動**
   - デスクトップまたはスタートメニューから起動

2. **モデルをダウンロード（推奨）**
   - 「Search」タブでモデルを検索
   - 推奨モデル：
     - **Qwen2.5-Coder-7B-Instruct**（軽量・高速・コーディング特化）
     - **DeepSeek-Coder-6.7B-Instruct**（コーディング特化）
     - **Qwen2.5-Coder-14B-Instruct**（より高精度、VRAMに余裕がある場合）

3. **モデルをダウンロード**
   - モデル名をクリック
   - 「Download」をクリック
   - ダウンロード完了まで待機

---

## 🚀 サーバー起動設定

### ステップ1: サーバータブを開く

1. LM Studioの上部タブから「**Server**」をクリック

### ステップ2: モデルを選択

1. ダウンロードしたモデルを選択
2. 推奨設定：
   - **Context Length**: 4096 または 8192（デフォルトでOK）
   - **Threads**: 自動（CPUコア数に応じて）

### ステップ3: サーバーを起動

1. 「**Start Server**」ボタンをクリック
2. サーバーが起動すると、以下の情報が表示されます：
   - `Server running on http://localhost:1234`
   - `OpenAI Compatible API` が有効になっている

---

## ✅ インストール確認

インストールが完了したら、以下で確認できます：

```powershell
# インストール確認
.\check_running_status.ps1

# または直接確認
Invoke-WebRequest -Uri "http://localhost:1234/v1/models" -Method GET
```

---

## 🔧 トラブルシューティング

### インストールが完了しない場合
- 管理者権限で実行してみる
- ウイルス対策ソフトがブロックしていないか確認
- 十分なディスク容量があるか確認（モデルは数GB〜数十GB必要）

### サーバーが起動しない場合
- LM Studioを再起動
- ポート1234が他のアプリケーションで使用されていないか確認
- ファイアウォールの設定を確認

### モデルがダウンロードできない場合
- インターネット接続を確認
- Hugging Faceのアカウントが必要な場合があります（通常は不要）
- 十分なディスク容量があるか確認

---

## 📝 次のステップ

LM Studioのインストールとサーバー起動が完了したら：

1. **CursorでローカルLLMを使用**
   - Cursorの設定で `http://localhost:1234/v1` を設定済み
   - モデルを選択して使用開始

2. **MCPサーバー経由でLLMルーティングを使用**
   - CursorのMCP設定で `llm_routing_mcp_server` が有効
   - ツール経由でLLMルーティング機能を使用可能

3. **API経由でLLMルーティングを使用**
   - `http://localhost:9501/api/llm/route` でルーティングAPIを使用
   - `http://localhost:9500/api/llm/route` で統合API経由でも使用可能

---

**インストール完了後、LM Studioサーバーを起動すれば完全運用開始です！🎉**



















