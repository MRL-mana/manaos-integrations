# 🔥 ManaOS外部ツール統合ガイド（ガチ選定版）

## 🎯 結論：今すぐ入れるならこの3つ

1. **Browse AI** → n8n統合で即効性MAX（金になる）
2. **Heptabase** → ManaOS構成の神視点（時間削減）
3. **tldraw** → 思考初速UP（設計加速）

---

## 📊 相性スコア比較

| ツール | ManaOS相性 | n8n連携 | 金になる度 | 実装難易度 | 総合スコア |
|--------|-----------|---------|-----------|-----------|-----------|
| **Browse AI** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **🥇 最強** |
| **Heptabase** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | **🥈 高** |
| **tldraw** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | **🥉 中** |
| Mem | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⚪ 低 |
| Rewind | ⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ⚪ 低 |
| Peltarion | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⚪ 将来 |

---

## 🥇 1. Browse AI（最優先・金になる）

### 🎯 なぜ最強か

**n8nと直接API連携可能** → ManaOSの自動化パイプラインに完全統合

### 💰 金になる理由

1. **情報収集の自動化**
   - セール監視 → 即座に通知
   - トレンド監視 → 先行者利益
   - ライバル分析 → 競争優位

2. **ROI計算**
   - 投資: Browse AI月額$49 + 統合2時間
   - リターン: 毎日30分削減 → 月15時間 → **年180時間**
   - **ROI: 180時間 × 時給換算 = 数十万円**

### 🔧 n8n統合構成

```
[Browse AI] → [n8n Webhook] → [ManaOS判断] → [Slack通知]
     ↓              ↓              ↓              ↓
  情報収集      データ整形      重要度判定      通知送信
```

### 📋 実装手順

#### Step 1: Browse AIセットアップ（30分）

1. **アカウント作成**: https://www.browse.ai/
2. **監視タスク作成**:
   - CivitAIセールページ
   - GitHub Trending
   - 競合サイト

#### Step 2: n8n統合（1時間）

**n8nワークフローJSON**:

```json
{
  "name": "Browse AI → ManaOS",
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
      "position": [250, 300]
    },
    {
      "parameters": {
        "jsCode": "const data = $input.first().json.body;\n\n// Browse AIからのデータ整形\nconst result = {\n  source: data.robot?.name || 'unknown',\n  url: data.capturedAt?.url || '',\n  changes: data.extractedData || {},\n  timestamp: new Date().toISOString(),\n  importance: calculateImportance(data)\n};\n\nfunction calculateImportance(data) {\n  let score = 0;\n  \n  // セール情報: 高重要度\n  if (data.extractedData?.salePrice) score += 10;\n  \n  // トレンド情報: 中重要度\n  if (data.extractedData?.stars || data.extractedData?.trending) score += 5;\n  \n  // 競合変更: 高重要度\n  if (data.extractedData?.changes) score += 8;\n  \n  return score;\n}\n\nreturn [{ json: result }];"
      },
      "name": "データ整形",
      "type": "n8n-nodes-base.code",
      "typeVersion": 1,
      "position": [450, 300]
    },
    {
      "parameters": {
        "conditions": {
          "conditions": [
            {
              "id": "high_importance",
              "leftValue": "={{ $json.importance }}",
              "rightValue": "5",
              "operator": {
                "type": "number",
                "operation": "largerEqual"
              }
            }
          ]
        }
      },
      "name": "重要度判定",
      "type": "n8n-nodes-base.if",
      "typeVersion": "1",
      "position": [650, 300]
    },
    {
      "parameters": {
        "url": "http://127.0.0.1:5000/api/manaos/judge",
        "method": "POST",
        "body": {
          "data": "={{ $json }}",
          "action": "notify_if_important"
        }
      },
      "name": "ManaOS判断",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [850, 200]
    },
    {
      "parameters": {
        "webhookUrl": "={{ $env.SLACK_WEBHOOK_URL }}",
        "text": "={{ $json.message || 'Browse AI: 新しい情報を検出' }}"
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
        "fileContent": "={{ $json.timestamp }}: {{ $json.source }}\n{{ JSON.stringify($json.changes, null, 2) }}\n\n"
      },
      "name": "Obsidian保存",
      "type": "n8n-nodes-base.writeFile",
      "typeVersion": 1,
      "position": [1050, 300]
    }
  ],
  "connections": {
    "Browse AI Webhook": {
      "main": [[{"node": "データ整形", "type": "main", "index": 0}]]
    },
    "データ整形": {
      "main": [[{"node": "重要度判定", "type": "main", "index": 0}]]
    },
    "重要度判定": {
      "main": [
        [{"node": "ManaOS判断", "type": "main", "index": 0}],
        [{"node": "Obsidian保存", "type": "main", "index": 0}]
      ]
    },
    "ManaOS判断": {
      "main": [[{"node": "Slack通知", "type": "main", "index": 0}]]
    }
  }
}
```

#### Step 3: Browse AI設定（30分）

1. **監視タスク作成**:
   - CivitAIセールページ
   - GitHub Trending
   - 競合サイト

2. **Webhook設定**:
   - URL: `http://127.0.0.1:5678/webhook/browse-ai-webhook`
   - または: `https://your-domain.com/webhook/browse-ai-webhook`

### 💡 使いどころ

- **セール監視**: CivitAI、Hugging Face、その他
- **トレンド監視**: GitHub、Hacker News、Reddit
- **競合分析**: 競合サイトの変更検知
- **価格監視**: 商品価格の変動通知

---

## 🥈 2. Heptabase（高優先・時間削減）

### 🎯 なぜ相性がいいか

**Obsidian×Notionの弱点を補完** → ManaOSの「構成図」「フェーズ管理」に激ハマり

### 💰 金になる理由

1. **迷子時間の削減**
   - 「あの情報どこだっけ？」: 5分 → 30秒
   - 「この依存関係どうなってる？」: 10分 → 1分
   - **年間60時間削減**

2. **ROI計算**
   - 投資: Heptabase月額$8 + 構造整理8時間
   - リターン: 年間60時間削減
   - **ROI: 7.5倍**

### 🔧 ManaOS統合構成

```
[Heptabase] ← [ManaOS構造] → [Obsidian] → [Notion]
     ↓              ↓              ↓           ↓
  全体構造      依存関係        思考記録     実績記録
```

### 📋 実装手順

#### Step 1: Heptabaseセットアップ（30分）

1. **アカウント作成**: https://heptabase.com/
2. **ワークスペース作成**: "ManaOS Structure"

#### Step 2: ManaOS構造マップ作成（4時間）

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

#### Step 3: 自動同期（任意・2時間）

**n8nワークフロー**:

```json
{
  "name": "ManaOS → Heptabase同期",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "hours",
              "hoursInterval": 24
            }
          ]
        }
      },
      "name": "毎日同期",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1,
      "position": [250, 300]
    },
    {
      "parameters": {
        "url": "http://127.0.0.1:5000/api/manaos/structure",
        "method": "GET"
      },
      "name": "ManaOS構造取得",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [450, 300]
    },
    {
      "parameters": {
        "url": "https://app.heptabase.com/api/v1/cards",
        "method": "POST",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "Authorization",
              "value": "Bearer {{ $env.HEPTABASE_API_KEY }}"
            }
          ]
        },
        "body": {
          "title": "={{ $json.name }}",
          "content": "={{ $json.description }}",
          "tags": "={{ $json.tags }}"
        }
      },
      "name": "Heptabase更新",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [650, 300]
    }
  ],
  "connections": {
    "毎日同期": {
      "main": [[{"node": "ManaOS構造取得", "type": "main", "index": 0}]]
    },
    "ManaOS構造取得": {
      "main": [[{"node": "Heptabase更新", "type": "main", "index": 0}]]
    }
  }
}
```

### 💡 使いどころ

- **ManaOS全体像**: 一発で可視化
- **フェーズ管理**: PHASE 0-3の進捗追跡
- **依存関係**: サービス間の依存を明確化
- **将来タスク**: 「将来やる」置き場

---

## 🥉 3. tldraw（中優先・設計加速）

### 🎯 なぜ相性がいいか

**設計思考の初速が異常に速い** → 「完成度よりスピード命のマナ向け」

### 💰 金になる理由

1. **設計時間の削減**
   - 設計前の脳内ダンプ: 30分 → 5分
   - **年間20時間削減**

2. **ROI計算**
   - 投資: 無料 + 学習30分
   - リターン: 年間20時間削減
   - **ROI: 40倍（ただし絶対値は小さい）**

### 🔧 ManaOS統合構成

```
[tldraw] → [設計図] → [Obsidian] → [実装]
    ↓          ↓           ↓          ↓
  ラフ設計   保存        思考記録    コード生成
```

### 📋 実装手順

#### Step 1: tldrawセットアップ（5分）

1. **開く**: https://www.tldraw.com/
2. **テンプレート参照**: `PHASE0_TLDRAW_TEMPLATE.md`

#### Step 2: ManaOS設計テンプレート作成（30分）

**テンプレート要素**:
- ManaOS Core
- 3つの環境（母艦/ローカル/外部）
- AIエージェント（レミ/ルナ/ミナ）
- データフロー

**詳細**: `PHASE0_TLDRAW_TEMPLATE.md` を参照

#### Step 3: 自動保存（任意・1時間）

**n8nワークフロー**:

```json
{
  "name": "tldraw → Obsidian保存",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "tldraw-webhook",
        "responseMode": "responseNode"
      },
      "name": "tldraw Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [250, 300]
    },
    {
      "parameters": {
        "operation": "write",
        "fileName": "={{ $now.format('YYYY-MM-DD') }}_design.md",
        "fileContent": "={{ $json.design }}"
      },
      "name": "Obsidian保存",
      "type": "n8n-nodes-base.writeFile",
      "typeVersion": 1,
      "position": [450, 300]
    }
  ],
  "connections": {
    "tldraw Webhook": {
      "main": [[{"node": "Obsidian保存", "type": "main", "index": 0}]]
    }
  }
}
```

### 💡 使いどころ

- **設計前の脳内ダンプ**: 5分で全体像
- **依存関係の可視化**: 矢印で接続
- **フェーズ進捗**: 進捗を色分け

---

## 🚫 後回しにするツール

### Mem（補助脳として使う）

**理由**:
- Obsidianの「人力リンク」が要らなくなるが、**全部移行は時間の無駄**
- ローカル主義のマナには**補助脳**として使うのが正解

**使い方**:
- 重要局面だけON
- 全部移行はしない

---

### Rewind（重要局面だけON）

**理由**:
- 便利だけど**使いすぎると脳が甘える**
- 画面・音声・操作を全部記憶するが、**常時ONは不要**

**使い方**:
- 問題が起きた時だけ使う
- 常時ONはしない

---

### Peltarion（将来検討）

**理由**:
- AIパイプライン管理が視覚的だが、**今すぐじゃなくてもいい**
- **ManaOS商用化ルート**として記憶しておく価値あり

**使い方**:
- 将来「人に売る」構成を考えるなら検討
- 今は後回し

---

## 🎯 実行プラン（優先順位順）

### Week 1: Browse AI統合（最優先）

**目標**: Browse AI → n8n → Slack 完全自動化
**時間**: 2時間
**成果**: 情報収集の完全自動化開始

**タスク**:
- [ ] Browse AIアカウント作成（30分）
- [ ] n8nワークフロー作成（1時間）
- [ ] テスト実行・調整（30分）

---

### Week 2: Heptabase統合（高優先）

**目標**: ManaOS構造マップ作成
**時間**: 8時間
**成果**: 迷子時間削減開始

**タスク**:
- [ ] Heptabaseアカウント作成（30分）
- [ ] 全体構造マップ作成（4時間）
- [ ] 依存関係整理（2時間）
- [ ] フェーズ管理設定（1.5時間）

---

### Week 3: tldraw活用（中優先）

**目標**: 設計テンプレート作成
**時間**: 1時間
**成果**: 設計時間削減開始

**タスク**:
- [ ] tldrawテンプレート作成（30分）
- [ ] 自動保存設定（30分）

---

## 📊 ROI比較（最終版）

| ツール | 投資時間 | 年間リターン | ROI | 優先度 |
|--------|---------|-------------|-----|--------|
| **Browse AI** | 2時間 | 180時間 | **90倍** | 🥇 最優先 |
| **Heptabase** | 8時間 | 60時間 | **7.5倍** | 🥈 高 |
| **tldraw** | 1時間 | 20時間 | **20倍** | 🥉 中 |

---

## 🎉 まとめ

**今すぐ入れるならこの3つ**:

1. **Browse AI** → n8n統合で即効性MAX（ROI 90倍）
2. **Heptabase** → ManaOS構成の神視点（ROI 7.5倍）
3. **tldraw** → 思考初速UP（ROI 20倍）

**全部やるけど、順番が命**。

Browse AIから始めて、情報収集を完全自動化。
その時間で、Heptabaseで構造を整理。
設計はtldrawで加速。

**ManaOS、次の進化段階いこ**🔥



