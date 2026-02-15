#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slack統合サーバーを再起動するスクリプト（環境変数込み）
"""

import os
import subprocess
import time
import httpx
from pathlib import Path

from manaos_process_manager import get_process_manager

try:
    from manaos_integrations._paths import (
        FILE_SECRETARY_PORT,
        ORCHESTRATOR_PORT,
        SLACK_INTEGRATION_PORT,
    )
except Exception:  # pragma: no cover
    try:
        from _paths import FILE_SECRETARY_PORT, ORCHESTRATOR_PORT, SLACK_INTEGRATION_PORT  # type: ignore
    except Exception:  # pragma: no cover
        FILE_SECRETARY_PORT = int(os.getenv("FILE_SECRETARY_PORT", "5120"))
        ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", "5106"))
        SLACK_INTEGRATION_PORT = int(os.getenv("SLACK_INTEGRATION_PORT", "5114"))

def load_slack_config():
    """Slack設定を読み込む"""
    # Secretsは環境変数/.env（ローカル）から供給する（ファイル走査・直書きは禁止）
    return {
        "webhook_url": os.environ.get("SLACK_WEBHOOK_URL"),
        "bot_token": os.environ.get("SLACK_BOT_TOKEN"),
        "verification_token": os.environ.get("SLACK_VERIFICATION_TOKEN"),
    }

def stop_slack_integration():
    """Slack統合サーバーを停止"""
    print("既存のSlack統合サーバーを停止中...")
    pm = get_process_manager()
    try:
        killed = pm.kill_processes_by_port(SLACK_INTEGRATION_PORT)
        if killed:
            time.sleep(2)
            print(f"  [OK] {killed} プロセスを停止しました")
        else:
            print("  [INFO] 実行中のプロセスは見つかりませんでした")
    except Exception as e:
        print(f"  [WARN] 停止エラー: {e}")

def start_slack_integration(config):
    """Slack統合サーバーを起動"""
    print("Slack統合サーバーを起動中...")
    
    # 環境変数を設定
    env = os.environ.copy()
    if config.get('webhook_url'):
        env['SLACK_WEBHOOK_URL'] = config['webhook_url']
    if config.get('bot_token'):
        env['SLACK_BOT_TOKEN'] = config['bot_token']
    if config.get('verification_token'):
        env['SLACK_VERIFICATION_TOKEN'] = config['verification_token']
    
    env['PORT'] = '5114'
    env['FILE_SECRETARY_URL'] = f'http://127.0.0.1:{FILE_SECRETARY_PORT}'
    env['ORCHESTRATOR_URL'] = f'http://127.0.0.1:{ORCHESTRATOR_PORT}'
    
    # サーバーを起動
    script_path = Path("slack_integration.py")
    if script_path.exists():
        process = subprocess.Popen(
            ["python", str(script_path)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print("  起動中...")
        time.sleep(5)
        
        # 起動確認
        try:
            base_url = f"http://127.0.0.1:{SLACK_INTEGRATION_PORT}"
            response = httpx.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    print("  [OK] サーバーが正常に起動しました")
                    
                    # 設定確認
                    test_response = httpx.get(f"{base_url}/api/slack/test", timeout=5)
                    if test_response.status_code == 200:
                        test_data = test_response.json()
                        print(f"  Webhook URL: {'設定済み' if test_data.get('slack_webhook_configured') else '未設定'}")
                        print(f"  Verification Token: {'設定済み' if test_data.get('slack_verification_token_configured') else '未設定'}")
                    return True
        except Exception as e:
            print(f"  [WARN] 起動確認エラー: {e}")
            return False
    else:
        print(f"  [ERROR] スクリプトが見つかりません: {script_path}")
        return False

def main():
    print("=" * 60)
    print("Slack統合サーバー再起動")
    print("=" * 60)
    
    # 設定を読み込み
    config = load_slack_config()
    print("\n読み込んだ設定:")
    print(f"  Webhook URL: {'設定済み' if config.get('webhook_url') else '未設定'}")
    print(f"  Bot Token: {'設定済み' if config.get('bot_token') else '未設定'}")
    print(f"  Verification Token: {'設定済み' if config.get('verification_token') else '未設定'}")
    
    # 停止
    print("\n" + "-" * 60)
    stop_slack_integration()
    
    # 起動
    print("\n" + "-" * 60)
    if start_slack_integration(config):
        print("\n" + "=" * 60)
        print("再起動完了")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("再起動に失敗しました")
        print("=" * 60)

if __name__ == "__main__":
    main()
