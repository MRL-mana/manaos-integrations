# 📊 Browse AI統合セットアップ状況

## ✅ 完了済み（自動化）

- [x] n8n起動確認 ✅ ポート5678で起動中
- [x] Portal UI起動確認 ✅ ポート5000で起動中
- [x] ワークフローファイル確認 ✅ 存在確認済み
- [x] セットアップスクリプト作成 ✅ 完了

---

## 🔄 次のステップ（手動）

### 1. n8nワークフローインポート（10分）

**推奨方法: Portal UI経由**

1. ブラウザで開く: **http://localhost:5000**
2. 「⚙️ 自動化ワークフロー（n8n）」セクションを開く
3. 「ワークフローをインポート」をクリック
4. ファイルを選択: `n8n_workflows\browse_ai_manaos_integration.json`

**代替方法: n8n直接アクセス**

1. ブラウザで開く: **http://localhost:5678**
2. ログイン（必要に応じて）
3. 「Workflows」→「Import from File」
4. ファイルを選択: `n8n_workflows\browse_ai_manaos_integration.json`

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

### 4. Browse AI設定（30分）

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

### 5. テスト実行（10分）

1. **Browse AIでテスト実行**:
   - ロボットを選択
   - 「Run Now」をクリック

2. **n8nワークフロー確認**:
   - Portal UI: http://localhost:5000
   - n8nセクション → ワークフロー実行履歴を確認

3. **Slack通知確認**:
   - Slackチャンネルで通知を確認

---

## 📊 進捗状況

- **自動化完了**: 40%
- **手動作業待ち**: 60%

**次のアクション**: n8nワークフローインポートから開始

---

## 🎯 完了条件

- [ ] n8nワークフローインポート済み
- [ ] Browse AIアカウント作成済み
- [ ] Slack Webhook URL取得済み
- [ ] Browse AIロボット作成済み
- [ ] Browse AI Webhook設定完了
- [ ] テスト実行成功
- [ ] Slack通知確認済み

---

## 💡 ヒント

- **Portal UI経由**が最も簡単
- **Webhook URL**はワークフローインポート後に確認
- **ngrok**を使うと外部公開できる（推奨）

---

## 📚 関連ファイル

- `QUICK_START_BROWSE_AI.md` - クイックスタートガイド
- `NEXT_STEPS.md` - 次のステップ
- `RECOMMENDED_SETUP_GUIDE.md` - 詳細ガイド
- `auto_setup_browse_ai.ps1` - 自動セットアップスクリプト



