# デバイス設定の説明

## 重要な注意事項

**母艦（Mothership）とX280は別々のパソコンです。**

- **母艦（Mothership）**: メインのWindows PC（このコードが実行されているPC）
- **X280**: 別のThinkPad Windows PC（Tailscale IP: 100.127.121.20）

## デバイス一覧

### 1. ManaOS（このはサーバー）
- **デバイスID**: `manaos`
- **タイプ**: `manaos`
- **APIエンドポイント**: `http://localhost:5106`（このはサーバー上で実行）
- **場所**: このはサーバー（Linux）

### 2. 母艦（Mothership）
- **デバイスID**: `mothership`
- **タイプ**: `mothership`
- **APIエンドポイント**: `null`（ローカル監視のみ）
- **場所**: **母艦（メインのWindows PC）** ← このコードが実行されているPC

### 3. X280
- **デバイスID**: `x280`
- **タイプ**: `x280`
- **APIエンドポイント**: `http://100.127.121.20:5120`（Tailscale経由）
- **場所**: **X280（別のThinkPad Windows PC）** ← 母艦とは別のPC

### 4. Konoha Server（このはサーバー）
- **デバイスID**: `konoha`
- **タイプ**: `konoha`
- **APIエンドポイント**: `http://100.93.120.33:5106`（Tailscale経由）
- **場所**: このはサーバー（Linux）

### 5. Pixel 7
- **デバイスID**: `pixel7`
- **タイプ**: `pixel7`
- **APIエンドポイント**: `http://100.127.121.20:5122`（Tailscale経由）
- **場所**: Pixel 7（Android端末、X280と同じTailscale IPを使用）

## ポート番号の説明

| デバイス | ポート | 説明 |
|---------|--------|------|
| ManaOS | 5106 | このはサーバー上のManaOS API |
| 母艦 | - | APIエンドポイントなし（ローカル監視のみ） |
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
   - X280側でのローカル接続: `http://localhost:5120`
   - 母艦側でのローカル接続: `http://localhost:5120`（File Secretaryサービスが母艦で実行されている場合）











