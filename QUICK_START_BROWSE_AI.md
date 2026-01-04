# ⚡ Browse AI統合｜クイックスタート（10分）

## 🎯 目標

**Browse AI → n8n → Slack** の完全自動化パイプラインを10分で構築

---

## 📋 前提条件

- ✅ n8nが起動している（http://localhost:5678）
- ✅ Slackアカウントがある
- ✅ Browse AIアカウント作成準備（https://www.browse.ai/）

---

## 🚀 クイックスタート手順

### Step 1: セットアップスクリプト実行（1分）

```powershell
cd manaos_integrations
.\setup_browse_ai.ps1
```

**確認事項**:
- ✅ n8nが動作している
- ✅ ワークフローファイルが存在する
- ⚠️  SLACK_WEBHOOK_URLが設定されている（後で設定可）

---

### Step 2: Slack Webhook URL取得（3分）

1. **Slack App作成**
   - https://api.slack.com/apps にアクセス
   - 「Create New App」→「From scratch」
   - App名: "ManaOS Browse AI"
   - Workspace選択

2. **Incoming Webhooks有効化**
   - 左メニュー「Incoming Webhooks」
   - 「Activate Incoming Webhooks」をON
   - 「Add New Webhook to Workspace」
   - チャンネル選択（例: #general）
   - Webhook URLをコピー

3. **環境変数設定**
```powershell
$env:SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

---

### Step 3: n8nワークフローインポート（2分）

**方法A: Portal UI経由（推奨）**

1. Portal UIにアクセス: http://localhost:5000
2. 「⚙️ 自動化ワークフロー（n8n）」セクションを開く
3. 「ワークフローをインポート」をクリック
4. `n8n_workflows/browse_ai_manaos_integration.json` を選択
5. インポート完了

**方法B: API経由**

```powershell
$workflowPath = "manaos_integrations\n8n_workflows\browse_ai_manaos_integration.json"
$workflowJson = Get-Content $workflowPath -Raw | ConvertFrom-Json | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://localhost:5678/rest/workflows" `
  -Method Post `
  -ContentType "application/json" `
  -Body $workflowJson
```

---

### Step 4: Webhook URL確認（1分）

ワークフローインポート後、Webhook URLを確認:

```
http://localhost:5678/webhook/browse-ai-webhook
```

**外部公開する場合（推奨）**:

```powershell
# ngrokインストール（未インストールの場合）
# https://ngrok.com/download

# ngrok起動
ngrok http 5678
```

取得したURL（例: `https://xxxx.ngrok.io/webhook/browse-ai-webhook`）をメモ

---

### Step 5: Browse AI設定（3分）

1. **Browse AIにアクセス**: https://www.browse.ai/
2. **アカウント作成**:
   - メールアドレスで登録
   - Starterプラン（$49/月）を選択

3. **新規ロボット作成**:
   - 「Create Robot」をクリック
   - **名前**: "CivitAI Sale Monitor"
   - **URL**: `https://civitai.com/models?onSale=true`
   - 「Next」をクリック

4. **監視設定**:
   - **監視タイプ**: "Monitor for changes"
   - **監視要素**: セール商品リストを選択
   - 「Next」をクリック

5. **データ抽出設定**:
   - 商品名、価格、割引率、リンクを選択
   - 「Save」をクリック

6. **Webhook設定**:
   - 「Integrations」→「Webhooks」
   - 「Add Webhook」をクリック
   - **URL**: `http://localhost:5678/webhook/browse-ai-webhook`
     - または: ngrok URL（外部公開した場合）
   - 「Save」をクリック

---

### Step 6: テスト実行（1分）

1. **Browse AIでテスト実行**:
   - ロボットを選択
   - 「Run Now」をクリック

2. **n8nワークフロー確認**:
   - Portal UI: http://localhost:5000
   - n8nセクション → ワークフロー実行履歴を確認

3. **Slack通知確認**:
   - Slackチャンネルで通知を確認

**期待される結果**:
```
🔍 **CivitAI Sale Monitor** から新しい情報を検出

💰 **セール情報**
商品: [商品名]
価格: [価格]
割引: [割引率]
リンク: [リンク]

重要度スコア: 10/20
```

---

## ✅ 完了チェックリスト

- [ ] n8nが動作している
- [ ] Slack Webhook URL取得済み
- [ ] n8nワークフローインポート済み
- [ ] Browse AIアカウント作成済み
- [ ] Browse AIロボット作成済み
- [ ] Webhook設定完了
- [ ] テスト実行成功
- [ ] Slack通知確認済み

---

## 🐛 トラブルシューティング

### n8nに接続できない

```powershell
# n8n確認
curl http://localhost:5678/rest/workflows

# n8n起動（必要に応じて）
# Dockerの場合
docker start n8n

# ローカルインストールの場合
n8n start
```

### Slack通知が届かない

1. **環境変数確認**:
```powershell
$env:SLACK_WEBHOOK_URL
```

2. **Webhook URL確認**:
   - Slack AppでWebhook URLが有効か確認
   - チャンネルが正しいか確認

3. **n8nワークフローログ確認**:
   - Portal UI → n8nセクション → 実行履歴
   - エラーがないか確認

### Browse AI Webhookが届かない

1. **Webhook URL確認**:
   - ローカル: `http://localhost:5678/webhook/browse-ai-webhook`
   - 外部: ngrok URL

2. **n8nワークフロー確認**:
   - ワークフローが有効か確認
   - Webhookノードが正しく設定されているか確認

3. **Browse AI設定確認**:
   - Webhook URLが正しく設定されているか
   - ロボットが実行されているか

---

## 🎉 完了！

**Browse AI統合が完了しました！**

これで以下が自動化されます:
- ✅ セール情報の自動収集
- ✅ 重要度判定
- ✅ Slack通知
- ✅ Obsidian保存

**次のステップ**: Heptabase統合（来週）

---

## 📚 関連ファイル

- `RECOMMENDED_SETUP_GUIDE.md` - 詳細ガイド
- `BROWSE_AI_N8N_INTEGRATION.md` - 完全統合ガイド
- `setup_browse_ai.ps1` - セットアップスクリプト



