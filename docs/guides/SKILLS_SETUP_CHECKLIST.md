# Skills運用開始チェックリスト

実装は完了していますが、実際に運用を開始するために必要な設定を確認してください。

## ✅ 実装完了状況

### Skills定義ファイル
- [x] `skills/daily_ops_skill.mdc`
- [x] `skills/drive_backup_skill.mdc`
- [x] `skills/n8n_workflow_skill.mdc`
- [x] `skills/git_ops_skill.mdc`

### 処理スクリプト
- [x] `scripts/apply_skill_daily_ops.py`
- [x] `scripts/apply_skill_drive_backup.py`
- [x] `scripts/apply_skill_n8n_workflow.py`
- [x] `scripts/apply_skill_git_ops.py`

### CLIヘルパー
- [x] `scripts/obsidian_cli.py`
- [x] `scripts/slack_cli.py`

### 例ファイル
- [x] `artifacts/example_daily_ops.yaml`
- [x] `artifacts/example_drive_backup.yaml`
- [x] `artifacts/example_n8n_workflow.yaml`
- [x] `artifacts/example_git_ops.yaml`

## 🔧 運用開始前のチェックリスト

### 1. 必要なライブラリの確認

```bash
python -c "import yaml, requests; print('OK')"
```

### 2. Skillsファイルの配置

#### Cursorを使用する場合

Skillsファイルを `.cursor/rules/` ディレクトリに配置する必要があります。

**方法1: 手動配置**
```powershell
# .cursor/rules/ ディレクトリを作成（存在しない場合）
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.cursor\rules"

# Skillsファイルをコピー
Copy-Item skills\*.mdc "$env:USERPROFILE\.cursor\rules\"
```

**方法2: rulesyncを使用（推奨）**
既にrulesyncを使用している場合は、`skills/` ディレクトリを管理対象に追加してください。

#### Claude Codeを使用する場合

プロジェクトルートの `skills/` ディレクトリから自動的に参照されます（既に配置済み）。

### 3. 環境変数の設定

必要な環境変数が設定されているか確認：

```powershell
# Obsidian Vaultパス
$env:OBSIDIAN_VAULT_PATH
# デフォルト: C:/Users/mana4/Documents/Obsidian Vault

# Slack Webhook URL
$env:SLACK_WEBHOOK_URL
# 設定が必要

# n8n設定（n8n_workflow Skill使用時）
$env:N8N_BASE_URL
$env:N8N_API_KEY

# Google Drive認証情報（drive_backup Skill使用時）
# credentials.json, token.json をプロジェクトルートに配置
```

### 4. 動作テスト

各Skillを個別にテスト：

```bash
# 1. 日次運用タスク処理
python scripts/apply_skill_daily_ops.py artifacts/example_daily_ops.yaml

# 2. Google Driveバックアップ（認証が必要）
python scripts/apply_skill_drive_backup.py artifacts/example_drive_backup.yaml

# 3. n8nワークフロー操作（n8nサーバーが必要）
python scripts/apply_skill_n8n_workflow.py artifacts/example_n8n_workflow.yaml

# 4. Git操作（Gitリポジトリが必要）
python scripts/apply_skill_git_ops.py artifacts/example_git_ops.yaml
```

### 5. 依存サービスの確認

#### Obsidian
- [ ] Obsidian Vaultが存在するか確認
- [ ] Vaultパスが正しく設定されているか

#### Slack
- [ ] Slack Webhook URLが設定されているか
- [ ] Webhook URLが有効かテスト

#### n8n
- [ ] n8nサーバーが起動しているか
- [ ] N8N_API_KEYが設定されているか

#### Google Drive
- [ ] credentials.jsonが存在するか
- [ ] token.jsonが存在するか（または認証が完了しているか）

#### Git
- [ ] Gitリポジトリが初期化されているか
- [ ] Git認証情報が設定されているか（プッシュ時）

## 🚀 運用開始の手順

### Step 1: 最小限のテスト

最も簡単な `daily_ops` Skillから始める：

1. 環境変数を確認
2. 例ファイルを編集してテスト実行
3. 動作を確認

### Step 2: 段階的に他のSkillsを有効化

1. `git_ops` - Gitリポジトリがあれば簡単
2. `n8n_workflow` - n8nサーバーが起動していれば
3. `drive_backup` - Google Drive認証が必要

### Step 3: SkillsファイルをAIに認識させる

Cursor/Claude CodeでSkillsファイルが認識されるように：

- Cursor: `.cursor/rules/` に配置してCursorを再起動
- Claude Code: `skills/` ディレクトリから自動参照

## 📝 使用方法（運用開始後）

### AIにYAML形式で出力させる

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

### スクリプトで処理

```bash
python scripts/apply_skill_daily_ops.py artifacts/daily_ops_2026-01-12.yaml
```

## ⚠️ 注意事項

1. **冪等性キー**: 同じ `idempotency_key` で再実行しても重複しません
2. **環境変数**: 各Skillに必要な環境変数が設定されているか確認
3. **依存サービス**: 各Skillが依存するサービス（Obsidian、Slack、n8n、Google Drive等）が利用可能か確認

## 🔗 参考

- [Skills README](../skills/README.md)
- [実装ガイド](SKILLS_IMPLEMENTATION_GUIDE.md)
- [拡張実装完了報告](SKILLS_EXPANSION_COMPLETE.md)
