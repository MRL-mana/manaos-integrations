# n8n MCPサーバー動作確認手順

## Cursor再起動後の確認

### 1. MCPツールが利用可能か確認

Cursorのチャットで以下のように入力して、MCPツールが動作するか確認してください：

```
n8nのワークフロー一覧を取得してください
```

### 2. 期待される動作

MCPサーバーが正常に動作している場合、以下のツールが使用可能です：

- `n8n_list_workflows` - ワークフロー一覧を取得
- `n8n_import_workflow` - ワークフローをインポート
- `n8n_activate_workflow` - ワークフローを有効化
- `n8n_deactivate_workflow` - ワークフローを無効化
- `n8n_execute_workflow` - ワークフローを実行
- `n8n_get_execution` - 実行履歴を取得
- `n8n_list_executions` - 実行履歴一覧を取得
- `n8n_get_webhook_url` - Webhook URLを取得

### 3. テストコマンド

以下のコマンドでn8nの接続を確認できます：

```powershell
# n8nの接続確認
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
$env:N8N_API_KEY = "your_n8n_api_key_here"
python -c "import os, requests; r = requests.get('http://localhost:5679/api/v1/workflows', headers={'X-N8N-API-KEY': os.environ['N8N_API_KEY']}); print('OK' if r.status_code == 200 else f'Error: {r.status_code}')"
```

### 4. トラブルシューティング

#### MCPツールが表示されない場合

1. **Cursorを完全に再起動**
   - すべてのCursorウィンドウを閉じる
   - タスクマネージャーでCursorプロセスを確認
   - 再起動

2. **MCP設定ファイルの確認**
   ```powershell
   Get-Content "$env:USERPROFILE\.cursor\mcp.json" | ConvertFrom-Json | Select-Object -ExpandProperty mcpServers | Select-Object -ExpandProperty n8n
   ```

3. **n8nが起動しているか確認**
   ```powershell
   # n8nがポート5679で起動しているか確認
   netstat -ano | findstr :5679
   ```

#### APIキーが無効な場合

1. n8nのWeb UIにアクセス: http://localhost:5679
2. Settings → API → Create API Key
3. 新しいAPIキーを取得
4. `set_api_key_manual.ps1` で再設定
5. Cursorを再起動

### 5. 動作確認の例

Cursorのチャットで以下を試してください：

```
n8nのワークフロー一覧を取得してください
```

正常に動作している場合、ワークフロー一覧が表示されます。














