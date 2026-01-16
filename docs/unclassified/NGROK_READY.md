# ✅ ngrokセットアップ完了！

## 🎯 現在の状態

**ngrokがインストールされました！** ✅

**インストール場所**: `C:\Users\mana4\Desktop\ngrok\ngrok.exe`

---

## 🚀 次のステップ

### Step 1: ngrokでトンネルを作成

**新しいウィンドウでngrokが起動しました。**

**または、手動で実行する場合**:

```powershell
cd C:\Users\mana4\Desktop\ngrok
.\ngrok.exe http 5678
```

---

### Step 2: URLをコピー

**ngrokウィンドウで出力されたURLを確認**:

```
Forwarding  https://xxxx-xxxx-xxxx.ngrok-free.app -> http://localhost:5678
```

**このURLに `/webhook/browse-ai-webhook` を追加**:

```
https://xxxx-xxxx-xxxx.ngrok-free.app/webhook/browse-ai-webhook
```

**例**:
```
https://abc123-def456.ngrok-free.app/webhook/browse-ai-webhook
```

---

### Step 3: Browse AIに設定

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

### ngrokを常時起動する場合

**ngrokウィンドウを閉じないでください。**

**または、ショートカットを作成**:

1. **デスクトップにショートカットを作成**
2. **リンク先**: `powershell.exe -NoExit -Command "cd C:\Users\mana4\Desktop\ngrok; .\ngrok.exe http 5678"`
3. **名前**: `ngrokトンネル`

---

## 🧪 テスト手順

### Step 1: ngrok URLを確認

**ngrokウィンドウで出力されたURLを確認**:
```
Forwarding  https://xxxx-xxxx-xxxx.ngrok-free.app -> http://localhost:5678
```

### Step 2: Browse AIに設定

1. **Browse AIダッシュボード → ロボット選択**
2. **「統合する」タブ**
3. **「Webhooks」を選択**
4. **Webhook URLにngrok URLを入力**
5. **保存**

### Step 3: テスト実行

1. **Browse AIでロボットを実行**
2. **ngrokのWeb UI（http://localhost:4040）でリクエストを確認**
3. **n8nのワークフローでデータを受信**
4. **Slack通知が届くか確認**

---

## 📚 関連ファイル

- `setup_ngrok.ps1` - ngrokセットアップスクリプト
- `START_NGROK.md` - ngrokトンネル作成ガイド
- `NGROK_URL_COPY.md` - ngrok URL取得ガイド
- `CURRENT_STATUS.md` - 現在の進捗状況

---

## ⚠️ 注意事項

### ngrok無料プランの制限

- **セッション時間**: 2時間（自動切断）
- **同時接続数**: 1つ
- **リクエスト数**: 制限あり

**長時間使用する場合**: ngrok有料プランまたは代替サービスを検討

---

### セキュリティ

- **ngrok URLは公開される**: 誰でもアクセス可能
- **認証を追加**: n8nワークフローで認証を設定することを推奨

---

## 🎊 完了！

**ngrokセットアップが完了しました！**

**次のステップ**: ngrokウィンドウで出力されたURLを確認して、Browse AIに設定してください！🔥

