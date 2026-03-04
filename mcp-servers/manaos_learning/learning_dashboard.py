#!/usr/bin/env python3
"""
ManaOS 学習ダッシュボード
学習状況を可視化するWeb UI
"""

from flask import Flask, render_template_string, jsonify, request
from datetime import datetime, timedelta
import json

from .learning_log import get_learning_log
from .rule_engine import get_rule_engine
from .pattern_extractor import get_pattern_extractor

app = Flask(__name__)

# HTMLテンプレート
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ManaOS 学習ダッシュボード</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
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
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
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
            font-size: 1.2em;
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
        .recent-logs {
            max-height: 400px;
            overflow-y: auto;
        }
        .log-item {
            background: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .log-item.bad {
            border-left-color: #dc3545;
        }
        .log-item.good {
            border-left-color: #28a745;
        }
        .log-item.needs_review {
            border-left-color: #ffc107;
        }
        .log-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        .log-tool {
            font-weight: bold;
            color: #667eea;
        }
        .log-time {
            color: #666;
            font-size: 0.9em;
        }
        .log-content {
            color: #333;
            font-size: 0.95em;
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin: 2px;
        }
        .badge.good {
            background: #28a745;
            color: white;
        }
        .badge.bad {
            background: #dc3545;
            color: white;
        }
        .badge.needs_review {
            background: #ffc107;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 ManaOS 学習ダッシュボード</h1>
            <p>まなOS全体の学習状況を可視化</p>
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
            <h2>📝 最近の学習ログ</h2>
            <div class="recent-logs" id="recentLogs">
                <!-- 最近のログがここに表示されます -->
            </div>
        </div>

        <div class="panel">
            <h2>🔧 アクション</h2>
            <button class="btn" onclick="extractPatterns()">パターン自動抽出</button>
            <button class="btn" onclick="refreshData()">データ更新</button>
        </div>
    </div>

    <script>
        async function loadData() {
            try {
                // 統計情報を取得
                const statsRes = await fetch('/api/statistics');
                const stats = await statsRes.json();
                renderStats(stats);

                // ツール別統計を取得
                const toolsRes = await fetch('/api/tools');
                const tools = await toolsRes.json();
                renderTools(tools);

                // 最近のログを取得
                const logsRes = await fetch('/api/recent_logs?limit=20');
                const logs = await logsRes.json();
                renderLogs(logs);
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
                    <h3>成功</h3>
                    <div class="stat-value" style="color: #28a745;">${stats.good || 0}</div>
                    <div class="stat-label">良好な結果</div>
                </div>
                <div class="stat-card">
                    <h3>失敗</h3>
                    <div class="stat-value" style="color: #dc3545;">${stats.bad || 0}</div>
                    <div class="stat-label">改善が必要</div>
                </div>
                <div class="stat-card">
                    <h3>要レビュー</h3>
                    <div class="stat-value" style="color: #ffc107;">${stats.needs_review || 0}</div>
                    <div class="stat-label">確認待ち</div>
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
                        成功: ${tool.good} | 失敗: ${tool.bad}
                    </div>
                </div>
            `).join('');
        }

        function renderLogs(logs) {
            const container = document.getElementById('recentLogs');
            if (logs.length === 0) {
                container.innerHTML = '<p>ログがありません</p>';
                return;
            }
            container.innerHTML = logs.map(log => `
                <div class="log-item ${log.feedback}">
                    <div class="log-header">
                        <span class="log-tool">${log.tool}</span>
                        <span class="log-time">${log.timestamp}</span>
                    </div>
                    <div class="log-content">
                        <strong>修正前:</strong> ${log.raw_output.substring(0, 100)}...<br>
                        <strong>修正後:</strong> ${log.corrected_output.substring(0, 100)}...
                    </div>
                    <div>
                        <span class="badge ${log.feedback}">${log.feedback}</span>
                        ${log.tags.map(tag => `<span class="badge">${tag}</span>`).join('')}
                    </div>
                </div>
            `).join('');
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
    log = get_learning_log()
    stats = log.get_statistics()
    return jsonify(stats)


@app.route('/api/tools')
def api_tools():
    """ツール別統計API"""
    log = get_learning_log()

    # 全ツールのリストを取得（簡易実装）
    conn = log.db_path
    import sqlite3
    conn = sqlite3.connect(log.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT tool FROM learning_log")
    tools = [row[0] for row in cursor.fetchall()]
    conn.close()

    tool_stats = []
    for tool in tools:
        stats = log.get_statistics(tool=tool)
        tool_stats.append({
            "name": tool,
            "total": stats["total"],
            "good": stats["good"],
            "bad": stats["bad"],
            "needs_review": stats["needs_review"]
        })

    return jsonify(tool_stats)


@app.route('/api/recent_logs')
def api_recent_logs():
    """最近のログAPI"""
    limit = request.args.get('limit', 20, type=int)
    log = get_learning_log()

    import sqlite3
    conn = sqlite3.connect(log.db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tool, input, raw_output, corrected_output, feedback, tags, timestamp
        FROM learning_log
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    logs = []
    for row in cursor.fetchall():
        logs.append({
            "tool": row[0],
            "input": row[1][:200] if row[1] else "",
            "raw_output": row[2][:200] if row[2] else "",
            "corrected_output": row[3][:200] if row[3] else "",
            "feedback": row[4],
            "tags": json.loads(row[5]) if row[5] else [],
            "timestamp": row[6]
        })

    conn.close()
    return jsonify(logs)


@app.route('/api/extract_patterns', methods=['POST'])
def api_extract_patterns():
    """パターン抽出API"""
    tool = request.args.get('tool', 'pdf_excel')
    extractor = get_pattern_extractor()

    patterns = extractor.extract_patterns_from_corrections(tool, min_occurrences=2)

    return jsonify({
        "tool": tool,
        "count": len(patterns),
        "patterns": patterns
    })


if __name__ == '__main__':
    print("🧠 ManaOS 学習ダッシュボード起動中...")
    print("📊 http://localhost:5085 でアクセスできます")
    app.run(host='0.0.0.0', port=5085, debug=False)









