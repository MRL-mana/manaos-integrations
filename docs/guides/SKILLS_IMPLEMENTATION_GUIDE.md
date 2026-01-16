# ManaOS Skills実装ガイド

bun913さんの記事「MCPでやる必要のない業務をSkillsに置き換えてトークンと時間の消費を爆減してみた」のアプローチをManaOSに適用した実装ガイドです。

## 📋 概要

### 問題点

従来のMCPベースのアプローチでは：

- **トークン消費が大きい**: 1件のノート作成に数千〜数万トークン
- **時間がかかる**: 1件あたり数秒〜数十秒
- **再実行が困難**: エラー時の再実行で重複が発生
- **成果物の再利用が難しい**: Markdown形式で構造化されていない

### 解決策

**「AIに考えさせる仕事」と「機械にやらせる仕事」を明確に分離**

- **AI（MCP）**: 思考・判断・整理・要約など、文脈が必要な作業
- **Skills + CLI**: 反復的・確定的な作業（ファイル作成、API呼び出し、通知など）

## 🎯 実装内容

### 1. YAML形式の成果物フォーマット

AIに出力させるYAML形式を定義：

```yaml
kind: daily_ops
date: 2026-01-12
title: "日報 + タスク整理"
tags: ["ops", "manaos"]
summary: |
  今日の要点を3行くらいで。
tasks:
  - title: "バックアップ確認"
    status: todo
    priority: high
notify:
  slack: true
  obsidian: true
idempotency_key: "daily_ops_2026-01-12"
```

**メリット**:
- 人間もAIも読みやすい
- プログラムで処理しやすい
- 後から編集・再利用可能

### 2. Pythonスクリプトによるバッチ処理

`scripts/apply_skill_daily_ops.py` で以下を実現：

- YAML読み込み・バリデーション
- 冪等性チェック（`idempotency_key`で重複防止）
- Obsidianノート生成
- Slack通知送信
- 処理履歴の記録

### 3. Skillsファイル

`skills/daily_ops_skill.mdc` でAIに使い方を教える：

- 目的と使用方法
- YAMLフォーマット仕様
- 処理フロー
- エラーハンドリング

### 4. CLIヘルパー

人間でもAIでも使えるCLIツール：

- `scripts/obsidian_cli.py`: Obsidianノート操作
- `scripts/slack_cli.py`: Slack通知送信

## 🚀 使用方法

### Step 1: AIにYAML形式で出力させる

CursorやClaude Codeで：

```
今日の日報をYAML形式で出力してください。
以下のフォーマットに従ってください：

```yaml
kind: daily_ops
date: 2026-01-12
title: "日報"
tags: ["ops"]
summary: "今日の要点"
tasks:
  - title: "タスク1"
    status: todo
    priority: high
notify:
  slack: true
  obsidian: true
idempotency_key: "daily_ops_2026-01-12"
```
```

### Step 2: YAMLファイルを保存

AIが出力したYAMLを `artifacts/daily_ops_2026-01-12.yaml` として保存

### Step 3: スクリプトで処理

```bash
python scripts/apply_skill_daily_ops.py artifacts/daily_ops_2026-01-12.yaml
```

**結果:**
- ✅ Obsidianに `Daily/2026-01-12_日報.md` が作成される
- ✅ Slackに通知が送信される（`notify.slack: true`の場合）
- ✅ 処理履歴に記録され、再実行しても重複しない

## 📊 効果測定

### トークン削減

| 方式 | 1件あたりのトークン | 100件処理時のトークン |
|------|-------------------|---------------------|
| MCP | 5,000〜50,000 | 500,000〜5,000,000 |
| Skills + CLI | 500〜1,000 | 50,000〜100,000 |

**削減率: 約90%**

### 時間削減

| 方式 | 1件あたりの時間 | 100件処理時の時間 |
|------|----------------|------------------|
| MCP | 5〜30秒 | 8〜50分 |
| Skills + CLI | 0.1〜0.5秒 | 10〜50秒 |

**削減率: 約95%**

## 🔧 環境設定

### 環境変数

```bash
# Obsidian Vaultパス
export OBSIDIAN_VAULT_PATH="C:/Users/mana4/Documents/Obsidian Vault"

# Slack Webhook URL
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

### Skillsファイルの配置

#### Cursor

`.cursor/rules/` ディレクトリに配置（またはrulesyncで管理）

#### Claude Code

プロジェクトルートの `skills/` ディレクトリに配置し、Claude Codeから参照

## 📝 拡張例

### Notion登録Skill

```yaml
kind: notion_entry
database_id: "xxx"
properties:
  title: "エントリタイトル"
  status: "進行中"
notify:
  slack: true
```

### Google DriveバックアップSkill

```yaml
kind: drive_backup
source: "C:/backup"
destination: "backup/2026-01-12"
notify:
  slack: true
```

## 🎓 ベストプラクティス

### 1. 冪等性の確保

すべてのSkillsで `idempotency_key` を使用：

```yaml
idempotency_key: "daily_ops_2026-01-12"
```

### 2. 構造化されたフォーマット

MarkdownではなくYAML/JSONを使用：

- ✅ YAML: 人間も読みやすい
- ✅ JSON: プログラム処理が簡単
- ❌ Markdown: パースが複雑

### 3. エラーハンドリング

- 部分的な失敗でも続行（Obsidian成功、Slack失敗など）
- エラーはログに記録
- 再実行可能な設計

### 4. バッチ処理の活用

複数ファイルを一度に処理：

```bash
python scripts/apply_skill_daily_ops.py artifacts/*.yaml
```

## 🔗 参考リンク

- [bun913さんの記事](https://zenn.dev/bun913/articles/mcp-to-skills-token-reduction)
- [Agent Skills公式ドキュメント](https://docs.anthropic.com/claude/docs/agent-skills)
- [ManaOS Skills README](../skills/README.md)

## 📌 まとめ

**「MCPで頑張らせてた雑務」をSkills + CLIに落とすことで：**

- ✅ トークン消費を約90%削減
- ✅ 処理時間を約95%削減
- ✅ 冪等性で安全な再実行
- ✅ 成果物の再利用が容易

**AIを「頑張る係」ではなく「賢い上司」にする** という発想が鍵です。
