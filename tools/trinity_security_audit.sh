#!/bin/bash

# Trinity v2.1 セキュリティ監査スクリプト
# 実行者: Mina (QA AI)
# 実行日: 2025-10-18

echo "🔍 Trinity v2.1 セキュリティ監査開始"
echo "=================================="
echo ""

WORKSPACE="/root/trinity_workspace"
REPORT_FILE="${WORKSPACE}/reports/security_audit_scan_$(date +%Y%m%d_%H%M%S).txt"

mkdir -p "${WORKSPACE}/reports"

# レポート初期化
echo "Trinity v2.1 セキュリティスキャン結果" > "$REPORT_FILE"
echo "実行日時: $(date)" >> "$REPORT_FILE"
echo "================================" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# カウンター
SQL_INJECTION_COUNT=0
XSS_COUNT=0
API_KEY_COUNT=0
LOG_LEAK_COUNT=0
CSRF_COUNT=0

# 1. SQLインジェクション脆弱性チェック
echo "=== 1. SQLインジェクション チェック ==="
echo "=== 1. SQLインジェクション チェック ===" >> "$REPORT_FILE"
echo "危険なSQL動的生成パターンを検索中..."

# execute with format/% 検索
SQL_RESULTS=$(grep -rn "execute.*format\|execute.*%\|f\".*execute\|\.format(.*execute" \
  --include="*.py" "$WORKSPACE" 2>/dev/null || true)

if [ -n "$SQL_RESULTS" ]; then
    echo "⚠️ 潜在的なSQLインジェクション脆弱性を発見:" | tee -a "$REPORT_FILE"
    echo "$SQL_RESULTS" | tee -a "$REPORT_FILE"
    SQL_INJECTION_COUNT=$(echo "$SQL_RESULTS" | wc -l)
else
    echo "✅ SQLインジェクション脆弱性なし" | tee -a "$REPORT_FILE"
fi
echo "" | tee -a "$REPORT_FILE"

# 2. XSS脆弱性チェック
echo "=== 2. XSS脆弱性 チェック ==="
echo "=== 2. XSS脆弱性 チェック ===" >> "$REPORT_FILE"
echo "危険なHTML挿入パターンを検索中..."

XSS_RESULTS=$(grep -rn "innerHTML\|dangerouslySetInnerHTML\|document\.write" \
  --include="*.js" --include="*.html" "$WORKSPACE/dashboard" "$WORKSPACE/static" 2>/dev/null || true)

if [ -n "$XSS_RESULTS" ]; then
    echo "⚠️ 潜在的なXSS脆弱性を発見:" | tee -a "$REPORT_FILE"
    echo "$XSS_RESULTS" | tee -a "$REPORT_FILE"
    XSS_COUNT=$(echo "$XSS_RESULTS" | wc -l)
else
    echo "✅ XSS脆弱性なし" | tee -a "$REPORT_FILE"
fi
echo "" | tee -a "$REPORT_FILE"

# 3. APIキー漏洩チェック
echo "=== 3. APIキー漏洩 チェック ==="
echo "=== 3. APIキー漏洩 チェック ===" >> "$REPORT_FILE"
echo "ハードコードされたAPIキーを検索中..."

API_KEY_RESULTS=$(grep -rn "api[_-]key\s*=\s*['\"]sk-\|API_KEY\s*=\s*['\"]sk-\|api[_-]key\s*=\s*['\"][A-Za-z0-9]\{20,\}" \
  --include="*.py" --include="*.js" --include="*.env" \
  "$WORKSPACE" 2>/dev/null | grep -v "\.example\|\.template\|# " || true)

if [ -n "$API_KEY_RESULTS" ]; then
    echo "❌ ハードコードされたAPIキーを発見（重大）:" | tee -a "$REPORT_FILE"
    echo "$API_KEY_RESULTS" | tee -a "$REPORT_FILE"
    API_KEY_COUNT=$(echo "$API_KEY_RESULTS" | wc -l)
else
    echo "✅ ハードコードされたAPIキーなし" | tee -a "$REPORT_FILE"
fi
echo "" | tee -a "$REPORT_FILE"

# 4. ログの機密情報チェック
echo "=== 4. ログの機密情報 チェック ==="
echo "=== 4. ログの機密情報 チェック ===" >> "$REPORT_FILE"
echo "ログに出力される機密情報を検索中..."

LOG_LEAK_RESULTS=$(grep -rn "logger.*password\|logger.*api_key\|logger.*token\|logger.*secret\|print.*password\|print.*api_key" \
  --include="*.py" "$WORKSPACE" 2>/dev/null || true)

if [ -n "$LOG_LEAK_RESULTS" ]; then
    echo "⚠️ ログに機密情報が出力される可能性:" | tee -a "$REPORT_FILE"
    echo "$LOG_LEAK_RESULTS" | tee -a "$REPORT_FILE"
    LOG_LEAK_COUNT=$(echo "$LOG_LEAK_RESULTS" | wc -l)
else
    echo "✅ ログの機密情報漏洩なし" | tee -a "$REPORT_FILE"
fi
echo "" | tee -a "$REPORT_FILE"

# 5. CSRF対策確認
echo "=== 5. CSRF対策 チェック ==="
echo "=== 5. CSRF対策 チェック ===" >> "$REPORT_FILE"
echo "CSRF対策の実装状況を確認中..."

CSRF_EXEMPT=$(grep -rn "@csrf_exempt" --include="*.py" "$WORKSPACE/dashboard" 2>/dev/null || true)
CSRF_TOKEN=$(grep -rn "csrf_token" --include="*.py" --include="*.html" "$WORKSPACE/dashboard" 2>/dev/null || true)

if [ -n "$CSRF_EXEMPT" ]; then
    echo "⚠️ CSRF対策が無効化されているエンドポイント:" | tee -a "$REPORT_FILE"
    echo "$CSRF_EXEMPT" | tee -a "$REPORT_FILE"
    CSRF_COUNT=$(echo "$CSRF_EXEMPT" | wc -l)
fi

if [ -n "$CSRF_TOKEN" ]; then
    echo "✅ CSRF対策実装あり:" | tee -a "$REPORT_FILE"
    echo "$CSRF_TOKEN" | head -3 | tee -a "$REPORT_FILE"
else
    echo "⚠️ CSRF対策が見つかりません" | tee -a "$REPORT_FILE"
    CSRF_COUNT=$((CSRF_COUNT + 1))
fi
echo "" | tee -a "$REPORT_FILE"

# 6. TLS/HTTPS設定確認
echo "=== 6. TLS/HTTPS設定 チェック ==="
echo "=== 6. TLS/HTTPS設定 チェック ===" >> "$REPORT_FILE"
echo "HTTPS強制設定を確認中..."

HTTPS_RESULTS=$(grep -rn "ssl_context\|HTTPS\|TLS\|redirect.*https" \
  --include="*.py" "$WORKSPACE/dashboard" 2>/dev/null || true)

if [ -n "$HTTPS_RESULTS" ]; then
    echo "✅ HTTPS/TLS設定あり:" | tee -a "$REPORT_FILE"
    echo "$HTTPS_RESULTS" | head -5 | tee -a "$REPORT_FILE"
else
    echo "⚠️ HTTPS/TLS設定が見つかりません（開発環境では許容）" | tee -a "$REPORT_FILE"
fi
echo "" | tee -a "$REPORT_FILE"

# 7. 認証・認可チェック
echo "=== 7. 認証・認可 チェック ==="
echo "=== 7. 認証・認可 チェック ===" >> "$REPORT_FILE"
echo "認証機構の実装を確認中..."

AUTH_RESULTS=$(grep -rn "@login_required\|@require_auth\|verify_token\|check_permission" \
  --include="*.py" "$WORKSPACE" 2>/dev/null || true)

if [ -n "$AUTH_RESULTS" ]; then
    echo "✅ 認証機構実装あり:" | tee -a "$REPORT_FILE"
    echo "$AUTH_RESULTS" | head -5 | tee -a "$REPORT_FILE"
else
    echo "⚠️ 認証機構が見つかりません" | tee -a "$REPORT_FILE"
fi
echo "" | tee -a "$REPORT_FILE"

# サマリー
echo "================================" | tee -a "$REPORT_FILE"
echo "セキュリティスキャン サマリー" | tee -a "$REPORT_FILE"
echo "================================" | tee -a "$REPORT_FILE"
echo "SQLインジェクション潜在問題: $SQL_INJECTION_COUNT 件" | tee -a "$REPORT_FILE"
echo "XSS潜在問題: $XSS_COUNT 件" | tee -a "$REPORT_FILE"
echo "APIキー漏洩: $API_KEY_COUNT 件" | tee -a "$REPORT_FILE"
echo "ログ機密情報漏洩: $LOG_LEAK_COUNT 件" | tee -a "$REPORT_FILE"
echo "CSRF対策問題: $CSRF_COUNT 件" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

TOTAL_ISSUES=$((SQL_INJECTION_COUNT + XSS_COUNT + API_KEY_COUNT + LOG_LEAK_COUNT + CSRF_COUNT))
echo "総問題数: $TOTAL_ISSUES 件" | tee -a "$REPORT_FILE"

if [ $TOTAL_ISSUES -eq 0 ]; then
    echo "✅ 重大な脆弱性は発見されませんでした" | tee -a "$REPORT_FILE"
elif [ $TOTAL_ISSUES -lt 5 ]; then
    echo "⚠️ いくつかの改善点が見つかりました" | tee -a "$REPORT_FILE"
else
    echo "❌ 複数の脆弱性が見つかりました。修正が必要です" | tee -a "$REPORT_FILE"
fi

echo "" | tee -a "$REPORT_FILE"
echo "詳細レポート: $REPORT_FILE"
echo "✅ セキュリティ監査スキャン完了"

