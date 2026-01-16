# Skills応用例・拡張アイデア

bun913方式のSkillsシステムは、様々な用途に応用できます。

## 🎯 応用の原則

1. **「AIに考えさせる仕事」と「機械にやらせる仕事」の分離**
2. **YAML形式の構造化された入力**
3. **Pythonスクリプトでの処理**
4. **冪等性の確保（idempotency_key）**

## 💡 応用可能な分野

### 1. データ管理・統合

#### ✅ Notion操作（notion_ops）
- Notionデータベースへの登録・更新
- ページ作成・更新
- データベースクエリ

**YAML例:**
```yaml
kind: notion_ops
action: create_page  # create_page, update_page, query_database
database_id: "xxx-xxx-xxx"
properties:
  title: "タスク名"
  status: "進行中"
  due_date: "2026-01-15"
idempotency_key: "notion_task_2026-01-13_001"
```

#### ✅ データベース操作（database_ops）
- SQLクエリ実行
- データ挿入・更新・削除
- バッチ処理

**YAML例:**
```yaml
kind: database_ops
action: execute_query  # execute_query, insert, update, delete
database_type: postgresql  # postgresql, mongodb, sqlite
connection_string: "postgresql://user:pass@localhost/db"
query: "SELECT * FROM tasks WHERE status = 'pending'"
idempotency_key: "db_query_2026-01-13_001"
```

#### ✅ Rowsスプレッドシート操作（rows_ops）
- データ送信
- クエリ実行
- スプレッドシート一覧取得

**YAML例:**
```yaml
kind: rows_ops
action: send_data  # send_data, query, list
spreadsheet_id: "xxx-xxx-xxx"
sheet_name: "Sheet1"
data:
  - name: "項目1"
    value: 100
  - name: "項目2"
    value: 200
idempotency_key: "rows_send_2026-01-13_001"
```

### 2. システム監視・運用

#### ✅ サーバー監視・復旧（server_monitor）
- サービス状態確認
- 自動再起動
- ヘルスチェック

**YAML例:**
```yaml
kind: server_monitor
action: check_and_restart  # check, restart, status
service_name: "unified_api_server"
port: 9500
auto_restart: true
notify:
  slack: true
idempotency_key: "server_check_2026-01-13_001"
```

#### ✅ ログ分析・レポート（log_analysis）
- ログファイル解析
- エラーレポート生成
- パフォーマンス分析

**YAML例:**
```yaml
kind: log_analysis
action: analyze  # analyze, report, alert
log_file: "logs/app.log"
analysis_type: "error_summary"  # error_summary, performance, pattern
output_format: "markdown"
output_path: "reports/log_analysis_2026-01-13.md"
idempotency_key: "log_analysis_2026-01-13"
```

### 3. コミュニケーション

#### ✅ メール送信（email_ops）
- メール送信
- バッチ送信
- テンプレート使用

**YAML例:**
```yaml
kind: email_ops
action: send  # send, batch_send
to: "user@example.com"
subject: "日報"
body: "今日の作業内容..."
attachments:
  - "reports/daily_report.pdf"
idempotency_key: "email_send_2026-01-13_001"
```

#### ✅ カレンダー操作（calendar_ops）
- イベント作成
- イベント更新
- イベント一覧取得

**YAML例:**
```yaml
kind: calendar_ops
action: create_event  # create_event, update_event, list_events
calendar_id: "primary"
title: "会議"
start_time: "2026-01-15T14:00:00"
end_time: "2026-01-15T15:00:00"
attendees:
  - "user@example.com"
idempotency_key: "calendar_event_2026-01-13_001"
```

### 4. ファイル・データ処理

#### ✅ ファイル整理（file_organize）
- ファイル分類
- フォルダ整理
- 重複ファイル削除

**YAML例:**
```yaml
kind: file_organize
action: organize  # organize, classify, deduplicate
source_directory: "Downloads"
rules:
  - pattern: "*.pdf"
    destination: "Documents/PDFs"
  - pattern: "*.jpg"
    destination: "Pictures"
idempotency_key: "file_organize_2026-01-13"
```

#### ✅ データ変換（data_transform）
- CSV/JSON/Excel変換
- データクリーニング
- フォーマット変換

**YAML例:**
```yaml
kind: data_transform
action: convert  # convert, clean, format
input_file: "data/raw.csv"
output_file: "data/processed.json"
transformation:
  - type: "filter"
    condition: "status == 'active'"
  - type: "format"
    date_format: "YYYY-MM-DD"
idempotency_key: "data_transform_2026-01-13_001"
```

### 5. バックアップ・復旧

#### ✅ データベースバックアップ（db_backup）
- データベースダンプ
- バックアップ管理
- リストア

**YAML例:**
```yaml
kind: db_backup
action: backup  # backup, restore, list
database_type: postgresql
database_name: "myapp"
backup_path: "backups/db_backup_2026-01-13.sql"
compress: true
notify:
  slack: true
idempotency_key: "db_backup_2026-01-13"
```

### 6. タスク管理

#### ✅ タスク管理システム連携（task_ops）
- タスク作成
- タスク更新
- タスク一覧取得

**YAML例:**
```yaml
kind: task_ops
action: create  # create, update, list
task_manager: "todoist"  # todoist, asana, jira
title: "新しい機能実装"
description: "詳細..."
due_date: "2026-01-20"
priority: "high"
idempotency_key: "task_create_2026-01-13_001"
```

## 🔧 実装パターン

既存のSkills（daily_ops, git_ops等）と同じパターンで実装：

1. **Skillsファイル作成** (`skills/<name>_skill.mdc`)
   - 目的、使い方、YAMLフォーマット、処理フローを記載

2. **処理スクリプト作成** (`scripts/apply_skill_<name>.py`)
   - YAML読み込み
   - 冪等性チェック（idempotency_key）
   - 実際の処理実行
   - 履歴記録

3. **サンプルYAML作成** (`artifacts/example_<name>.yaml`)

4. **README更新** (`skills/README.md`)

## 📊 優先度の高い応用例（推奨）

1. **notion_ops** - Notionデータベースへの登録（よく使う）
2. **server_monitor** - サーバー監視・復旧（運用効率化）
3. **database_ops** - データベース操作（データ管理）

## 🚀 実装方法

既存のSkillsを参考に、同じパターンで実装できます。

1. `scripts/apply_skill_daily_ops.py` を参考にスクリプト作成
2. `skills/daily_ops_skill.mdc` を参考にSkillsファイル作成
3. 冪等性キーと履歴管理を実装
4. Cursorに配置して動作確認

## 🔗 参考

- [実装ガイド](SKILLS_IMPLEMENTATION_GUIDE.md)
- [Skills README](../skills/README.md)
- [bun913さんの記事](https://zenn.dev/bun913/articles/mcp-to-skills-token-reduction)
