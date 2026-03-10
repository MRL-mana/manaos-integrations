#!/usr/bin/env python3
"""
ManaOS 学習ダッシュボード（強化版）
メトリクス表示、ペンディングルール管理、SLO監視
"""

from flask import Flask, render_template_string, jsonify, request
from datetime import datetime, timedelta
import json
import sys
import os

sys.path.insert(0, '/root/scripts')
sys.path.insert(0, '/root/manaos_learning')

# インポート（相対インポート回避）
import importlib.util

# learning_api
spec1 = importlib.util.spec_from_file_location("learning_api", "/root/scripts/learning_api.py")
learning_api = importlib.util.module_from_spec(spec1)  # type: ignore
spec1.loader.exec_module(learning_api)  # type: ignore[union-attr]

# rule_engine
spec2 = importlib.util.spec_from_file_location("rule_engine", "/root/manaos_learning/rule_engine.py")
rule_engine_module = importlib.util.module_from_spec(spec2)  # type: ignore
spec2.loader.exec_module(rule_engine_module)  # type: ignore[union-attr]

# learning_control
spec3 = importlib.util.spec_from_file_location("learning_control", "/root/scripts/learning_control.py")
learning_control = importlib.util.module_from_spec(spec3)  # type: ignore
spec3.loader.exec_module(learning_control)  # type: ignore[union-attr]

get_statistics = learning_api.get_statistics
get_recent_examples = learning_api.get_recent_examples
get_pending_rules = learning_api.get_pending_rules
approve_rule = learning_api.approve_rule
reject_rule = learning_api.reject_rule
get_rule_engine = rule_engine_module.get_rule_engine
is_learning_enabled = learning_control.is_learning_enabled
get_slo_status = learning_control.get_slo_status

app = Flask(__name__)

# HTMLテンプレート
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧠 ManaOS 学習ダッシュボード</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 2.5em;
            color: #764ba2;
            margin-bottom: 10px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-card h3 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #764ba2;
            margin: 10px 0;
        }
        .stat-label {
            color: #666;
            font-size: 0.9em;
        }
        .panel {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .panel h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }
        .tool-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
        }
        .tool-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        .tool-item h4 {
            color: #333;
            margin-bottom: 8px;
        }
        .tool-stats {
            font-size: 0.9em;
            color: #666;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            margin: 5px;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: scale(1.05);
        }
        .btn-danger {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
        }
        .btn-success {
            background: linear-gradient(135deg, #28a745 0%, #218838 100%);
        }
        .pending-rule {
            background: #fff3cd;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border-left: 4px solid #ffc107;
        }
        .pending-rule h4 {
            color: #856404;
            margin-bottom: 8px;
        }
        .pending-rule .actions {
            margin-top: 10px;
        }
        .slo-status {
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
        }
        .slo-status.ok {
            background: #d4edda;
            border-left: 4px solid #28a745;
        }
        .slo-status.warning {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
        }
        .slo-status.critical {
            background: #f8d7da;
            border-left: 4px solid #dc3545;
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin: 2px;
        }
        .badge.success {
            background: #28a745;
            color: white;
        }
        .badge.warning {
            background: #ffc107;
            color: #333;
        }
        .badge.danger {
            background: #dc3545;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 ManaOS 学習ダッシュボード</h1>
            <p>まなOS全体の学習状況を可視化・制御</p>
        </div>

        <div class="stats-grid" id="statsGrid">
            <!-- 統計情報がここに表示されます -->
        </div>

        <div class="panel">
            <h2>📊 ツール別統計</h2>
            <div class="tool-list" id="toolList">
                <!-- ツールリストがここに表示されます -->
            </div>
        </div>

        <div class="panel">
            <h2>⏳ ペンディングルール（承認待ち）</h2>
            <div id="pendingRules">
                <!-- ペンディングルールがここに表示されます -->
            </div>
        </div>

        <div class="panel">
            <h2>🛡️ SLO監視</h2>
            <div id="sloStatus">
                <!-- SLO状態がここに表示されます -->
            </div>
        </div>

        <div class="panel">
            <h2>🔧 アクション</h2>
            <button class="btn" onclick="extractPatterns()">パターン自動抽出</button>
            <button class="btn" onclick="refreshData()">データ更新</button>
            <button class="btn btn-danger" onclick="disableAll()">全ツールOFF</button>
            <button class="btn btn-success" onclick="enableAll()">全ツールON</button>
        </div>
    </div>

    <script>
        async function loadData() {
            try {
                // 統計情報
                const statsRes = await fetch('/api/statistics');
                const stats = await statsRes.json();
                renderStats(stats);

                // ツール別統計
                const toolsRes = await fetch('/api/tools');
                const tools = await toolsRes.json();
                renderTools(tools);

                // ペンディングルール
                const pendingRes = await fetch('/api/pending_rules');
                const pending = await pendingRes.json();
                renderPendingRules(pending);

                // SLO状態
                const sloRes = await fetch('/api/slo_status');
                const slo = await sloRes.json();
                renderSLO(slo);
            } catch (error) {
                console.error('データ読み込みエラー:', error);
            }
        }

        function renderStats(stats) {
            const grid = document.getElementById('statsGrid');
            grid.innerHTML = `
                <div class="stat-card">
                    <h3>総ログ数</h3>
                    <div class="stat-value">${stats.total || 0}</div>
                    <div class="stat-label">全ツールの学習ログ</div>
                </div>
                <div class="stat-card">
                    <h3>修正済み</h3>
                    <div class="stat-value" style="color: #28a745;">${stats.with_correction || 0}</div>
                    <div class="stat-label">修正履歴あり</div>
                </div>
                <div class="stat-card">
                    <h3>アクティブルール</h3>
                    <div class="stat-value" style="color: #667eea;">${stats.active_rules || 0}</div>
                    <div class="stat-label">適用中ルール</div>
                </div>
                <div class="stat-card">
                    <h3>ペンディング</h3>
                    <div class="stat-value" style="color: #ffc107;">${stats.pending_rules || 0}</div>
                    <div class="stat-label">承認待ちルール</div>
                </div>
            `;
        }

        function renderTools(tools) {
            const list = document.getElementById('toolList');
            if (tools.length === 0) {
                list.innerHTML = '<p>ツールデータがありません</p>';
                return;
            }
            list.innerHTML = tools.map(tool => `
                <div class="tool-item">
                    <h4>${tool.name}</h4>
                    <div class="tool-stats">
                        総数: ${tool.total}<br>
                        修正済み: ${tool.with_correction}
                    </div>
                </div>
            `).join('');
        }

        function renderPendingRules(pending) {
            const container = document.getElementById('pendingRules');
            if (pending.length === 0) {
                container.innerHTML = '<p>ペンディングルールはありません</p>';
                return;
            }
            container.innerHTML = pending.map(rule => `
                <div class="pending-rule">
                    <h4>${rule.id}</h4>
                    <p><strong>パターン:</strong> ${rule.pattern}</p>
                    <p><strong>アクション:</strong> ${rule.action}</p>
                    <p><strong>対象ツール:</strong> ${rule.target.join(', ')}</p>
                    <p><strong>出現回数:</strong> ${rule.occurrences}</p>
                    <div class="actions">
                        <button class="btn btn-success" onclick="approveRule('${rule.id}')">承認</button>
                        <button class="btn btn-danger" onclick="rejectRule('${rule.id}')">却下</button>
                    </div>
                </div>
            `).join('');
        }

        function renderSLO(slo) {
            const container = document.getElementById('sloStatus');
            const statusClass = slo.status || 'ok';
            container.innerHTML = `
                <div class="slo-status ${statusClass}">
                    <h3>SLO状態: ${slo.status.toUpperCase()}</h3>
                    <p>最大エラー率増加: ${(slo.max_error_rate_increase * 100).toFixed(1)}%</p>
                    <p>自動停止: ${slo.auto_disable_enabled ? '有効' : '無効'}</p>
                    <p>警告モード: ${slo.warning_mode ? '有効' : '無効'}</p>
                </div>
            `;
        }

        async function approveRule(ruleId) {
            try {
                const res = await fetch(`/api/approve_rule?rule_id=${ruleId}`, { method: 'POST' });
                const result = await res.json();
                if (result.success) {
                    alert('ルールを承認しました');
                    refreshData();
                } else {
                    alert('エラー: ' + result.error);
                }
            } catch (error) {
                alert('エラー: ' + error.message);
            }
        }

        async function rejectRule(ruleId) {
            if (!confirm('このルールを却下しますか？')) return;
            try {
                const res = await fetch(`/api/reject_rule?rule_id=${ruleId}`, { method: 'POST' });
                const result = await res.json();
                if (result.success) {
                    alert('ルールを却下しました');
                    refreshData();
                } else {
                    alert('エラー: ' + result.error);
                }
            } catch (error) {
                alert('エラー: ' + error.message);
            }
        }

        async function extractPatterns() {
            const tool = prompt('ツール名を入力してください（例: pdf_excel）');
            if (!tool) return;
            try {
                const res = await fetch(`/api/extract_patterns?tool=${tool}`, { method: 'POST' });
                const result = await res.json();
                alert(`パターン抽出完了: ${result.count}個のパターンを発見`);
                refreshData();
            } catch (error) {
                alert('エラー: ' + error.message);
            }
        }

        async function disableAll() {
            if (!confirm('全ツールの学習レイヤーを無効化しますか？')) return;
            try {
                const res = await fetch('/api/disable_all', { method: 'POST' });
                const result = await res.json();
                alert('全ツールを無効化しました');
                refreshData();
            } catch (error) {
                alert('エラー: ' + error.message);
            }
        }

        async function enableAll() {
            try {
                const res = await fetch('/api/enable_all', { method: 'POST' });
                const result = await res.json();
                alert('全ツールを有効化しました');
                refreshData();
            } catch (error) {
                alert('エラー: ' + error.message);
            }
        }

        function refreshData() {
            loadData();
        }

        // 初期読み込み
        loadData();
        // 30秒ごとに自動更新
        setInterval(loadData, 30000);
    </script>
</body>
</html>
"""


@app.route('/')
def dashboard():
    """ダッシュボード表示"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/statistics')
def api_statistics():
    """統計情報API"""
    stats = get_statistics()

    # アクティブルール数
    engine = get_rule_engine()
    active_rules = engine.get_active_rules()
    stats['active_rules'] = len([r for r in active_rules if r.get('status') == 'active'])

    # ペンディングルール数
    pending_rules = get_pending_rules()
    stats['pending_rules'] = len(pending_rules)

    return jsonify(stats)


@app.route('/api/tools')
def api_tools():
    """ツール別統計API"""
    # 簡易実装：learning_log.jsonlから読み込み
    log_file = "/root/manaos_learning/learning_log.jsonl"
    tools = {}

    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    tool = rec.get("tool", "unknown")
                    if tool not in tools:
                        tools[tool] = {"total": 0, "with_correction": 0}
                    tools[tool]["total"] += 1
                    if rec.get("corrected_output"):
                        tools[tool]["with_correction"] += 1
                except:
                    continue

    tool_list = [{"name": k, **v} for k, v in tools.items()]
    return jsonify(tool_list)


@app.route('/api/pending_rules')
def api_pending_rules():
    """ペンディングルールAPI"""
    pending = get_pending_rules()
    return jsonify(pending)


@app.route('/api/approve_rule', methods=['POST'])
def api_approve_rule():
    """ルール承認API"""
    rule_id = request.args.get('rule_id')
    if not rule_id:
        return jsonify({"success": False, "error": "rule_id is required"}), 400

    success = approve_rule(rule_id)
    return jsonify({"success": success})


@app.route('/api/reject_rule', methods=['POST'])
def api_reject_rule():
    """ルール却下API"""
    rule_id = request.args.get('rule_id')
    if not rule_id:
        return jsonify({"success": False, "error": "rule_id is required"}), 400

    success = reject_rule(rule_id)
    return jsonify({"success": success})


@app.route('/api/slo_status')
def api_slo_status():
    """SLO状態API"""
    slo = get_slo_status()
    return jsonify(slo)


@app.route('/api/extract_patterns', methods=['POST'])
def api_extract_patterns():
    """パターン抽出API"""
    tool = request.args.get('tool', 'pdf_excel')

    try:
        from pattern_extractor import get_pattern_extractor
        extractor = get_pattern_extractor()
        patterns = extractor.extract_patterns_from_corrections(tool, min_occurrences=2)

        # ペンディングに追加
        added = extractor.auto_add_rules(tool, min_occurrences=2, dry_run=False)

        return jsonify({
            "tool": tool,
            "count": len(patterns),
            "added_to_pending": len(added),
            "patterns": patterns
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/disable_all', methods=['POST'])
def api_disable_all():
    """全ツール無効化API"""
    try:
        from learning_control import disable_all_learning
        disable_all_learning()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/enable_all', methods=['POST'])
def api_enable_all():
    """全ツール有効化API"""
    try:
        from learning_control import enable_all_learning
        enable_all_learning()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    import socket

    # ポート5085が使われている場合は5086を使う
    port = 5085
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()

    if result == 0:
        port = 5086
        print(f"⚠️ ポート5085は使用中のため、ポート{port}で起動します")

    print("🧠 ManaOS 学習ダッシュボード（強化版）起動中...")
    print(f"📊 http://localhost:{port} でアクセスできます")
    app.run(host='0.0.0.0', port=port, debug=False)

