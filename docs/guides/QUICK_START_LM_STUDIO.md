# LM Studioサーバー起動ガイド

## 🚀 クイックスタート

### 現在の状態
- ✅ LLMルーティングAPI: 起動中 (`http://localhost:9501`)
- ✅ 統合APIサーバー: 起動中 (`http://localhost:9500`)
- ⚠️  LM Studioサーバー: **手動起動が必要**

---

## 📋 LM Studioサーバー起動手順

### ステップ1: LM Studioを起動
1. LM Studioアプリケーションを起動
2. モデルを選択（推奨: Qwen2.5-Coder-7B-Instruct または DeepSeek-Coder-6.7B）

### ステップ2: サーバーを開始
1. LM Studioの上部タブから「**Server**」をクリック
2. モデルが選択されていることを確認
3. 「**Start Server**」ボタンをクリック
4. サーバーが起動すると、以下のような表示が確認できます：
   - `Server running on http://localhost:1234`
   - `OpenAI Compatible API` が有効になっている

### ステップ3: 起動確認
以下のコマンドで確認できます：

```powershell
.\check_running_status.ps1
```

または、ブラウザで以下にアクセス：
- `http://localhost:1234/v1/models`

---

## ✅ 完全運用開始の確認

すべてのサービスが起動していることを確認：

```powershell
# すべてのサービスを確認
.\check_running_status.ps1
```

**期待される結果：**
- ✅ LM Studioサーバー: 起動中
- ✅ LLMルーティングAPI: 起動中
- ✅ 統合APIサーバー: 起動中

---

## 🎯 次のステップ

LM Studioサーバーが起動したら：

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

## 🔧 トラブルシューティング

### LM Studioが見つからない場合
- LM Studioがインストールされているか確認
- 通常のインストール場所：
  - `C:\Users\<ユーザー名>\AppData\Local\Programs\LM Studio`
  - `C:\Program Files\LM Studio`

### サーバーが起動しない場合
- LM Studioの「Server」タブでエラーメッセージを確認
- ポート1234が他のアプリケーションで使用されていないか確認
- LM Studioを再起動して再試行

### 接続できない場合
- ファイアウォールでローカル接続がブロックされていないか確認
- `http://localhost:1234/v1/models` にブラウザでアクセスして確認

---

## 📝 自動起動について

LM StudioはGUIアプリケーションのため、自動起動は設定されていません。
必要に応じて、WindowsのスタートアップフォルダにLM Studioのショートカットを追加してください。

---

**準備完了！LM Studioサーバーを起動すれば完全運用開始です！🎉**



















