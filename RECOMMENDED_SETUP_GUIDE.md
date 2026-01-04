# 🚀 ManaOS外部ツール統合｜推奨セットアップガイド

## 🎯 推奨順序（ROI順）

1. **Browse AI** → ROI 90倍（最優先・今週）
2. **Heptabase** → ROI 7.5倍（高優先・来週）
3. **tldraw** → ROI 20倍（中優先・任意）

---

## 🥇 Step 1: Browse AI統合（今週・最優先）

### 📋 準備（5分）

1. **n8n確認**
```bash
curl http://localhost:5678/rest/workflows
```

2. **Slack Webhook URL準備**
   - Slack App作成: https://api.slack.com/apps
   - Incoming Webhooks有効化
   - Webhook URL取得

### 📝 実装手順

#### 1. Browse AIアカウント作成（30分）

1. **Browse AIにアクセス**: https://www.browse.ai/
2. **アカウント作成**: メールアドレスで登録
3. **プラン選択**: Starter（$49/月）で開始

#### 2. n8nワークフローインポート（10分）

**方法A: Portal UI経由（推奨）**

1. Portal UIにアクセス: http://localhost:5000
2. n8nセクションを開く
3. 「ワークフローをインポート」をクリック
4. `n8n_workflows/browse_ai_manaos_integration.json` を選択
5. インポート完了

**方法B: API経由**

```bash
curl -X POST http://localhost:5678/rest/workflows \
  -H "Content-Type: application/json" \
  -H "X-N8N-API-KEY: your-api-key" \
  -d @manaos_integrations/n8n_workflows/browse_ai_manaos_integration.json
```

#### 3. 環境変数設定（5分）

**n8n環境変数設定**:

```bash
# Slack Webhook URL
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

または、n8n UIで設定:
- Settings → Environment Variables
- `SLACK_WEBHOOK_URL` を追加

#### 4. Webhook URL取得（5分）

ワークフロー実行後、Webhook URLを取得:

```
http://localhost:5678/webhook/browse-ai-webhook
```

**外部公開する場合**（推奨）:
- ngrok使用: `ngrok http 5678`
- または、サーバーでポート公開

#### 5. Browse AI設定（30分）

1. **Browse AIダッシュボード**にアクセス
2. **新規ロボット作成**:
   - 名前: "CivitAI Sale Monitor"
   - URL: https://civitai.com/models?onSale=true
   - 監視タイプ: 変更検知
3. **Webhook設定**:
   - URL: `http://localhost:5678/webhook/browse-ai-webhook`
   - または: `https://your-domain.com/webhook/browse-ai-webhook`
4. **テスト実行**: ロボットを手動実行して動作確認

#### 6. テスト確認（10分）

1. **Browse AIでロボット実行**
2. **n8nワークフロー**でデータ受信確認
3. **Slack通知**確認

**完了条件**: Slackに通知が届くこと

---

## 🥈 Step 2: Heptabase統合（来週・高優先）

### 📋 準備（5分）

1. **Heptabaseアカウント作成**: https://heptabase.com/
2. **ワークスペース作成**: "ManaOS Structure"

### 📝 実装手順

#### 1. 全体構造マップ作成（4時間）

**カード構造**:

```
Level 1: ManaOS Core
  ├─ Level 2: 環境（母艦/ローカル/外部）
  │   ├─ Level 3: サービス
  │   └─ Level 3: AIエージェント
  └─ Level 2: フェーズ（0-3）
      └─ Level 3: 依存関係
```

**詳細**: `PHASE2_HEPTABASE_CONTENT_LIST.md` を参照

#### 2. 依存関係整理（2時間）

- サービス間の依存を明確化
- リンク構造を作成
- タグ付け

#### 3. フェーズ管理設定（1.5時間）

- PHASE 0-3の進捗追跡
- 状態管理
- 次のアクション設定

**完了条件**: 全体構造が見える状態

---

## 🥉 Step 3: tldraw活用（任意・中優先）

### 📋 準備（5分）

1. **tldraw開く**: https://www.tldraw.com/
2. **テンプレート参照**: `PHASE0_TLDRAW_TEMPLATE.md`

### 📝 実装手順

#### 1. 設計テンプレート作成（30分）

**テンプレート要素**:
- ManaOS Core
- 3つの環境（母艦/ローカル/外部）
- AIエージェント（レミ/ルナ/ミナ）
- データフロー

**詳細**: `PHASE0_TLDRAW_TEMPLATE.md` を参照

#### 2. 自動保存設定（30分・任意）

n8nワークフローで自動保存（任意）:
- tldraw Webhook設定
- Obsidian保存

**完了条件**: 設計時間が削減されること

---

## 📊 進捗トラッキング

### Week 1: Browse AI統合

- [ ] Browse AIアカウント作成
- [ ] n8nワークフローインポート
- [ ] 環境変数設定
- [ ] Webhook URL取得
- [ ] Browse AI設定
- [ ] テスト確認

**目標**: 情報収集の完全自動化開始

---

### Week 2: Heptabase統合

- [ ] Heptabaseアカウント作成
- [ ] 全体構造マップ作成
- [ ] 依存関係整理
- [ ] フェーズ管理設定

**目標**: 迷子時間削減開始

---

### Week 3: tldraw活用（任意）

- [ ] 設計テンプレート作成
- [ ] 自動保存設定（任意）

**目標**: 設計時間削減開始

---

## 🎯 今すぐやること（今日）

### 1. Browse AIアカウント作成（30分）

1. Browse AIにアクセス: https://www.browse.ai/
2. アカウント作成
3. Starterプラン選択

### 2. n8nワークフローインポート（10分）

1. Portal UI: http://localhost:5000
2. n8nセクション → ワークフローインポート
3. `browse_ai_manaos_integration.json` をインポート

### 3. Slack Webhook URL設定（5分）

1. Slack App作成: https://api.slack.com/apps
2. Incoming Webhooks有効化
3. Webhook URL取得
4. n8n環境変数に設定

### 4. Browse AI設定（30分）

1. ロボット作成: "CivitAI Sale Monitor"
2. Webhook設定
3. テスト実行

---

## 💡 トラブルシューティング

### Browse AI Webhookが届かない

1. **n8nワークフローが有効か確認**
   ```bash
   curl http://localhost:5678/rest/workflows
   ```

2. **Webhook URL確認**
   - ローカル: `http://localhost:5678/webhook/browse-ai-webhook`
   - 外部: ngrok使用

3. **n8nログ確認**
   ```bash
   docker logs n8n
   ```

### Slack通知が届かない

1. **環境変数確認**
   - `SLACK_WEBHOOK_URL` が設定されているか

2. **Webhook URL確認**
   - Slack AppでWebhook URLが有効か

3. **n8nワークフローログ確認**
   - エラーがないか確認

---

## 🎉 完成したら

**Week 1完了時点**:

- ✅ Browse AI統合完了
- ✅ 情報収集の完全自動化開始
- ✅ 毎日30分削減開始

**Week 2完了時点**:

- ✅ Heptabase統合完了
- ✅ 迷子時間削減開始
- ✅ 全体構造が見える状態

**Week 3完了時点**（任意）:

- ✅ tldraw活用開始
- ✅ 設計時間削減開始

---

## 📚 関連ファイル

1. **`BROWSE_AI_N8N_INTEGRATION.md`** - Browse AI完全統合ガイド
2. **`EXTERNAL_TOOLS_INTEGRATION_GUIDE.md`** - 総合ガイド
3. **`PHASE2_HEPTABASE_CONTENT_LIST.md`** - Heptabase内容リスト
4. **`PHASE0_TLDRAW_TEMPLATE.md`** - tldrawテンプレート
5. **`n8n_workflows/browse_ai_manaos_integration.json`** - n8nワークフローJSON

---

## 🚀 次のステップ

**今週**: Browse AI統合完了 → 情報収集の完全自動化

**来週**: Heptabase統合完了 → 迷子時間削減

**その次**: tldraw活用 → 設計時間削減

**ManaOS、次の進化段階いこ**🔥



