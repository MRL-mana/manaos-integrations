# ManaOS Skills コレクション

bun913さんの記事「MCPでやる必要のない業務をSkillsに置き換えてトークンと時間の消費を爆減してみた」のアプローチをManaOSに適用したSkills集です。

## コンセプト

**「AIに考えさせる仕事」と「機械にやらせる仕事」を明確に分離**

- **AI（MCP）**: 思考・判断・整理・要約など、文脈が必要な作業
- **Skills + CLI**: 反復的・確定的な作業（ファイル作成、API呼び出し、通知など）

## 構成

```
skills/
├── daily_ops_skill.mdc          # 日次運用タスク処理Skill
├── drive_backup_skill.mdc       # Google DriveバックアップSkill
├── n8n_workflow_skill.mdc       # n8nワークフロー操作Skill
├── git_ops_skill.mdc            # Git操作Skill
└── README.md                     # このファイル

scripts/
├── apply_skill_daily_ops.py      # 日次運用タスク処理スクリプト
├── apply_skill_drive_backup.py   # Google Driveバックアップスクリプト
├── apply_skill_n8n_workflow.py   # n8nワークフロー操作スクリプト
├── apply_skill_git_ops.py        # Git操作スクリプト
├── obsidian_cli.py               # Obsidian CLIヘルパー
└── slack_cli.py                  # Slack CLIヘルパー

artifacts/                        # AIが出力するYAML成果物の保存先
data/
├── skill_daily_ops_history.json    # 処理履歴（冪等性管理用）
├── skill_drive_backup_history.json # バックアップ処理履歴
├── skill_n8n_workflow_history.json # n8nワークフロー処理履歴
└── skill_git_ops_history.json      # Git操作処理履歴
```

## 使用方法

### 1. 日次運用タスク処理（daily_ops）

#### Step 1: AIにYAML形式で出力させる

CursorやClaude Codeで以下のように指示：

```
今日の日報をYAML形式で出力してください。
以下のフォーマットに従ってください：

```yaml
kind: daily_ops
date: 2026-01-12
title: "日報"
tags: ["ops", "manaos"]
summary: |
  今日の要点を3行くらいで。
tasks:
  - title: "バックアップ確認"
    status: todo
    priority: high
  - title: "n8nワークフロー整理"
    status: doing
notes:
  - "気づき1"
  - "気づき2"
notify:
  slack: true
  obsidian: true
idempotency_key: "daily_ops_2026-01-12"
```
```

#### Step 2: YAMLファイルを保存

AIが出力したYAMLを `artifacts/daily_ops_2026-01-12.yaml` として保存

#### Step 3: スクリプトで処理

```bash
python scripts/apply_skill_daily_ops.py artifacts/daily_ops_2026-01-12.yaml
```

**結果:**
- ✅ Obsidianに `Daily/2026-01-12_日報.md` が作成される
- ✅ Slackに通知が送信される（`notify.slack: true`の場合）
- ✅ 処理履歴に記録され、再実行しても重複しない（冪等性）

### 2. Google Driveバックアップ（drive_backup）

#### Step 1: AIにYAML形式で出力させる

```yaml
kind: drive_backup
date: 2026-01-12
source: "C:/backup/data"
destination: "backup/2026-01-12"
description: "データバックアップ"
compress: true
notify:
  slack: true
idempotency_key: "drive_backup_2026-01-12"
```

#### Step 2: スクリプトで処理

```bash
python scripts/apply_skill_drive_backup.py artifacts/backup_2026-01-12.yaml
```

**結果:**
- ✅ Google Driveにバックアップがアップロードされる
- ✅ 圧縮オプションでZIPファイルとして保存可能
- ✅ Slackに通知が送信される（`notify.slack: true`の場合）

### 3. n8nワークフロー操作（n8n_workflow）

#### Step 1: AIにYAML形式で出力させる

```yaml
kind: n8n_workflow
action: activate  # activate, deactivate, execute, import
workflow_id: "2ViGYzDtLBF6H4zn"
notify:
  slack: true
idempotency_key: "n8n_activate_2026-01-12"
```

#### Step 2: スクリプトで処理

```bash
python scripts/apply_skill_n8n_workflow.py artifacts/n8n_workflow_2026-01-12.yaml
```

**結果:**
- ✅ ワークフローが有効化/無効化/実行/インポートされる
- ✅ Slackに通知が送信される（`notify.slack: true`の場合）

### 4. Git操作（git_ops）

#### Step 1: AIにYAML形式で出力させる

```yaml
kind: git_ops
action: commit_and_push  # commit, push, pull, tag, status, commit_and_push
commit_message: "Update: Skills実装"
branch: "main"
files:
  - "scripts/*.py"
  - "skills/*.mdc"
notify:
  slack: true
idempotency_key: "git_commit_2026-01-12_001"
```

#### Step 2: スクリプトで処理

```bash
python scripts/apply_skill_git_ops.py artifacts/git_ops_2026-01-12.yaml
```

**結果:**
- ✅ Git操作が実行される（commit, push, pull, tag, status）
- ✅ Slackに通知が送信される（`notify.slack: true`の場合）

## CLIヘルパー

### Obsidian CLI

```bash
# ノート作成
python scripts/obsidian_cli.py create "タイトル" --content "内容" --tags ops manaos --folder Daily

# ファイルからノート作成
python scripts/obsidian_cli.py create "タイトル" --file content.md --folder Daily

# ノート検索
python scripts/obsidian_cli.py search "検索クエリ" --folder Daily
```

### Slack CLI

```bash
# メッセージ送信
python scripts/slack_cli.py send --message "通知内容"

# ファイルから送信
python scripts/slack_cli.py send --file message.txt

# チャンネル指定
python scripts/slack_cli.py send --message "通知" --channel "#general"
```

## 環境変数

```bash
# Obsidian Vaultパス
export OBSIDIAN_VAULT_PATH="C:/Users/mana4/Documents/Obsidian Vault"

# Slack Webhook URL
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# n8n設定
export N8N_BASE_URL="http://localhost:5678"
export N8N_API_KEY="your-api-key-here"

# Google Drive認証情報
# credentials.json, token.json をプロジェクトルートに配置
```

## Skillsファイルの配置

### Cursor

`.cursor/rules/` ディレクトリに配置（またはrulesyncで管理）

### Claude Code

プロジェクトルートの `skills/` ディレクトリに配置し、Claude Codeから参照

## メリット

### トークン削減

- **従来（MCP）**: 1件のノート作成に数千〜数万トークン
- **Skills + CLI**: YAML生成のみ（数百トークン）+ スクリプト実行（0トークン）

### 時間削減

- **従来（MCP）**: 1件あたり数秒〜数十秒
- **Skills + CLI**: バッチ処理で数百件を数分で処理可能

### 冪等性

- 同じ `idempotency_key` で再実行しても重複しない
- エラー時の再実行が安全

### 再利用性

- YAML成果物を後から編集・再利用可能
- スクリプトは人間でもAIでも使える

## 実装済みSkills

- [x] 日次運用タスク処理（daily_ops）
- [x] Google Driveバックアップ（drive_backup）
- [x] n8nワークフロー操作（n8n_workflow）
- [x] Git操作（git_ops）
- [x] Notion操作（notion_ops）
- [x] サーバー監視・復旧（server_monitor）
- [x] データベース操作（database_ops）
- [x] Rows操作（rows_ops）
- [x] ファイル整理（file_organize）
- [x] データ変換（data_transform）
- [x] ログ分析（log_analysis）
- [x] メール送信（email_ops）
- [x] カレンダー操作（calendar_ops）
- [x] データベースバックアップ（db_backup）

## 参考

- [bun913さんの記事](https://zenn.dev/bun913/articles/mcp-to-skills-token-reduction)
- [Agent Skills公式ドキュメント](https://docs.anthropic.com/claude/docs/agent-skills)
