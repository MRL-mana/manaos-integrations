# N8N セットアップ・設定・MCPサーバー・コンテナ確認レポート

**確認日時**: 2026年1月8日

---

## 📊 確認結果サマリー

| 項目 | 状態 | 詳細 |
|------|------|------|
| N8N Dockerコンテナ | ✅ 起動中 | ポート5678、healthy |
| N8N ローカルインスタンス | ✅ 起動中 | ポート5679 |
| MCP設定ファイル | ✅ 設定済み | Cursor MCP設定に登録済み |
| APIキー | ⚠️ 無効 | 401エラー発生 |
| MCPサーバーコード | ✅ 正常 | 8つのツール実装済み |

---

## 🔍 詳細確認結果

### 1. N8Nインスタンスの状態

#### Dockerコンテナ（ポート5678）
```
コンテナ名: n8n
状態: Up 3 minutes (healthy)
ポート: 0.0.0.0:5678->5678/tcp
```

**環境変数:**
- `N8N_BASIC_AUTH_USER=mana`
- `N8N_BASIC_AUTH_PASSWORD=changeme`
- `N8N_BASIC_AUTH_ACTIVE=true`
- `N8N_HOST=localhost`
- `N8N_PROTOCOL=http`
- `N8N_PORT=5678`
- `N8N_LOG_LEVEL=debug`
- `N8N_RELEASE_TYPE=stable`

**ログ確認:**
- 正常に起動済み
- Editorは `http://localhost:5678` でアクセス可能
- イベントバス、実行履歴のプルーニングが動作中

#### ローカルインスタンス（ポート5679）
```
状態: 起動中
URL: http://localhost:5679
ヘルスチェック: OK
Web UI: アクセス可能
```

**起動方法:**
```powershell
.\start_n8n_local.ps1
```

**データディレクトリ:**
- `%USERPROFILE%\.n8n`

---

### 2. MCPサーバーの設定

#### MCP設定ファイルの場所
```
%APPDATA%\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json
```

#### 現在の設定内容
```json
{
  "mcpServers": {
    "n8n": {
      "command": "python",
      "args": ["-m", "n8n_mcp_server.server"],
      "cwd": "C:\\Users\\mana4\\OneDrive\\Desktop\\manaos_integrations",
      "env": {
        "N8N_API_KEY": "your_n8n_api_key_here",
        "N8N_BASE_URL": "http://localhost:5679",
        "PYTHONPATH": "C:\\Users\\mana4\\OneDrive\\Desktop\\manaos_integrations"
      }
    }
  }
}
```

**設定状況:**
- ✅ MCP設定ファイルに登録済み
- ✅ N8N_BASE_URL: `http://localhost:5679`（ローカルインスタンス）
- ⚠️ N8N_API_KEY: 設定されているが無効（401エラー）

---

### 3. MCPサーバーの実装状況

#### 実装済みツール（8つ）

1. **n8n_list_workflows**
   - ワークフロー一覧を取得
   - パラメータ: `active` (boolean, オプション)

2. **n8n_import_workflow**
   - ワークフローをインポート
   - パラメータ: `workflow_file` (string, 必須), `activate` (boolean, デフォルト: true)

3. **n8n_activate_workflow**
   - ワークフローを有効化
   - パラメータ: `workflow_id` (string, 必須)

4. **n8n_deactivate_workflow**
   - ワークフローを無効化
   - パラメータ: `workflow_id` (string, 必須)

5. **n8n_execute_workflow**
   - ワークフローを実行
   - パラメータ: `workflow_id` (string, 必須), `data` (object, オプション)

6. **n8n_get_execution**
   - 実行履歴を取得
   - パラメータ: `execution_id` (string, 必須)

7. **n8n_list_executions**
   - 実行履歴一覧を取得
   - パラメータ: `workflow_id` (string, オプション), `limit` (number, デフォルト: 10)

8. **n8n_get_webhook_url**
   - Webhook URLを取得
   - パラメータ: `workflow_id` (string, 必須)

#### サーバーファイル
- **場所**: `n8n_mcp_server/server.py`
- **デフォルトURL**: `http://localhost:5679`
- **APIキー取得方法**: 環境変数 `N8N_API_KEY` から取得

---

### 4. 問題点と解決方法

#### ⚠️ 問題1: APIキーが無効

**症状:**
```
[NG] APIリクエストエラー: 401
レスポンス: {"message":"unauthorized"}
```

**原因:**
- MCP設定ファイルに設定されているAPIキーが無効または期限切れ

**解決方法:**

1. **N8NのWeb UIから新しいAPIキーを取得**
   ```powershell
   # ブラウザでN8Nを開く
   Start-Process "http://localhost:5679/settings/api"
   ```

2. **手順:**
   - 右上のユーザーアイコンをクリック
   - Settings を選択
   - 左メニューから API を選択
   - Create API Key をクリック
   - APIキー名を入力（例: MCP Server）
   - Create をクリック
   - 生成されたAPIキーをコピー

3. **MCP設定ファイルを更新**
   ```powershell
   # 設定ファイルを開く
   $mcpConfigPath = "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"
   notepad $mcpConfigPath
   ```
   
   `N8N_API_KEY` の値を新しいAPIキーに更新

4. **または、自動設定スクリプトを使用**
   ```powershell
   python n8n_mcp_server/get_api_key_from_local.py
   ```

5. **Cursorを再起動**
   - MCP設定を反映するため、Cursorを再起動してください

---

### 5. 推奨される構成

#### 現在の構成
- **開発・テスト用**: ローカルN8N（ポート5679）
- **本番・常時稼働**: Dockerコンテナ（ポート5678）

#### 推奨設定
- MCPサーバーはローカルN8N（ポート5679）に接続
- Dockerコンテナは別用途で使用可能

---

### 6. 確認コマンド

#### N8Nの状態確認
```powershell
# ローカルN8Nの状態確認
python n8n_mcp_server/check_n8n_status.py

# Dockerコンテナの状態確認
docker ps | Select-String -Pattern "n8n"
docker logs n8n --tail 20
```

#### ポート確認
```powershell
# ポート5678（Docker）
Test-NetConnection -ComputerName localhost -Port 5678

# ポート5679（ローカル）
Test-NetConnection -ComputerName localhost -Port 5679
```

#### MCP設定確認
```powershell
# MCP設定ファイルの確認
$mcpConfigPath = "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"
Get-Content $mcpConfigPath | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

#### ワークフロー一覧取得（APIキーが有効な場合）
```powershell
python n8n_mcp_server/list_workflows_detail.py
```

---

### 7. 次のステップ

1. **✅ 完了**: N8Nインスタンスの確認
2. **✅ 完了**: MCP設定ファイルの確認
3. **⚠️ 要対応**: APIキーの再取得と設定
4. **⏳ 未実施**: ワークフローの確認
5. **⏳ 未実施**: MCPツールの動作確認

---

### 8. 関連ファイル

#### 設定ファイル
- `n8n_mcp_server/server.py` - MCPサーバーのメインファイル
- `start_n8n_local.ps1` - ローカルN8N起動スクリプト
- `n8n_mcp_server/check_n8n_status.py` - 状態確認スクリプト
- `n8n_mcp_server/get_api_key_from_local.py` - APIキー取得スクリプト

#### ドキュメント
- `N8N_LOCAL_SETUP.md` - ローカルインストール手順
- `n8n_設定完了レポート.md` - 過去の設定レポート
- `n8n_mcp_server/README.md` - MCPサーバーのREADME
- `n8n_mcp_server/CURSOR_MCP_SETUP.md` - Cursor MCP設定手順

---

## 📝 まとめ

### ✅ 正常に動作している項目
- N8N Dockerコンテナ（ポート5678）
- N8N ローカルインスタンス（ポート5679）
- MCP設定ファイルの設定
- MCPサーバーのコード実装

### ⚠️ 要対応項目
- **APIキーの再取得と設定**（最優先）
- Cursor再起動後のMCP接続確認
- ワークフローの動作確認

### 💡 推奨アクション
1. N8NのWeb UIから新しいAPIキーを取得
2. MCP設定ファイルを更新
3. Cursorを再起動
4. MCPツールの動作確認

---

**確認完了日時**: 2026年1月8日
