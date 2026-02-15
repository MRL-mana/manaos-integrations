# MCP サーバー一覧ガイド

最終更新: 2026-02-06

## 概要

ManaOS で利用可能な MCP サーバーの一覧と、用途・起動条件・Cursor 設定方法。

---

## 0. 役割の使い分け（重要）

| 用途 | 推奨 MCP | 理由 |
|------|----------|------|
| **全機能を1つで使う** | **manaos-media / manaos-productivity / manaos-ai / manaos-devices / manaos-moltbot**（分割版） | ドメイン別に軽量起動。ツール数が多くてもトークン効率が良い |
| **ask_orchestrator のみ** | **unified-api** | オーケストレーター問い合わせ専用の軽量ラッパー |
| **LTX-2 画像生成** | **ltx2** | LTX-2 専用 |
| **Phase1 実験** | **phase1** | 自己観察実験専用 |
| **専門調査・ギャラリー等** | step-deep-research, gallery-api 等 | 必要に応じて有効化 |

**unified-api** と **manaos-*** は役割が異なる。unified-api は ask_orchestrator 等の統合API ラッパー。manaos-* は ComfyUI / Rows / Obsidian / MoltBot 等の全ツール群。

---

## 1. 主要 MCP サーバー（manaos-unified 系）

### モジュール共通

| 項目 | 内容 |
|------|------|
| **モジュール** | `manaos_unified_mcp_server` |
| **ツール数** | 40+（SVI, ComfyUI, CivitAI, Rows, Obsidian, memory, llm_chat, 秘書, 学習, Phase1, デバイス, MoltBot 等） |
| **起動条件** | 統合API (9500)、各種インテグレーション |
| **Cursor 設定** | `add_all_mcp_servers_to_cursor.ps1`（プロジェクトルートで実行、パスは自動取得） |

### 分割版（軽量起動・推奨）

`MCP_DOMAIN` でツールを絞り込んだ起動。1プロセスあたりのトークン消費を抑えられる。

| サーバー | MCP_DOMAIN | 主なツール |
|----------|------------|-----------|
| **manaos-media** | media | SVI, ComfyUI, CivitAI, image_stock |
| **manaos-productivity** | productivity | Rows, Obsidian, Google Drive, notification |
| **manaos-ai** | ai | memory, llm_chat, secretary, learning, phase1, personality, autonomy, 検索 |
| **manaos-devices** | devices | device_discover, device_get_status, device_get_health, device_get_resources, device_get_alerts |
| **manaos-moltbot** | moltbot | moltbot_submit_plan, moltbot_get_result, moltbot_health |

---

## 2. 専用 MCP サーバー

| サーバー | モジュール | 役割 | 主なツール | 起動条件 |
|----------|-----------|------|-----------|----------|
| **unified-api** | unified_api_mcp_server | 統合API ラッパー | ask_orchestrator, 統合API 問い合わせ | 統合API (9500) |
| **ltx2** | ltx2_mcp_server | LTX-2 画像生成 | ltx2_generate, ltx2_get_queue, ltx2_get_history | 統合API (9500)、LTX-2 有効 |
| **phase1** | phase1_mcp_server | Phase1 自己観察実験 | phase1_run_off, phase1_run_on, phase1_aggregate, phase1_compare | 統合API (9500)、PHASE1_REFLECTION 設定 |
| **step-deep-research** | step_deep_research_mcp_server | 専門調査員AI | リサーチジョブ作成・実行 | 5121 |
| **gallery-api** | gallery_api_mcp_server | ギャラリー | 画像管理API | 5559 |
| **system-status** | system_status_mcp_server | システムステータス | 全サービス状態 | 5112 |
| **portal-integration** | portal_integration_mcp_server | ポータル・オーケストレーター | デバイス・オーケストレーター問い合わせ | 5108 |
| **slack-integration** | slack_integration_mcp_server | Slack | Slack 連携 | 5114 |

---

## 3. 一括登録

```powershell
.\add_all_mcp_servers_to_cursor.ps1
```

登録後、Cursor を再起動。

---

## 4. 環境変数

| 変数 | 用途 | デフォルト |
|------|------|-----------|
| `MANAOS_INTEGRATION_API_URL` | 統合API URL | http://127.0.0.1:9502 |
| `PORTAL_INTEGRATION_URL` | Portal API（デバイス詳細） | http://127.0.0.1:5108 |
| `MCP_DOMAIN` | ツール分割（media/productivity/ai/devices/moltbot） | 空=全ツール |
| `COMFYUI_URL` | ComfyUI | http://127.0.0.1:8188 |
| `OBSIDIAN_VAULT_PATH` | Obsidian Vault | - |

---

## 5. ヘルスチェック・テスト

```powershell
# ヘルスチェック（全 MCP サーバーが list_tools 可能か確認）
python scripts/check_mcp_health.py
# または
.\scripts\check_mcp_health.ps1

# 統合テスト
python scripts/test_mcp_servers.py
```

## 6. トラブルシューティング

- **ツールが表示されない**: Cursor 再起動、各APIサービス起動確認
- **device_get_health エラー**: Portal API (5108) 起動、device_health_monitor 利用可能か確認
- **Phase1 エラー**: unified_api_server が PHASE1_REFLECTION=on/off で起動していること

