# Slack Integration公開設定（簡単版）

## 🚀 ngrok起動

ngrokを起動しました。以下の手順で設定してください。

---

## 📋 手順

### Step 1: ngrok URLを確認

**ngrokのターミナルウィンドウで、以下のような行を探してください：**
```
Forwarding  https://xxxx-xxxx-xxxx.ngrok.io -> http://localhost:5114
```

**このURL（`https://xxxx-xxxx-xxxx.ngrok.io`）をコピーしてください。**

または、ブラウザで http://localhost:4040 にアクセスして確認できます。

---

### Step 2: Slack Appの設定

1. **https://api.slack.com/apps にアクセス**
2. **あなたのSlack Appを選択**
3. **「Event Subscriptions」を開く**
4. **「Enable Events」をONにする**
5. **「Request URL」に以下を設定:**
   ```
   https://xxxx-xxxx-xxxx.ngrok.io/api/slack/events
   ```
   （実際のngrok URLに置き換える）

6. **「Subscribe to bot events」で以下を追加:**
   - `app_mentions` - Botメンション
   - `message.im` - DM（直接メッセージ）

7. **「Save Changes」をクリック**

---

### Step 3: Verification Token設定

1. **「Basic Information」→「App Credentials」を開く**
2. **「Verification Token」をコピー**
3. **PowerShellで設定:**
   ```powershell
   $env:SLACK_VERIFICATION_TOKEN = "your_verification_token"
   ```
4. **Slack Integrationを再起動**

---

## 🧪 動作確認

SlackでBotにメンションまたはDMを送って、返信があるか確認してください。

---

## 💡 ヒント

- ngrokのURLは、ngrokを起動するたびに変わります
- ngrokを停止すると、URLは無効になります
- 常時利用する場合は、ngrokの有料プラン（固定URL）を検討してください

---

**ngrokのターミナルウィンドウでURLを確認して、Slack Appに設定してください！**

