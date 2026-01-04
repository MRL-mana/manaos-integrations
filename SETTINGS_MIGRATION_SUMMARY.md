# 設定・接続情報の移行まとめ

## ✅ 完了した作業

### 1. 設定ファイルのパス更新
以下のファイルのOneDriveパスを新しいパスに更新しました：

- ✅ `manaos_unified_mcp_server/add_to_cursor_mcp.ps1`
- ✅ `svi_mcp_server/add_to_cursor_mcp.ps1`
- ✅ `n8n_mcp_server/add_to_cursor_mcp.ps1`
- ✅ `import_n8n_via_ssh.ps1`
- ✅ `n8n_mcp_server/verify_connection.ps1`

### 2. データベースファイル
- ✅ すべての`.db`ファイルが新しいワークスペースにコピー済み
- ✅ データベースの内容はそのまま引き継がれます

### 3. 認証情報
- ✅ `credentials.json` - Google Drive認証情報
- ✅ `token.json` - 認証トークン
- ✅ `.env` - 環境変数設定

## ⚠️ 必要な作業

### CursorのMCP設定を更新

CursorのMCP設定ファイル（`%USERPROFILE%\.cursor\mcp.json`）にOneDriveのパスが含まれている場合、更新が必要です。

**更新方法：**

1. **自動更新（推奨）**:
   ```powershell
   cd C:\Users\mana4\Desktop\manaos_integrations
   .\update_mcp_settings.ps1
   ```

2. **手動更新**:
   - Cursorの設定ファイルを開く: `%USERPROFILE%\.cursor\mcp.json`
   - `OneDrive\Desktop\manaos_integrations` を `Desktop\manaos_integrations` に置換
   - Cursorを再起動

### 環境変数の確認

環境変数にOneDriveのパスが設定されている場合、更新が必要です：

```powershell
# 環境変数を確認
Get-ChildItem Env: | Where-Object { $_.Value -like "*OneDrive*manaos*" }

# 必要に応じて更新
$env:MANAOS_INTEGRATIONS_PATH = "C:\Users\mana4\Desktop\manaos_integrations"
```

## 📋 確認事項

### 接続情報の確認

以下の接続情報は**変更不要**です（相対パスまたは外部URLのため）：

- ✅ **n8nサーバー**: `http://100.93.120.33:5678` - 変更不要
- ✅ **このはサーバー**: `100.93.120.33` - 変更不要
- ✅ **ComfyUI**: `http://localhost:8188` - 変更不要
- ✅ **Google Drive API**: 認証情報は引き継がれます
- ✅ **Obsidian Vault**: `C:\Users\mana4\Documents\Obsidian Vault` - 変更不要

### データベースファイル

以下のデータベースファイルは新しいワークスペースにコピー済み：

- `auth.db` - 認証情報
- `content_generation.db` - コンテンツ生成履歴
- `cost_tracking.db` - コスト追跡
- `metrics.db` - メトリクス
- `rag_memory.db` - RAGメモリ
- `revenue_tracker.db` - 収益追跡
- `secretary_system.db` - 秘書システム
- `task_queue.db` - タスクキュー

## 🔄 次のステップ

1. **CursorのMCP設定を更新**:
   ```powershell
   .\update_mcp_settings.ps1
   ```

2. **Cursorを再起動**

3. **MCPサーバーの動作確認**:
   - Cursorの開発者ツール（Ctrl+Shift+I）でエラーがないか確認
   - MCPツールが正常に動作するか確認

4. **接続テスト**:
   - n8nワークフローの実行テスト
   - Google Drive連携のテスト
   - その他の外部サービス連携のテスト

## 📝 注意事項

- **環境変数**: システム環境変数にOneDriveのパスが設定されている場合は、手動で更新が必要です
- **自動起動設定**: Windowsの自動起動設定（タスクスケジューラなど）にOneDriveのパスが含まれている場合は更新が必要です
- **ショートカット**: デスクトップやスタートメニューのショートカットも更新が必要な場合があります

## ✅ まとめ

**設定や接続情報は基本的に問題ありません**。以下のみ更新が必要です：

1. ✅ プロジェクト内の設定ファイル（完了）
2. ⚠️ CursorのMCP設定ファイル（`update_mcp_settings.ps1`を実行）
3. ⚠️ 環境変数（必要に応じて確認・更新）

それ以外の接続情報（APIキー、認証情報、外部URLなど）はそのまま引き継がれます。

