# LTX-2 専用 MCP サーバー

統合API (9500) の `/api/ltx2/*` を MCP ツールとして提供。

## ツール

- `ltx2_generate` - 動画生成
- `ltx2_get_queue` - キュー状態
- `ltx2_get_history` - 実行履歴
- `ltx2_get_status` - 指定 prompt_id の状態

## Cursor 設定

```json
{
  "ltx2": {
    "command": "python",
    "args": ["-m", "ltx2_mcp_server.server"],
    "env": { "MANAOS_INTEGRATION_API_URL": "http://localhost:9500" },
    "cwd": "C:\\Users\\mana4\\Desktop\\manaos_integrations"
  }
}
```

## 前提

- 統合API (9500) が起動していること
- LTX-2 統合が有効であること
