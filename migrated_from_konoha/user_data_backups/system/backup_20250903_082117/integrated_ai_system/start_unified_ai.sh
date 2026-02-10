#!/bin/bash
# 統合AIシステム起動スクリプト

echo "🚀 統合AIシステム起動中..."
cd "$(dirname "$0")"

# 依存関係チェック
python3 -c "import asyncio, sqlite3, json" || {
    echo "❌ 必要なPythonモジュールが不足しています"
    exit 1
}

# 統合AIシステム起動
python3 unified_ai_system.py

echo "✅ 統合AIシステム起動完了"
