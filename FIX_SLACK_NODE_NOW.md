# 🔧 Slack通知ノード修正（今すぐ）

## 🎯 現在のエラー

Slack通知ノードで以下の必須フィールドが未設定：
- **"Credential to connect with"** （認証情報）
- **"Send Message To"** （送信先）

---

## ✅ 解決方法：HTTP Requestノードに変更（推奨）

Slackノードは認証が複雑なので、**HTTP Requestノード**に変更します。

### Step 1: Slack通知ノードを削除

1. **「Slack通知」ノードをクリック**
2. **Deleteキーを押す**、または右クリック → 「Delete」

---

### Step 2: HTTP Requestノードを追加

1. **「通知判定」ノードの出力（true側）をクリック**
2. **「+」ボタンをクリック**
3. **「HTTP Request」を検索して選択**

---

### Step 3: HTTP Requestノードを設定

1. **ノード名を変更**: "Slack通知"に変更
2. **設定**:
   - **URL**: `={{ $env.SLACK_WEBHOOK_URL }}`
     - または直接: `https://hooks.slack.com/services/YOUR/WEBHOOK/URL`
   - **Method**: POST
   - **Send Body**: ON
   - **Specify Body**: JSON
   - **JSON Body**: 
     ```json
     {{ { "text": $json.message } }}
     ```

---

### Step 4: 接続を確認

1. **「通知判定」ノードの出力（true側）** → **「Slack通知」ノード**に接続
2. **「Obsidian保存」ノード**はそのまま（false側に接続）

---

## 🎯 環境変数設定（後で）

Slack Webhook URLを環境変数に設定：

```powershell
$env:SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

または、n8n UIで直接URLを入力してもOK。

---

## ✅ 完了後の確認

1. **すべてのノードが接続されている**
2. **エラーアイコンがない**
3. **「Save」をクリック**

---

## 📚 詳細

- `FIX_WORKFLOW_ERRORS.md` - エラー修正ガイド
- `browse_ai_manaos_integration_simple.json` - シンプル版ワークフロー（参考）

---

**HTTP Requestノードに変更すれば、認証不要で動作します！**🔥



