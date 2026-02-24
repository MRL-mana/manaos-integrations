#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slack統合サーバー自動起動用ラッパースクリプト
環境変数を設定してからサーバーを起動
"""

import os
import sys
from pathlib import Path

try:
    from manaos_integrations._paths import FILE_SECRETARY_PORT, ORCHESTRATOR_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import FILE_SECRETARY_PORT, ORCHESTRATOR_PORT  # type: ignore
    except Exception:  # pragma: no cover
        FILE_SECRETARY_PORT = int(os.getenv("FILE_SECRETARY_PORT", "5120"))
        ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", "5106"))

os.environ['PORT'] = '5114'
os.environ['FILE_SECRETARY_URL'] = f'http://127.0.0.1:{FILE_SECRETARY_PORT}'
os.environ['ORCHESTRATOR_URL'] = f'http://127.0.0.1:{ORCHESTRATOR_PORT}'

# Slack統合サーバーを起動
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# slack_integration.pyをインポートして実行
if __name__ == '__main__':
    from slack_integration import app
    
    port = int(os.getenv("PORT", 5114))
    print(f"Slack統合サーバーを起動中... (ポート: {port})")
    print(f"Webhook URL: {'設定済み' if os.getenv('SLACK_WEBHOOK_URL') else '未設定'}")
    print(f"Bot Token: {'設定済み' if os.getenv('SLACK_BOT_TOKEN') else '未設定'}")
    print(f"Verification Token: {'設定済み' if os.getenv('SLACK_VERIFICATION_TOKEN') else '未設定'}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
