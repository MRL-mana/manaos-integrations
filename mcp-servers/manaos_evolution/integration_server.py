#!/usr/bin/env python3
"""
ManaOS統合サーバー
3つのPhaseを統合した統一インターフェース
"""

from flask import Flask, request, jsonify
import requests
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 各Phaseのエンドポイント
PHASE1_URL = os.environ.get('PHASE1_URL', 'http://localhost:5001')
PHASE2_URL = os.environ.get('PHASE2_URL', 'http://localhost:5002')
PHASE3_URL = os.environ.get('PHASE3_URL', 'http://localhost:5003')

@app.route('/')
def index():
    """統合ダッシュボード"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>ManaOS 統合ダッシュボード</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding-bottom: 40px;
            height: auto;
            min-height: auto;
        }
        h1 { color: white; text-align: center; margin-bottom: 30px; font-size: 2.5em; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .card h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.5em;
        }
        .battery-display {
            text-align: center;
            padding: 20px;
        }
        .battery-level {
            font-size: 4em;
            font-weight: bold;
            color: #667eea;
            margin: 20px 0;
        }
        .mode-badge {
            display: inline-block;
            padding: 10px 20px;
            border-radius: 25px;
            font-weight: bold;
            margin-top: 10px;
        }
        .attack-mode { background: #ff6b6b; color: white; }
        .normal-mode { background: #4ecdc4; color: white; }
        .rest-mode { background: #ffe66d; color: #333; }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            margin: 5px;
            transition: transform 0.2s;
        }
        button:hover { transform: scale(1.05); }
        input, textarea {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 8px;
            margin: 5px 0;
            font-size: 1em;
        }
        .status { padding: 10px; border-radius: 8px; margin: 10px 0; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .score-input {
            display: flex;
            gap: 10px;
            align-items: center;
            margin: 10px 0;
        }
        .score-input input {
            flex: 1;
            width: auto;
        }
        .score-input label {
            min-width: 100px;
            font-weight: bold;
        }
        #proposalResult {
            max-height: 400px;
            overflow-y: auto;
            overflow-x: hidden;
            word-wrap: break-word;
            word-break: break-all;
        }
        #proposalResult pre {
            margin: 0;
            padding: 10px;
            white-space: pre-wrap;
            word-wrap: break-word;
            word-break: break-all;
            max-width: 100%;
            overflow-x: auto;
        }
        #voiceStatus {
            max-height: 100px;
            overflow-y: auto;
        }
        body {
            overflow-x: hidden;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 ManaOS 統合ダッシュボード</h1>

        <div class="grid">
            <!-- バッテリー管理 -->
            <div class="card">
                <h2>⚡ バッテリー管理</h2>
                <div class="battery-display" id="batteryDisplay">
                    <div class="battery-level" id="batteryLevel">-</div>
                    <div id="modeDisplay">読み込み中...</div>
                </div>
                <div class="score-input">
                    <label>健康:</label>
                    <input type="number" id="healthScore" min="1" max="10" value="8">
                </div>
                <div class="score-input">
                    <label>疲労:</label>
                    <input type="number" id="fatigueScore" min="1" max="10" value="3">
                </div>
                <div class="score-input">
                    <label>やる気:</label>
                    <input type="number" id="motivationScore" min="1" max="10" value="9">
                </div>
                <button onclick="updateBattery()">バッテリー更新</button>
                <button onclick="loadBatteryStatus()">状態を読み込む</button>
            </div>

            <!-- 音声入力 -->
            <div class="card">
                <h2>🎤 音声入力</h2>
                <textarea id="voiceInput" placeholder="「メモ：明日の会議準備」のように入力..."></textarea>
                <button onclick="sendVoiceInput()">タスクを送信</button>
                <div id="voiceStatus"></div>
            </div>

            <!-- ナビAI提案 -->
            <div class="card">
                <h2>🧭 ナビAI提案</h2>
                <button onclick="getMorningProposal()">🌅 朝の提案</button>
                <button onclick="getNoonProposal()">☀️ 昼の提案</button>
                <button onclick="getNightProposal()">🌙 夜の提案</button>
                <div id="proposalResult" style="margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px;"></div>
            </div>
        </div>
    </div>

    <script>
        // バッテリー状態読み込み
        async function loadBatteryStatus() {
            try {
                const res = await fetch('{{ PHASE3_URL }}/battery/status');
                const data = await res.json();
                if (data.status === 'success') {
                    const { battery_level, mode, scores } = data.data;
                    document.getElementById('batteryLevel').textContent = battery_level;
                    const modeNames = {
                        'attack_mode': { name: '攻めモード 🔥', class: 'attack-mode' },
                        'normal_mode': { name: '通常運転 ⚡', class: 'normal-mode' },
                        'rest_mode': { name: '休息モード 🍓', class: 'rest-mode' }
                    };
                    const modeInfo = modeNames[mode.mode] || { name: mode.name, class: 'normal-mode' };
                    document.getElementById('modeDisplay').innerHTML =
                        `<span class="mode-badge ${modeInfo.class}">${modeInfo.name}</span>`;
                    document.getElementById('healthScore').value = scores.health;
                    document.getElementById('fatigueScore').value = scores.fatigue;
                    document.getElementById('motivationScore').value = scores.motivation;
                }
            } catch (e) {
                console.error(e);
            }
        }

        // バッテリー更新
        async function updateBattery() {
            const health = document.getElementById('healthScore').value;
            const fatigue = document.getElementById('fatigueScore').value;
            const motivation = document.getElementById('motivationScore').value;

            try {
                const res = await fetch('{{ PHASE3_URL }}/battery/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ health, fatigue, motivation })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    loadBatteryStatus();
                    document.getElementById('voiceStatus').innerHTML =
                        '<div class="status success">バッテリー更新成功！</div>';
                }
            } catch (e) {
                document.getElementById('voiceStatus').innerHTML =
                    '<div class="status error">エラー: ' + e.message + '</div>';
            }
        }

        // 音声入力送信
        async function sendVoiceInput() {
            const text = document.getElementById('voiceInput').value;
            if (!text) return;

            try {
                const res = await fetch('{{ PHASE1_URL }}/webhook/voice-input', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, user_id: 'mana', source: 'web' })
                });
                const data = await res.json();
                document.getElementById('voiceStatus').innerHTML =
                    '<div class="status success">送信完了: ' + text + '</div>';
                document.getElementById('voiceInput').value = '';
            } catch (e) {
                document.getElementById('voiceStatus').innerHTML =
                    '<div class="status error">エラー: ' + e.message + '</div>';
            }
        }

        // ナビAI提案
        async function getMorningProposal() {
            document.getElementById('proposalResult').innerHTML = '提案を生成中...';
            try {
                const res = await fetch('{{ PHASE2_URL }}/propose/morning', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        calendar_events: '今日の予定なし',
                        pending_tasks: 'タスク1, タスク2',
                        battery_level: 8,
                        yesterday_completed: '3タスク完了'
                    })
                });
                const data = await res.json();
                const jsonStr = JSON.stringify(data, null, 2);
                document.getElementById('proposalResult').innerHTML =
                    '<pre style="max-height: 350px; overflow-y: auto;">' + jsonStr + '</pre>';
            } catch (e) {
                document.getElementById('proposalResult').innerHTML =
                    '<div class="status error">エラー: ' + e.message + '</div>';
            }
        }

        async function getNoonProposal() {
            document.getElementById('proposalResult').innerHTML = '提案を生成中...';
            try {
                const res = await fetch('{{ PHASE2_URL }}/propose/noon', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        morning_progress: '2タスク完了',
                        current_battery: 7,
                        remaining_tasks: 'タスク3, タスク4',
                        next_event: 'なし'
                    })
                });
                const data = await res.json();
                const jsonStr = JSON.stringify(data, null, 2);
                document.getElementById('proposalResult').innerHTML =
                    '<pre style="max-height: 350px; overflow-y: auto;">' + jsonStr + '</pre>';
            } catch (e) {
                document.getElementById('proposalResult').innerHTML =
                    '<div class="status error">エラー: ' + e.message + '</div>';
            }
        }

        async function getNightProposal() {
            document.getElementById('proposalResult').innerHTML = '提案を生成中...';
            try {
                const res = await fetch('{{ PHASE2_URL }}/propose/night', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        today_completed: '5タスク完了',
                        battery_consumption: '7.5',
                        emotion_score: 8,
                        incomplete_tasks: '1タスク残り'
                    })
                });
                const data = await res.json();
                const jsonStr = JSON.stringify(data, null, 2);
                document.getElementById('proposalResult').innerHTML =
                    '<pre style="max-height: 350px; overflow-y: auto;">' + jsonStr + '</pre>';
            } catch (e) {
                document.getElementById('proposalResult').innerHTML =
                    '<div class="status error">エラー: ' + e.message + '</div>';
            }
        }

        // 初期読み込み
        window.onload = () => {
            loadBatteryStatus();
            setInterval(loadBatteryStatus, 30000); // 30秒ごとに更新
        };
    </script>
</body>
</html>
    """
    html = html.replace('{{ PHASE1_URL }}', PHASE1_URL)
    html = html.replace('{{ PHASE2_URL }}', PHASE2_URL)
    html = html.replace('{{ PHASE3_URL }}', PHASE3_URL)
    return html

@app.route('/api/voice', methods=['POST'])
def voice_api():
    """音声入力API（統合）"""
    data = request.get_json()
    try:
        res = requests.post(f'{PHASE1_URL}/webhook/voice-input', json=data, timeout=5)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/battery/status', methods=['GET'])
def battery_status_api():
    """バッテリー状態API（統合）"""
    try:
        res = requests.get(f'{PHASE3_URL}/battery/status', timeout=5)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/navi/propose/<time_of_day>', methods=['POST'])
def navi_propose_api(time_of_day):
    """ナビAI提案API（統合）"""
    data = request.get_json()
    try:
        res = requests.post(f'{PHASE2_URL}/propose/{time_of_day}', json=data, timeout=10)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    status = {}
    for phase, url in [('phase1', PHASE1_URL), ('phase2', PHASE2_URL), ('phase3', PHASE3_URL)]:
        try:
            res = requests.get(f'{url}/health', timeout=2)
            status[phase] = 'healthy' if res.status_code == 200 else 'unhealthy'
        except requests.RequestException:
            status[phase] = 'unreachable'

    return jsonify({
        'status': 'healthy' if all(s == 'healthy' for s in status.values()) else 'degraded',
        'phases': status
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting ManaOS Integration Server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
