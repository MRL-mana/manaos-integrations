# Phase1 自己観察実験 専用 MCP サーバー

Phase1 実験ツールを MCP として提供。

## ツール

- `phase1_run_off_3rounds` - OFF 3往復テスト
- `phase1_run_on_rounds` - ON N往復テスト（デフォルト15）
- `phase1_save_run` - ログを phase1_runs/ に保存
- `phase1_aggregate` - 集計（継続率・テーマ再訪・満足度）
- `phase1_compare_on_off` - ON/OFF 比較

## Cursor 設定

```json
{
  "phase1": {
    "command": "python",
    "args": ["-m", "phase1_mcp_server.server"],
    "cwd": "C:\\Users\\mana4\\Desktop\\manaos_integrations"
  }
}
```

## 前提

- Phase1 用に unified_api_server が PHASE1_REFLECTION=on/off で起動していること
