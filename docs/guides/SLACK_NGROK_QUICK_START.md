# Slack Integration ngrok公開 クイックスタート

## 🚀 現在の状態

ngrokを起動しました。数秒待ってから確認してください。

---

## 📋 確認方法

### 方法1: ngrokのWeb UIで確認（推奨）

1. **ブラウザで開く**: http://127.0.0.1:4040
2. **「Forwarding」セクションを確認**
3. **表示されたURLをコピー**（例: `https://xxxx-xxxx-xxxx.ngrok.io`）

### 方法2: ngrokのターミナルウィンドウで確認

ngrokを起動したPowerShellウィンドウで、以下のような行を探してください：
```
Forwarding  https://xxxx-xxxx-xxxx.ngrok.io -> http://127.0.0.1:5114
```

このURLをコピーしてください。

---

## 🔧 Slack Appの設定

### Step 1: Event Subscriptionsを有効化

1. **https://api.slack.com/apps にアクセス**
2. **あなたのSlack Appを選択**
3. **「Event Subscriptions」を開く**
4. **「Enable Events」をONにする**

### Step 2: Request URLを設定

1. **「Request URL」フィールドに以下を入力:**
   ```
   https://xxxx-xxxx-xxxx.ngrok.io/api/slack/events
   ```
   （実際のngrok URLに置き換える）

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
$env:FILE_SECRETARY_URL = "http://127.0.0.1:5120"
$env:ORCHESTRATOR_URL = "http://127.0.0.1:5106"
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

## ⚠️ トラブルシューティング

### ngrokのWeb UIに接続できない場合

1. **ngrokが起動しているか確認**
   ```powershell
   Get-Process ngrok
   ```

2. **数秒待ってから再度アクセス**
   - ngrokの起動に時間がかかることがあります

3. **ngrokのターミナルウィンドウを確認**
   - エラーメッセージがないか確認

### Slack Events APIの検証が失敗する場合

1. **Slack Integrationが起動しているか確認**
   ```powershell
   Test-NetConnection -ComputerName localhost -Port 5114
   ```

2. **ngrok URLが正しいか確認**
   - `/api/slack/events`が含まれているか

3. **Slack Integrationを再起動**

---

## 🎉 完了

**ngrok経由でSlack Integrationを公開する準備ができました！**

次のステップ:
1. ngrok URLを確認（http://127.0.0.1:4040 またはターミナルウィンドウ）
2. Slack AppのEvent Subscriptionsに設定
3. Verification Tokenを設定
4. Slack Integrationを再起動
5. 動作確認

これで安全に公開できます！
