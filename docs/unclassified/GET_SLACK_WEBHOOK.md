# 📥 Slack Webhook URL取得ガイド（3分）

## 🎯 目的

Slack Webhook URLを取得して、n8nのHTTP Requestノードに設定します。

---

## ✅ 手順

### Step 1: Slack App作成（1分）

1. **ブラウザで開く**: https://api.slack.com/apps
2. **「Create New App」をクリック**
3. **「From scratch」を選択**
4. **設定**:
   - **App Name**: "ManaOS Browse AI"
   - **Pick a workspace**: ワークスペースを選択
5. **「Create App」をクリック**

---

### Step 2: Incoming Webhooks有効化（1分）

1. **左メニュー「Incoming Webhooks」をクリック**
2. **「Activate Incoming Webhooks」をONにする**（トグルスイッチ）
3. **「Add New Webhook to Workspace」をクリック**
4. **チャンネル選択**: 
   - #general を選択（または任意のチャンネル）
   - 複数チャンネルに送信したい場合は後で追加可能
5. **「Allow」をクリック**

---

### Step 3: Webhook URLをコピー（30秒）

1. **「Webhook URL」が表示されます**
2. **URLをコピー**:
   ```
   https://hooks.slack.com/services/<YOUR>/<WEBHOOK>/<URL>
   ```
3. **メモ帳などに保存**（一時的に）

---

### Step 4: n8nに設定（30秒）

1. **n8n UI: http://localhost:5678**
2. **ワークフローを開く**
3. **「Slack通知」ノード（HTTP Request）をクリック**
4. **URLフィールドをクリック**
5. **コピーしたWebhook URLを貼り付け**
6. **「Save」をクリック**

---

## ✅ 完了確認

- [ ] Slack App作成済み
- [ ] Incoming Webhooks有効化済み
- [ ] Webhook URL取得済み
- [ ] n8nのHTTP Requestノードに設定済み
- [ ] 保存完了

---

## 💡 ヒント

### 環境変数を使用する場合

1. **URLフィールドを「Expression」モードに切り替え**
2. **以下を入力**:
   ```
   {{ $env.SLACK_WEBHOOK_URL }}
   ```
3. **PowerShellで環境変数を設定**:
   ```powershell
   $env:SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/<YOUR>/<WEBHOOK>/<URL>"
   ```

**注意**: 環境変数はセッション終了で消えるので、永続化する場合はシステム環境変数に設定してください。

---

## 🎯 次のステップ

Webhook URL設定完了後:

1. **Browse AIアカウント作成**（30分）
2. **Browse AIロボット作成**（30分）
3. **Browse AI Webhook設定**（5分）
4. **テスト実行**（10分）

---

**3分で完了します！**🔥


