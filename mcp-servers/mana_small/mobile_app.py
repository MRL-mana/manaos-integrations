#!/usr/bin/env python3
"""
スマホUI: Web App + ショートカット
"""
import logging
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

# ログ設定
log_dir = Path("/root/logs/mobile_ui")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "mobile_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="ManaOS Mobile UI",
    version="1.0.0",
    description="スマホUI: Web App + ショートカット"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 設定 =====


class Config:
    """設定"""
    PORT = int(os.getenv("MOBILE_UI_PORT", "5022"))
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost")


# ===== UI =====
@app.get("/", response_class=HTMLResponse)
async def mobile_ui():
    """モバイルUI"""
    html_content = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#667eea">
    <title>ManaOS</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            min-height: 100vh;
            overflow-x: hidden;
        }
        .container {
            max-width: 100%;
            width: 100%;
        }
        h1 {
            text-align: center;
            font-size: 2em;
            margin-bottom: 30px;
        }
        .shortcuts {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }
        .shortcut-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        .shortcut-card:active {
            transform: scale(0.95);
        }
        .shortcut-icon {
            font-size: 3em;
            margin-bottom: 10px;
        }
        .shortcut-title {
            font-size: 1.2em;
            font-weight: bold;
        }
        .status {
            background: rgba(0, 0, 0, 0.3);
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
        }
        .input-group {
            margin-bottom: 20px;
        }
        input[type="text"] {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-size: 1.1em;
            background: rgba(255, 255, 255, 0.2);
            color: white;
        }
        input[type="text"]::placeholder {
            color: rgba(255, 255, 255, 0.7);
        }
        button {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-size: 1.1em;
            background: #4285F4;
            color: white;
            cursor: pointer;
            margin-top: 10px;
        }
        button:active {
            transform: scale(0.98);
        }
        .mode-btn {
            padding: 10px 20px;
            font-size: 0.9em;
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid rgba(255, 255, 255, 0.3);
        }
        .mode-btn.active {
            background: rgba(255, 255, 255, 0.4);
            border-color: rgba(255, 255, 255, 0.6);
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 ManaOS</h1>

        <!-- モード表示・切り替え -->
        <div class="mode-section" id="modeSection" style="background: rgba(0, 0, 0, 0.3); padding: 15px; border-radius: 10px; margin-bottom: 20px; text-align: center;">
            <div style="margin-bottom: 10px;">
                <span id="currentModeName">読み込み中...</span>
            </div>
            <div style="display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
                <button onclick="switchMode('work')" class="mode-btn" id="btn-work">🔸 Work</button>
                <button onclick="switchMode('creative')" class="mode-btn" id="btn-creative">🔸 Creative</button>
                <button onclick="switchMode('autopilot')" class="mode-btn" id="btn-autopilot">🔸 Auto-Pilot</button>
            </div>
        </div>

        <div class="shortcuts" id="shortcutsContainer">
            <!-- ショートカットはJavaScriptで動的に生成 -->
        </div>

        <div class="input-group">
            <input type="text" id="quickInput" placeholder="クイックアクション...">
            <button onclick="quickAction()">実行</button>
        </div>

        <div class="status" id="status">
            準備完了
        </div>
    </div>

    <script>
        const API_BASE = 'http://localhost';
        const MOBILE_UI_PORT = 5022;
        const SERVICES = {
            openwebui: { port: 3012, name: 'Open WebUI' },
            voice: { port: 5014, name: 'Voice Stream' },
            trinity: { port: 5015, name: 'Trinity Agent' },
            vtuber: { port: 5020, name: 'VTuber Remi' },
            flux: { port: 5017, name: 'Flux ControlNet' },
            audit: { port: 5021, name: 'Audit Log' },
            trend: { port: 5034, name: 'Trend Crawler' },
            memory: { port: 5030, name: 'Memory Graph' },
            intent: { port: 5031, name: 'Intent Predictor' },
            incident: { port: 5032, name: 'Incident Orchestrator' },
            publisher: { port: 5033, name: 'Auto Publisher' },
            template: { port: 5035, name: 'Template Store' }
        };

        function openService(serviceId) {
            const service = SERVICES[serviceId];
            if (service) {
                const url = `${API_BASE}:${service.port}`;
                updateStatus(`🔗 ${service.name}を開いています...`);
                window.open(url, '_blank');
            }
        }

        async function quickAction(text) {
            // 引数がなければ入力欄から取得
            if (!text) {
                text = document.getElementById('quickInput').value;
            }
            if (!text) return;

            updateStatus('⏳ 処理中...');

            try {
                // プリセット処理
                if (text === '今日のやること3つ出して') {
                    const response = await fetch(`${API_BASE}:5015/task`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            description: '今日のやること3つをリストアップして',
                            use_langgraph: false
                        })
                    });
                    const data = await response.json();
                    updateStatus(`✅ 完了: ${data.result || '処理完了'}`);
                } else if (text === 'チラシ案作って') {
                    const response = await fetch(`${API_BASE}:5017/generate`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            prompt: '洗車キャンペーンのチラシデザイン',
                            style: 'marketing'
                        })
                    });
                    const data = await response.json();
                    updateStatus(`✅ チラシ案生成完了`);
                } else if (text === '日報まとめ') {
                    const response = await fetch(`${API_BASE}:5015/task`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            description: '今日の作業内容を日報形式でまとめて',
                            use_langgraph: false
                        })
                    });
                    const data = await response.json();
                    updateStatus(`✅ 日報まとめ完了`);
                } else {
                    // 通常のTrinity API経由で実行
                    const response = await fetch(`${API_BASE}:5015/task`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            description: text,
                            use_langgraph: false
                        })
                    });
                    const data = await response.json();
                    updateStatus(`✅ 完了: ${data.result || '処理完了'}`);
                }
            } catch (error) {
                updateStatus(`❌ エラー: ${error.message}`);
            }
        }

        async function toggleVoice() {
            try {
                const response = await fetch(`${API_BASE}:5019/toggle`, {
                    method: 'POST'
                });
                const data = await response.json();
                updateStatus(`✅ 音声: ${data.enabled ? 'ON' : 'OFF'}`);
            } catch (error) {
                updateStatus(`❌ エラー: ${error.message}`);
            }
        }

        function updateStatus(message) {
            document.getElementById('status').textContent = message;
        }

        // キーボードショートカット
        document.getElementById('quickInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                quickAction();
            }
        });

        // モード別ショートカット定義
        const MODE_SHORTCUTS = {
            work: [
                { icon: '📋', title: '今日のやること', action: () => quickAction('今日のやること3つ出して'), priority: 'high' },
                { icon: '📝', title: '日報', action: () => quickAction('日報まとめ'), priority: 'high' },
                { icon: '📄', title: 'チラシ案', action: () => quickAction('チラシ案作って'), priority: 'high' },
                { icon: '💬', title: 'Open WebUI', action: () => openService('openwebui'), priority: 'medium' },
                { icon: '🎤', title: 'Voice Stream', action: () => openService('voice'), priority: 'medium' },
                { icon: '🤖', title: 'Trinity Agent', action: () => openService('trinity'), priority: 'medium' },
                { icon: '📊', title: 'Audit Log', action: () => openService('audit'), priority: 'medium' },
                { icon: '📰', title: 'Trend Crawler', action: () => openService('trend'), priority: 'low' },
                { icon: '🧠', title: 'Memory Graph', action: () => openService('memory'), priority: 'low' },
                { icon: '🎯', title: 'Intent Predictor', action: () => openService('intent'), priority: 'low' }
            ],
            creative: [
                { icon: '🎨', title: 'Flux ControlNet', action: () => openService('flux'), priority: 'high' },
                { icon: '🎭', title: 'VTuber Remi', action: () => openService('vtuber'), priority: 'high' },
                { icon: '🚀', title: 'Auto Publisher', action: () => openService('publisher'), priority: 'high' },
                { icon: '📋', title: 'Template Store', action: () => openService('template'), priority: 'high' },
                { icon: '🎤', title: 'Voice Stream', action: () => openService('voice'), priority: 'high' },
                { icon: '🤖', title: 'Trinity Agent', action: () => openService('trinity'), priority: 'medium' },
                { icon: '📱', title: 'Mobile UI', action: () => {}, priority: 'medium' },
                { icon: '🎯', title: 'Intent Predictor', action: () => openService('intent'), priority: 'medium' }
            ],
            autopilot: [
                { icon: '🛡️', title: 'Incident', action: () => openService('incident'), priority: 'high' },
                { icon: '📊', title: 'Audit Log', action: () => openService('audit'), priority: 'high' },
                { icon: '🧠', title: 'Memory Graph', action: () => openService('memory'), priority: 'high' },
                { icon: '🎯', title: 'Intent Predictor', action: () => openService('intent'), priority: 'high' },
                { icon: '📰', title: 'Trend Crawler', action: () => openService('trend'), priority: 'medium' },
                { icon: '📱', title: 'Mobile UI', action: () => {}, priority: 'medium' }
            ],
            default: [
                { icon: '💬', title: 'Open WebUI', action: () => openService('openwebui'), priority: 'high' },
                { icon: '🎤', title: 'Voice Stream', action: () => openService('voice'), priority: 'high' },
                { icon: '🤖', title: 'Trinity Agent', action: () => openService('trinity'), priority: 'high' },
                { icon: '🎨', title: 'Flux ControlNet', action: () => openService('flux'), priority: 'medium' },
                { icon: '🎭', title: 'VTuber Remi', action: () => openService('vtuber'), priority: 'medium' },
                { icon: '📊', title: 'Audit Log', action: () => openService('audit'), priority: 'medium' }
            ]
        };

        // ショートカットを描画
        function renderShortcuts(mode) {
            const container = document.getElementById('shortcutsContainer');
            const shortcuts = MODE_SHORTCUTS[mode] || MODE_SHORTCUTS.default;

            // 優先度順にソート（high > medium > low）
            const priorityOrder = { high: 0, medium: 1, low: 2 };
            shortcuts.sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);

            container.innerHTML = shortcuts.map((shortcut, index) => {
                // アクションをデータ属性に保存して、クリック時に実行
                const actionId = `action_${index}`;
                // グローバルスコープにアクションを保存
                window[actionId] = shortcut.action;
                return `
                <div class="shortcut-card" onclick="window['${actionId}']()">
                    <div class="shortcut-icon">${shortcut.icon}</div>
                    <div class="shortcut-title">${shortcut.title}</div>
                </div>
            `;
            }).join('');
        }

        // モード管理
        async function loadCurrentMode() {
            try {
                const response = await fetch(`${API_BASE}:${MOBILE_UI_PORT}/api/mode`);
                const data = await response.json();
                document.getElementById('currentModeName').textContent = `現在: ${data.name} - ${data.description}`;

                // ボタンのアクティブ状態を更新
                document.querySelectorAll('.mode-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                if (data.mode) {
                    const activeBtn = document.getElementById(`btn-${data.mode}`);
                    if (activeBtn) activeBtn.classList.add('active');
                    // ショートカットを描画
                    renderShortcuts(data.mode);
                } else {
                    renderShortcuts('default');
                }
            } catch (error) {
                updateStatus(`❌ モード取得エラー: ${error.message}`);
                renderShortcuts('default');
            }
        }

        async function switchMode(modeName) {
            updateStatus(`⏳ ${modeName}モードに切り替え中...`);
            try {
                const response = await fetch(`${API_BASE}:${MOBILE_UI_PORT}/api/mode/${modeName}`, {
                    method: 'POST'
                });
                const data = await response.json();
                if (data.success) {
                    updateStatus(`✅ ${data.message}`);
                    // モード表示を更新（ショートカットも自動更新される）
                    await loadCurrentMode();
                } else {
                    updateStatus(`❌ モード切り替え失敗: ${data.message}`);
                }
            } catch (error) {
                updateStatus(`❌ エラー: ${error.message}`);
            }
        }

        // ページ読み込み時に現在のモードを取得
        window.addEventListener('load', () => {
            loadCurrentMode();
            // 定期的にモードを更新（5秒ごと）
            setInterval(loadCurrentMode, 5000);
        });
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/mode")
async def get_current_mode():
    """現在のモードを取得"""
    mode_file = Path("/root/.manaos_current_mode")
    if mode_file.exists():
        current_mode = mode_file.read_text().strip()
        mode_names = {
            "work": "Workモード",
            "creative": "Creativeモード",
            "autopilot": "Auto-Pilotモード"
        }
        return {
            "mode": current_mode,
            "name": mode_names.get(current_mode, "未設定"),
            "description": get_mode_description(current_mode)
        }
    return {
        "mode": None,
        "name": "未設定",
        "description": "モードが設定されていません"
    }


@app.post("/api/mode/{mode_name}")
async def switch_mode(mode_name: str):
    """モードを切り替え"""
    valid_modes = ["work", "creative", "autopilot"]
    if mode_name not in valid_modes:
        raise HTTPException(status_code=400, detail=f"無効なモード: {mode_name}")

    script_path = Path(f"/root/scripts/enable_{mode_name}_mode.sh")
    if not script_path.exists():
        raise HTTPException(
            status_code=404, detail=f"モード切り替えスクリプトが見つかりません: {script_path}")

    try:
        # モード切り替えスクリプトを実行
        result = subprocess.run(
            ["bash", str(script_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            return {
                "success": True,
                "mode": mode_name,
                "message": f"{mode_name}モードに切り替えました",
                "output": result.stdout
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"モード切り替えに失敗: {result.stderr}"
            )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="モード切り替えがタイムアウトしました")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エラー: {str(e)}")


def get_mode_description(mode: str) -> str:
    """モードの説明を取得"""
    descriptions = {
        "work": "「考える前に、やること出てる」状態",
        "creative": "「思いついた瞬間、そのまま世界に出せる」",
        "autopilot": "「トラブルがあったことすら、後からレポートで知る」"
    }
    return descriptions.get(mode, "")


@app.on_event("startup")
async def startup():
    """起動時の初期化"""
    logger.info("🚀 Mobile UI 起動中...")
    logger.info(f"📊 ポート: {Config.PORT}")
    logger.info("✅ サーバー準備完了")


@app.on_event("shutdown")
async def shutdown():
    """シャットダウン時のクリーンアップ"""
    logger.info("🛑 Mobile UI シャットダウン中...")


if __name__ == "__main__":
    from datetime import datetime
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=Config.PORT,
        log_level="info"
    )
