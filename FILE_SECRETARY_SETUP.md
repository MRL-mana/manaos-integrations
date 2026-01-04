# File Secretary Phase1 - セットアップガイド

## 📋 概要

ファイル秘書システム Phase1のセットアップ手順です。

## 🔧 必要な環境

- Python 3.8+
- SQLite3
- Flask
- watchdog
- httpx

## 📦 インストール

```bash
pip install flask flask-cors watchdog httpx
```

## 🚀 起動方法

### 1. データベースとIndexer起動

```bash
python file_secretary_start.py
```

これで以下が実行されます：
- データベース初期化
- INBOX監視開始（`/root/00_INBOX`）
- 既存ファイルのインデックス

### 2. File Secretary API起動

別のターミナルで：

```bash
export PORT=5120
export FILE_SECRETARY_DB_PATH=file_secretary.db
export INBOX_PATH=/root/00_INBOX
python file_secretary_api.py
```

### 3. Slack Integration起動（既存）

```bash
export PORT=5114
export FILE_SECRETARY_URL=http://localhost:5120
export ORCHESTRATOR_URL=http://localhost:5106
python slack_integration.py
```

## 🧪 テスト

### APIテスト

```bash
# ヘルスチェック
curl http://localhost:5120/health

# INBOX状況取得
curl http://localhost:5120/api/inbox/status

# ファイル検索
curl "http://localhost:5120/api/files/search?query=日報"
```

### Slackテスト

Slackで以下を送信：

- `Inboxどう？` - INBOX状況確認
- `終わった` - ファイル整理実行
- `戻して` - ファイル復元
- `探して：日報` - ファイル検索

## 📁 ディレクトリ構造

```
manaos_integrations/
├── file_secretary_db.py          # データベース管理
├── file_secretary_indexer.py      # ファイル監視・インデックス
├── file_secretary_organizer.py   # ファイル整理
├── file_secretary_api.py         # APIサーバー
├── file_secretary_schemas.py     # データモデル
├── file_secretary_templates.py   # Slack返信テンプレート
├── file_secretary_start.py       # 起動スクリプト
├── file_secretary.db             # SQLiteデータベース（自動生成）
└── FILE_SECRETARY_DESIGN.md      # 設計書
```

## 🔍 確認事項

1. **INBOXパス**: 環境変数`INBOX_PATH`で指定（デフォルト: `/root/00_INBOX`）
2. **データベース**: 環境変数`FILE_SECRETARY_DB_PATH`で指定（デフォルト: `file_secretary.db`）
3. **ポート**: File Secretary APIは5120、Slack Integrationは5114

## 🐛 トラブルシューティング

### データベースが作成されない

- 書き込み権限を確認
- パスの存在を確認

### ファイル監視が動かない

- INBOXパスの存在を確認
- watchdogがインストールされているか確認

### Slack連携が動かない

- `FILE_SECRETARY_URL`環境変数が設定されているか確認
- File Secretary APIが起動しているか確認

## 📝 次のステップ

Phase2では以下を追加予定：
- Google Drive INBOX監視
- OCR統合
- より高度なタグ推定（LLM）


