# ⚡ クイック修正手順（3分）

## 🎯 今すぐやること

### 1. Slack通知ノードを削除（30秒）

1. **「Slack通知」ノードをクリック**
2. **Deleteキーを押す**

---

### 2. HTTP Requestノードを追加（1分）

1. **「通知判定」ノードの出力（true側）をクリック**
2. **「+」ボタンをクリック**
3. **検索ボックスに「HTTP Request」と入力**
4. **「HTTP Request」を選択**

---

### 3. HTTP Requestノードを設定（1分）

1. **ノード名**: "Slack通知"に変更
2. **URL**: 
   ```
   {{ $env.SLACK_WEBHOOK_URL }}
   ```
   または直接:
   ```
   https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   ```
3. **Method**: POST
4. **Send Body**: ON
5. **Specify Body**: JSON
6. **JSON Body**:
   ```json
   {{ { "text": $json.message } }}
   ```

---

### 4. 接続確認（30秒）

1. **「通知判定」ノード** → **「Slack通知」ノード**に接続されているか確認
2. **「Obsidian保存」ノード**はそのまま（false側）

---

### 5. 保存（10秒）

1. **「Save」をクリック**（右上）
2. **エラーがないか確認**

---

## ✅ 完了！

これでワークフローが動作します。

**次のステップ**: Browse AIアカウント作成 → Slack Webhook URL取得 → テスト実行

---

**3分で修正完了！**🔥



