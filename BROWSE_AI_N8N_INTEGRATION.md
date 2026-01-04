# 🤖 Browse AI × n8n × ManaOS 完全統合ガイド

## 🎯 目的

**Browse AI → n8n → ManaOS → Slack** の完全自動化パイプライン構築

情報収集を完全自動化して、**マナは「見るだけ・判断するだけ」**に。

---

## 📋 必要なもの

### 1. Browse AIアカウント

- **URL**: https://www.browse.ai/
- **プラン**: Starter（$49/月）で十分
- **機能**: Web監視、変更検知、データ抽出

### 2. n8n（既に完了済み）

```bash
# 確認
curl http://localhost:5678/rest/workflows
```

### 3. Slack Webhook URL

- Slack App作成: https://api.slack.com/apps
- Incoming Webhooks有効化
- Webhook URL取得

---

## 🔧 統合構成

```
[Browse AI] → [Webhook] → [n8n] → [ManaOS判断] → [Slack通知]
     ↓            ↓          ↓          ↓              ↓
  情報収集    データ送信   データ整形   重要度判定      通知送信
```

---

## 📝 Step 1: Browse AIセットアップ（30分）

### 1.1 アカウント作成

1. **Browse AIにアクセス**: https://www.browse.ai/
2. **アカウント作成**: メールアドレスで登録
3. **プラン選択**: Starter（$49/月）で開始

### 1.2 監視タスク作成

#### タスク1: CivitAIセール監視

1. **新規ロボット作成**
   - 名前: "CivitAI Sale Monitor"
   - URL: https://civitai.com/models?onSale=true

2. **監視設定**:
   - **監視タイプ**: 変更検知
   - **監視要素**: セール商品リスト
   - **通知頻度**: 変更検知時

3. **データ抽出**:
   - 商品名
   - 価格
   - セール割引率
   - リンク

#### タスク2: GitHub Trending監視

1. **新規ロボット作成**
   - 名前: "GitHub Trending Monitor"
   - URL: https://github.com/trending

2. **監視設定**:
   - **監視タイプ**: 定期取得
   - **監視頻度**: 毎日8時
   - **データ抽出**: リポジトリ名、スター数、言語

#### タスク3: 競合サイト監視

1. **新規ロボット作成**
   - 名前: "Competitor Monitor"
   - URL: [競合サイトURL]

2. **監視設定**:
   - **監視タイプ**: 変更検知
   - **監視要素**: ページ全体
   - **通知頻度**: 変更検知時

---

## 📝 Step 2: n8nワークフロー作成（1時間）

### 2.1 Webhookエンドポイント作成

**n8nワークフローJSON**:

```json
{
  "name": "Browse AI → ManaOS統合",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "browse-ai-webhook",
        "responseMode": "responseNode",
        "options": {}
      },
      "name": "Browse AI Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [250, 300],
      "webhookId": "browse-ai-webhook"
    },
    {
      "parameters": {
        "jsCode": "// Browse AIからのデータ整形\nconst input = $input.first().json.body || $input.first().json;\n\n// データ抽出\nconst robotName = input.robot?.name || input.robotName || 'unknown';\nconst url = input.capturedAt?.url || input.url || '';\nconst extractedData = input.extractedData || input.data || {};\nconst timestamp = input.capturedAt?.timestamp || new Date().toISOString();\n\n// 重要度スコア計算\nfunction calculateImportance(data, robotName) {\n  let score = 0;\n  \n  // セール情報: 高重要度\n  if (robotName.includes('Sale') || robotName.includes('セール')) {\n    if (data.salePrice || data.discount) score += 10;\n    if (data.price && data.originalPrice) score += 8;\n  }\n  \n  // トレンド情報: 中重要度\n  if (robotName.includes('Trending') || robotName.includes('トレンド')) {\n    if (data.stars || data.starCount) score += 5;\n    if (data.trending) score += 5;\n  }\n  \n  // 競合変更: 高重要度\n  if (robotName.includes('Competitor') || robotName.includes('競合')) {\n    if (data.changes || data.diff) score += 8;\n    score += 5; // 競合は常に重要\n  }\n  \n  return score;\n}\n\nconst importance = calculateImportance(extractedData, robotName);\n\n// メッセージ生成\nfunction generateMessage(robotName, data, importance) {\n  let message = `🔍 **${robotName}** から新しい情報を検出\\n\\n`;\n  \n  if (robotName.includes('Sale')) {\n    message += `💰 **セール情報**\\n`;\n    if (data.name) message += `商品: ${data.name}\\n`;\n    if (data.price) message += `価格: ${data.price}\\n`;\n    if (data.discount) message += `割引: ${data.discount}\\n`;\n    if (data.link) message += `リンク: ${data.link}\\n`;\n  } else if (robotName.includes('Trending')) {\n    message += `📈 **トレンド情報**\\n`;\n    if (data.name) message += `リポジトリ: ${data.name}\\n`;\n    if (data.stars) message += `⭐ ${data.stars} stars\\n`;\n    if (data.language) message += `言語: ${data.language}\\n`;\n  } else if (robotName.includes('Competitor')) {\n    message += `🕵️ **競合サイト変更**\\n`;\n    message += `URL: ${url}\\n`;\n    if (data.changes) message += `変更内容: ${JSON.stringify(data.changes)}\\n`;\n  }\n  \n  message += `\\n重要度スコア: ${importance}/20`;\n  \n  return message;\n}\n\nconst message = generateMessage(robotName, extractedData, importance);\n\nreturn [{\n  json: {\n    robotName,\n    url,\n    extractedData,\n    timestamp,\n    importance,\n    message,\n    shouldNotify: importance >= 5\n  }\n}];"
      },
      "name": "データ整形・重要度判定",
      "type": "n8n-nodes-base.code",
      "typeVersion": 1,
      "position": [450, 300]
    },
    {
      "parameters": {
        "conditions": {
          "conditions": [
            {
              "id": "should_notify",
              "leftValue": "={{ $json.shouldNotify }}",
              "rightValue": "true",
              "operator": {
                "type": "boolean",
                "operation": "true"
              }
            }
          ]
        }
      },
      "name": "通知判定",
      "type": "n8n-nodes-base.if",
      "typeVersion": "1",
      "position": [650, 300]
    },
    {
      "parameters": {
        "url": "http://localhost:5000/api/manaos/judge",
        "method": "POST",
        "authentication": "none",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "data",
              "value": "={{ $json }}"
            },
            {
              "name": "action",
              "value": "notify_if_important"
            }
          ]
        },
        "options": {}
      },
      "name": "ManaOS判断API",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [850, 200]
    },
    {
      "parameters": {
        "webhookUrl": "={{ $env.SLACK_WEBHOOK_URL }}",
        "text": "={{ $json.message }}",
        "options": {
          "username": "Browse AI Monitor"
        }
      },
      "name": "Slack通知",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 1,
      "position": [1050, 200]
    },
    {
      "parameters": {
        "operation": "append",
        "fileName": "browse_ai_log.md",
        "fileContent": "## {{ $json.timestamp }}\n\n**ロボット**: {{ $json.robotName }}\n**URL**: {{ $json.url }}\n**重要度**: {{ $json.importance }}/20\n\n### データ\n```json\n{{ JSON.stringify($json.extractedData, null, 2) }}\n```\n\n---\n\n"
      },
      "name": "Obsidian保存",
      "type": "n8n-nodes-base.writeFile",
      "typeVersion": 1,
      "position": [1050, 300]
    }
  ],
  "connections": {
    "Browse AI Webhook": {
      "main": [[{"node": "データ整形・重要度判定", "type": "main", "index": 0}]]
    },
    "データ整形・重要度判定": {
      "main": [[{"node": "通知判定", "type": "main", "index": 0}]]
    },
    "通知判定": {
      "main": [
        [{"node": "ManaOS判断API", "type": "main", "index": 0}],
        [{"node": "Obsidian保存", "type": "main", "index": 0}]
      ]
    },
    "ManaOS判断API": {
      "main": [[{"node": "Slack通知", "type": "main", "index": 0}]]
    }
  },
  "pinData": {},
  "settings": {
    "executionOrder": "v1"
  },
  "staticData": null,
  "tags": [],
  "triggerCount": 0,
  "updatedAt": "2025-01-01T00:00:00.000Z",
  "versionId": "1"
}
```

### 2.2 ワークフローインポート

```bash
# n8n API経由
curl -X POST http://localhost:5678/rest/workflows \
  -H "Content-Type: application/json" \
  -H "X-N8N-API-KEY: your-api-key" \
  -d @browse_ai_workflow.json

# または Portal UI経由
# http://localhost:5000 → n8nセクション → インポート
```

### 2.3 Webhook URL取得

ワークフロー実行後、Webhook URLを取得:

```
http://localhost:5678/webhook/browse-ai-webhook
```

または、外部公開する場合:

```
https://your-domain.com/webhook/browse-ai-webhook
```

---

## 📝 Step 3: Browse AI設定（30分）

### 3.1 Webhook設定

1. **Browse AIダッシュボード**にアクセス
2. **各ロボットの設定**を開く
3. **Webhook設定**:
   - URL: `http://localhost:5678/webhook/browse-ai-webhook`
   - または: `https://your-domain.com/webhook/browse-ai-webhook`
   - Method: POST
   - Headers: なし（必要に応じて追加）

### 3.2 監視頻度設定

- **CivitAIセール**: 変更検知時（リアルタイム）
- **GitHub Trending**: 毎日8時
- **競合サイト**: 変更検知時（リアルタイム）

---

## 🧪 Step 4: テスト実行（30分）

### 4.1 Browse AIテスト実行

1. **Browse AIダッシュボード**で各ロボットを手動実行
2. **n8nワークフロー**でデータ受信を確認
3. **Slack通知**を確認

### 4.2 エラーハンドリング確認

```bash
# n8nログ確認
docker logs n8n

# または
tail -f /root/.n8n/logs/n8n.log
```

### 4.3 重要度スコア調整

重要度スコアが適切でない場合、`データ整形・重要度判定`ノードのコードを調整:

```javascript
// 重要度スコアの閾値調整
const shouldNotify = importance >= 5; // 5 → 3（より多くの通知）
```

---

## 📊 監視・確認

### 5.1 ログ確認

**Obsidianログファイル**: `browse_ai_log.md`

```markdown
## 2025-01-01T12:00:00.000Z

**ロボット**: CivitAI Sale Monitor
**URL**: https://civitai.com/models?onSale=true
**重要度**: 10/20

### データ
```json
{
  "name": "Example Model",
  "price": "$9.99",
  "discount": "50%"
}
```
```

### 5.2 Slack通知確認

Slackチャンネルで通知を確認:

```
🔍 **CivitAI Sale Monitor** から新しい情報を検出

💰 **セール情報**
商品: Example Model
価格: $9.99
割引: 50%
リンク: https://civitai.com/models/12345

重要度スコア: 10/20
```

---

## 🎯 カスタマイズポイント

### 6.1 監視タスク追加

新しい監視タスクを追加する場合:

1. **Browse AIでロボット作成**
2. **Webhook設定**（同じURL）
3. **n8nワークフロー**で自動処理（コードは共通）

### 6.2 通知頻度調整

- **重要度スコア**: 5 → 3（より多くの通知）
- **通知時間帯**: 営業時間のみ通知
- **通知チャンネル**: 重要度に応じてチャンネル分け

### 6.3 データ保存先追加

- **Notion**: Notion APIノード追加
- **Google Drive**: Google Drive APIノード追加
- **データベース**: PostgreSQL/MySQLノード追加

---

## 💡 使いどころ

### 7.1 セール監視

- **CivitAI**: モデルセール通知
- **Hugging Face**: データセットセール通知
- **その他**: 任意のECサイト

### 7.2 トレンド監視

- **GitHub**: トレンドリポジトリ通知
- **Hacker News**: トップストーリー通知
- **Reddit**: サブレディットのトレンド通知

### 7.3 競合分析

- **競合サイト**: 変更検知通知
- **価格監視**: 価格変動通知
- **機能追加**: 新機能検知通知

---

## 🎉 完成したら

**マナは「見るだけ・判断するだけ」**

情報収集は完全自動化。時間を**判断と実行**に集中できる。

**ROI**: 投資2時間 → 年間180時間削減 = **90倍**🔥



