# 🔑 Slack Webhook URL

## 📋 Webhook URL

```
https://hooks.slack.com/services/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
```

---

## ✅ n8nに設定

### Step 1: HTTP Requestノードを開く

1. **n8n UI: http://localhost:5678**
2. **ワークフローを開く**
3. **「Slack通知」ノード（HTTP Request）をクリック**

---

### Step 2: URLを設定

1. **URLフィールドをクリック**
2. **以下を入力**:
   ```
   https://hooks.slack.com/services/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
   ```
3. **「Save」をクリック**

---

### Step 3: 設定確認

- ✅ **URL**: 上記のWebhook URL
- ✅ **Method**: POST
- ✅ **Send Body**: ON
- ✅ **Specify Body**: Using JSON
- ✅ **JSON Body**: `{{ { "text": $json.message } }}`

---

### Step 4: テスト実行

1. **HTTP Requestノードをクリック**
2. **右上の「Execute step」をクリック**
3. **Slackチャンネルを確認**

---

## 🎯 次のステップ

Slack接続確認後:

1. **Browse AIアカウント作成**（30分）
2. **Browse AIロボット作成**（30分）
3. **Browse AI Webhook設定**（5分）
4. **テスト実行**（10分）

---

**Webhook URLをn8nに設定してください！**🔥


