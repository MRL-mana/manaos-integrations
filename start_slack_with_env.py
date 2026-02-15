#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slack統合サーバーを環境変数込みで起動
"""

import os

os.environ['PORT'] = '5114'
os.environ['FILE_SECRETARY_URL'] = 'http://127.0.0.1:5120'
os.environ['ORCHESTRATOR_URL'] = 'http://127.0.0.1:5106'

# Slack統合サーバーを起動
print("\nSlack統合サーバーを起動中...")
from slack_integration import app

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5114))
    print(f"ポート: {port}")
    print(f"Webhook URL: {'設定済み' if os.getenv('SLACK_WEBHOOK_URL') else '未設定'}")
    print(f"Bot Token: {'設定済み' if os.getenv('SLACK_BOT_TOKEN') else '未設定'}")
    print(f"Verification Token: {'設定済み' if os.getenv('SLACK_VERIFICATION_TOKEN') else '未設定'}")
    app.run(host='0.0.0.0', port=port, debug=False)
