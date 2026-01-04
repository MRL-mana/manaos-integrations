#!/bin/bash
# X280統合セットアップスクリプト（このはサーバー側）

set -e

echo "🔌 X280 ManaOS統合セットアップを開始します..."

# 環境変数の設定
export X280_HOST="${X280_HOST:-x280}"
export X280_USER="${X280_USER:-mana}"
export X280_PORT="${X280_PORT:-22}"
export X280_API_PORT="${X280_API_PORT:-5120}"
export X280_TAILSCALE_IP="${X280_TAILSCALE_IP:-100.127.121.20}"
export X280_NODE_MANAGER_PORT="${X280_NODE_MANAGER_PORT:-5121}"

# 作業ディレクトリ
WORK_DIR="/root/manaos_integrations"
cd "$WORK_DIR"

echo "📦 必要なパッケージを確認..."
python3 -c "import fastapi, httpx, uvicorn" 2>/dev/null || {
    echo "必要なパッケージをインストール中..."
    pip3 install fastapi httpx uvicorn
}

echo "📋 X280接続を確認..."
if ssh -o ConnectTimeout=5 "$X280_USER@$X280_HOST" "echo 'Connection OK'" 2>/dev/null; then
    echo "✅ X280への接続確認成功"
else
    echo "⚠️  X280への接続に失敗しました。SSH設定を確認してください。"
    exit 1
fi

echo "📤 X280 API Gatewayファイルを転送中..."
scp "$WORK_DIR/x280_api_gateway.py" "$X280_USER@$X280_HOST:C:/manaos_x280/" || {
    echo "⚠️  ファイル転送に失敗しました。X280側で C:/manaos_x280/ ディレクトリを作成してください。"
    echo "X280側で実行: mkdir C:\\manaos_x280"
}

echo "📝 systemdサービスファイルを作成中..."
sudo tee /etc/systemd/system/x280-node-manager.service > /dev/null <<EOF
[Unit]
Description=X280 Node Manager
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$WORK_DIR
Environment="X280_HOST=$X280_HOST"
Environment="X280_USER=$X280_USER"
Environment="X280_PORT=$X280_PORT"
Environment="X280_API_PORT=$X280_API_PORT"
Environment="X280_TAILSCALE_IP=$X280_TAILSCALE_IP"
Environment="X280_NODE_MANAGER_PORT=$X280_NODE_MANAGER_PORT"
ExecStart=/usr/bin/python3 $WORK_DIR/x280_node_manager.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "🔄 systemdサービスを有効化中..."
sudo systemctl daemon-reload
sudo systemctl enable x280-node-manager
sudo systemctl start x280-node-manager

echo "⏳ サービス起動を待機中..."
sleep 3

if sudo systemctl is-active --quiet x280-node-manager; then
    echo "✅ X280 Node Managerが正常に起動しました"
else
    echo "⚠️  サービス起動に問題があります。ログを確認してください:"
    echo "   sudo journalctl -u x280-node-manager -n 20"
    exit 1
fi

echo ""
echo "🎉 セットアップが完了しました！"
echo ""
echo "📋 次のステップ:"
echo "1. X280側でAPI Gatewayを起動:"
echo "   ssh x280"
echo "   cd C:\\manaos_x280"
echo "   python x280_api_gateway.py"
echo ""
echo "2. 接続確認:"
echo "   curl http://localhost:5121/api/status"
echo ""
echo "3. 詳細は X280_INTEGRATION_GUIDE.md を参照してください"

