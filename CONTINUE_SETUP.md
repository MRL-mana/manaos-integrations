# 🚀 Browse AI統合続き（次のステップ）

## ✅ 完了済み

- [x] n8n起動確認
- [x] ワークフローファイル作成
- [x] ワークフローインポート
- [x] Slack通知ノードをHTTP Requestノードに変更
- [x] HTTP Requestノード設定完了

---

## 🔄 次のステップ（順番通り）

### Step 1: Slack Webhook URL取得（3分）

#### 1.1 Slack App作成

1. **ブラウザで開く**: https://api.slack.com/apps
2. **「Create New App」をクリック**
3. **「From scratch」を選択**
4. **設定**:
   - **App Name**: "ManaOS Browse AI"
   - **Pick a workspace**: ワークスペースを選択
5. **「Create App」をクリック**

#### 1.2 Incoming Webhooks有効化

1. **左メニュー「Incoming Webhooks」をクリック**
2. **「Activate Incoming Webhooks」をONにする**
3. **「Add New Webhook to Workspace」をクリック**
4. **チャンネル選択**: #general など
5. **「Allow」をクリック**
6. **Webhook URLをコピー**:
   ```
   https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
   ```

#### 1.3 n8nに設定

1. **n8nのHTTP Requestノードを開く**
2. **URLフィールドをクリック**
3. **コピーしたWebhook URLを貼り付け**
4. **「Save」をクリック**

---

### Step 2: Browse AIアカウント作成（30分）

#### 2.1 アカウント作成

1. **Browse AIにアクセス**: https://www.browse.ai/
2. **「Sign Up」をクリック**
3. **メールアドレスで登録**
4. **プラン選択**: Starter（$49/月）を選択
5. **支払い情報入力**（必要に応じて）

#### 2.2 ダッシュボード確認

1. **ログイン後、ダッシュボードを確認**
2. **「Create Robot」ボタンがあるか確認**

---

### Step 3: Browse AIロボット作成（30分）

#### 3.1 新規ロボット作成

1. **「Create Robot」をクリック**
2. **「Monitor for changes」を選択**
3. **設定**:
   - **名前**: "CivitAI Sale Monitor"
   - **URL**: `https://civitai.com/models?onSale=true`
   - **「Next」をクリック**

#### 3.2 監視要素選択

1. **ページが読み込まれるまで待つ**
2. **セール商品リストの要素を選択**
3. **「Next」をクリック**

#### 3.3 データ抽出設定

1. **抽出するデータを選択**:
   - 商品名
   - 価格
   - 割引率
   - リンク
2. **「Save」をクリック**

#### 3.4 Webhook設定

1. **ロボット設定を開く**
2. **「Integrations」タブをクリック**
3. **「Webhooks」セクションを開く**
4. **「Add Webhook」をクリック**
5. **Webhook URLを入力**:
   ```
   http://localhost:5678/webhook/browse-ai-webhook
   ```
   **注意**: 外部公開する場合はngrokを使用
6. **「Save」をクリック**

---

### Step 4: テスト実行（10分）

#### 4.1 Browse AIでテスト実行

1. **Browse AIダッシュボードでロボットを選択**
2. **「Run Now」をクリック**
3. **実行完了を待つ**

#### 4.2 n8nワークフロー確認

1. **n8n UI: http://localhost:5678**
2. **ワークフローを開く**
3. **「Executions」タブを確認**
4. **実行履歴を確認**

#### 4.3 Slack通知確認

1. **Slackチャンネルを確認**
2. **通知が届いているか確認**

**期待される通知**:
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

## 📊 進捗トラッキング

- [x] n8nワークフロー設定完了
- [ ] Slack Webhook URL取得（3分）
- [ ] Browse AIアカウント作成（30分）
- [ ] Browse AIロボット作成（30分）
- [ ] Browse AI Webhook設定（5分）
- [ ] テスト実行（10分）

---

## 🎯 今すぐやること

1. **Slack Webhook URL取得**（3分）
   - https://api.slack.com/apps
   - Incoming Webhooks有効化
   - Webhook URLをコピー
   - n8nのHTTP Requestノードに設定

2. **Browse AIアカウント作成**（30分）
   - https://www.browse.ai/
   - Starterプラン選択

---

## 📚 関連ファイル

- `QUICK_START_BROWSE_AI.md` - クイックスタートガイド
- `BROWSE_AI_N8N_INTEGRATION.md` - 完全統合ガイド
- `RECOMMENDED_SETUP_GUIDE.md` - 推奨セットアップガイド

---

**まずはSlack Webhook URL取得から始めましょう！**🔥


