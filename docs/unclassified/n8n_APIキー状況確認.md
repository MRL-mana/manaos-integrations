# n8n APIキー 状況確認

## 現在の状況

### MCP設定ファイル（`~/.cursor/mcp.json`）
- ✅ APIキーが設定されています
- ⚠️ ただし、このAPIキーは**このはサーバーのn8n**用の可能性があります

### ローカルのn8n（http://localhost:5679）
- ❌ 現在のAPIキーでは認証エラー（401）が発生
- ⚠️ ローカルのn8nから**新しいAPIキー**を取得する必要があります

## 解決方法

### 方法1: ローカルのn8nから新しいAPIキーを取得（推奨）

1. **ブラウザでn8nを開く**
   - http://localhost:5679 にアクセス

2. **APIキーを作成**
   - 右上のユーザーアイコン → Settings → API
   - 「Create API Key」をクリック
   - APIキー名を入力（例: `MCP Server Local`）
   - 「Create」をクリック
   - **生成されたAPIキーをコピー**

3. **MCP設定ファイルを更新**
   ```powershell
   cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
   python n8n_mcp_server/set_api_key_manual.ps1
   ```
   または、手動で `~/.cursor/mcp.json` を編集:
   ```json
   {
     "mcpServers": {
       "n8n": {
         "env": {
           "N8N_BASE_URL": "http://localhost:5679",
           "N8N_API_KEY": "新しいAPIキーをここに貼り付け"
         }
       }
     }
   }
   ```

4. **Cursorを再起動**（MCP設定を反映するため）

5. **確認**
   ```powershell
   cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
   python n8n_mcp_server/check_workflow_status.py 2ViGYzDtLBF6H4zn
   ```

### 方法2: 環境変数に設定（一時的）

```powershell
$env:N8N_API_KEY = "新しいAPIキー"
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python n8n_mcp_server/check_workflow_status.py 2ViGYzDtLBF6H4zn
```

## 注意事項

- **このはサーバーのn8nのAPIキー**と**ローカルのn8nのAPIキー**は別物です
- ローカルのn8nを使用する場合は、ローカルで作成したAPIキーが必要です
- MCP設定ファイルを更新したら、Cursorを再起動してください











