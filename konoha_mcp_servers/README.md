# このはサーバーMCPサーバー統合プロジェクト

**移行日**: 2026-01-06  
**統合完了日**: 2026-01-06

## 📋 概要

このはサーバー（旧母艦）から移行したMCPサーバーを統合・最適化し、母艦（現在のPC）で使用可能にしました。

## ✅ 移行完了

- **Pythonファイル**: 60個
- **JavaScriptファイル**: 160個
- **合計**: 220+ファイル

## 🎯 動作確認済みMCPサーバー

### 1. manaos-unified-konoha（推奨）

**パス**: `archive_20251106/manaos_mcp_server.py`

**機能**: ManaOSの全機能を統合（30+ツール）

**特徴**:
- 動画生成（SVI × Wan 2.2）
- 画像生成（ComfyUI）
- Google Drive統合
- Rows統合
- Obsidian統合
- 画像ストック
- 通知機能
- 記憶システム
- LLMルーティング
- 秘書機能

**Cursor設定**: ✅ 追加済み（`manaos-unified-konoha`）

### 2. n8n MCPサーバー

**パス**: `manaos_unified_system_mcp/n8n_mcp_server.py`

**機能**: n8nワークフロー操作（4ツール）

**特徴**:
- ワークフロー一覧取得
- ワークフロー実行
- Webhookトリガー
- 実行ステータス取得

### 3. ChatGPT MCPサーバー

**パス**: `archive_20251106/chatgpt_mcp_server.py`

**機能**: ChatGPT統合

## 🚀 使用方法

### Cursorから使用

1. **Cursorを再起動**（MCP設定を反映）

2. **チャットで使用**
   ```
   manaos-unified-konohaのツール一覧を取得してください
   ```

### 直接実行

```powershell
# 統合版manaos_mcp_server.pyを実行
cd C:\Users\mana4\Desktop\manaos_integrations
python konoha_mcp_servers\archive_20251106\manaos_mcp_server.py
```

## 📁 ディレクトリ構造

```
konoha_mcp_servers/
├── archive_20251106/          # アーカイブ（最新版）
│   ├── manaos_mcp_server.py   # ⭐ 統合版（推奨）
│   ├── chatgpt_mcp_server.py
│   └── ...
├── manaos_unified_system_mcp/  # このはサーバー版
│   └── n8n_mcp_server.py
├── manaos-knowledge_mcp/       # ManaOS Knowledge版
├── scripts_mcp_servers/        # スクリプト版
├── mcp_proxy/                  # プロキシ版
├── duplicates_backup/          # 重複ファイルのバックアップ
└── ...
```

## 🔧 セットアップ

### 依存関係のインストール

```powershell
pip install mcp requests httpx pydantic
```

### CursorのMCP設定

`%USERPROFILE%\.cursor\mcp.json` に以下が追加済み:

```json
{
  "mcpServers": {
    "manaos-unified-konoha": {
      "command": "python",
      "args": [
        "C:\\Users\\mana4\\Desktop\\manaos_integrations\\konoha_mcp_servers\\archive_20251106\\manaos_mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "C:\\Users\\mana4\\Desktop\\manaos_integrations",
        "MANAOS_INTEGRATION_API_URL": "http://localhost:9500",
        "COMFYUI_URL": "http://localhost:8188",
        "OBSIDIAN_VAULT_PATH": "C:\\Users\\mana4\\Documents\\Obsidian Vault"
      },
      "cwd": "C:\\Users\\mana4\\Desktop\\manaos_integrations"
    }
  }
}
```

## 📊 統計

- **移行ファイル数**: 220+個
- **正常動作**: 44個
- **MCPサーバー**: 3個確認済み
- **重複ファイル**: 6種類（整理済み）

## 🎯 推奨事項

1. **統合版の使用**: `manaos_mcp_server.py`は30+のツールを提供するため、個別のMCPサーバーよりも統合版の使用を推奨

2. **Cursor再起動**: MCP設定を変更した場合は、Cursorを完全に再起動してください

3. **環境変数の確認**: 各MCPサーバーに必要な環境変数が設定されているか確認してください

## 📝 関連ファイル

- `INTEGRATION_COMPLETE.md` - 統合完了レポート
- `MIGRATION_SUMMARY.md` - 移行サマリー
- `COMPARISON_REPORT.md` - 比較レポート
- `FINAL_MIGRATION_STATUS.md` - 最終移行ステータス

## 🔍 トラブルシューティング

### MCPサーバーが起動しない場合

1. **依存関係の確認**
   ```powershell
   pip list | findstr "mcp requests httpx"
   ```

2. **環境変数の確認**
   ```powershell
   echo $env:PYTHONPATH
   ```

3. **ログの確認**
   - Cursorの開発者ツール（Ctrl+Shift+I）でMCPログを確認

### ツールが表示されない場合

1. **Cursorを再起動**
2. **MCP設定ファイルの確認**
3. **Pythonパスの確認**

---

**統合プロジェクト完了！** 🎉










