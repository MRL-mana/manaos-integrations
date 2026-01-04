# Cursorから直接n8nワークフローをインポート

**✅ CursorのMCP設定にn8n MCPサーバーを追加しました！**

---

## 🚀 使い方

### ステップ1: APIキーを取得（初回のみ）

1. n8nのWeb UIにアクセス: http://100.93.120.33:5678
2. Settings → API → Create API Key
3. APIキーをコピー

### ステップ2: 設定ファイルにAPIキーを追加

```powershell
# 設定ファイルを開く
notepad "$env:USERPROFILE\.cursor\mcp.json"

# N8N_API_KEY の値をAPIキーに設定
```

### ステップ3: Cursorを再起動

### ステップ4: Cursorから直接呼び出す

Cursorのチャットで以下を入力：

```
n8n_import_workflow を使って、n8n_workflow_template.json をインポートしてください
```

**Cursorが自動的にMCPツールを呼び出して、ワークフローをインポートします！**

---

## 🎯 これで100%完了！

Cursorから直接ワークフローをインポートできるようになりました。

---

## 💡 利用可能なMCPツール

- `n8n_list_workflows` - ワークフロー一覧取得
- `n8n_import_workflow` - ワークフローインポート
- `n8n_activate_workflow` - ワークフロー有効化
- `n8n_deactivate_workflow` - ワークフロー無効化
- `n8n_execute_workflow` - ワークフロー実行
- `n8n_get_execution` - 実行履歴取得
- `n8n_list_executions` - 実行履歴一覧取得
- `n8n_get_webhook_url` - Webhook URL取得

---

**進捗:** 99%完了 → **100%まであと1%（APIキー設定のみ）**


















