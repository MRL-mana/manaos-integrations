#!/bin/bash
# カバレッジレポート生成スクリプト

set -e

echo "="
echo "カバレッジレポート生成中..."
echo "="
echo

# Python のによって異なるため、powershell用のバッチファイルも必要
# ここではシェルスクリプト版も作成

# カバレッジの実行
python -m pytest tests/unit/ \
    --cov=. \
    --cov-config=.coveragerc \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=xml \
    -v

echo
echo "="
echo "✅ カバレッジレポート生成完了"
echo "="
echo

# HTML レポートの場所を表示
echo "📊 HTML レポート: htmlcov/index.html"
echo "📄 XML レポート: coverage.xml"
echo

# サマリーを表示
coverage report --skip-covered
