# ManaOS MCPサーバー一覧

## 📋 実装済みMCPサーバー

### 1. n8n MCPサーバー ✅

**パス**: `manaos_integrations/n8n_mcp_server/`

**機能**: n8nワークフローをCursorから直接操作

**ツール数**: 8個
- n8n_list_workflows
- n8n_import_workflow
- n8n_activate_workflow
- n8n_deactivate_workflow
- n8n_execute_workflow
- n8n_get_execution
- n8n_list_executions
- n8n_get_webhook_url

**状態**: ✅ 実装完了・動作確認済み

---

### 2. SVI × Wan 2.2 MCPサーバー ✅

**パス**: `manaos_integrations/svi_mcp_server/`

**機能**: SVI動画生成をCursorから直接実行

**ツール数**: 6個
- svi_generate_video
- svi_extend_video
- svi_create_story_video
- svi_get_queue_status
- svi_get_history
- svi_check_connection

**状態**: ✅ 実装完了・Cursor設定追加済み

---

### 3. ManaOS統合MCPサーバー ✅

**パス**: `manaos_integrations/manaos_unified_mcp_server/`

**機能**: ManaOSのすべての機能を統合

**ツール数**: 30+個

#### カテゴリ別ツール

**動画生成（3個）**
- svi_generate_video
- svi_extend_video
- svi_get_queue_status

**画像生成（1個）**
- comfyui_generate_image

**Google Drive（2個）**
- google_drive_upload
- google_drive_list_files

**Rows（3個）**
- rows_query
- rows_send_data
- rows_list_spreadsheets

**Obsidian（2個）**
- obsidian_create_note
- obsidian_search_notes

**画像ストック（2個）**
- image_stock_add
- image_stock_search

**通知（1個）**
- notification_send

**記憶システム（2個）**
- memory_store
- memory_recall

**LLMルーティング（1個）**
- llm_chat

**秘書機能（3個）**
- secretary_morning_routine
- secretary_noon_routine
- secretary_evening_routine

**状態**: ✅ 実装完了・Cursor設定追加済み

---

## 🚀 セットアップ方法

### 方法1: 自動設定スクリプト（推奨）

```powershell
# n8n MCPサーバー
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations\n8n_mcp_server
.\add_to_cursor_mcp.ps1

# SVI MCPサーバー
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations\svi_mcp_server
.\add_to_cursor_mcp.ps1

# ManaOS統合MCPサーバー（すべての機能を含む）
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations\manaos_unified_mcp_server
.\add_to_cursor_mcp.ps1
```

### 方法2: 手動設定

Cursorの設定ファイル: `%APPDATA%\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`

```json
{
  "mcpServers": {
    "n8n": {
      "command": "python",
      "args": ["-m", "n8n_mcp_server.server"],
      "env": {
        "N8N_BASE_URL": "http://100.93.120.33:5678",
        "N8N_API_KEY": "your-api-key"
      },
      "cwd": "C:\\Users\\mana4\\OneDrive\\Desktop\\manaos_integrations"
    },
    "svi-video": {
      "command": "python",
      "args": ["-m", "svi_mcp_server.server"],
      "env": {
        "COMFYUI_URL": "http://localhost:8188"
      },
      "cwd": "C:\\Users\\mana4\\OneDrive\\Desktop\\manaos_integrations"
    },
    "manaos-unified": {
      "command": "python",
      "args": ["-m", "manaos_unified_mcp_server.server"],
      "env": {
        "COMFYUI_URL": "http://localhost:8188",
        "MANAOS_INTEGRATION_API_URL": "http://localhost:9500",
        "OBSIDIAN_VAULT_PATH": "C:\\Users\\mana4\\Documents\\Obsidian Vault"
      },
      "cwd": "C:\\Users\\mana4\\OneDrive\\Desktop\\manaos_integrations"
    }
  }
}
```

---

## 💡 使い分け

### n8n MCPサーバー
- n8nワークフローの管理に特化
- ワークフローのインポート・実行・管理

### SVI MCPサーバー
- SVI動画生成に特化
- 動画生成・延長・ストーリー生成

### ManaOS統合MCPサーバー（推奨）
- **すべての機能を含む**
- 1つのMCPサーバーで全機能にアクセス可能
- 設定が簡単

---

## 🎯 推奨設定

**ManaOS統合MCPサーバーだけを設定することを推奨**

理由:
- すべての機能を含む
- 設定が1つで済む
- 機能の追加・更新が容易

---

## 📚 関連ドキュメント

- [n8n MCPサーバー](n8n_mcp_server/README.md)
- [SVI MCPサーバー](svi_mcp_server/README.md)
- [ManaOS統合MCPサーバー](manaos_unified_mcp_server/README.md)

---

*最終更新: 2025-01-28*











