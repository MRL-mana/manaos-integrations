#!/bin/bash
# ピクセル7ワイヤレスADB接続セットアップスクリプト

set -e

echo "📱 ピクセル7ワイヤレスADB接続セットアップを開始します..."

# 設定
PIXEL7_IP="${PIXEL7_IP:-100.127.121.20}"
PIXEL7_ADB_PORT="${PIXEL7_ADB_PORT:-5555}"

echo ""
echo "📋 手順1: ピクセル7側の設定"
echo "=================================="
echo "1. 設定 > デバイス情報 > ビルド番号を7回タップして開発者オプションを有効化"
echo "2. 設定 > 開発者オプション > USBデバッグを有効化"
echo "3. 設定 > 開発者オプション > ワイヤレスデバッグを有効化"
echo "4. ワイヤレスデバッグをタップして、ポート番号を確認（通常は5桁の数字）"
echo ""
read -p "ピクセル7側の設定は完了しましたか？ (y/n): " confirm

if [ "$confirm" != "y" ]; then
    echo "ピクセル7側の設定を完了してから再度実行してください。"
    exit 1
fi

echo ""
echo "📋 手順2: ワイヤレスデバッグポートの確認"
echo "=================================="
read -p "ピクセル7のワイヤレスデバッグポート番号を入力してください（例: 12345）: " WIRELESS_PORT

if [ -z "$WIRELESS_PORT" ]; then
    echo "ポート番号が入力されていません。"
    exit 1
fi

echo ""
echo "📋 手順3: ADB接続の確認"
echo "=================================="

# ADBがインストールされているか確認
if ! command -v adb &> /dev/null; then
    echo "ADBがインストールされていません。インストールしますか？"
    read -p "(y/n): " install_adb
    if [ "$install_adb" = "y" ]; then
        echo "ADBをインストール中..."
        # Ubuntu/Debianの場合
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y android-tools-adb android-tools-fastboot
        # CentOS/RHELの場合
        elif command -v yum &> /dev/null; then
            sudo yum install -y android-tools
        else
            echo "パッケージマネージャーが見つかりません。手動でADBをインストールしてください。"
            exit 1
        fi
    else
        echo "ADBが必要です。インストールしてから再度実行してください。"
        exit 1
    fi
fi

echo "ADBバージョン確認:"
adb version

echo ""
echo "📋 手順4: ワイヤレスADB接続"
echo "=================================="

# 既存の接続を切断
echo "既存の接続を確認中..."
adb disconnect ${PIXEL7_IP}:${PIXEL7_ADB_PORT} 2>/dev/null || true

# ワイヤレスデバッグポート経由で接続
echo "ワイヤレスデバッグポート経由で接続中..."
adb connect ${PIXEL7_IP}:${WIRELESS_PORT}

sleep 2

# 接続確認
echo ""
echo "接続デバイスを確認中..."
adb devices

# 通常のADBポートに切り替え
echo ""
echo "ADB TCP/IPモードに切り替え中..."
adb tcpip ${PIXEL7_ADB_PORT}

sleep 2

# 通常ポートで再接続
echo ""
echo "通常ポートで再接続中..."
adb disconnect ${PIXEL7_IP}:${WIRELESS_PORT} 2>/dev/null || true
adb connect ${PIXEL7_IP}:${PIXEL7_ADB_PORT}

sleep 2

# 最終確認
echo ""
echo "📋 最終確認"
echo "=================================="
DEVICES=$(adb devices | grep -v "List" | grep -v "^$" | wc -l)

if [ "$DEVICES" -gt 0 ]; then
    echo "✅ 接続成功！"
    echo ""
    echo "接続中のデバイス:"
    adb devices
    echo ""
    echo "ピクセル7の情報:"
    adb shell getprop ro.product.model
    adb shell getprop ro.build.version.release
    echo ""
    echo "🎉 セットアップ完了！"
    echo ""
    echo "次回からは以下のコマンドで接続できます:"
    echo "  adb connect ${PIXEL7_IP}:${PIXEL7_ADB_PORT}"
else
    echo "❌ 接続に失敗しました。"
    echo ""
    echo "確認事項:"
    echo "1. ピクセル7と母艦が同じTailscaleネットワークに接続されているか"
    echo "2. ピクセル7のワイヤレスデバッグが有効になっているか"
    echo "3. ファイアウォールでポートがブロックされていないか"
    exit 1
fi

