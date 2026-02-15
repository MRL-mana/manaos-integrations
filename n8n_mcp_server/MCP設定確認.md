# n8n MCPサーバー設定確認

## 設定状況

### 1. MCP設定ファイル (`~/.cursor/mcp.json`)

n8n MCPサーバーが正しく設定されているか確認：

```powershell
Get-Content "$env:USERPROFILE\.cursor\mcp.json" | ConvertFrom-Json | Select-Object -ExpandProperty mcpServers | Select-Object -ExpandProperty n8n
```

期待される設定：

```json
{
  "command": "python",
  "args": ["-m", "n8n_mcp_server.server"],
  "env": {
    "N8N_BASE_URL": "http://127.0.0.1:5679",
    "N8N_API_KEY": "your_n8n_api_key_here"
  },
  "cwd": "C:\\Users\\mana4\\OneDrive\\Desktop\\manaos_integrations"
}
```

### 2. 利用可能なMCPツール

n8n MCPサーバーが提供するツール：

1. **n8n_list_workflows** - ワークフロー一覧を取得
2. **n8n_import_workflow** - ワークフローをインポート
3. **n8n_activate_workflow** - ワークフローを有効化
4. **n8n_deactivate_workflow** - ワークフローを無効化
5. **n8n_execute_workflow** - ワークフローを実行
6. **n8n_get_execution** - 実行履歴を取得
7. **n8n_list_executions** - 実行履歴一覧を取得
8. **n8n_get_webhook_url** - Webhook URLを取得

### 3. Cursorでの使用方法

Cursorを再起動後、以下のようにMCPツールを使用できます：

```
n8nのワークフロー一覧を取得してください
```

```
n8nにワークフローをインポートしてください
```

## 設定確認手順

### ステップ1: MCP設定ファイルの確認

```powershell
# MCP設定ファイルの内容を確認
Get-Content "$env:USERPROFILE\.cursor\mcp.json" | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### ステップ2: 環境変数の確認

```powershell
# n8n MCPサーバーの環境変数を確認
$config = Get-Content "$env:USERPROFILE\.cursor\mcp.json" | ConvertFrom-Json
$config.mcpServers.n8n.env
```

期待される出力：
```
N8N_BASE_URL : http://127.0.0.1:5679
N8N_API_KEY  : your_n8n_api_key_here
```

### ステップ3: MCPサーバーの動作確認

```powershell
# MCPサーバーのモジュールが正しくインポートできるか確認
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python -c "from n8n_mcp_server.server import server; print('MCPサーバーモジュール: OK')"
```

### ステップ4: Cursorを再起動

MCP設定を変更した場合、Cursorを完全に再起動してください。

### ステップ5: MCPツールの使用確認

Cursorを再起動後、以下のコマンドでMCPツールが使えるか確認：

```
n8nのワークフロー一覧を取得してください
```

## トラブルシューティング

### MCPサーバーが認識されない

1. **Cursorを完全に再起動**
   - すべてのCursorウィンドウを閉じる
   - タスクマネージャーでCursorプロセスを確認
   - 再起動

2. **MCP設定ファイルの構文確認**
   ```powershell
   # JSONの構文エラーを確認
   Get-Content "$env:USERPROFILE\.cursor\mcp.json" | ConvertFrom-Json
   ```

3. **パスの確認**
   - `cwd` が正しいか確認
   - Pythonのパスが正しいか確認

### APIキーが無効

1. n8nのWeb UIで新しいAPIキーを作成
2. `set_api_key_manual.ps1` で再設定
3. Cursorを再起動

### Base URLが間違っている

```powershell
# Base URLを更新
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\n8n_mcp_server\set_api_key_manual.ps1 -ApiKey "既存のAPIキー" -BaseUrl "http://127.0.0.1:5679"
```

## 完了チェックリスト

- ✅ n8n MCPサーバーの実装（`n8n_mcp_server/server.py`）
- ✅ MCP設定ファイルへの追加（`add_to_cursor_mcp.ps1`）
- ✅ APIキーの設定
- ✅ Base URLの設定（`http://127.0.0.1:5679`）
- ⏳ Cursorの再起動
- ⏳ MCPツールの動作確認

## 次のステップ

1. **Cursorを再起動**
2. **MCPツールの動作確認**
   - `n8n_list_workflows` でワークフロー一覧を取得
   - `n8n_get_webhook_url` でWebhook URLを取得
3. **ワークフローの管理**
   - Cursorから直接ワークフローをインポート・有効化・実行















