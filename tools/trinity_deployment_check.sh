#!/bin/bash
# ==============================================================================
# Trinity v2.0 Deployment Verification Script
# ==============================================================================
# 
# デプロイ前の最終確認スクリプト
#
# Author: Luna (Trinity Implementation AI)
# Created: 2025-10-18
# ==============================================================================

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 結果カウンター
PASSED=0
FAILED=0
WARNINGS=0

# 結果配列
RESULTS=()

echo -e "${CYAN}"
echo "=============================================================="
echo "🔍 Trinity v2.0 Deployment Verification"
echo "=============================================================="
echo -e "${NC}"
echo ""

# チェック関数
check_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    PASSED=$((PASSED + 1))
    RESULTS+=("PASS: $1")
}

check_fail() {
    echo -e "${RED}❌ $1${NC}"
    FAILED=$((FAILED + 1))
    RESULTS+=("FAIL: $1")
}

check_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    WARNINGS=$((WARNINGS + 1))
    RESULTS+=("WARN: $1")
}

# 1. ディレクトリ構造チェック
echo -e "${BLUE}[1/10] ディレクトリ構造チェック${NC}"
echo "--------------------------------------------------------------"

REQUIRED_DIRS=(
    "core"
    "agents"
    "dashboard"
    "shared"
    "logs"
    "scripts"
    "config"
    "systemd"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        check_pass "ディレクトリ存在: $dir/"
    else
        check_fail "ディレクトリ不足: $dir/"
    fi
done

echo ""

# 2. 必須ファイルチェック
echo -e "${BLUE}[2/10] 必須ファイルチェック${NC}"
echo "--------------------------------------------------------------"

REQUIRED_FILES=(
    "setup.sh"
    "core/db_manager.py"
    "core/autonomous_orchestrator.py"
    "dashboard/server.py"
    "config/env.example"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        check_pass "ファイル存在: $file"
    else
        check_fail "ファイル不足: $file"
    fi
done

echo ""

# 3. 実行権限チェック
echo -e "${BLUE}[3/10] 実行権限チェック${NC}"
echo "--------------------------------------------------------------"

EXECUTABLE_FILES=(
    "setup.sh"
    "scripts/auto_monitor.py"
    "dashboard/server.py"
)

for file in "${EXECUTABLE_FILES[@]}"; do
    if [ -f "$file" ] && [ -x "$file" ]; then
        check_pass "実行権限OK: $file"
    elif [ -f "$file" ]; then
        check_warn "実行権限なし: $file (chmod +x で設定可能)"
    fi
done

echo ""

# 4. Python環境チェック
echo -e "${BLUE}[4/10] Python環境チェック${NC}"
echo "--------------------------------------------------------------"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    check_pass "Python: $PYTHON_VERSION"
else
    check_fail "Python 3がインストールされていません"
fi

# pip確認
if command -v pip3 &> /dev/null; then
    check_pass "pip3: インストール済み"
else
    check_fail "pip3がインストールされていません"
fi

echo ""

# 5. 依存パッケージチェック
echo -e "${BLUE}[5/10] 依存パッケージチェック${NC}"
echo "--------------------------------------------------------------"

REQUIRED_PACKAGES=(
    "flask"
    "flask-socketio"
    "click"
    "tabulate"
    "watchdog"
    "psutil"
)

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import ${package//-/_}" 2>/dev/null; then
        check_pass "パッケージ: $package"
    else
        check_fail "パッケージ不足: $package"
    fi
done

echo ""

# 6. 環境変数チェック
echo -e "${BLUE}[6/10] 環境変数チェック${NC}"
echo "--------------------------------------------------------------"

if [ -f ".env" ]; then
    check_pass ".env ファイル存在"
    
    # APIキー確認
    if grep -q "OPENAI_API_KEY=" ".env" && ! grep -q "your_openai_api_key_here" ".env"; then
        check_pass "OpenAI API Key: 設定済み"
    else
        check_warn "OpenAI API Key: 未設定"
    fi
    
    if grep -q "ANTHROPIC_API_KEY=" ".env" && ! grep -q "your_anthropic_api_key_here" ".env"; then
        check_pass "Anthropic API Key: 設定済み"
    else
        check_warn "Anthropic API Key: 未設定"
    fi
else
    check_fail ".env ファイルが見つかりません"
fi

echo ""

# 7. データベースチェック
echo -e "${BLUE}[7/10] データベースチェック${NC}"
echo "--------------------------------------------------------------"

DB_PATH="shared/tasks.db"

if [ -f "$DB_PATH" ]; then
    check_pass "データベース存在: $DB_PATH"
    
    # データベース接続テスト
    if python3 -c "
from core.db_manager import DatabaseManager
try:
    db = DatabaseManager()
    tasks = db.get_tasks()
    print(f'データベース接続成功 (タスク数: {len(tasks)})')
    exit(0)
except Exception as e:
    print(f'データベース接続失敗: {e}')
    exit(1)
" 2>/dev/null; then
        check_pass "データベース接続テスト成功"
    else
        check_fail "データベース接続テスト失敗"
    fi
else
    check_warn "データベース未作成（初回起動時に自動作成されます）"
fi

echo ""

# 8. ポート使用状況チェック
echo -e "${BLUE}[8/10] ポート使用状況チェック${NC}"
echo "--------------------------------------------------------------"

REQUIRED_PORTS=(5100)

for port in "${REQUIRED_PORTS[@]}"; do
    if command -v netstat &> /dev/null; then
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            check_warn "ポート $port は既に使用中です"
        else
            check_pass "ポート $port は利用可能"
        fi
    elif command -v ss &> /dev/null; then
        if ss -tuln 2>/dev/null | grep -q ":$port "; then
            check_warn "ポート $port は既に使用中です"
        else
            check_pass "ポート $port は利用可能"
        fi
    else
        check_warn "ポートチェックツール（netstat/ss）が見つかりません"
        break
    fi
done

echo ""

# 9. ログディレクトリチェック
echo -e "${BLUE}[9/10] ログディレクトリチェック${NC}"
echo "--------------------------------------------------------------"

if [ -d "logs" ]; then
    check_pass "ログディレクトリ存在"
    
    # 書き込み権限確認
    if [ -w "logs" ]; then
        check_pass "ログディレクトリ書き込み可能"
    else
        check_fail "ログディレクトリ書き込み不可"
    fi
    
    # ディスク容量確認
    AVAILABLE_SPACE=$(df -BM logs | tail -1 | awk '{print $4}' | sed 's/M//')
    if [ "$AVAILABLE_SPACE" -gt 100 ]; then
        check_pass "ディスク空き容量: ${AVAILABLE_SPACE}MB"
    else
        check_warn "ディスク空き容量が少ない: ${AVAILABLE_SPACE}MB"
    fi
else
    check_fail "ログディレクトリが見つかりません"
fi

echo ""

# 10. systemdサービスファイルチェック
echo -e "${BLUE}[10/10] systemdサービスファイルチェック${NC}"
echo "--------------------------------------------------------------"

SERVICE_FILES=(
    "systemd/trinity-dashboard.service"
    "systemd/trinity-orchestrator.service"
    "systemd/trinity-monitor.service"
)

for service in "${SERVICE_FILES[@]}"; do
    if [ -f "$service" ]; then
        check_pass "サービスファイル: $service"
    else
        check_warn "サービスファイル不足: $service"
    fi
done

echo ""

# 結果サマリー
echo "=============================================================="
echo -e "${CYAN}📊 検証結果サマリー${NC}"
echo "=============================================================="
echo ""

TOTAL=$((PASSED + FAILED + WARNINGS))

echo -e "${GREEN}✅ 成功: $PASSED${NC}"
echo -e "${RED}❌ 失敗: $FAILED${NC}"
echo -e "${YELLOW}⚠️  警告: $WARNINGS${NC}"
echo ""
echo "総チェック数: $TOTAL"
echo ""

# 成功率計算
if [ $TOTAL -gt 0 ]; then
    SUCCESS_RATE=$(awk "BEGIN {printf \"%.1f\", ($PASSED/$TOTAL)*100}")
    echo "成功率: ${SUCCESS_RATE}%"
fi

echo ""

# 詳細結果をファイルに保存
REPORT_FILE="deployment_check_report_$(date +%Y%m%d_%H%M%S).txt"
{
    echo "Trinity v2.0 Deployment Verification Report"
    echo "Generated: $(date)"
    echo ""
    echo "Results:"
    for result in "${RESULTS[@]}"; do
        echo "$result"
    done
    echo ""
    echo "Summary:"
    echo "  Passed:   $PASSED"
    echo "  Failed:   $FAILED"
    echo "  Warnings: $WARNINGS"
    echo "  Total:    $TOTAL"
    echo "  Success Rate: ${SUCCESS_RATE}%"
} > "$REPORT_FILE"

echo "📄 詳細レポートを保存: $REPORT_FILE"
echo ""

# 最終判定
if [ $FAILED -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}🎉 完璧です！デプロイ準備完了${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠️  警告があります確認してください${NC}"
        exit 0
    fi
else
    echo -e "${RED}❌ エラーがあります。修正してください${NC}"
    exit 1
fi

