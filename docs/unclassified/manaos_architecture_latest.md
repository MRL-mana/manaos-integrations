# 🏗️ ManaOS 全体アーキテクチャ図（最新版）

**最終更新**: 2026-01-06  
**バージョン**: 2.0.0（Obsidian/NotebookLM/Antigravity統合版）  
**状態**: 完全実装・動作確認済み

---

## 🎯 全体像

```
【現実の行動・思考】
        ↓
   Obsidian（母艦）
  ─ 記録 / ログ / 構想 ─
        ↓
 NotebookLM（分析AI）
  ─ 気づき / 傾向 / 因果 ─
        ↓
 Antigravity（再構築AI）
  ─ 記事化 / MOC / 道具化 ─
        ↓
     ManaOS
  ─ 記憶 / 自動化 / 収益 ─
```

**核心**: Obsidianが一次情報。AIは全部"二次加工"。

---

## 🏗️ システムアーキテクチャ

### レイヤー構造

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: 人間側UI（記録・分析・再構築）                    │
├─────────────────────────────────────────────────────────┤
│ Obsidian (母艦)                                          │
│   ├─ Daily/ (デイリーノート)                             │
│   ├─ Health/ (体調ログ)                                  │
│   ├─ Ideas/ (思考の断片)                                 │
│   ├─ Learning/ (学習ログ)                                 │
│   ├─ Review/ (振り返り)                                  │
│   └─ MOCs/ (Map of Content)                             │
│                                                           │
│ NotebookLM (分析AI)                                      │
│   ├─ 週次分析（傾向・体調・改善点）                        │
│   ├─ 月次分析（振り返り・行動パターン）                    │
│   └─ テーマ別分析（学習・思考・時間）                      │
│                                                           │
│ Antigravity (再構築AI)                                   │
│   ├─ MOC再構築                                           │
│   ├─ 記事化（note/Zenn/Obsidian）                        │
│   └─ YAML一括編集                                        │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 2: ManaOS Core（思考・判断・実行・評価）            │
├─────────────────────────────────────────────────────────┤
│ Intent Router (5100)                                     │
│   └─ 意図分類（会話/タスク/検索/生成/制御）                │
│                                                           │
│ Task Planner (5101)                                      │
│   └─ 実行計画作成（ステップバイステップ）                  │
│                                                           │
│ Task Queue (5104)                                        │
│   └─ タスクキュー（Priority制御・Rate Limit）             │
│                                                           │
│ Executor Enhanced (5107)                                 │
│   ├─ n8nワークフロー実行                                 │
│   ├─ API呼び出し                                         │
│   ├─ スクリプト実行                                       │
│   └─ コマンド実行                                         │
│                                                           │
│ Task Critic (5102)                                       │
│   └─ 結果評価（成功・失敗判定）                           │
│                                                           │
│ RAG Memory (5103)                                        │
│   ├─ 重要度スコア                                         │
│   ├─ 重複チェック                                         │
│   └─ 時系列メモリ                                         │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 3: ManaOS統合（オーケストレーション）                │
├─────────────────────────────────────────────────────────┤
│ Unified Orchestrator (5106)                              │
│   ├─ Intent Router                                       │
│   ├─ Task Planner                                        │
│   ├─ Task Critic                                         │
│   ├─ Task Queue                                          │
│   ├─ Executor Enhanced                                   │
│   └─ RAG Memory                                          │
│                                                           │
│ LLM Optimization (5110)                                  │
│   ├─ GPU効率化                                           │
│   ├─ フィルタ機能                                         │
│   └─ 動的モデル管理                                       │
│                                                           │
│ Content Generation (5109)                                │
│   ├─ 日報→ブログ                                         │
│   ├─ 構成ログ→note/Zenn記事                              │
│   └─ 画像→テンプレ商品                                   │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 4: ManaOS UI（操作・表示・通知）                    │
├─────────────────────────────────────────────────────────┤
│ UI Operations (5105)                                     │
│   ├─ 実行ボタン                                           │
│   ├─ モード切替                                           │
│   └─ コストメーター                                       │
│                                                           │
│ Portal Integration (5108)                                │
│   ├─ Unified Portal v2統合                               │
│   └─ UI操作機能統合                                       │
│                                                           │
│ Slack Integration (5114)                                 │
│   ├─ メッセージ受信                                       │
│   ├─ コマンド実行                                         │
│   └─ 結果通知                                             │
│                                                           │
│ Web Voice Interface (5115)                               │
│   └─ 音声入力・出力                                       │
└─────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 5: ManaOS収益化（自動化・商品化）                   │
├─────────────────────────────────────────────────────────┤
│ Revenue Tracker (5117)                                   │
│   └─ 収益追跡システム                                     │
│                                                           │
│ Product Automation (5118)                               │
│   └─ 成果物自動商品化                                     │
│                                                           │
│ Payment Integration (5119)                               │
│   └─ 決済統合                                             │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 データフロー

### 記録 → 分析 → 再構築 → 記憶

```
【STEP 1: 記録（Obsidian）】
Daily/2026-01-06.md
  ├─ 体調: ◎△×
  ├─ ひとこと: 自由記述
  ├─ 思考メモ: 箇条書き
  └─ 行動ログ: 簡潔に

【STEP 2: 分析（NotebookLM）】
週次分析（週1回）
  ├─ 傾向分析
  ├─ 体調と行動の関係
  ├─ 無駄に疲れている原因
  └─ 改善ポイント3つ
  ↓
Review/2026-01-06-notebooklm.md

【STEP 3: 再構築（Antigravity）】
関連ノートを選択
  ├─ MOC再構築
  ├─ 記事化（note/Zenn）
  └─ YAML一括編集
  ↓
MOCs/テーマ名-MOC.md
または
Articles/記事名.md

【STEP 4: 記憶（ManaOS）】
RAG Memory (5103)
  ├─ 重要度スコア判定
  ├─ 重複チェック
  └─ 時系列メモリ保存
  ↓
Unified Memory System
```

---

## 🧩 ツール間の棲み分け

| ツール         | 向いてること              | 使うタイミング           |
|------------|---------------------|-------------------|
| **Obsidian** | 記録・ログ・構想          | 毎日（考えずに放り込む）    |
| **NotebookLM** | 分析・振り返り            | 週1回（セルフ反省会）      |
| **Antigravity** | まとめ・再構築・軽作業      | アウトプット時（記事化）    |
| **Cursor** | ガチ実装・コード          | 開発時（実装が必要）      |
| **ローカルLLM** | 常駐・自律・監視          | 常時（ManaOS内部）       |
| **ManaOS** | 記憶・判断・自動実行        | 常時（司令塔）           |

**全部使う。役割を混ぜない。**

---

## 🔌 統合ポイント

### Obsidian → ManaOS

```
Obsidian Vault
  ↓ (環境変数: OBSIDIAN_VAULT_PATH)
RAG Memory (5103)
  ├─ ノート読み込み
  ├─ 重要度スコア判定
  └─ 記憶システムに保存
```

### NotebookLM → ManaOS

```
NotebookLM分析結果
  ↓ (Review/YYYY-MM-DD-notebooklm.md)
Obsidianに保存
  ↓
RAG Memory (5103)
  └─ 分析結果を記憶システムに登録
```

### Antigravity → ManaOS

```
Antigravity再構築結果
  ↓ (MOCs/*.md or Articles/*.md)
Obsidianに保存
  ↓
Content Generation (5109)
  └─ 記事化・商品化
```

---

## 🎯 サービス一覧（全19サービス）

### Core Services (11サービス)

| # | サービス | ポート | 役割 |
|---|---------|--------|------|
| 1 | Intent Router | 5100 | 意図分類 |
| 2 | Task Planner | 5101 | 実行計画作成 |
| 3 | Task Critic | 5102 | 結果評価 |
| 4 | RAG Memory | 5103 | 記憶管理 |
| 5 | Task Queue | 5104 | タスクキュー |
| 6 | UI Operations | 5105 | UI操作 |
| 7 | Unified Orchestrator | 5106 | 統合オーケストレーター |
| 8 | Executor Enhanced | 5107 | 実行エンジン |
| 9 | Portal Integration | 5108 | Portal統合 |
| 10 | Content Generation | 5109 | 成果物自動生成 |
| 11 | LLM Optimization | 5110 | LLM最適化 |

### Phase 1: "壊れた時の自分"を救う (2サービス)

| # | サービス | ポート | 役割 |
|---|---------|--------|------|
| 12 | System Status API | 5112 | 統合ステータスAPI |
| 13 | Crash Snapshot | 5113 | 障害スナップショット |

### Phase 2: 操作を"人間語"にする (3サービス)

| # | サービス | ポート | 役割 |
|---|---------|--------|------|
| 14 | Slack Integration | 5114 | Slack統合 |
| 15 | Web Voice Interface | 5115 | Web音声インターフェース |
| 16 | Portal Voice Integration | 5116 | Portal統合拡張 |

### Phase 3: 金になる導線 (3サービス)

| # | サービス | ポート | 役割 |
|---|---------|--------|------|
| 17 | Revenue Tracker | 5117 | 収益追跡システム |
| 18 | Product Automation | 5118 | 成果物自動商品化 |
| 19 | Payment Integration | 5119 | 決済統合 |

---

## 🔄 実行フロー（完全版）

```
ユーザー入力（音声/テキスト/イベント）
  ↓
[LLM最適化 (5110)] - フィルタ・モデル選択
  ↓
[Intent Router (5100)] - 意図分類
  ↓
[Task Planner (5101)] - 実行計画作成
  ↓
[Task Queue (5104)] - キューに追加（Priority制御・Rate Limit）
  ↓
[Executor Enhanced (5107)] - タスク実行
  ├─ n8nワークフロー実行
  ├─ API呼び出し
  ├─ スクリプト実行
  └─ コマンド実行
  ↓
[Task Critic (5102)] - 結果評価
  ↓
[RAG Memory (5103)] - 記憶保存（重要度・重複チェック・時系列）
  ├─ Obsidian連携（一次情報として保存）
  ├─ NotebookLM分析結果連携（分析結果として保存）
  └─ Antigravity再構築結果連携（再構築結果として保存）
  ↓
[Content Generation (5109)] - 成果物自動生成（オプション）
  ├─ 日報→ブログ
  ├─ 構成ログ→note/Zenn記事
  └─ 画像→テンプレ商品
  ↓
[UI Operations (5105)] - 結果表示・コスト追跡
  ↓
[Unified Orchestrator (5106)] - 全体統合
  ↓
[Portal Integration (5108)] - UI統合
  ↓
[Slack Integration (5114)] - 通知
```

---

## 🎯 重要原則

### 1. 「原本は人間」

- Obsidianが一次情報
- AIは全部"二次加工"
- ManaOSの思想「原本は人間」が完全に守られている

### 2. 役割分担

- **Obsidian**: 事実と一次思考の保管庫
- **NotebookLM**: 自分専用の分析官
- **Antigravity**: 知識加工工場
- **ManaOS**: 司令塔・記憶・自動化

### 3. 全部使う。役割を混ぜない。

- ツール間の棲み分けを明確に
- 各ツールの強みを活かす
- 無理に1つのツールで全部やらない

---

## 📋 設定ファイル

### 環境変数

```bash
# Obsidian
OBSIDIAN_VAULT_PATH=C:/Users/mana4/Documents/Obsidian Vault

# ManaOS
ORCHESTRATOR_URL=http://localhost:5106
FILE_SECRETARY_URL=http://localhost:5120
SLACK_WEBHOOK_URL=
SLACK_BOT_TOKEN=
SLACK_VERIFICATION_TOKEN=

# LLM
OLLAMA_URL=http://localhost:11434
```

### 設定ファイル

- `intent_router_config.json` - Intent Router設定
- `task_planner_config.json` - Task Planner設定
- `rag_memory_config.json` - RAG Memory設定
- `llm_optimization_config.json` - LLM最適化設定

---

## 🎯 今後の拡張ポイント

### 短期（1〜3ヶ月）

1. ✅ Obsidian統合（完了）
2. ✅ NotebookLM統合（完了）
3. ✅ Antigravity統合（完了）
4. 🔄 自動化ワークフロー（n8n）の拡張

### 中期（3〜6ヶ月）

1. NotebookLM API自動化
2. Antigravity API自動化
3. 記事自動投稿（note/Zenn）
4. 収益化の自動化

### 長期（6ヶ月〜）

1. 他ツール統合（Heptabase、Notionなど）
2. マルチ環境対応（母艦/ローカル/外部）
3. 分散実行システム

---

## 📌 まとめ

**これは「新しい何か」じゃない。  
すでにマナが作ってきた世界の"人間側UIの完成形"。**

**Obsidian → NotebookLM → Antigravity → ManaOS**

**全部使う。役割を混ぜない。完璧を目指さない。**

---




















