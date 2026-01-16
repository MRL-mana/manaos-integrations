# 🧪 Browse AI統合テストガイド

## ✅ 現在の状態

**設定完了**:
- ✅ ngrok起動中
- ✅ n8nワークフロー設定済み
- ✅ Slack Webhook設定済み
- ✅ Browse AI Webhook URL設定済み

**Browse AI設定**:
- Webhook URL: `https://unrevetted-terrie-organometallic.ngrok-free.app/webhook/browse-ai-webhook`
- トリガー: 「タスクは完了しました」

---

## 🚀 テスト手順

### Step 1: n8nのワークフローを確認

**n8nにアクセス**:
- **URL**: http://localhost:5678
- **ワークフロー**: `browse_ai_manaos_integration`

**確認項目**:
1. **ワークフローが有効化されているか確認**
2. **WebhookノードのURLを確認**
3. **Slack通知ノードの設定を確認**

---

### Step 2: Browse AIでロボットを実行

**Browse AIダッシュボードで**:
1. **ロボットを選択**
2. **「実行」または「Run」をクリック**
3. **ロボットが完了するまで待つ**

**期待される動作**:
- Browse AIがデータを収集
- タスク完了時にWebhookがn8nに送信される

---

### Step 3: ngrokのWeb UIで確認

**ngrokのWeb UIにアクセス**:
- **URL**: http://localhost:4040

**確認項目**:
1. **リクエスト履歴を確認**
2. **Browse AIからのリクエストが表示されているか確認**
3. **レスポンスステータスを確認**（200 OKが理想）

---

### Step 4: n8nのワークフローで確認

**n8nのワークフローで**:
1. **ワークフローを開く**
2. **各ノードの実行状態を確認**
3. **データが正しく流れているか確認**

**確認項目**:
- **Webhookノード**: データを受信しているか
- **Codeノード**: データが正しく整形されているか
- **Ifノード**: 重要度判定が正しく動作しているか
- **HTTP Requestノード**: ManaOS判断APIに送信されているか
- **Slackノード**: 通知が送信されているか

---

### Step 5: Slack通知を確認

**Slackで確認**:
1. **設定したSlackチャンネルを開く**
2. **Browse AIからの通知が届いているか確認**

**通知内容**:
- ロボット名
- 検出された情報
- 重要度スコア
- URL

---

## 🔍 トラブルシューティング

### 問題1: ngrokのWeb UIにリクエストが表示されない

**原因**:
- Browse AIからWebhookが送信されていない
- ngrokが起動していない

**解決方法**:
1. **ngrokが起動しているか確認**
2. **Browse AIのWebhook URLが正しいか確認**
3. **Browse AIでロボットを再実行**

---

### 問題2: n8nのワークフローでデータが流れない

**原因**:
- WebhookノードのURLが正しくない
- ワークフローが有効化されていない

**解決方法**:
1. **WebhookノードのURLを確認**
2. **ワークフローを有効化**
3. **n8nを再起動**

---

### 問題3: Slack通知が届かない

**原因**:
- Slack Webhook URLが正しくない
- 重要度スコアが5未満

**解決方法**:
1. **Slack Webhook URLを確認**
2. **重要度スコアの設定を確認**
3. **HTTP Requestノードの設定を確認**

---

## 📊 期待される動作フロー

```
Browse AIロボット実行
    ↓
タスク完了
    ↓
Webhook送信 → ngrok → n8n Webhookノード
    ↓
Codeノード（データ整形・重要度判定）
    ↓
Ifノード（重要度5以上？）
    ↓
HTTP Requestノード（ManaOS判断API）
    ↓
Slack通知
```

---

## 🎯 成功の確認

**以下のすべてが確認できれば成功**:
- ✅ ngrokのWeb UIにリクエストが表示される
- ✅ n8nのワークフローでデータが流れる
- ✅ Slack通知が届く
- ✅ データが正しく整形されている

---

## 📚 関連ファイル

- `NGROK_SETUP_COMPLETE.md` - ngrok設定完了ガイド
- `BROWSE_AI_N8N_INTEGRATION.md` - Browse AI統合ガイド
- `SLACK_WEBHOOK_URL.md` - Slack Webhook URL設定ガイド

---

## 🎊 次のステップ

テストが成功したら:
1. **複数のロボットでテスト**
2. **重要度判定の調整**
3. **ManaOS判断APIの実装**
4. **Obsidianへの自動保存**

