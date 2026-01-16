#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slack統合サーバー自動起動用ラッパースクリプト
環境変数を設定してからサーバーを起動
"""

import os
import sys

os.environ['PORT'] = '5114'
os.environ['FILE_SECRETARY_URL'] = 'http://localhost:5120'
os.environ['ORCHESTRATOR_URL'] = 'http://localhost:5106'

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
