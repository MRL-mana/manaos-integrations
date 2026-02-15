# デバイス設定の説明

## 重要な注意事項

**母艦（Mothership）とX280は別々のパソコンです。**

- **母艦（Mothership）**: メインのWindows PC（このコードが実行されているPC）
- **X280**: 別のThinkPad Windows PC（Tailscale IP: 100.127.121.20）

## デバイス一覧

### 1. ManaOS（このはサーバー）
- **デバイスID**: `manaos`
- **タイプ**: `manaos`
- **APIエンドポイント**: `http://127.0.0.1:5106`（このはサーバー上で実行）
- **場所**: このはサーバー（Linux）

### 2. 母艦（Mothership）
- **デバイスID**: `mothership`
- **タイプ**: `mothership`
- **APIエンドポイント**: `null`（ローカル監視のみ）
- **場所**: **母艦（メインのWindows PC）** ← このコードが実行されているPC

### 3. NanoKVM
- **デバイスID**: `nanokvm`
- **タイプ**: `nanokvm`
- **Web UI**: `https://100.105.25.84/#/auth/login`（Tailscale 等）
- **APIエンドポイント**: `https://100.105.25.84`
- **場所**: 母艦に接続（KVM / リモートコンソール）
- **ログイン**: ユーザー `mana`。パスワードは `.env` の `NANOKVM_PASSWORD` に設定（`env.example` 参照）
- **マナが画面を確認するには（ちょい上級）**: AI はプライベートIPに直接アクセスできないため、**Cursor の browser MCP（cursor-ide-browser）** を使う。あなたのPC上のブラウザを操作して NanoKVM の URL を開き、スナップショットを取得する。これは「あなたの環境から見る」扱いになるので利用可能。有効化は `.cursor/mcp.json` に `cursor-ide-browser` を追加済み。Cursor 再起動または 設定 → MCP でリロードすること。

**ログイン後の流れ**: ログインすると KVM コンソール画面になる。接続先マシン（母艦に接続された対象）の画面操作・リモート管理が可能。URL は統合API `GET /api/nanokvm/console_url` または MCP `nanokvm_console_url` で取得できる（疎通確認は `GET /api/nanokvm` または `GET /api/nanokvm/health`）。

### 4. X280
- **デバイスID**: `x280`
- **タイプ**: `x280`
- **APIエンドポイント**: `http://100.127.121.20:5120`（Tailscale経由）
- **場所**: **X280（別のThinkPad Windows PC）** ← 母艦とは別のPC

### 5. Konoha Server（このはサーバー）
- **デバイスID**: `konoha`
- **タイプ**: `konoha`
- **APIエンドポイント**: `http://100.93.120.33:5106`（Tailscale経由）
- **場所**: このはサーバー（Linux）

### 6. Pixel 7
- **デバイスID**: `pixel7`
- **タイプ**: `pixel7`
- **APIエンドポイント**: `http://100.127.121.20:5122`（Tailscale経由）
- **場所**: Pixel 7（Android端末、X280と同じTailscale IPを使用）

## ポート番号の説明

| デバイス | ポート | 説明 |
|---------|--------|------|
| ManaOS | 5106 | このはサーバー上のManaOS API |
| 母艦 | - | APIエンドポイントなし（ローカル監視のみ） |
| NanoKVM | 443 (HTTPS) | https://100.105.25.84（ログイン: mana / .env でパスワード） |
| X280 | 5120 | X280 API Gateway（X280側で実行） |
| Konoha Server | 5106 | このはサーバー上のKonoha API |
| Pixel 7 | 5122 | Pixel 7 API Gateway（Pixel 7側で実行） |

## 設定ファイル

- `device_orchestrator_config.json`: デバイス統合管理システムの設定
- `device_health_config.json`: デバイス健康状態監視システムの設定

## 注意事項

1. **母艦とX280は別々のPCです**
   - 母艦で実行されるコードは、X280に接続する際はTailscale IP（100.127.121.20）を使用します
   - X280側で実行されるコードは、localhostを使用します

2. **ポート5120について**
   - X280のAPI Gatewayはポート5120を使用します
   - File Secretaryサービスもポート5120を使用する場合がありますが、これは**母艦側で実行される場合**です
   - X280のAPI GatewayとFile Secretaryサービスは別々のサービスです

3. **接続方法**
   - 母艦からX280への接続: `http://100.127.121.20:5120`
   - X280側でのローカル接続: `http://127.0.0.1:5120`
   - 母艦側でのローカル接続: `http://127.0.0.1:5120`（File Secretaryサービスが母艦で実行されている場合）
