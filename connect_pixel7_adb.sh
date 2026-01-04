#!/bin/bash
# ピクセル7ワイヤレスADB接続スクリプト（簡易版）

PIXEL7_IP="${PIXEL7_IP:-100.127.121.20}"
PIXEL7_ADB_PORT="${PIXEL7_ADB_PORT:-5555}"

echo "📱 ピクセル7に接続中..."

# 接続試行
adb connect ${PIXEL7_IP}:${PIXEL7_ADB_PORT}

sleep 2

# 接続確認
if adb devices | grep -q "${PIXEL7_IP}:${PIXEL7_ADB_PORT}"; then
    echo "✅ 接続成功！"
    adb devices
else
    echo "❌ 接続失敗。以下を確認してください:"
    echo "1. ピクセル7のワイヤレスデバッグが有効か"
    echo "2. 同じTailscaleネットワークに接続されているか"
    echo "3. 初回接続の場合は setup_pixel7_adb.sh を実行してください"
fi

