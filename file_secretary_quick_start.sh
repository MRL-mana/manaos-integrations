#!/bin/bash
# File Secretary クイック起動スクリプト（Linux/Mac用）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== File Secretary クイック起動 ==="
echo ""

# 環境変数設定
export PORT=5120
export FILE_SECRETARY_DB_PATH=file_secretary.db
export INBOX_PATH="${SCRIPT_DIR}/00_INBOX"

# INBOXディレクトリ作成
mkdir -p "$INBOX_PATH"

# データベース初期化
echo "📊 データベース初期化中..."
python3 -c "from file_secretary_db import FileSecretaryDB; FileSecretaryDB('file_secretary.db')" || true

# Indexer起動（バックグラウンド）
echo "📂 Indexer起動中..."
python3 file_secretary_start.py &
INDEXER_PID=$!
echo "✅ Indexer起動完了 (PID: $INDEXER_PID)"

# APIサーバー起動（バックグラウンド）
sleep 2
echo "🔌 APIサーバー起動中..."
python3 file_secretary_api.py &
API_PID=$!
echo "✅ APIサーバー起動完了 (PID: $API_PID)"

# 起動確認
sleep 3
echo ""
echo "📊 状態確認中..."
if curl -s http://localhost:5120/health > /dev/null; then
    echo "✅ APIサーバー: 正常応答"
else
    echo "⚠️ APIサーバー: 応答なし"
fi

echo ""
echo "✅ File Secretary 起動完了"
echo ""
echo "停止するには:"
echo "  kill $INDEXER_PID $API_PID"
echo "または:"
echo "  python3 file_secretary_manager.py stop"

# プロセスを待機
wait

