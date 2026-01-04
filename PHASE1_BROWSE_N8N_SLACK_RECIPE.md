# 🟡 PHASE 1｜Browse → n8n → Slack 完全レシピ

## 🎯 目的

**自分がやらなくていい作業を消す**

- セール情報
- トレンド情報
- ライバル分析
- 技術ネタ

全部 **n8n → Slack / Obsidian / Notion** に自動化。

---

## 📋 必要なもの

### 1. n8n セットアップ（既に完了済み）

```bash
# 確認
curl http://localhost:5678/rest/workflows
```

### 2. Slack Webhook URL

1. Slack App 作成: https://api.slack.com/apps
2. Incoming Webhooks 有効化
3. Webhook URL 取得

### 3. Obsidian API（任意）

- Obsidian URI スキーム使用
- またはローカルファイル書き込み

### 4. Notion API（任意）

- Notion Integration 作成
- API Key 取得

---

## 🔧 ワークフロー1：セール情報収集

### トリガー
- **Schedule**: 毎日 9:00 / 18:00

### ノード構成

```
1. [Schedule Trigger]
   ↓
2. [HTTP Request] - CivitAI セール情報取得
   ↓
3. [Code] - データ整形
   ↓
4. [IF] - セール有無判定
   ↓
5. [Slack] - 通知送信
   ↓
6. [Obsidian] - ファイル保存（任意）
```

### n8n ワークフロー JSON

```json
{
  "name": "セール情報収集",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "hours",
              "hoursInterval": 9
            }
          ]
        }
      },
      "name": "毎日9時",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1,
      "position": [250, 300]
    },
    {
      "parameters": {
        "url": "https://civitai.com/api/v1/models",
        "options": {
          "queryParameters": {
            "parameters": [
              {
                "name": "onSale",
                "value": "true"
              }
            ]
          }
        }
      },
      "name": "CivitAI API",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [450, 300]
    },
    {
      "parameters": {
        "jsCode": "const items = $input.all();\nconst sales = items.filter(item => item.json.data?.some(model => model.onSale));\n\nif (sales.length > 0) {\n  return sales.map(item => ({\n    json: {\n      message: `🎉 セール情報\\n${item.json.data.filter(m => m.onSale).map(m => `- ${m.name}: ${m.price}`).join('\\n')}`\n    }\n  }));\n}\n\nreturn [];"
      },
      "name": "データ整形",
      "type": "n8n-nodes-base.code",
      "typeVersion": 1,
      "position": [650, 300]
    },
    {
      "parameters": {
        "conditions": {
          "options": {
            "caseSensitive": true,
            "leftValue": "",
            "type": "string"
          },
          "conditions": [
            {
              "id": "has_sales",
              "leftValue": "={{ $json.message }}",
              "rightValue": "",
              "operator": {
                "type": "string",
                "operation": "notEmpty"
              }
            }
          ],
          "combinator": "and"
        },
        "options": {}
      },
      "name": "セール有無判定",
      "type": "n8n-nodes-base.if",
      "typeVersion": "1",
      "position": [850, 300]
    },
    {
      "parameters": {
        "webhookUrl": "={{ $env.SLACK_WEBHOOK_URL }}",
        "text": "={{ $json.message }}",
        "options": {}
      },
      "name": "Slack通知",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 1,
      "position": [1050, 300]
    }
  ],
  "connections": {
    "毎日9時": {
      "main": [[{"node": "CivitAI API", "type": "main", "index": 0}]]
    },
    "CivitAI API": {
      "main": [[{"node": "データ整形", "type": "main", "index": 0}]]
    },
    "データ整形": {
      "main": [[{"node": "セール有無判定", "type": "main", "index": 0}]]
    },
    "セール有無判定": {
      "main": [[{"node": "Slack通知", "type": "main", "index": 0}]]
    }
  }
}
```

---

## 🔧 ワークフロー2：技術トレンド収集

### トリガー
- **Schedule**: 毎日 8:00

### ノード構成

```
1. [Schedule Trigger]
   ↓
2. [HTTP Request] - GitHub Trending
   ↓
3. [HTTP Request] - Hacker News
   ↓
4. [Merge] - データ統合
   ↓
5. [Code] - 重要度スコア計算
   ↓
6. [IF] - 重要度フィルタ
   ↓
7. [Slack] - 通知
   ↓
8. [Obsidian] - ファイル保存
```

### 実装例

```json
{
  "name": "技術トレンド収集",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "hours",
              "hoursInterval": 8
            }
          ]
        }
      },
      "name": "毎日8時",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1,
      "position": [250, 300]
    },
    {
      "parameters": {
        "url": "https://api.github.com/search/repositories",
        "options": {
          "queryParameters": {
            "parameters": [
              {
                "name": "q",
                "value": "created:>2025-01-01 stars:>100"
              },
              {
                "name": "sort",
                "value": "stars"
              }
            ]
          }
        }
      },
      "name": "GitHub Trending",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [450, 200]
    },
    {
      "parameters": {
        "url": "https://hacker-news.firebaseio.com/v0/topstories.json"
      },
      "name": "Hacker News",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [450, 400]
    },
    {
      "parameters": {
        "mode": "combine",
        "combineBy": "combineAll"
      },
      "name": "データ統合",
      "type": "n8n-nodes-base.merge",
      "typeVersion": 2,
      "position": [650, 300]
    },
    {
      "parameters": {
        "jsCode": "const items = $input.all();\nreturn items.map(item => {\n  const score = (item.json.stars || 0) + (item.json.score || 0) * 10;\n  return {\n    json: {\n      ...item.json,\n      importanceScore: score,\n      message: `📈 ${item.json.name || item.json.title}\\n⭐ ${score}ポイント`\n    }\n  };\n});"
      },
      "name": "重要度計算",
      "type": "n8n-nodes-base.code",
      "typeVersion": 1,
      "position": [850, 300]
    },
    {
      "parameters": {
        "conditions": {
          "conditions": [
            {
              "id": "high_importance",
              "leftValue": "={{ $json.importanceScore }}",
              "rightValue": "100",
              "operator": {
                "type": "number",
                "operation": "larger"
              }
            }
          ]
        }
      },
      "name": "重要度フィルタ",
      "type": "n8n-nodes-base.if",
      "typeVersion": "1",
      "position": [1050, 300]
    },
    {
      "parameters": {
        "webhookUrl": "={{ $env.SLACK_WEBHOOK_URL }}",
        "text": "={{ $json.message }}"
      },
      "name": "Slack通知",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 1,
      "position": [1250, 300]
    },
    {
      "parameters": {
        "operation": "write",
        "fileName": "={{ $now.format('YYYY-MM-DD') }}_trends.md",
        "fileContent": "={{ $json.message }}",
        "options": {}
      },
      "name": "Obsidian保存",
      "type": "n8n-nodes-base.writeFile",
      "typeVersion": 1,
      "position": [1250, 400]
    }
  ],
  "connections": {
    "毎日8時": {
      "main": [
        [{"node": "GitHub Trending", "type": "main", "index": 0}],
        [{"node": "Hacker News", "type": "main", "index": 0}]
      ]
    },
    "GitHub Trending": {
      "main": [[{"node": "データ統合", "type": "main", "index": 0}]]
    },
    "Hacker News": {
      "main": [[{"node": "データ統合", "type": "main", "index": 0}]]
    },
    "データ統合": {
      "main": [[{"node": "重要度計算", "type": "main", "index": 0}]]
    },
    "重要度計算": {
      "main": [[{"node": "重要度フィルタ", "type": "main", "index": 0}]]
    },
    "重要度フィルタ": {
      "main": [
        [{"node": "Slack通知", "type": "main", "index": 0}],
        [{"node": "Obsidian保存", "type": "main", "index": 0}]
      ]
    }
  }
}
```

---

## 🔧 ワークフロー3：ライバル分析

### トリガー
- **Schedule**: 毎週月曜 9:00

### ノード構成

```
1. [Schedule Trigger]
   ↓
2. [HTTP Request] - 競合サイト監視
   ↓
3. [Code] - 差分検出
   ↓
4. [IF] - 変更有無判定
   ↓
5. [Slack] - 通知
   ↓
6. [Notion] - 記録（任意）
```

### 実装例

```json
{
  "name": "ライバル分析",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "cronExpression",
              "expression": "0 9 * * 1"
            }
          ]
        }
      },
      "name": "毎週月曜9時",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1,
      "position": [250, 300]
    },
    {
      "parameters": {
        "url": "={{ $env.COMPETITOR_URL }}",
        "options": {
          "response": {
            "response": {
              "responseFormat": "text"
            }
          }
        }
      },
      "name": "競合サイト取得",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [450, 300]
    },
    {
      "parameters": {
        "operation": "read",
        "fileName": "last_check.html"
      },
      "name": "前回データ読み込み",
      "type": "n8n-nodes-base.readFile",
      "typeVersion": 1,
      "position": [450, 400]
    },
    {
      "parameters": {
        "jsCode": "const current = $input.first().json.data;\nconst previous = $input.all()[1]?.json.data || '';\n\nif (current !== previous) {\n  return [{\n    json: {\n      changed: true,\n      message: `🔍 競合サイトに変更を検出\\n${current.substring(0, 200)}...`\n    }\n  }];\n}\n\nreturn [{ json: { changed: false } }];"
      },
      "name": "差分検出",
      "type": "n8n-nodes-base.code",
      "typeVersion": 1,
      "position": [650, 300]
    },
    {
      "parameters": {
        "conditions": {
          "conditions": [
            {
              "id": "has_changes",
              "leftValue": "={{ $json.changed }}",
              "rightValue": "true",
              "operator": {
                "type": "boolean",
                "operation": "true"
              }
            }
          ]
        }
      },
      "name": "変更判定",
      "type": "n8n-nodes-base.if",
      "typeVersion": "1",
      "position": [850, 300]
    },
    {
      "parameters": {
        "webhookUrl": "={{ $env.SLACK_WEBHOOK_URL }}",
        "text": "={{ $json.message }}"
      },
      "name": "Slack通知",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 1,
      "position": [1050, 300]
    }
  ],
  "connections": {
    "毎週月曜9時": {
      "main": [
        [{"node": "競合サイト取得", "type": "main", "index": 0}],
        [{"node": "前回データ読み込み", "type": "main", "index": 0}]
      ]
    },
    "競合サイト取得": {
      "main": [[{"node": "差分検出", "type": "main", "index": 0}]]
    },
    "前回データ読み込み": {
      "main": [[{"node": "差分検出", "type": "main", "index": 0}]]
    },
    "差分検出": {
      "main": [[{"node": "変更判定", "type": "main", "index": 0}]]
    },
    "変更判定": {
      "main": [[{"node": "Slack通知", "type": "main", "index": 0}]]
    }
  }
}
```

---

## 🚀 デプロイ手順

### 1. 環境変数設定

```bash
# n8n 環境変数
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
export COMPETITOR_URL="https://example.com"
export OBSIDIAN_VAULT_PATH="/path/to/vault"
export NOTION_API_KEY="your_notion_api_key"
```

### 2. ワークフローインポート

```bash
# n8n API経由
curl -X POST http://localhost:5678/rest/workflows \
  -H "Content-Type: application/json" \
  -d @workflow_sales.json

# または Portal UI経由
# http://localhost:5000 → n8nセクション → インポート
```

### 3. ワークフロー有効化

```bash
# API経由
curl -X PATCH http://localhost:5678/rest/workflows/{id} \
  -H "Content-Type: application/json" \
  -d '{"active": true}'
```

---

## 📊 監視・確認

### Slack通知確認

```bash
# テスト実行
curl -X POST http://localhost:5678/rest/workflows/{id}/execute
```

### ログ確認

```bash
# n8nログ
docker logs n8n

# または
tail -f /root/.n8n/logs/n8n.log
```

---

## 🎯 カスタマイズポイント

### 通知頻度調整

- **セール情報**: 毎日 → 週3回
- **技術トレンド**: 毎日 → 週1回
- **ライバル分析**: 毎週 → 月1回

### フィルタリング強化

- **重要度スコア**: 100 → 200（より厳しく）
- **キーワードフィルタ**: 特定ワードのみ通知
- **時間帯フィルタ**: 営業時間のみ通知

---

## 💡 次のステップ

1. **実際に動かす**: 1つずつテスト実行
2. **通知内容を調整**: マナが見たい情報だけ
3. **Obsidian/Notion連携**: 自動保存を有効化
4. **エラーハンドリング**: 失敗時の通知設定

---

## 🎉 完成したら

**マナは「見るだけ・判断するだけ」**

情報収集は完全自動化。時間を**判断と実行**に集中できる。



