# konoha_mcp_servers（アーカイブ）

**状態**: アーカイブ（メンテナンス対象外）

最終更新: 2026-02-06

---

## 概要

このディレクトリは、このはサーバー向け・過去の MCP 実験・X280 転送等の**レガシー・アーカイブ**です。

**現在の ManaOS MCP サーバーは本リポジトリ直下の以下を使用してください：**

| 用途 | モジュール・場所 |
|------|------------------|
| 統合 MCP（全ツール） | `manaos_unified_mcp_server/` |
| 分割版（media/productivity/ai/devices/moltbot） | 同上（MCP_DOMAIN で切り替え） |
| LTX-2 | `ltx2_mcp_server/` |
| Phase1 | `phase1_mcp_server/` |
| 統合 API ラッパー | `unified_api_mcp_server/` |
| その他専用 | `*_mcp_server/` |

→ 詳細: [docs/guides/MCP_SERVERS_GUIDE.md](../docs/guides/MCP_SERVERS_GUIDE.md)

---

## 本ディレクトリの内容

| サブディレクトリ・ファイル | 説明 |
|---------------------------|------|
| `archive_20251106/` | 2025-11-06 時点のアーカイブ MCP サーバー |
| `duplicates_backup/` | 重複バックアップ |
| `manaos_unified_system_mcp/` | このは向け Docker 構成（n8n 等）※必要時のみ参照 |
| `scripts_x280_transfer/` | X280 転送スクリプト群 |
| `*.js` | 過去の MCP 拡張スクリプト（参照用） |

---

## 新規開発時の注意

- **新規 MCP サーバーは `manaos_unified_mcp_server` にツール追加** または **専用 `*_mcp_server/` をルートに作成**すること
- 本ディレクトリへの追加・修正は行わないこと
- 削除は行わず、アーカイブとして保持
