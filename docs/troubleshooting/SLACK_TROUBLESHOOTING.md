# Slack返信がない問題のトラブルシューティング

## ✅ 確認済み

1. **Slack Webhook URL**: 正常動作（ステータス200）
2. **ローカルLLM**: 正常動作
3. **Slack Integration**: 起動中（ポート5114）

## 🔍 問題の可能性

### 1. Slack Events APIの設定

Slack Appの設定で以下を確認してください：

1. **Event Subscriptions**が有効になっているか
2. **Request URL**が正しく設定されているか
   - 例: `http://your-domain.com/api/slack/events`
   - または: ngrok経由のURL

### 2. Slack Appの権限設定

以下のスコープが必要です：
- `app_mentions:read` - Botメンションを読み取る
- `chat:write` - メッセージを送信する
- `im:read` - DMを読み取る
- `im:write` - DMを送信する

### 3. BotのメンションまたはDM

現在の実装では、以下の場合のみ返信します：
- Botへのメンション（`@bot_name こんにちは`）
- BotへのDM（直接メッセージ）

## 🚀 テスト方法

### 方法1: Webhook直接送信テスト

```python
python test_slack_webhook_direct.py
```

これでSlackにメッセージが送信されるか確認できます。

### 方法2: APIエンドポイント直接テスト

```powershell
curl -X POST http://localhost:5114/api/slack/webhook `
  -H "Content-Type: application/json" `
  -d '{\"text\": \"こんにちは\", \"user\": \"test_user\", \"channel\": \"test\"}'
```

### 方法3: Slack Events APIテスト

Slack Appの設定で、Event SubscriptionsのRequest URLに以下を設定：
- ローカル: `http://localhost:5114/api/slack/events`（ngrok経由が必要）
- または: ngrok URL + `/api/slack/events`

## 💡 解決方法

### 1. ngrokで公開する（推奨）

```powershell
# ngrokを起動
ngrok http 5114

# 表示されたURLをSlack AppのEvent Subscriptionsに設定
# 例: https://xxxx-xxxx-xxxx.ngrok.io/api/slack/events
```

### 2. Botにメンションする

SlackでBotにメンションして会話：
```
@bot_name こんにちは
```

### 3. BotにDMを送る

Botに直接メッセージを送る：
```
こんにちは
```

## 📊 現在の状態

| 項目 | 状態 | 詳細 |
|------|------|------|
| Slack Webhook URL | ✅ 動作中 | ステータス200 |
| ローカルLLM | ✅ 動作中 | GPUモード |
| Slack Integration | ✅ 起動中 | ポート5114 |
| Event Subscriptions | ⚠️ 要確認 | Slack App設定を確認 |

---

**Slack Appの設定を確認して、Event Subscriptionsを有効にしてください！**
