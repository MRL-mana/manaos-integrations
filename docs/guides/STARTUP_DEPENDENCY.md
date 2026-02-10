# 起動依存関係

最終更新: 2026-02-06

---

## 最小起動（MCP・秘書ファイル整理）

```
start_unified_api_and_moltbot.bat
    ├── 統合API (9500)  ← MCP の土台
    └── MoltBot Gateway (8088)  ← 秘書ファイル整理
```

**確認**: `scripts\check_manaos_stack.bat` または `scripts\check_manaos_stack.ps1`

---

## 拡張起動（サービス別）

```
統合API (9500)  ← 必須。他サービスはオプション
    │
    ├── Portal Integration (5108)  ← device_get_health 等で使用
    ├── System Status (5112)       ← system-status MCP
    ├── SSOT API (5120)           ← ssot-api MCP
    ├── Step Deep Research (5121) ← step-deep-research MCP
    ├── Gallery API (5559)        ← gallery-api MCP
    └── Service Monitor (5111)    ← service-monitor MCP
```

**一括起動**: `docker-compose -f docker-compose.manaos-services.yml up -d`

**拡張疎通確認**: `.\scripts\check_manaos_stack.ps1 -Extended`

---

## MCP の起動順序

1. **統合API (9500)** を起動
2. 必要に応じて Portal (5108)、MoltBot Gateway (8088) 等を起動
3. Cursor を起動（MCP は統合API への接続を試みる）

MCP サーバー自体は Cursor が起動時に子プロセスとして起動。**統合API が先に立っていれば** MCP は利用可能。

---

## 起動コマンド一覧

| 目的 | コマンド |
|------|----------|
| 統合API + MoltBot | `start_unified_api_and_moltbot.bat` |
| 統合API のみ | `python unified_api_server.py` |
| 全 Docker サービス | `docker-compose -f docker-compose.manaos-services.yml up -d` |
| デバイスまとめて | `quick_start_devices.bat` |
| Pixel 7 音声 | `scripts\voice\start_pixel7_realtime_voice.bat` |

---

## 参照

- [QUICK_REFERENCE](../QUICK_REFERENCE.md)
- [MCP_SERVERS_GUIDE](MCP_SERVERS_GUIDE.md)
