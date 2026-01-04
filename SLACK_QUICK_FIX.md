# ⚡ Slack接続クイック修正

## 🎯 問題

n8nからSlack Webhookに接続できない

---

## ✅ 確認・修正手順

### 1. Webhook URL確認（30秒）

**n8nのHTTP Requestノードで確認**:

1. **HTTP Requestノードを開く**
2. **URLフィールドを確認**
3. **正しい形式か確認**:
   ```
   https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
   ```

**問題がある場合**:
- `YOUR/WEBHOOK/URL` のようなプレースホルダーが残っていないか
- URLが正しくコピーされているか

---

### 2. PowerShellで直接テスト（1分）

**テストスクリプト実行**:

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\test_slack_webhook.ps1
```

**または手動テスト**:

```powershell
$webhookUrl = "YOUR_SLACK_WEBHOOK_URL"
$body = '{"text":"テストメッセージ"}'
Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $body -ContentType "application/json"
```

**成功した場合**: Slackにメッセージが届く → n8nの設定を確認
**失敗した場合**: Webhook URLを再確認

---

### 3. n8nの設定確認（1分）

#### 3.1 HTTP Requestノード設定

- ✅ **URL**: 正しいWebhook URL
- ✅ **Method**: POST
- ✅ **Send Body**: ON
- ✅ **Specify Body**: Using JSON
- ✅ **JSON Body**: `{{ { "text": $json.message } }}`

#### 3.2 テスト実行

1. **HTTP Requestノードをクリック**
2. **右上の「Execute step」をクリック**
3. **エラーメッセージを確認**

---

### 4. よくあるエラーと解決策

#### エラー: 401 Unauthorized

**原因**: Webhook URLが無効

**解決策**:
1. Slack App設定を確認: https://api.slack.com/apps
2. 「Incoming Webhooks」を開く
3. Webhook URLを再コピー
4. n8nに再設定

---

#### エラー: 404 Not Found

**原因**: Webhook URLが間違っている

**解決策**:
- URLを再確認
- プレースホルダーが残っていないか確認

---

#### エラー: Connection Error

**原因**: ネットワーク接続の問題

**解決策**:
- インターネット接続を確認
- ファイアウォール設定を確認
- プロキシ設定を確認

---

## 🧪 テスト手順

### Step 1: PowerShellでテスト

```powershell
$webhookUrl = "YOUR_SLACK_WEBHOOK_URL"
$body = '{"text":"テストメッセージ"}'
Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $body -ContentType "application/json"
```

**成功したら**: n8nの設定を確認
**失敗したら**: Webhook URLを再確認

---

### Step 2: n8nでテスト

1. **HTTP Requestノードをクリック**
2. **「Execute step」をクリック**
3. **結果を確認**

---

## 📚 関連ファイル

- `test_slack_webhook.ps1` - テストスクリプト
- `SLACK_CONNECTION_TROUBLESHOOTING.md` - 詳細トラブルシューティング

---

**まずはPowerShellで直接テストして、Webhook URLが正しいか確認してください！**🔥


