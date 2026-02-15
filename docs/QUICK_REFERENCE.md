# クイックリファレンス（よく使う起動・確認）

## 起動（リポジトリルートで実行）

| 目的 | コマンド |
|------|----------|
| **統合API ＋ MoltBot**（MCP・秘書ファイル整理） | `start_unified_api_and_moltbot.bat` |
| 統合API のみ | `python unified_api_server.py` |
| MoltBot Gateway のみ（8088） | `moltbot_gateway\deploy\start_gateway_mothership.bat` |
| **Pixel 7 リアルタイム音声**（8765＋8766） | `scripts\voice\start_pixel7_realtime_voice.bat` |
| 本番用統合API（Waitress） | `start_unified_api_server_prod.bat` |
| デバイス（Pixel 7 ブリッジ等）まとめて | `quick_start_devices.bat` または `quick_start_devices.ps1`（詳細は [DEVICES_ONLINE_SETUP.md](guides/DEVICES_ONLINE_SETUP.md)） |

## 確認

| 目的 | コマンド |
|------|----------|
| 9502・8088 の疎通 | `scripts\check_manaos_stack.bat` または `scripts\check_manaos_stack.ps1` |
| 全サービス疎通 | `.\scripts\check_manaos_stack.ps1 -Extended` |
| デバイス状態（MCP） | `device_get_status` / `device_discover` |
| MoltBot 稼働（MCP） | `moltbot_health` |
| NanoKVM URL（MCP） | `nanokvm_console_url` |

## 統合API 新エンドポイント（2026-02-07）

| 目的 | API |
|------|-----|
| **意図に応じて直接実行** | `POST /api/intent/execute`（JSON: `{"text":"Pixel 7 のバッテリー教えて"}`） |
| **アラート → 通知** | `POST /api/devices/alerts/notify` |
| **Phase2 メモコンテキスト** | `POST /api/phase2/memo-context`（JSON: `{"messages":[...]}`） |

## 次の一手（スタック起動後）

1. **秘書ファイル整理**: MCP `secretary_file_organize`（path=~/Downloads, intent=list_only）→ 8088 が起動していること
2. **デバイス一覧**: MCP `device_get_status` でオンライン数・キュー確認
3. **Pixel 7 音声**: 上記で 8765/8766 起動 → Pixel 7 ブラウザで `http://<母艦IP>:8766`、WebSocket に `ws://<母艦IP>:8765`
4. **NanoKVM**: ブラウザで `http://127.0.0.1:9502/api/nanokvm/console_url` で URL 取得 → ログイン

## トラブル時

- **9502 や 8088 が応答しない**: `start_unified_api_and_moltbot.bat` を再実行。起動後は `scripts\check_manaos_stack.bat` で両方 OK か確認。
- **MCP がつながらない**: 統合API が 9502 で起動しているか確認（ブラウザで `http://127.0.0.1:9502/health` が 200 なら OK）。
- **秘書ファイル整理が失敗する**: MoltBot Gateway (8088) が起動しているか確認。.env に `MOLTBOT_GATEWAY_URL=http://127.0.0.1:8088` を設定。

## 参照

- **統合サマリー**: [INTEGRATION_UNIFIED_SUMMARY.md](INTEGRATION_UNIFIED_SUMMARY.md)
- **MoltBot × File Secretary**: [integration/MOLTBOT_FILE_SECRETARY_ROLES.md](integration/MOLTBOT_FILE_SECRETARY_ROLES.md)
- **Skills と MCP の使い分け**: [SKILLS_AND_MCP_GUIDE.md](guides/SKILLS_AND_MCP_GUIDE.md)
- **MCP サーバー一覧**: [MCP_SERVERS_GUIDE.md](guides/MCP_SERVERS_GUIDE.md)
- 機能一覧: [WHAT_ELSE_YOU_CAN_DO.md](guides/WHAT_ELSE_YOU_CAN_DO.md)
- デバイス起動手順: [DEVICES_ONLINE_SETUP.md](guides/DEVICES_ONLINE_SETUP.md)
- ルート: [../README.md](../README.md)
