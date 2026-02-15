# n8n MCPサーバー設定完了確認

## ✅ 設定状況

### 1. MCP設定ファイル (`~/.cursor/mcp.json`)

**設定内容:**
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

**確認結果:** ✅ 正しく設定されています

### 2. MCPサーバーモジュール

**確認結果:** ✅ 正常にインポートできます

### 3. 利用可能なMCPツール

以下のツールがCursorから使用可能になります：

1. **n8n_list_workflows** - ワークフロー一覧を取得
2. **n8n_import_workflow** - ワークフローをインポート
3. **n8n_activate_workflow** - ワークフローを有効化
4. **n8n_deactivate_workflow** - ワークフローを無効化
5. **n8n_execute_workflow** - ワークフローを実行
6. **n8n_get_execution** - 実行履歴を取得
7. **n8n_list_executions** - 実行履歴一覧を取得
8. **n8n_get_webhook_url** - Webhook URLを取得

## 🚀 次のステップ

### ステップ1: Cursorを再起動

MCP設定を変更したため、**Cursorを完全に再起動**してください。

### ステップ2: MCPツールの動作確認

Cursorを再起動後、以下のようにMCPツールを使用できます：

**例1: ワークフロー一覧を取得**
```
n8nのワークフロー一覧を取得してください
```

**例2: Webhook URLを取得**
```
ワークフローID 2ViGYzDtLBF6H4zn のWebhook URLを取得してください
```

**例3: ワークフローを実行**
```
ワークフローID 2ViGYzDtLBF6H4zn を実行してください
```

## 📋 完了チェックリスト

- ✅ n8n MCPサーバーの実装
- ✅ MCP設定ファイルへの追加
- ✅ APIキーの設定
- ✅ Base URLの設定（`http://127.0.0.1:5679`）
- ✅ MCPサーバーモジュールの動作確認
- ⏳ **Cursorの再起動** ← これが必要です
- ⏳ MCPツールの動作確認

## 💡 使用方法

Cursorを再起動後、以下のように自然言語でn8nを操作できます：

```
n8nのワークフロー一覧を見せて
```

```
n8nに新しいワークフローをインポートして
```

```
ワークフローを有効化して
```

MCPサーバーが自動的に適切なツールを呼び出します。

## 🔧 トラブルシューティング

### MCPツールが表示されない場合

1. **Cursorを完全に再起動**
   - すべてのCursorウィンドウを閉じる
   - タスクマネージャーでCursorプロセスを確認
   - 再起動

2. **MCP設定ファイルの確認**
   ```powershell
   Get-Content "$env:USERPROFILE\.cursor\mcp.json" | ConvertFrom-Json | Select-Object -ExpandProperty mcpServers | Select-Object -ExpandProperty n8n
   ```

3. **ログの確認**
   - Cursorの開発者ツール（F12）でエラーを確認
   - MCPサーバーのログを確認

### APIキーが無効な場合

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\n8n_mcp_server\set_api_key_manual.ps1 -ApiKey "新しいAPIキー" -BaseUrl "http://127.0.0.1:5679"
```

その後、Cursorを再起動してください。















