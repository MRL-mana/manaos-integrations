#!/usr/bin/env python3
"""
X280 RDP Bridge - X280のRDP接続をブラウザ経由で操作できるようにする
"""

import os
import sys
import subprocess
import signal
import time
import logging
import atexit
from flask import Flask, render_template_string, jsonify

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# プロセス管理
processes = {
    'xvfb': None,
    'xfreerdp': None,
    'x11vnc': None,
    'websockify': None
}

DISPLAY_NUM = 99
VNC_PORT = 5902
WEBSOCKIFY_PORT = 6082
WEB_PORT = 5015  # Web UIポート
RDP_HOST = '100.127.121.20'
RDP_USER = 'mana'

def cleanup_processes():
    """全プロセスをクリーンアップ"""
    logger.info("🧹 プロセスをクリーンアップ中...")
    for name, proc in processes.items():
        if proc and proc.poll() is None:
            logger.info(f"停止中: {name}")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            processes[name] = None

def start_xvfb():
    """Xvfb（仮想ディスプレイ）を起動"""
    display = f":{DISPLAY_NUM}"
    cmd = ['Xvfb', display, '-screen', '0', '1920x1080x24', '-ac', '+extension', 'RANDR']
    logger.info(f"🚀 Xvfbを起動: DISPLAY={display}")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)  # 起動待機
    if proc.poll() is None:
        processes['xvfb'] = proc  # type: ignore
        os.environ['DISPLAY'] = display
        logger.info("✅ Xvfb起動成功")
        return True
    else:
        logger.error("❌ Xvfb起動失敗")
        return False

def start_xfreerdp():
    """xfreerdpでX280に接続"""
    display = f":{DISPLAY_NUM}"
    os.environ['DISPLAY'] = display

    # パスワードは環境変数から取得
    rdp_password = os.environ.get('X280_RDP_PASSWORD', '')
    if not rdp_password:
        logger.warning("⚠️ X280_RDP_PASSWORD環境変数が未設定です。")
        logger.info("💡 環境変数を設定するか、手動でRDP接続してください。")
        logger.info("💡 手動接続: xfreerdp /v:100.127.121.20 /u:mana /cert:ignore")
        return False

    cmd = [
        'xfreerdp',
        f'/v:{RDP_HOST}',
        f'/u:{RDP_USER}',
        f'/p:{rdp_password}',
        '/cert:ignore',
        '/sec:tls',
        '/gfx:rfx',
        '/rfx-mode:image',
        '/f',  # フルスクリーン
        '/bpp:24',
        '/dynamic-resolution',
        '+clipboard',
        '+fonts',
        '+home-drive',
        '/audio-mode:0',  # オーディオ無効化
    ]
    logger.info(f"🚀 xfreerdpを起動: {RDP_HOST}")
    # ログをファイルに出力してデバッグしやすく
    with open('/tmp/xfreerdp.log', 'a') as log_file:
        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=os.environ.copy()
        )
        time.sleep(5)  # 接続待機
        if proc.poll() is None:
            processes['xfreerdp'] = proc  # type: ignore
            logger.info("✅ xfreerdp起動成功")
            return True
        else:
            logger.warning("⚠️ xfreerdpがすぐ終了しました（パスワード確認が必要かも）")
            log_file.flush()
            with open('/tmp/xfreerdp.log', 'r') as f:
                log_lines = f.readlines()[-10:]
                if log_lines:
                    logger.warning(f"ログ: {''.join(log_lines)}")
            processes['xfreerdp'] = proc  # type: ignore
            return False

def start_x11vnc():
    """x11vncで仮想ディスプレイをVNCとして配信"""
    display = f":{DISPLAY_NUM}"
    cmd = [
        'x11vnc',
        '-display', display,
        '-rfbport', str(VNC_PORT),
        '-forever',
        '-shared',
        '-nopw',  # パスワードなし（Tailscale経由なので）
        '-xkb',
        '-noxrecord',
        '-noxfixes',
        '-noxdamage',
        '-wait', '10',
        '-defer', '10',
    ]
    logger.info(f"🚀 x11vncを起動: ポート{VNC_PORT}")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    if proc.poll() is None:
        processes['x11vnc'] = proc  # type: ignore
        logger.info("✅ x11vnc起動成功")
        return True
    else:
        logger.error("❌ x11vnc起動失敗")
        return False

def start_websockify():
    """websockifyでVNCをWebSocket経由で配信"""
    # noVNCディレクトリを確認
    novnc_paths = ['/usr/share/novnc', '/usr/share/novnc', '/opt/novnc', '/tmp/novnc_fallback']
    web_path = None
    for path in novnc_paths:
        if os.path.exists(path):
            web_path = path
            break

    cmd = ['websockify', str(WEBSOCKIFY_PORT), f'localhost:{VNC_PORT}']
    if web_path:
        cmd.extend(['--web', web_path])

    logger.info(f"🚀 websockifyを起動: ポート{WEBSOCKIFY_PORT}")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    if proc.poll() is None:
        processes['websockify'] = proc  # type: ignore
        logger.info("✅ websockify起動成功")
        return True
    else:
        logger.warning("⚠️ websockify起動失敗（VNC直接接続を使用）")
        return False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>X280 RDP Bridge</title>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255,255,255,0.1);
            padding: 30px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .status-card {
            background: rgba(255,255,255,0.15);
            padding: 20px;
            border-radius: 15px;
            border: 2px solid rgba(255,255,255,0.3);
        }
        .status-card h3 {
            margin-bottom: 10px;
            font-size: 1.2em;
        }
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            margin-top: 10px;
        }
        .status-online {
            background: #10b981;
            color: white;
        }
        .status-offline {
            background: #ef4444;
            color: white;
        }
        .btn {
            display: inline-block;
            padding: 15px 30px;
            background: #10b981;
            color: white;
            text-decoration: none;
            border-radius: 10px;
            font-weight: bold;
            margin: 10px;
            transition: all 0.3s;
        }
        .btn:hover {
            background: #059669;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        .btn-secondary {
            background: #6366f1;
        }
        .btn-secondary:hover {
            background: #4f46e5;
        }
        .access-section {
            text-align: center;
            margin: 40px 0;
            padding: 30px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
        }
        .info-box {
            background: rgba(59, 130, 246, 0.2);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            border-left: 4px solid #3b82f6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🖥️ X280 RDP Bridge</h1>

        <div class="info-box">
            <h3>📋 使い方</h3>
            <p>1. 下の「VNC Viewer で接続」ボタンをクリック</p>
            <p>2. ブラウザでX280のデスクトップが表示されます</p>
            <p>3. Affinityを起動して使用できます</p>
        </div>

        <div class="status-grid">
            <div class="status-card">
                <h3>Xvfb (仮想ディスプレイ)</h3>
                <div id="status-xvfb" class="status-badge status-online">✅ 稼働中</div>
            </div>
            <div class="status-card">
                <h3>RDP接続</h3>
                <div id="status-rdp" class="status-badge status-online">✅ 接続中</div>
            </div>
            <div class="status-card">
                <h3>VNC Server</h3>
                <div id="status-vnc" class="status-badge status-online">✅ 稼働中</div>
            </div>
            <div class="status-card">
                <h3>WebSocket</h3>
                <div id="status-ws" class="status-badge status-online">✅ 稼働中</div>
            </div>
        </div>

        <div class="access-section">
            <h2>🌐 アクセス方法</h2>
            <button onclick="showVNCViewer()" class="btn btn-secondary">
                🖥️ Cursorから直接操作（VNC Viewer起動）
            </button>
            <a href="vnc://localhost:5902" class="btn btn-secondary">
                📱 VNCクライアントで接続 (ポート5902)
            </a>
            <br><br>
            <p style="margin-top: 10px; font-size: 0.9em;">
                🌍 外部アクセス:<br>
                外部IP: <code>163.44.120.49:5902</code><br>
                Tailscale: <code>100.93.120.33:5902</code>
            </p>
        </div>

        <div id="vnc-viewer-section" style="display: none; margin: 30px 0;">
            <div style="background: rgba(0,0,0,0.8); padding: 20px; border-radius: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h2 style="margin: 0;">🖥️ VNC Viewer</h2>
                    <button onclick="hideVNCViewer()" style="padding: 10px 20px; background: #ef4444; color: white; border: none; border-radius: 5px; cursor: pointer;">
                        ✕ 閉じる
                    </button>
                </div>
                <div style="position: relative; width: 100%; padding-bottom: 56.25%; background: #000; border-radius: 10px; overflow: hidden;">
                    <iframe id="vnc-iframe" src="" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; display: none;"></iframe>
                    <div id="vnc-placeholder" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: #fff;">
                        <div style="text-align: center;">
                            <p style="font-size: 1.2em; margin-bottom: 20px;">VNC Viewer</p>
                            <p style="opacity: 0.7;">接続ボタンをクリックして開始</p>
                        </div>
                    </div>
                </div>
                <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap;">
                    <button onclick="connectVNC()" class="btn" id="connect-btn">
                        🔌 接続
                    </button>
                    <button onclick="disconnectVNC()" class="btn" id="disconnect-btn" style="background: #ef4444; display: none;">
                        ❌ 切断
                    </button>
                    <span id="vnc-status" style="padding: 10px 20px; background: rgba(255,255,255,0.2); border-radius: 5px;">
                        未接続
                    </span>
                </div>
            </div>
        </div>
    </div>

    <script>
        // VNC Viewer表示/非表示
        function showVNCViewer() {
            document.getElementById('vnc-viewer-section').style.display = 'block';
        }

        function hideVNCViewer() {
            disconnectVNC();
            document.getElementById('vnc-viewer-section').style.display = 'none';
        }

        // VNC接続（noVNCをCDNから読み込み）
        function connectVNC() {
            const statusEl = document.getElementById('vnc-status');
            const iframe = document.getElementById('vnc-iframe');
            const placeholder = document.getElementById('vnc-placeholder');

            statusEl.textContent = '接続中...';
            statusEl.style.background = 'rgba(255, 165, 0, 0.3)';

            // noVNCをCDN経由で読み込んだHTMLページを作成
            const wsPort = ${WEBSOCKIFY_PORT};
            const html = \`<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>VNC Viewer</title>
    <script src="https://cdn.jsdelivr.net/npm/@novnc/novnc@1.4.0/core/rfb.js"><\/script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { margin: 0; padding: 0; background: #000; overflow: hidden; }
        #vnc-canvas { width: 100vw; height: 100vh; display: block; }
        #status { position: absolute; top: 10px; left: 10px; color: #fff; background: rgba(0,0,0,0.7); padding: 10px; border-radius: 5px; font-family: monospace; z-index: 1000; }
    </style>
</head>
<body>
    <div id="status">接続中...</div>
    <canvas id="vnc-canvas"></canvas>
    <script>
        const canvas = document.getElementById('vnc-canvas');
        const status = document.getElementById('status');
        let rfb = null;

        try {
            rfb = new RFB(canvas, 'ws://localhost:' + wsPort, {
                credentials: { password: '' }
            });

            rfb.addEventListener("connect", () => {
                status.textContent = '✅ 接続済み';
                status.style.background = 'rgba(16, 185, 129, 0.8)';
            });

            rfb.addEventListener("disconnect", (e) => {
                status.textContent = '❌ 切断: ' + (e.detail.clean ? '正常' : 'エラー');
                status.style.background = 'rgba(239, 68, 68, 0.8)';
            });

            rfb.addEventListener("credentialsrequired", () => {
                status.textContent = '🔐 認証が必要';
            });
        } catch (error) {
            status.textContent = '❌ エラー: ' + error.message;
            status.style.background = 'rgba(239, 68, 68, 0.8)';
        }
    <\/script>
</body>
</html>\`;

            iframe.src = 'data:text/html;charset=utf-8,' + encodeURIComponent(html);
            iframe.style.display = 'block';
            placeholder.style.display = 'none';

            setTimeout(() => {
                statusEl.textContent = '✅ 接続済み（接続中...）';
                statusEl.style.background = 'rgba(16, 185, 129, 0.3)';
                document.getElementById('connect-btn').style.display = 'none';
                document.getElementById('disconnect-btn').style.display = 'inline-block';
            }, 1000);
        }

        function disconnectVNC() {
            const iframe = document.getElementById('vnc-iframe');
            const placeholder = document.getElementById('vnc-placeholder');
            const statusEl = document.getElementById('vnc-status');

            iframe.src = '';
            iframe.style.display = 'none';
            placeholder.style.display = 'flex';

            statusEl.textContent = '未接続';
            statusEl.style.background = 'rgba(255,255,255,0.2)';
            document.getElementById('connect-btn').style.display = 'inline-block';
            document.getElementById('disconnect-btn').style.display = 'none';
        }

        // ステータスを定期的に更新
        function updateStatus() {
            fetch('/api/status')
                .then(res => res.json())
                .then(data => {
                    Object.keys(data.status).forEach(key => {
                        const el = document.getElementById(`status-${key}`);
                        if (el) {
                            if (data.status[key]) {
                                el.className = 'status-badge status-online';
                                el.textContent = '✅ 稼働中';
                            } else {
                                el.className = 'status-badge status-offline';
                                el.textContent = '❌ 停止中';
                            }
                        }
                    });
                })
                .catch(err => console.error('Status update failed:', err));
        }
        setInterval(updateStatus, 5000);
        updateStatus();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def get_status():
    status = {}
    for name, proc in processes.items():
        if proc:
            status[name] = proc.poll() is None
        else:
            status[name] = False
    return jsonify({'status': status})

def initialize():
    """全サービスを初期化"""
    logger.info("🚀 X280 RDP Bridgeを初期化中...")

    # クリーンアップ関数を登録
    atexit.register(cleanup_processes)
    signal.signal(signal.SIGTERM, lambda s, f: (cleanup_processes(), sys.exit(0)))
    signal.signal(signal.SIGINT, lambda s, f: (cleanup_processes(), sys.exit(0)))

    # 順番に起動
    if not start_xvfb():
        logger.error("❌ 初期化失敗: Xvfb")
        return False

    if not start_x11vnc():
        logger.error("❌ 初期化失敗: x11vnc")
        return False

    if not start_websockify():
        logger.warning("⚠️ websockify起動失敗（VNC直接接続を使用）")

    # RDP接続は少し待ってから
    time.sleep(1)
    rdp_started = start_xfreerdp()
    if not rdp_started:
        logger.warning("⚠️ xfreerdp自動起動失敗")
        logger.info("💡 手動でRDP接続する方法:")
        logger.info(f"   export DISPLAY=:{DISPLAY_NUM}")
        logger.info(f"   xfreerdp /v:{RDP_HOST} /u:{RDP_USER} /cert:ignore")

    logger.info("✅ 初期化完了")
    return True

if __name__ == '__main__':
    if not initialize():
        logger.error("❌ 初期化に失敗しました")
        sys.exit(1)

    logger.info(f"🌐 Web UI: http://localhost:{WEB_PORT}")
    logger.info(f"🖥️ VNC: http://localhost:{WEBSOCKIFY_PORT}")
    logger.info(f"📱 VNC直接: localhost:{VNC_PORT}")
    app.run(host='0.0.0.0', port=WEB_PORT, debug=os.getenv("DEBUG", "False").lower() == "true")

