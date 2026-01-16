#!/bin/bash
# MCP-Proxy セットアップスクリプト

set -e

echo "🚀 MCP-Proxy セットアップ開始..."

# ディレクトリ作成
mkdir -p /root/mcp_proxy
mkdir -p /root/logs/mcp_proxy

# 認証トークンの生成（未設定の場合）
if [ -z "$MCP_PROXY_AUTH_TOKEN" ]; then
    echo "⚠️  認証トークンが未設定です。生成します..."
    TOKEN=$(openssl rand -hex 32)
    echo "生成されたトークン: $TOKEN"
    echo ""
    echo "以下のコマンドで環境変数に設定してください:"
    echo "export MCP_PROXY_AUTH_TOKEN=\"$TOKEN\""
    echo ""
    echo "または、.env ファイルに記述:"
    echo "echo 'MCP_PROXY_AUTH_TOKEN=$TOKEN' > /root/mcp_proxy/.env"
    echo ""
    read -p "このトークンを使用しますか？ (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        export MCP_PROXY_AUTH_TOKEN="$TOKEN"
        echo "export MCP_PROXY_AUTH_TOKEN=\"$TOKEN\"" >> ~/.bashrc
        echo "✅ 環境変数に設定しました"
    fi
fi

# systemdサービスのインストール
echo "📦 systemdサービスをインストール中..."
sudo cp /root/mcp_proxy/mcp_proxy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mcp-proxy

echo "✅ セットアップ完了！"
echo ""
echo "次のコマンドで起動:"
echo "  sudo systemctl start mcp-proxy"
echo ""
echo "状態確認:"
echo "  sudo systemctl status mcp-proxy"
echo ""
echo "ログ確認:"
echo "  sudo journalctl -u mcp-proxy -f"

