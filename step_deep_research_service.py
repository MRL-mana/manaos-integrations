#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step-Deep-Research ManaOSサービス
ポート5121でAPIサーバーとして起動
"""

import json
import sys
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

from step_deep_research.api_server import init_orchestrator, app

# 設定読み込み
config_path = Path("step_deep_research_config.json")
if not config_path.exists():
    print(f"❌ 設定ファイルが見つかりません: {config_path}")
    sys.exit(1)

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

# ポート設定
PORT = 5121
SERVICE_NAME = config.get("service_name", "Step Deep Research")

# オーケストレーター初期化
orchestrator = init_orchestrator()

if __name__ == '__main__':
    print(f"🚀 {SERVICE_NAME} 起動中...")
    print(f"   ポート: {PORT}")
    print(f"   URL: http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)



