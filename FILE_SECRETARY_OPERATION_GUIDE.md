# File Secretary 運用ガイド

**最終更新**: 2026-01-03  
**バージョン**: 3.0.0

---

## 📋 目次

1. [クイックスタート](#クイックスタート)
2. [日常運用](#日常運用)
3. [トラブルシューティング](#トラブルシューティング)
4. [設定項目一覧](#設定項目一覧)
5. [APIリファレンス](#apiリファレンス)

---

## 🚀 クイックスタート

### Windows環境

```powershell
# PowerShellで実行
.\file_secretary_quick_start.ps1
```

### Linux/Mac環境

```bash
# 実行権限付与
chmod +x file_secretary_quick_start.sh

# 起動
./file_secretary_quick_start.sh
```

### 手動起動

```bash
# 1. Indexer起動
python file_secretary_start.py

# 2. APIサーバー起動（別ターミナル）
export PORT=5120
python file_secretary_api.py

# 3. Slack Integration起動（別ターミナル）
export PORT=5114
export FILE_SECRETARY_URL=http://localhost:5120
python slack_integration.py
```

---

## 💼 日常運用

### 基本的な使い方

1. **ファイルをINBOXに放り込む**
   - `00_INBOX/` にファイルを保存
   - 自動的に検知・インデックスされます

2. **Slackで状況確認**
   ```
   Inboxどう？
   ```

3. **整理実行**
   ```
   終わった
   ```

4. **復元（必要に応じて）**
   ```
   戻して
   ```

5. **検索**
   ```
   探して：日報
   ```

### 運用管理コマンド

```bash
# 状態確認
python file_secretary_manager.py status

# 再起動
python file_secretary_manager.py restart

# 停止
python file_secretary_manager.py stop
```

---

## 🔧 トラブルシューティング

### データベースエラー

**症状**: "database disk image is malformed"

**対処**:
1. すべてのプロセスを停止
2. データベースファイルを削除
3. 再起動（自動的に再作成されます）

```bash
# Windows
Get-Process python | Stop-Process -Force
Remove-Item file_secretary.db* -Force
python file_secretary_start.py
```

### APIサーバーが起動しない

**確認事項**:
- ポート5120が使用中でないか確認
- 環境変数が正しく設定されているか確認

```bash
# ポート確認（Windows）
netstat -ano | findstr :5120

# ポート確認（Linux/Mac）
lsof -i :5120
```

### ファイルが検知されない

**確認事項**:
- INBOXパスが正しいか確認
- ファイル監視が起動しているか確認
- ファイルの書き込みが完了しているか確認（デバウンス2秒）

---

## ⚙️ 設定項目一覧

### 必須設定

| 環境変数 | 説明 | デフォルト |
|---------|------|-----------|
| `FILE_SECRETARY_DB_PATH` | データベースファイルパス | `file_secretary.db` |
| `INBOX_PATH` | INBOXディレクトリパス | `/root/00_INBOX` (Linux) / `00_INBOX` (Windows) |

### オプション設定

| 環境変数 | 説明 | デフォルト |
|---------|------|-----------|
| `PORT` | APIサーバーポート | `5120` |
| `GOOGLE_DRIVE_CREDENTIALS` | Google Drive認証情報ファイル | `credentials.json` |
| `GOOGLE_DRIVE_TOKEN` | Google Driveトークンファイル | `token.json` |
| `ROWS_API_KEY` | Rows APIキー | - |
| `FILE_SECRETARY_SPREADSHEET_ID` | RowsスプレッドシートID | - |
| `COMFYUI_URL` | ComfyUI API URL | `http://localhost:8188` |
| `COMFYUI_OUTPUT_DIR` | ComfyUI出力ディレクトリ | `output` |
| `OCR_TEXT_DIR` | OCRテキスト保存ディレクトリ | `ocr_texts` |

---

## 📚 APIリファレンス

### 基本エンドポイント

#### `GET /health`
ヘルスチェック

**レスポンス**:
```json
{
  "status": "healthy",
  "service": "File Secretary",
  "version": "1.0.0"
}
```

#### `GET /api/inbox/status`
INBOX状況取得

**クエリパラメータ**:
- `source` (optional): mother/drive/x280
- `status` (optional): inbox/triaged/done/archived
- `days` (optional): 新規判定日数（デフォルト: 1）

**レスポンス**:
```json
{
  "status": "success",
  "summary": {
    "new_count": 3,
    "old_count": 12,
    "long_term_count": 7,
    "by_type": {"pdf": 5, "image": 4}
  },
  "candidates": [...]
}
```

#### `POST /api/files/organize`
ファイル整理実行

**リクエスト**:
```json
{
  "targets": ["file_id_1", "file_id_2"],
  "thread_ref": "C01234ABCDE",
  "user": "U01234ABCDE",
  "auto_tag": true,
  "auto_alias": true
}
```

#### `POST /api/files/restore`
ファイル復元

**リクエスト**:
```json
{
  "targets": ["file_id_1"],
  "user": "U01234ABCDE"
}
```

#### `GET /api/files/search`
ファイル検索

**クエリパラメータ**:
- `query` (required): 検索クエリ
- `source` (optional): mother/drive/x280
- `status` (optional): inbox/triaged/done/archived
- `limit` (optional): 結果数上限（デフォルト: 10）

---

## 📝 ログ確認

### ログファイルの場所

```
logs/
├── file_secretary_db.log
├── file_secretary_indexer.log
├── file_secretary_api.log
└── file_secretary_organizer.log
```

### ログ確認コマンド

```bash
# 最新のログを確認
tail -f logs/file_secretary_api.log

# エラーログのみ確認
grep ERROR logs/*.log
```

---

## 🎯 ベストプラクティス

1. **定期的なバックアップ**
   - データベースファイル（`file_secretary.db`）を定期的にバックアップ

2. **ログローテーション**
   - ログファイルは自動ローテーション（10MB、5ファイル保持）

3. **監視設定**
   - APIサーバーのヘルスチェックを定期的に実行
   - エラーログを監視

4. **パフォーマンス**
   - 大量のファイルがある場合は、インデックス処理に時間がかかる可能性あり
   - 必要に応じてバッチ処理を検討

---

## 🔗 関連ドキュメント

- `FILE_SECRETARY_DESIGN.md` - 実装設計書
- `FILE_SECRETARY_SETUP.md` - Phase1セットアップガイド
- `FILE_SECRETARY_COMPLETE.md` - 完全実装完了ドキュメント
- `FILE_SECRETARY_TEST_COMPLETE.md` - Phase1テスト完了報告
- `FILE_SECRETARY_PHASE2_3_TEST.md` - Phase2・Phase3テスト結果
- `FILE_SECRETARY_FINAL_SUMMARY.md` - 最終サマリ

---

**完成！** File Secretaryシステムの運用準備が整いました。

