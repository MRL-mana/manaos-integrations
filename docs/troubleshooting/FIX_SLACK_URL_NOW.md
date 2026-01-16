# 🔧 Slack URL設定修正（今すぐ）

## 🎯 問題

URLフィールドで環境変数エラー: `[ERROR: access to env vars denied]`

---

## ✅ 解決方法

### Step 1: URLフィールドを「Fixed」モードに切り替え

1. **URLフィールドの右側にある「Expression」をクリック**
2. **「Fixed」を選択**

---

### Step 2: Webhook URLを直接入力

1. **URLフィールドをクリック**
2. **以下を直接入力（コピー&ペースト）**:
   ```
   https://hooks.slack.com/services/<YOUR>/<WEBHOOK>/<URL>
   ```
3. **「Save」をクリック**

---

### Step 3: 設定確認

- ✅ **URL**: `https://hooks.slack.com/services/<YOUR>/<WEBHOOK>/<URL>`（Fixedモード）
- ✅ **Method**: POST
- ✅ **Send Body**: ON
- ✅ **Body Content Type**: JSON
- ✅ **Specify Body**: Using JSON
- ✅ **JSON Body**: `{{ { "text": $json.message } }}`

---

### Step 4: テスト実行

1. **右上の「Execute step」ボタンをクリック**
2. **Slackチャンネルを確認**

---

## 💡 環境変数を使いたい場合（オプション）

n8nで環境変数を使うには、n8nの設定ファイル（`.n8n/config`)で環境変数を許可する必要があります。

**簡単な方法**: URLを直接入力する方が確実です。

---

## 📚 関連ファイル

- `SLACK_WEBHOOK_URL.md` - Webhook URL設定ガイド

---

**URLフィールドを「Fixed」モードに切り替えて、Webhook URLを直接入力してください！**🔥


