# Slack Integration設定用URL

## ✅ ngrok URL確認

**ngrok URL:**
```
https://unrevetted-terrie-organometallic.ngrok-free.dev
```

**Slack Events API URL:**
```
https://unrevetted-terrie-organometallic.ngrok-free.dev/api/slack/events
```

**✅ クリップボードにコピー済み**

---

## 🔧 Slack Appの設定手順

### Step 1: Event Subscriptionsを有効化

1. **https://api.slack.com/apps にアクセス**
2. **あなたのSlack Appを選択**
3. **「Event Subscriptions」を開く**
4. **「Enable Events」をONにする**

### Step 2: Request URLを設定

1. **「Request URL」フィールドに以下を貼り付け:**
   ```
   https://unrevetted-terrie-organometallic.ngrok-free.dev/api/slack/events
   ```

2. **Slackが自動的に検証します**
   - ✅ 成功すると「Verified」と表示されます
   - ❌ 失敗する場合は、Slack Integrationが起動しているか確認してください

### Step 3: Bot Eventsを追加

1. **「Subscribe to bot events」セクションを開く**
2. **「Add Bot User Event」をクリック**
3. **以下を追加:**
   - `app_mentions` - Botメンション
   - `message.im` - DM（直接メッセージ）

4. **「Save Changes」をクリック**

---

## 🔑 Verification Token設定

### Step 1: Tokenを取得

1. **「Basic Information」→「App Credentials」を開く**
2. **「Verification Token」をコピー**

### Step 2: 環境変数に設定

```powershell
$env:SLACK_VERIFICATION_TOKEN = "your_verification_token"
```

### Step 3: Slack Integrationを再起動

```powershell
# 既存のプロセスを停止
Get-Process python | Where-Object {$_.CommandLine -like "*slack_integration.py*"} | Stop-Process -Force

# 再起動
$config = Get-Content "notification_hub_enhanced_config.json" | ConvertFrom-Json
$env:SLACK_WEBHOOK_URL = $config.slack_webhook_url
$env:SLACK_VERIFICATION_TOKEN = "your_token"
$env:PORT = "5114"
$env:FILE_SECRETARY_URL = "http://localhost:5120"
$env:ORCHESTRATOR_URL = "http://localhost:5106"
Start-Process python -ArgumentList "slack_integration.py" -WindowStyle Normal
```

---

## 🧪 動作確認

### 1. SlackでBotにメンション

```
@bot_name こんにちは
```

### 2. BotにDMを送る

```
こんにちは
```

### 3. 返信を確認

Botから返信が来れば成功です！

---

## ⚠️ 注意事項

- ngrokのURLは、ngrokを起動するたびに変わります
- ngrokを停止すると、URLは無効になります
- 常時利用する場合は、ngrokの有料プラン（固定URL）を検討してください

---

**Slack Appの設定を完了すれば、Slackで会話できるようになります！**

