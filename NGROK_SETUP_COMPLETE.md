# ✅ ngrok設定完了！

## 🎯 現在の状態

**authtokenが設定されました！** ✅

**設定ファイル**: `C:\Users\mana4\AppData\Local\ngrok\ngrok.yml`

**ngrokが起動しています！** ✅

---

## 🚀 次のステップ

### Step 1: ngrokのURLを確認

**ngrokウィンドウで出力されたURLを確認**:

```
Forwarding  https://xxxx-xxxx-xxxx.ngrok-free.app -> http://localhost:5678
```

**または、ngrokのWeb UIで確認**:
- **URL**: http://localhost:4040
- **表示内容**: Forwarding URL、リクエスト履歴、レスポンス詳細

---

### Step 2: Browse AIに設定

**ngrokのURLに `/webhook/browse-ai-webhook` を追加**:

```
https://xxxx-xxxx-xxxx.ngrok-free.app/webhook/browse-ai-webhook
```

**例**:
```
https://abc123-def456.ngrok-free.app/webhook/browse-ai-webhook
```

---

### Step 3: Browse AIで設定

1. **Browse AIダッシュボードにログイン**
2. **ロボットを選択**（または新規作成）
3. **「統合する」または「Integrations」タブを開く**
4. **「Webhooks」を選択**
5. **Webhook URLに以下を入力**:
   ```
   https://xxxx-xxxx-xxxx.ngrok-free.app/webhook/browse-ai-webhook
   ```
   （実際のngrok URLに置き換える）
6. **「Save」または「Add」をクリック**

---

## 🧪 テスト手順

### Step 1: n8nのワークフローを確認

**n8nのワークフロー**:
1. **n8nにアクセス**: http://localhost:5678
2. **「browse_ai_manaos_integration」ワークフローを開く**
3. **Webhookノードを確認**
4. **ワークフローを有効化**

---

### Step 2: Browse AIでテスト実行

1. **Browse AIでロボットを実行**
2. **ngrokのWeb UI（http://localhost:4040）でリクエストを確認**
3. **n8nのワークフローでデータを受信**
4. **Slack通知が届くか確認**

---

## 💡 ヒント

### ngrokのWeb UIで確認

**ngrokのWeb UIにアクセス**:
- **URL**: http://localhost:4040
- **表示内容**: 
  - Forwarding URL
  - リクエスト履歴
  - レスポンス詳細

---

### ngrokを停止する場合

**ngrokウィンドウで**:
- `Ctrl + C` を押す

**または、PowerShellで**:
```powershell
Get-Process ngrok | Stop-Process
```

---

### ngrokを再起動する場合

**PowerShellで実行**:

```powershell
cd C:\Users\mana4\Desktop\ngrok
.\ngrok.exe http 5678
```

**または、スクリプトを使用**:

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\start_ngrok_simple.ps1
```

---

## ⚠️ 注意事項

### ngrok無料プランの制限

- **セッション時間**: 2時間（自動切断）
- **同時接続数**: 1つ
- **リクエスト数**: 制限あり

**長時間使用する場合**: ngrok有料プランまたは代替サービスを検討

---

### セキュリティ

- **authtokenは機密情報**: 他人に共有しないでください
- **Gitにコミットしない**: `.gitignore`に`ngrok.yml`を追加

---

## 📚 関連ファイル

- `SET_NGROK_AUTHTOKEN.md` - ngrok authtoken設定手順
- `NGROK_TROUBLESHOOTING.md` - ngrokトラブルシューティングガイド
- `start_ngrok_simple.ps1` - ngrok簡単起動スクリプト

---

## 🎊 完了！

**ngrok設定が完了しました！**

**次のステップ**: ngrokウィンドウで出力されたURLを確認して、Browse AIに設定してください！🔥


