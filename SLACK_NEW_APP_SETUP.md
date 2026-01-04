# Slack App新規作成時の設定手順

## 🎯 現在の状態

Slack Appを新規作成中で、Event Subscriptionsの設定でURL検証が必要です。

---

## ✅ 設定手順

### Step 1: Slack Integrationの起動確認

Slack Integrationが起動していることを確認してください。

**確認方法:**
```powershell
Test-NetConnection -ComputerName localhost -Port 5114
```

**起動していない場合:**
```powershell
$config = Get-Content "notification_hub_enhanced_config.json" | ConvertFrom-Json
$env:SLACK_WEBHOOK_URL = $config.slack_webhook_url
$env:PORT = "5114"
$env:FILE_SECRETARY_URL = "http://localhost:5120"
$env:ORCHESTRATOR_URL = "http://localhost:5106"
Start-Process python -ArgumentList "slack_integration.py" -WindowStyle Normal
```

---

### Step 2: ngrok URLの設定

**Slack Appの「Event Subscriptions」ページで:**

1. **「Enable Events」をONにする**
2. **「Request URL」に以下を入力:**
   ```
   https://unrevetted-terrie-organometallic.ngrok-free.dev/api/slack/events
   ```
3. **「リトライ」ボタンをクリック**

**Slackが自動的にURL検証を行います:**
- ✅ 成功すると「Verified」と表示されます
- ❌ 失敗する場合は、Slack Integrationが起動しているか確認してください

---

### Step 3: Bot Eventsを追加

1. **「Subscribe to bot events」セクションを開く**
2. **「Add Bot User Event」をクリック**
3. **以下を追加:**
   - `app_mentions` - Botメンション
   - `message.im` - DM（直接メッセージ）
4. **「Save Changes」をクリック**

---

### Step 4: Verification Token設定（後で）

**Slack Appの設定が完了したら:**

1. **「Basic Information」→「App Credentials」を開く**
2. **「Verification Token」をコピー**
3. **環境変数に設定:**
   ```powershell
   $env:SLACK_VERIFICATION_TOKEN = "your_verification_token"
   ```
4. **Slack Integrationを再起動**

---

## 🔍 URL検証が失敗する場合

### 確認事項

1. **Slack Integrationが起動しているか**
   ```powershell
   Test-NetConnection -ComputerName localhost -Port 5114
   ```

2. **ngrokが起動しているか**
   - ngrokのターミナルウィンドウを確認
   - http://localhost:4040 にアクセス

3. **URLが正しいか**
   - `/api/slack/events`が含まれているか
   - ngrok URLが最新か（ngrokを再起動すると変わる）

### 解決方法

1. **Slack Integrationを再起動**
2. **ngrokを再起動して新しいURLを取得**
3. **Slack Appの「Request URL」を更新**

---

## 🎉 設定完了後

設定が完了したら、SlackでBotにメンションまたはDMを送って、返信があるか確認してください。

---

**Slack Integrationを起動して、URL検証を再試行してください！**

