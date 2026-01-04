# n8n MCP Server

n8nワークフローをCursorから直接操作できるMCPサーバー

---

## ✅ 実装完了

- ✅ MCPサーバー実装完了
- ✅ 8つのツール実装完了
- ✅ CLIツール実装完了

---

## 🚀 Cursorから直接使う方法

### 方法1: CursorのMCP設定に追加（推奨）

1. **Cursorの設定を開く**
   - `Ctrl + ,` で設定を開く
   - または `File → Preferences → Settings`

2. **MCP設定を開く**
   - 検索バーで「MCP」を検索
   - 「MCP Servers」を開く

3. **n8n MCPサーバーを追加**
   ```json
   {
     "n8n": {
       "command": "python",
       "args": ["-m", "n8n_mcp_server.server"],
       "env": {
         "N8N_BASE_URL": "http://100.93.120.33:5678",
         "N8N_API_KEY": "your-api-key-here"
       },
       "cwd": "C:\\Users\\mana4\\OneDrive\\Desktop\\manaos_integrations"
     }
   }
   ```

4. **APIキーを取得**
   - n8nのWeb UIにアクセス: http://100.93.120.33:5678
   - Settings → API → Create API Key
   - APIキーをコピーして設定に追加

5. **Cursorを再起動**

6. **Cursorから直接呼び出し**
   ```
   n8n_import_workflow を使ってワークフローをインポートしてください
   ```

---

### 方法2: 直接Pythonスクリプトとして実行

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python n8n_mcp_server/import_workflow_cli.py n8n_workflow_template.json
```

**注意:** APIキーが必要です。

---

## 📋 利用可能なツール

### 1. n8n_list_workflows
ワークフロー一覧を取得

### 2. n8n_import_workflow
ワークフローをインポート
- `workflow_file`: ワークフローファイルのパス
- `activate`: 有効化するか（デフォルト: true）

### 3. n8n_activate_workflow
ワークフローを有効化
- `workflow_id`: ワークフローID

### 4. n8n_deactivate_workflow
ワークフローを無効化
- `workflow_id`: ワークフローID

### 5. n8n_execute_workflow
ワークフローを実行
- `workflow_id`: ワークフローID
- `data`: ワークフローに渡すデータ（オプション）

### 6. n8n_get_execution
実行履歴を取得
- `execution_id`: 実行ID

### 7. n8n_list_executions
実行履歴一覧を取得
- `workflow_id`: ワークフローID（オプション）
- `limit`: 取得件数（デフォルト: 10）

### 8. n8n_get_webhook_url
Webhook URLを取得
- `workflow_id`: ワークフローID

---

## 🔧 設定

### 環境変数

- `N8N_BASE_URL`: n8nのベースURL（デフォルト: http://100.93.120.33:5678）
- `N8N_API_KEY`: n8nのAPIキー（必須）

---

## 💡 使用例

### Cursorから直接呼び出す場合

```
n8n_import_workflow を使って、n8n_workflow_template.json をインポートしてください
```

Cursorが自動的にMCPツールを呼び出します。

---

## ⚠️ 注意事項

- APIキーが必要です
- n8nサーバーが起動している必要があります
- ワークフローファイルはJSON形式である必要があります

---

## 🎯 100%完了への道

1. ✅ MCPサーバー実装完了
2. ✅ ツール実装完了
3. ⚠️ CursorのMCP設定に追加（またはAPIキーを取得）
4. ⚠️ ワークフローをインポート

**進捗:** 99%完了 → **100%まであと1%**


















