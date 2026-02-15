# MCP-Proxy

安全で高性能なMCPサーバープロキシ

## 機能

- ✅ **レート制限**: リクエスト数の制限（デフォルト: 60リクエスト/分）
- ✅ **認証・認可**: Bearer トークン認証
- ✅ **リクエストログ**: 全リクエストの記録
- ✅ **エラーハンドリング**: 自動リトライ（最大3回）
- ✅ **ヘルスチェック**: サーバー状態の監視
- ✅ **メトリクス収集**: リクエスト統計

## セットアップ

### 1. 認証トークンの設定

```bash
# 環境変数に設定
export MCP_PROXY_AUTH_TOKEN="your-secret-token-here"

# または .env ファイルに記述
echo 'MCP_PROXY_AUTH_TOKEN=your-secret-token-here' > /root/mcp_proxy/.env
```

### 2. systemdサービスのインストール

```bash
# サービスファイルをコピー
sudo cp /root/mcp_proxy/mcp_proxy.service /etc/systemd/system/

# サービスを有効化
sudo systemctl daemon-reload
sudo systemctl enable mcp-proxy
sudo systemctl start mcp-proxy

# 状態確認
sudo systemctl status mcp-proxy
```

### 3. ログ確認

```bash
# システムログ
sudo journalctl -u mcp-proxy -f

# アプリケーションログ
tail -f /root/logs/mcp_proxy/mcp_proxy.log
```

## 使用方法

### ヘルスチェック

```bash
curl http://127.0.0.1:3011/health
```

### サーバー一覧

```bash
curl http://127.0.0.1:3011/servers
```

### MCPリクエスト送信

```bash
curl -X POST http://127.0.0.1:3011/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "mcp_server": "trinity-agents",
    "method": "tools/list",
    "params": {},
    "id": "req-123"
  }'
```

### メトリクス取得

```bash
curl http://127.0.0.1:3011/metrics
```

## 設定

環境変数で設定可能：

- `MCP_PROXY_PORT`: ポート番号（デフォルト: 3011）
- `MCP_PROXY_RATE_LIMIT`: レート制限（デフォルト: 60）
- `MCP_PROXY_AUTH_TOKEN`: 認証トークン（必須）

## トラブルシューティング

### サービスが起動しない

```bash
# ログ確認
sudo journalctl -u mcp-proxy -n 50

# 手動実行でエラー確認
cd /root/mcp_proxy
python3 mcp_proxy_server.py
```

### 認証エラー

認証トークンが正しく設定されているか確認：

```bash
echo $MCP_PROXY_AUTH_TOKEN
```

### ポート競合

別のポートを使用する場合：

```bash
export MCP_PROXY_PORT=3012
sudo systemctl restart mcp-proxy
```

## 開発

### ローカル実行

```bash
cd /root/mcp_proxy
python3 mcp_proxy_server.py
```

### テスト

```bash
# ヘルスチェック
curl http://127.0.0.1:3011/health

# サーバー一覧
curl http://127.0.0.1:3011/servers
```

