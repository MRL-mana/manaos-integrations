#!/usr/bin/env python3
from flask import Flask, jsonify, request
import requests
import subprocess
import json
from datetime import datetime

app = Flask(__name__)

# 設定
X280_TAILSCALE_IP = "100.127.230.67"
X280_MCP_PORT = "8421"
LOCAL_MCP_PORT = "8421"

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "server": "Integrated API Server",
        "timestamp": datetime.now().isoformat(),
        "services": ["main_server", "x280_mcp", "tailscale"]
    })

@app.route('/api/x280/status')
def x280_status():
    try:
        response = requests.get(f"http://{X280_TAILSCALE_IP}:{X280_MCP_PORT}/health", timeout=5)
        return jsonify({
            "status": "connected",
            "x280_ip": X280_TAILSCALE_IP,
            "response": response.json(),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/local/status')
def local_status():
    try:
        response = requests.get(f"http://localhost:{LOCAL_MCP_PORT}/health", timeout=5)
        return jsonify({
            "status": "connected",
            "response": response.json(),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/unified/status')
def unified_status():
    x280_status = "unknown"
    local_status = "unknown"
    
    # X280接続確認
    try:
        x280_response = requests.get(f"http://{X280_TAILSCALE_IP}:{X280_MCP_PORT}/health", timeout=5)
        x280_status = "connected" if x280_response.status_code == 200 else "error"
    except:
        x280_status = "disconnected"
    
    # ローカル接続確認
    try:
        local_response = requests.get(f"http://localhost:{LOCAL_MCP_PORT}/health", timeout=5)
        local_status = "connected" if local_response.status_code == 200 else "error"
    except:
        local_status = "disconnected"
    
    return jsonify({
        "unified_status": "healthy" if x280_status == "connected" and local_status == "connected" else "partial",
        "x280": x280_status,
        "local": local_status,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/execute/<service>', methods=['POST'])
def execute_service(service):
    data = request.get_json()
    command = data.get('command', '')
    
    if service == 'x280':
        try:
            # X280経由でコマンド実行
            ssh_command = f"ssh root@{X280_TAILSCALE_IP} '{command}'"
            result = subprocess.run(ssh_command, shell=True, capture_output=True, text=True, timeout=30)
            return jsonify({
                "status": "success",
                "output": result.stdout,
                "error": result.stderr,
                "return_code": result.returncode
            })
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500
    
    elif service == 'local':
        try:
            # ローカルでコマンド実行
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            return jsonify({
                "status": "success",
                "output": result.stdout,
                "error": result.stderr,
                "return_code": result.returncode
            })
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500
    
    else:
        return jsonify({"status": "error", "error": "Unknown service"}), 400

if __name__ == '__main__':
    print("🚀 統合APIサーバー起動中...")
    print("📡 エンドポイント:")
    print("  GET /health - ヘルスチェック")
    print("  GET /api/x280/status - X280状況")
    print("  GET /api/local/status - ローカル状況")
    print("  GET /api/unified/status - 統合状況")
    print("  POST /api/execute/x280 - X280コマンド実行")
    print("  POST /api/execute/local - ローカルコマンド実行")
    import sys
    port = 8081
    if len(sys.argv) > 1 and sys.argv[1] == '--port':
        port = int(sys.argv[2])
    app.run(host='0.0.0.0', port=port, debug=False)
