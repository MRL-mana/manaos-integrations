# Skills 運用開始ガイド

## ✅ 準備完了！

Cursorを再起動して、12個のSkillsがすべて認識されました。

## 🎯 すぐに使えるSkills

### 1. daily_ops（日次運用タスク）✅ 推奨

**最も簡単で、すぐに使えます！**

```yaml
# AIに「今日の日報をYAML形式で出力して」と指示
kind: daily_ops
date: 2026-01-13
title: "日報"
tags: ["ops", "manaos"]
summary: "今日の要点"
tasks:
  - title: "タスク1"
    status: todo
    priority: high
notify:
  slack: false
  obsidian: true
idempotency_key: "daily_ops_2026-01-13"
```

**実行:**
```bash
python scripts/apply_skill_daily_ops.py artifacts/daily_ops_2026-01-13.yaml
```

### 2. git_ops（Git操作）✅ すぐ使える

```yaml
kind: git_ops
action: status  # status, commit, push, pull, tag
repository_path: "."
idempotency_key: "git_status_2026-01-13"
```

**実行:**
```bash
python scripts/apply_skill_git_ops.py artifacts/git_status_2026-01-13.yaml
```

### 3. file_organize（ファイル整理）✅ すぐ使える

```yaml
kind: file_organize
action: organize
source_directory: "Downloads"
rules:
  - pattern: "*.pdf"
    destination: "Documents/PDFs"
idempotency_key: "file_organize_2026-01-13"
```

**実行:**
```bash
python scripts/apply_skill_file_organize.py artifacts/file_organize_2026-01-13.yaml
```

### 4. log_analysis（ログ分析）✅ すぐ使える

```yaml
kind: log_analysis
action: analyze
log_file: "logs/app.log"
analysis_type: "error_summary"
output_format: "markdown"
output_path: "reports/log_analysis_2026-01-13.md"
idempotency_key: "log_analysis_2026-01-13"
```

**実行:**
```bash
python scripts/apply_skill_log_analysis.py artifacts/log_analysis_2026-01-13.yaml
```

## 🔧 設定が必要なSkills

### 5. notion_ops（Notion操作）

**必要な設定:**
```powershell
$env:NOTION_API_KEY = "your-notion-api-key"
```

### 6. n8n_workflow（n8nワークフロー操作）

**必要な設定:**
```powershell
$env:N8N_BASE_URL = "http://localhost:5678"
$env:N8N_API_KEY = "your-api-key"
```

### 7. drive_backup（Google Driveバックアップ）

**必要な設定:**
- Google Drive認証ファイル（credentials.json, token.json）

### 8. email_ops（メール送信）

**必要な設定:**
```powershell
$env:SMTP_HOST = "smtp.gmail.com"
$env:SMTP_PORT = "587"
$env:SMTP_USER = "your-email@gmail.com"
$env:SMTP_PASSWORD = "your-app-password"
$env:EMAIL_FROM = "your-email@gmail.com"
```

### 9. database_ops（データベース操作）

**必要な設定:**
- データベース接続文字列
- 必要に応じて `psycopg2-binary` や `pymongo` をインストール

### 10. rows_ops（Rows操作）

**必要な設定:**
```powershell
$env:ROWS_API_KEY = "your-rows-api-key"
```

### 11. server_monitor（サーバー監視）

**必要な設定:**
- 監視対象サーバーのHTTPヘルスチェックエンドポイント（`/health`）

### 12. data_transform（データ変換）

**必要な設定:**
```bash
pip install pandas openpyxl
```

## 💡 使い方のコツ

### 1. AIにYAML形式で出力させる

Cursorのチャットで：
```
今日の日報をYAML形式で出力してください。
daily_ops Skillのフォーマットに従ってください。
```

### 2. YAMLファイルを保存

AIが出力したYAMLを `artifacts/` ディレクトリに保存：
- `artifacts/daily_ops_2026-01-13.yaml`
- `artifacts/git_ops_2026-01-13.yaml`
- など

### 3. スクリプトで処理

```bash
python scripts/apply_skill_*.py artifacts/*.yaml
```

### 4. 冪等性キーについて

同じ `idempotency_key` で再実行しても重複しません：
- `"daily_ops_2026-01-13"`
- `"git_commit_2026-01-13_001"`
- `"n8n_activate_2026-01-13_001"`

## 🎉 運用開始！

準備は完了しています。AIに「YAML形式で日報を出力して」と指示するだけです！

## 📚 参考

- [Skills README](../skills/README.md) - 全Skillsの詳細
- [クイックスタートガイド](SKILLS_QUICK_START.md) - 詳細な使い方
- [実装ガイド](SKILLS_IMPLEMENTATION_GUIDE.md) - 実装の詳細
- [運用状況](SKILLS_OPERATIONAL_STATUS.md) - 現在の運用状況
