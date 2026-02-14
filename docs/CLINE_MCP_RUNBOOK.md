# Cline（VS Code）で ManaOS MCP を使う Runbook

対象: VS Code + Cline 拡張（`saoudrizwan.claude-dev`）から、ManaOS の MCP サーバ（stdio）を安定運用する。

## 0) 前提（重要）

- MCP が stdio の場合、**stdout はプロトコル専用**。ログが stdout に混ざると接続が壊れる。
- ManaOS 側は `MANAOS_LOG_TO_STDERR=1` でログを stderr に逃がす（必須）。

## 1) まず動く最短チェック（CLI）

1. VS Code タスクでサービス起動
   - `Tasks: Run Task` → `ManaOS: すべてのサービスを起動`

2. ヘルスチェック（HTTP）
   - `Tasks: Run Task` → `ManaOS: サービスヘルスチェック`

3. MCPプロトコルのスモーク（stdio）
   - `pwsh -NoProfile -ExecutionPolicy Bypass -File devtools\mcp_smoke_all.ps1`

`devtools\mcp_smoke_all.ps1` は `initialize → list_tools → call_tool` まで実行するため、Cline以前に「MCPサーバが本当に動く」ことを客観的に確認できる。

## 2) Cline 側の確認ポイント（UI）

1. VS Code で Cline を開く
2. MCP サーバ一覧で、対象サーバが Connected/Reconnected になっていることを確認
3. 代表ツールを1回叩く（例）
   - `manaos-video-pipeline`: `system_check`
   - `manaos-pico-hid`: `hid_status`
   - `manaos-unified-api`: `unified_api_health`

## 3) つながらない時の切り分け（最短）

### A. まずプロセスが落ちていないか
- `devtools\mcp_smoke_all.ps1` が通るか（通らないなら Cline 以前の問題）

### B. stdout 汚染を疑う
- 症状: Cline が `Transport error` / `Failed to connect` / すぐ切断
- 対策: MCP 起動 env に `MANAOS_LOG_TO_STDERR=1`

### C. MCP サーバが「起動直後に終了」していないか
- 症状: 接続以前にプロセスが即終了（exit code 0 のこともある）
- 対策: `-m` 起動で `main()` が確実に動く `__main__` / entrypoint を確認

## 4) Cline の設定ファイル場所（参考）

Cline の MCP 設定は VS Code の globalStorage 配下にある。
- 例: `...\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`

※パスは環境で変わるため、必要なら `devtools\extract_cline_mcp_settings_path.py` を利用する。
