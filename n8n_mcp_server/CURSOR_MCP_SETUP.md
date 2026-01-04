# Cursor MCP設定 - n8n MCPサーバー

Cursorからn8n MCPサーバーを使えるようにする設定手順

---

## 設定ファイルの場所

CursorのMCP設定ファイルは通常、以下の場所にあります：

```
%APPDATA%\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json
```

または

```
%APPDATA%\Cursor\User\settings.json
```

---

## 設定内容

以下のJSONをCursorのMCP設定に追加してください：

```json
{
  "mcpServers": {
    "n8n": {
      "command": "python",
      "args": [
        "-m",
        "n8n_mcp_server.server"
      ],
      "env": {
        "N8N_BASE_URL": "http://100.93.120.33:5678",
        "N8N_API_KEY": "your-api-key-here"
      },
      "cwd": "C:\\Users\\mana4\\OneDrive\\Desktop\\manaos_integrations"
    }
  }
}
```

---

## APIキーの取得方法

1. n8nのWeb UIにアクセス
   ```
   http://100.93.120.33:5678
   ```

2. Settings → API → Create API Key

3. APIキーをコピー

4. 上記の設定の`N8N_API_KEY`に設定

---

## 使用方法

設定後、Cursorから以下のように呼び出せます：

```
n8n_import_workflow を使ってワークフローをインポートしてください
```

Cursorが自動的にMCPツールを呼び出します。

---

## 利用可能なツール

- `n8n_list_workflows` - ワークフロー一覧取得
- `n8n_import_workflow` - ワークフローインポート
- `n8n_activate_workflow` - ワークフロー有効化
- `n8n_deactivate_workflow` - ワークフロー無効化
- `n8n_execute_workflow` - ワークフロー実行
- `n8n_get_execution` - 実行履歴取得
- `n8n_list_executions` - 実行履歴一覧取得
- `n8n_get_webhook_url` - Webhook URL取得


















