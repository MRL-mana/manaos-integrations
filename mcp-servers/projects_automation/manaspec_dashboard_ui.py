#!/usr/bin/env python3
"""
🎨 ManaSpec Dashboard UI
リアルタイム仕様管理ダッシュボード（Trinity色テーマ）
"""

import os
from flask import Flask, render_template_string, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Dashboard HTML Template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 ManaSpec Dashboard - 仕様駆動開発</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --remi-color: #FF6B9D;      /* Remi（戦略指令）ピンク */
            --luna-color: #4ECDC4;      /* Luna（実務遂行）シアン */
            --mina-color: #FFE66D;      /* Mina（洞察記録）イエロー */
            --bg-dark: #1a1a2e;
            --bg-card: #16213e;
            --text-light: #eaeaea;
            --text-dim: #b8b8b8;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: var(--text-light);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, var(--remi-color), var(--luna-color), var(--mina-color));
            padding: 40px;
            border-radius: 20px;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(255, 107, 157, 0.3);
        }
        
        .header h1 {
            font-size: 3em;
            font-weight: 700;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2em;
            margin-top: 10px;
            opacity: 0.9;
        }
        
        /* Status Bar */
        .status-bar {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .status-card {
            background: var(--bg-card);
            padding: 25px;
            border-radius: 15px;
            border-left: 5px solid;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .status-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.4);
        }
        
        .status-card.remi { border-left-color: var(--remi-color); }
        .status-card.luna { border-left-color: var(--luna-color); }
        .status-card.mina { border-left-color: var(--mina-color); }
        
        .status-card h3 {
            font-size: 1.1em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-card .value {
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .status-card.remi .value { color: var(--remi-color); }
        .status-card.luna .value { color: var(--luna-color); }
        .status-card.mina .value { color: var(--mina-color); }
        
        /* Main Grid */
        .main-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        @media (max-width: 1200px) {
            .main-grid { grid-template-columns: 1fr; }
        }
        
        /* Card */
        .card {
            background: var(--bg-card);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.3);
        }
        
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(255,255,255,0.1);
        }
        
        .card-header h2 {
            font-size: 1.5em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }
        
        .badge.proposed { background: var(--remi-color); }
        .badge.active { background: var(--luna-color); }
        .badge.completed { background: var(--mina-color); color: #333; }
        
        /* Stage Pipeline */
        .stage-pipeline {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            margin: 20px 0;
        }
        
        .stage {
            flex: 1;
            text-align: center;
            padding: 20px;
            border-radius: 10px;
            position: relative;
            transition: all 0.3s;
        }
        
        .stage:hover {
            transform: scale(1.05);
        }
        
        .stage.proposal {
            background: linear-gradient(135deg, rgba(255, 107, 157, 0.2), rgba(255, 107, 157, 0.1));
            border: 2px solid var(--remi-color);
        }
        
        .stage.apply {
            background: linear-gradient(135deg, rgba(78, 205, 196, 0.2), rgba(78, 205, 196, 0.1));
            border: 2px solid var(--luna-color);
        }
        
        .stage.archive {
            background: linear-gradient(135deg, rgba(255, 230, 109, 0.2), rgba(255, 230, 109, 0.1));
            border: 2px solid var(--mina-color);
        }
        
        .stage-icon {
            font-size: 3em;
            margin-bottom: 10px;
        }
        
        .stage-title {
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .stage-count {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .stage.proposal .stage-count { color: var(--remi-color); }
        .stage.apply .stage-count { color: var(--luna-color); }
        .stage.archive .stage-count { color: var(--mina-color); }
        
        .stage-arrow {
            font-size: 2em;
            color: var(--text-dim);
            margin: 0 10px;
        }
        
        /* Item List */
        .item-list {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .item {
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 15px;
            border-left: 4px solid;
            transition: all 0.3s;
            cursor: pointer;
        }
        
        .item:hover {
            background: rgba(255,255,255,0.1);
            transform: translateX(5px);
        }
        
        .item.proposal { border-left-color: var(--remi-color); }
        .item.spec { border-left-color: var(--luna-color); }
        .item.archive { border-left-color: var(--mina-color); }
        
        .item-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .item-title {
            font-size: 1.1em;
            font-weight: 600;
        }
        
        .item-meta {
            color: var(--text-dim);
            font-size: 0.9em;
            margin-top: 5px;
        }
        
        /* Link Buttons */
        .link-buttons {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        
        .link-btn {
            padding: 8px 16px;
            border-radius: 8px;
            border: none;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        
        .link-btn.obsidian {
            background: #7c3aed;
            color: white;
        }
        
        .link-btn.notion {
            background: white;
            color: #000;
        }
        
        .link-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        
        /* Loading */
        .loading {
            text-align: center;
            padding: 40px;
            color: var(--text-dim);
        }
        
        .spinner {
            border: 4px solid rgba(255,255,255,0.1);
            border-left-color: var(--luna-color);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Refresh Button */
        .refresh-btn {
            background: linear-gradient(135deg, var(--luna-color), var(--remi-color));
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .refresh-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 8px 25px rgba(78, 205, 196, 0.4);
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 10px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-dark);
        }
        
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, var(--remi-color), var(--luna-color));
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🎯 ManaSpec Dashboard</h1>
            <p>OPENSPEC × MRL Trinity - 仕様駆動開発の完全可視化</p>
        </div>
        
        <!-- Status Bar -->
        <div class="status-bar">
            <div class="status-card remi">
                <h3>👩‍💼 Active Changes (Remi)</h3>
                <div class="value" id="active-changes">-</div>
                <div class="item-meta">提案中の変更</div>
            </div>
            
            <div class="status-card luna">
                <h3>👩‍🔧 Total Specs (Luna)</h3>
                <div class="value" id="total-specs">-</div>
                <div class="item-meta">実装済み仕様</div>
            </div>
            
            <div class="status-card mina">
                <h3>👩‍🎓 Archives (Mina)</h3>
                <div class="value" id="total-archives">-</div>
                <div class="item-meta">学習済みパターン</div>
            </div>
            
            <div class="status-card">
                <h3>🧠 AI Learning</h3>
                <div class="value" id="total-patterns">-</div>
                <div class="item-meta">抽出されたパターン</div>
            </div>
        </div>
        
        <!-- Stage Pipeline -->
        <div class="card">
            <div class="card-header">
                <h2>📊 ワークフローステージ</h2>
                <button class="refresh-btn" onclick="refreshData()">🔄 更新</button>
            </div>
            
            <div class="stage-pipeline">
                <div class="stage proposal">
                    <div class="stage-icon">📋</div>
                    <div class="stage-title">Proposal</div>
                    <div class="stage-count" id="stage-proposal">0</div>
                    <div class="item-meta">Remi が提案生成</div>
                </div>
                
                <div class="stage-arrow">→</div>
                
                <div class="stage apply">
                    <div class="stage-icon">⚙️</div>
                    <div class="stage-title">Apply</div>
                    <div class="stage-count" id="stage-apply">0</div>
                    <div class="item-meta">Luna が実装実行</div>
                </div>
                
                <div class="stage-arrow">→</div>
                
                <div class="stage archive">
                    <div class="stage-icon">📦</div>
                    <div class="stage-title">Archive</div>
                    <div class="stage-count" id="stage-archive">0</div>
                    <div class="item-meta">Mina が学習記録</div>
                </div>
            </div>
        </div>
        
        <!-- Main Grid -->
        <div class="main-grid">
            <!-- Left Column: Changes & Specs -->
            <div>
                <!-- Active Changes -->
                <div class="card" style="margin-bottom: 30px;">
                    <div class="card-header">
                        <h2>📋 Active Changes</h2>
                        <span class="badge proposed" id="changes-badge">0</span>
                    </div>
                    <div class="item-list" id="changes-list">
                        <div class="loading">
                            <div class="spinner"></div>
                            Loading changes...
                        </div>
                    </div>
                </div>
                
                <!-- Specs -->
                <div class="card">
                    <div class="card-header">
                        <h2>📚 Specifications</h2>
                        <span class="badge active" id="specs-badge">0</span>
                    </div>
                    <div class="item-list" id="specs-list">
                        <div class="loading">
                            <div class="spinner"></div>
                            Loading specs...
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Right Column: Archives & Patterns -->
            <div>
                <!-- Recent Archives -->
                <div class="card" style="margin-bottom: 30px;">
                    <div class="card-header">
                        <h2>📦 Recent Archives</h2>
                        <span class="badge completed" id="archives-badge">0</span>
                    </div>
                    <div class="item-list" id="archives-list">
                        <div class="loading">
                            <div class="spinner"></div>
                            Loading archives...
                        </div>
                    </div>
                </div>
                
                <!-- Top Patterns -->
                <div class="card">
                    <div class="card-header">
                        <h2>🧠 Top Patterns</h2>
                    </div>
                    <div class="item-list" id="patterns-list">
                        <div class="loading">
                            <div class="spinner"></div>
                            Loading patterns...
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const API_BASE = 'http://localhost:9301/api/manaspec';
        
        // Auto-refresh every 10 seconds
        let autoRefreshInterval;
        
        async function fetchData(endpoint) {
            try {
                const response = await fetch(`${API_BASE}${endpoint}`);
                return await response.json();
            } catch (error) {
                console.error(`Error fetching ${endpoint}:`, error);
                return null;
            }
        }
        
        async function refreshData() {
            console.log('Refreshing data...');
            
            // Fetch all data
            const [status, changes, specs, archives, aiStats] = await Promise.all([
                fetchData('/status'),
                fetchData('/changes'),
                fetchData('/specs'),
                fetchData('/archives'),
                fetchData('/ai-learning/stats')
            ]);
            
            // Update status bar
            if (status) {
                document.getElementById('active-changes').textContent = status.openspec?.active_changes || 0;
                document.getElementById('total-specs').textContent = status.openspec?.total_specs || 0;
                document.getElementById('total-archives').textContent = aiStats?.total_archives || 0;
                document.getElementById('total-patterns').textContent = aiStats?.total_patterns || 0;
            }
            
            // Update stage pipeline
            if (changes) {
                document.getElementById('stage-proposal').textContent = changes.total || 0;
                document.getElementById('changes-badge').textContent = changes.total || 0;
            }
            
            if (specs) {
                document.getElementById('stage-apply').textContent = specs.total || 0;
                document.getElementById('specs-badge').textContent = specs.total || 0;
            }
            
            if (archives) {
                document.getElementById('stage-archive').textContent = archives.total || 0;
                document.getElementById('archives-badge').textContent = archives.total || 0;
            }
            
            // Render changes list
            if (changes && changes.changes) {
                const changesList = document.getElementById('changes-list');
                if (changes.changes.length === 0) {
                    changesList.innerHTML = '<div class="loading">No active changes</div>';
                } else {
                    changesList.innerHTML = changes.changes.map(change => `
                        <div class="item proposal">
                            <div class="item-header">
                                <div class="item-title">${change.id}</div>
                                <span class="badge proposed">Proposed</span>
                            </div>
                            <div class="item-meta">${change.tasks || 'No tasks info'}</div>
                            <div class="link-buttons">
                                <a href="obsidian://open?vault=ManaVault&file=specs/${change.id}" class="link-btn obsidian">
                                    📝 Obsidian
                                </a>
                                <a href="#" class="link-btn notion" onclick="alert('Notion統合は準備中')">
                                    📄 Notion
                                </a>
                            </div>
                        </div>
                    `).join('');
                }
            }
            
            // Render specs list
            if (specs && specs.specs) {
                const specsList = document.getElementById('specs-list');
                if (specs.specs.length === 0) {
                    specsList.innerHTML = '<div class="loading">No specs found</div>';
                } else {
                    specsList.innerHTML = specs.specs.map(spec => `
                        <div class="item spec">
                            <div class="item-header">
                                <div class="item-title">${spec.id}</div>
                                <span class="badge active">Active</span>
                            </div>
                            <div class="item-meta">${spec.info || ''}</div>
                            <div class="link-buttons">
                                <a href="obsidian://open?vault=ManaVault&file=specs/${spec.id}" class="link-btn obsidian">
                                    📝 Obsidian
                                </a>
                                <a href="#" class="link-btn notion" onclick="alert('Notion統合は準備中')">
                                    📄 Notion
                                </a>
                            </div>
                        </div>
                    `).join('');
                }
            }
            
            // Render archives list
            if (archives && archives.archives) {
                const archivesList = document.getElementById('archives-list');
                if (archives.archives.length === 0) {
                    archivesList.innerHTML = '<div class="loading">No archives found</div>';
                } else {
                    archivesList.innerHTML = archives.archives.slice(0, 5).map(archive => `
                        <div class="item archive">
                            <div class="item-header">
                                <div class="item-title">${archive.change_id}</div>
                                <span class="badge completed">${archive.archive_date}</span>
                            </div>
                            <div class="item-meta">${archive.proposal_preview || 'No description'}</div>
                        </div>
                    `).join('');
                }
            }
            
            // Render patterns list
            if (aiStats && aiStats.top_patterns) {
                const patternsList = document.getElementById('patterns-list');
                if (aiStats.top_patterns.length === 0) {
                    patternsList.innerHTML = '<div class="loading">No patterns found</div>';
                } else {
                    patternsList.innerHTML = aiStats.top_patterns.map(pattern => `
                        <div class="item">
                            <div class="item-header">
                                <div class="item-title">${pattern.name}</div>
                                <span class="badge" style="background: var(--mina-color); color: #333;">
                                    Used ${pattern.usage}x
                                </span>
                            </div>
                            <div class="item-meta">Type: ${pattern.type} | Success Rate: ${(pattern.success_rate * 100).toFixed(0)}%</div>
                        </div>
                    `).join('');
                }
            }
        }
        
        // Initial load
        refreshData();
        
        // Auto-refresh every 10 seconds
        autoRefreshInterval = setInterval(refreshData, 10000);
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (autoRefreshInterval) {
                clearInterval(autoRefreshInterval);
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """ManaSpec Dashboard UI"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/health')
def health():
    """Health check"""
    return jsonify({"status": "healthy", "service": "manaspec-dashboard-ui"})

if __name__ == '__main__':
    print("🎨 ManaSpec Dashboard UI starting...")
    print("🌐 Dashboard: http://localhost:9302")
    print("📊 API Backend: http://localhost:9301")
    
    app.run(host='0.0.0.0', port=9302, debug=os.getenv("DEBUG", "False").lower() == "true")

