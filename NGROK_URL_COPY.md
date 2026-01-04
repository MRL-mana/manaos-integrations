# 🔗 ngrok URL取得ガイド

## 🎯 現在の状態

**ngrokトンネル作成中...**

---

## ✅ 次のステップ

### Step 1: ngrokの出力を確認

**新しいウィンドウでngrokが起動しました。**

**出力例**:
```
ngrok                                                                            

Session Status                online
Account                       Your Account (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Latency                       45ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://xxxx-xxxx-xxxx.ngrok-free.app -> http://localhost:5678

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

---

### Step 2: URLをコピー

**重要なURL**:
```
https://xxxx-xxxx-xxxx.ngrok-free.app/webhook/browse-ai-webhook
```

**注意**: `xxxx-xxxx-xxxx`の部分は実際のngrok URLに置き換えてください。

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

**または、サービスとして実行**:
```powershell
ngrok service install
ngrok service start
```

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

- `START_NGROK.md` - ngrokトンネル作成ガイド
- `BROWSE_AI_WEBHOOK_SETUP.md` - Webhook設定ガイド
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

**ngrok URLをコピーして、Browse AIに設定してください！**🔥

