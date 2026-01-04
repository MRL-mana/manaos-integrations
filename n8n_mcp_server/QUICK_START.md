# n8n MCP Server クイックスタート

**Cursorから直接n8nワークフローをインポートする方法**

---

## 🚀 最も簡単な方法

### ステップ1: Cursorから直接呼び出す

Cursorのチャットで以下を入力：

```
n8n_import_workflow を使って、n8n_workflow_template.json をインポートしてください
```

**注意:** まずCursorのMCP設定にn8n MCPサーバーを追加する必要があります。

---

## 📋 CursorのMCP設定に追加する手順

### 1. Cursorの設定を開く

- `Ctrl + ,` で設定を開く
- または `File → Preferences → Settings`

### 2. MCP設定を検索

- 検索バーで「MCP」を検索
- 「MCP Servers」を開く

### 3. n8n MCPサーバーを追加

以下のJSONを追加：

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

### 4. APIキーを取得

1. n8nのWeb UIにアクセス: http://100.93.120.33:5678
2. Settings → API → Create API Key
3. APIキーをコピー
4. 上記の設定の`N8N_API_KEY`に設定

### 5. Cursorを再起動

### 6. Cursorから直接呼び出し

```
n8n_import_workflow を使って、n8n_workflow_template.json をインポートしてください
```

---

## 🎯 これで100%完了！

Cursorから直接ワークフローをインポートできるようになります。

---

## 💡 代替方法

MCP設定が難しい場合は、ブラウザで手動インポート（2分）:

1. n8nのWeb UIにアクセス
2. 「Workflows」→「Import from File」
3. `n8n_workflow_template.json`を選択
4. 「Import」をクリック
5. ワークフローを有効化

---

**進捗:** 99%完了 → **100%まであと1%**


















