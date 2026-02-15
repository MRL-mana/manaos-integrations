# MCPサーバーのトラブルシューティングガイド

## 問題1: llm-routingが表示されない

### 確認事項

1. **設定ファイルの確認**
   - パス: `%APPDATA%\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`
   - `llm-routing`が設定されているか確認

2. **依存関係の確認**
   ```powershell
   pip install mcp requests
   ```

3. **MCPサーバーの起動テスト**
   ```powershell
   cd C:\Users\mana4\Desktop\manaos_integrations
   python -m llm_routing_mcp_server.server
   ```
   - エラーが表示される場合は、エラー内容を確認

4. **Cursorの再起動**
   - 設定を変更した後は、Cursorを再起動する必要があります

### 解決方法

1. **設定を再適用**
   ```powershell
   .\fix_mcp_servers.ps1
   ```

2. **Cursorを再起動**

3. **「Tools & MCP」→「Installed MCP Servers」で確認**

---

## 問題2: n8nがエラーを表示する

### 確認事項

1. **n8nサーバーの起動確認**
   ```powershell
   # ローカルサーバー
   Invoke-WebRequest -Uri "http://127.0.0.1:5678" -TimeoutSec 2
   
   # リモートサーバー
   Invoke-WebRequest -Uri "http://100.93.120.33:5678" -TimeoutSec 2
   ```

2. **APIキーの設定**
   - n8nのWeb UIにアクセス: http://100.93.120.33:5678
   - Settings → API → Create API Key
   - 設定ファイルの `N8N_API_KEY` に設定

3. **設定ファイルの確認**
   - `n8n`が設定されているか確認
   - `N8N_BASE_URL`が正しいか確認
   - `N8N_API_KEY`が設定されているか確認

### 解決方法

1. **設定を再適用**
   ```powershell
   .\fix_mcp_servers.ps1
   ```

2. **APIキーを設定**
   - 設定ファイルを開く
   - `N8N_API_KEY`にAPIキーを設定

3. **Cursorを再起動**

4. **エラーログを確認**
   - 「Show Output」をクリックしてエラー内容を確認

---

## 一般的なトラブルシューティング

### MCPサーバーが表示されない場合

1. **設定ファイルのパスを確認**
   ```powershell
   $mcpConfigPath = "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"
   Get-Content $mcpConfigPath
   ```

2. **JSONの構文エラーを確認**
   - JSONが正しい形式か確認
   - カンマや引用符のエラーがないか確認

3. **作業ディレクトリの確認**
   - `cwd`で指定されたディレクトリが存在するか確認
   - パスが正しいか確認（`OneDrive` vs `Desktop`）

### MCPサーバーがエラーを表示する場合

1. **「Show Output」をクリック**
   - エラーメッセージを確認

2. **依存関係の確認**
   ```powershell
   pip install mcp requests
   ```

3. **Pythonパスの確認**
   - `python`コマンドが正しく動作するか確認
   - 仮想環境が有効になっているか確認

4. **環境変数の確認**
   - `env`で指定された環境変数が正しいか確認
   - API URLが正しいか確認

---

## 設定ファイルの例

```json
{
  "mcpServers": {
    "llm-routing": {
      "command": "python",
      "args": ["-m", "llm_routing_mcp_server.server"],
      "env": {
            "MANAOS_INTEGRATION_API_URL": "http://127.0.0.1:9510",
            "LLM_ROUTING_API_URL": "http://127.0.0.1:5111"
      },
      "cwd": "C:\\Users\\mana4\\Desktop\\manaos_integrations"
    },
    "n8n": {
      "command": "python",
      "args": ["-m", "n8n_mcp_server.server"],
      "env": {
        "N8N_BASE_URL": "http://100.93.120.33:5678",
        "N8N_API_KEY": "your-api-key-here"
      },
      "cwd": "C:\\Users\\mana4\\Desktop\\manaos_integrations"
    }
  }
}
```

---

## サポート

問題が解決しない場合は、以下を確認してください：

1. Cursorのバージョンが最新か
2. Pythonのバージョンが3.8以上か
3. すべての依存関係がインストールされているか
4. 設定ファイルのパスが正しいか

















