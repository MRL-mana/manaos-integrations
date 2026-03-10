#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slack統合サーバーを環境変数込みで起動
"""

import os

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
print("\nSlack統合サーバーを起動中...")
from slack_integration import app  # type: ignore[attr-defined]

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5114))
    print(f"ポート: {port}")
    print(f"Webhook URL: {'設定済み' if os.getenv('SLACK_WEBHOOK_URL') else '未設定'}")
    print(f"Bot Token: {'設定済み' if os.getenv('SLACK_BOT_TOKEN') else '未設定'}")
    print(f"Verification Token: {'設定済み' if os.getenv('SLACK_VERIFICATION_TOKEN') else '未設定'}")
    app.run(host='0.0.0.0', port=port, debug=False)
