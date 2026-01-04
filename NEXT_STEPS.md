# 🚀 次のステップ（今すぐやること）

## ✅ 完了済み

- [x] セットアップスクリプト作成
- [x] n8nワークフローJSON作成
- [x] クイックスタートガイド作成
- [x] 推奨セットアップガイド作成
- [x] セットアップスクリプト実行

---

## 🔄 今すぐやること（順番通り）

### 1. n8n起動確認（2分）

```powershell
# n8nが起動しているか確認
# Portal UI: http://localhost:5000
# または直接: http://localhost:5678
```

**確認方法**:
- ブラウザで http://localhost:5678 にアクセス
- ログイン画面が表示されればOK

**起動していない場合**:
- Docker: `docker start n8n`
- ローカル: `n8n start`

---

### 2. Browse AIアカウント作成（30分）

1. **Browse AIにアクセス**: https://www.browse.ai/
2. **アカウント作成**:
   - メールアドレスで登録
   - Starterプラン（$49/月）を選択
3. **ダッシュボード確認**: ログインできればOK

---

### 3. Slack Webhook URL取得（3分）

1. **Slack App作成**:
   - https://api.slack.com/apps にアクセス
   - 「Create New App」→「From scratch」
   - App名: "ManaOS Browse AI"
   - Workspace選択

2. **Incoming Webhooks有効化**:
   - 左メニュー「Incoming Webhooks」
   - 「Activate Incoming Webhooks」をON
   - 「Add New Webhook to Workspace」
   - チャンネル選択（例: #general）
   - **Webhook URLをコピー**

3. **環境変数設定**:
```powershell
$env:SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

---

### 4. n8nワークフローインポート（10分）

**方法A: Portal UI経由（推奨）**

1. Portal UIにアクセス: http://localhost:5000
2. 「⚙️ 自動化ワークフロー（n8n）」セクションを開く
3. 「ワークフローをインポート」をクリック
4. ファイルを選択: `n8n_workflows\browse_ai_manaos_integration.json`
5. インポート完了

**方法B: API経由**

```powershell
$workflowPath = "C:\Users\mana4\OneDrive\Desktop\manaos_integrations\n8n_workflows\browse_ai_manaos_integration.json"
$workflowJson = Get-Content $workflowPath -Raw

Invoke-RestMethod -Uri "http://localhost:5678/rest/workflows" `
  -Method Post `
  -ContentType "application/json" `
  -Body $workflowJson
```

---

### 5. Webhook URL確認（1分）

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

### 6. Browse AI設定（30分）

1. **Browse AIダッシュボード**にアクセス
2. **新規ロボット作成**:
   - 「Create Robot」をクリック
   - **名前**: "CivitAI Sale Monitor"
   - **URL**: `https://civitai.com/models?onSale=true`
   - 「Next」をクリック

3. **監視設定**:
   - **監視タイプ**: "Monitor for changes"
   - **監視要素**: セール商品リストを選択
   - 「Next」をクリック

4. **データ抽出設定**:
   - 商品名、価格、割引率、リンクを選択
   - 「Save」をクリック

5. **Webhook設定**:
   - 「Integrations」→「Webhooks」
   - 「Add Webhook」をクリック
   - **URL**: `http://localhost:5678/webhook/browse-ai-webhook`
     - または: ngrok URL（外部公開した場合）
   - 「Save」をクリック

---

### 7. テスト実行（10分）

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

- [ ] n8nが起動している
- [ ] Browse AIアカウント作成済み
- [ ] Slack Webhook URL取得済み
- [ ] 環境変数設定済み
- [ ] n8nワークフローインポート済み
- [ ] Webhook URL確認済み
- [ ] Browse AIロボット作成済み
- [ ] Browse AI Webhook設定完了
- [ ] テスト実行成功
- [ ] Slack通知確認済み

---

## 📚 関連ファイル

- `QUICK_START_BROWSE_AI.md` - クイックスタートガイド（10分）
- `RECOMMENDED_SETUP_GUIDE.md` - 推奨セットアップガイド
- `BROWSE_AI_N8N_INTEGRATION.md` - 完全統合ガイド
- `setup_browse_ai.ps1` - セットアップスクリプト

---

## 🎉 完了したら

**Browse AI統合が完了したら**:

1. **Step 2（Heptabase統合）**に進む
2. `SETUP_PROGRESS.md` を更新
3. 次のフェーズ準備

**ManaOS、次の進化段階いこ**🔥



