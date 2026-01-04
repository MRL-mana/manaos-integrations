# Slack Integration公開設定完了

## ✅ 設定完了

ngrok経由でSlack Integrationを公開する準備ができました。

---

## 🚀 次のステップ

### Step 1: ngrok URLを確認

ngrokのWeb UIにアクセス:
- **URL**: http://localhost:4040
- **表示内容**: Forwarding URL（例: `https://xxxx-xxxx-xxxx.ngrok.io`）

または、ngrokのターミナルウィンドウに表示されたURLを確認してください。

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
3. **環境変数に設定:**
   ```powershell
   $env:SLACK_VERIFICATION_TOKEN = "your_verification_token"
   ```
4. **Slack Integrationを再起動:**
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

## 🔒 セキュリティ対策

✅ **実装済み:**
- Verification Token検証
- Botメッセージ無視
- ログ記録

✅ **ngrok経由:**
- HTTPS自動
- 一時的な公開（必要時のみ）

---

## 📊 現在の状態

| 項目 | 状態 | 詳細 |
|------|------|------|
| Slack Integration | ✅ 起動中 | ポート5114 |
| ngrok | ✅ 起動中 | ポート5114を公開 |
| Verification Token | ⚠️ 要設定 | Slack Appから取得 |
| Event Subscriptions | ⚠️ 要設定 | Slack Appで設定 |

---

## 🎉 完了

**ngrok経由でSlack Integrationを公開する準備ができました！**

次のステップ:
1. ngrok URLを確認
2. Slack AppのEvent Subscriptionsに設定
3. Verification Tokenを設定
4. Slack Integrationを再起動
5. 動作確認

これで安全に公開できます！

