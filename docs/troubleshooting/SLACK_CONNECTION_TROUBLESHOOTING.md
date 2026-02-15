# 🔧 Slack接続トラブルシューティング

## 🎯 問題

n8nからSlack Webhookに接続できない

---

## ✅ 確認ポイント

### 1. Webhook URL確認

**正しい形式**:
```
https://hooks.slack.com/services/<YOUR>/<WEBHOOK>/<URL>
```

**確認事項**:
- ✅ `https://hooks.slack.com/services/` で始まっているか
- ✅ `/` で区切られた3つの部分があるか
- ✅ `YOUR/WEBHOOK/URL` のようなプレースホルダーが残っていないか

---

### 2. n8nのHTTP Requestノード設定確認

#### 2.1 URL設定

1. **HTTP Requestノードを開く**
2. **URLフィールドを確認**:
   - **Expressionモード**: `{{ $env.SLACK_WEBHOOK_URL }}`
   - **Fixedモード**: 直接URL
3. **URLが正しく入力されているか確認**

#### 2.2 Method確認

- **Method**: **POST**になっているか確認

#### 2.3 Body設定確認

- **Send Body**: **ON**になっているか
- **Specify Body**: **Using JSON**になっているか
- **JSON Body**: `{{ { "text": $json.message } }}` になっているか

---

### 3. テスト実行

#### 3.1 n8nでテスト実行

1. **HTTP Requestノードをクリック**
2. **右上の「Execute step」をクリック**
3. **エラーメッセージを確認**

#### 3.2 エラーメッセージ確認

**よくあるエラー**:

- **401 Unauthorized**: Webhook URLが無効
- **404 Not Found**: Webhook URLが間違っている
- **Connection Error**: ネットワーク接続の問題

---

## 🔧 解決方法

### 方法A: Webhook URLを再確認

1. **Slack App設定を確認**:
   - https://api.slack.com/apps
   - 「Incoming Webhooks」を開く
   - Webhook URLを再コピー

2. **n8nのURLフィールドに再設定**

---

### 方法B: 直接テスト

**PowerShellでテスト**:

```powershell
$webhookUrl = "https://hooks.slack.com/services/<YOUR>/<WEBHOOK>/<URL>"
$body = @{
    text = "テストメッセージ"
} | ConvertTo-Json

Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $body -ContentType "application/json"
```

**成功した場合**: Slackにメッセージが届く
**失敗した場合**: エラーメッセージを確認

---

### 方法C: n8nのログ確認

1. **n8n UI: http://127.0.0.1:5678**
2. **「Executions」タブを開く**
3. **最新の実行を確認**
4. **エラーメッセージを確認**

---

### 方法D: 簡易テストワークフロー作成

1. **新しいワークフローを作成**
2. **「Manual Trigger」ノードを追加**
3. **「HTTP Request」ノードを追加**
4. **設定**:
   - URL: Slack Webhook URL
   - Method: POST
   - Send Body: ON
   - JSON Body: `{{ { "text": "テスト" } }}`
5. **実行してテスト**

---

## 💡 よくある問題と解決策

### 問題1: Webhook URLが無効

**解決策**:
- Slack AppでWebhook URLを再生成
- 新しいURLをコピーして設定

---

### 問題2: 環境変数が設定されていない

**解決策**:
- URLを直接入力（Fixedモード）
- または環境変数を設定:
  ```powershell
  $env:SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/<YOUR>/<WEBHOOK>/<URL>"
  ```

---

### 問題3: JSON Bodyの形式が間違っている

**正しい形式**:
```json
{{ { "text": $json.message } }}
```

**間違った形式**:
```json
{{ $json.message }}  // これは間違い
```

---

### 問題4: n8nから外部接続がブロックされている

**解決策**:
- ファイアウォール設定を確認
- プロキシ設定を確認

---

## 🧪 テスト手順

### Step 1: PowerShellで直接テスト

```powershell
$webhookUrl = "YOUR_SLACK_WEBHOOK_URL"
$body = @{
    text = "テストメッセージ from PowerShell"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $body -ContentType "application/json"
    Write-Host "OK: Slackにメッセージを送信しました" -ForegroundColor Green
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Webhook URLを確認してください" -ForegroundColor Yellow
}
```

---

### Step 2: n8nでテスト実行

1. **HTTP Requestノードをクリック**
2. **「Execute step」をクリック**
3. **結果を確認**

---

## 📚 関連ファイル

- `GET_SLACK_WEBHOOK.md` - Webhook URL取得ガイド
- `QUICK_FIX_STEPS.md` - クイック修正手順

---

**まずはPowerShellで直接テストして、Webhook URLが正しいか確認してください！**🔥


