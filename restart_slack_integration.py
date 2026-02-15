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
    
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True
        )
        
        processes_to_kill = []
        for line in result.stdout.split('\n'):
            if ':5114' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    processes_to_kill.append(pid)
        
        if processes_to_kill:
            for pid in set(processes_to_kill):
                try:
                    proc = subprocess.run(
                        ["powershell", "-Command", f"Get-WmiObject Win32_Process -Filter 'ProcessId = {pid}' | Select-Object -ExpandProperty CommandLine"],
                        capture_output=True,
                        text=True
                    )
                    if "slack_integration" in proc.stdout.lower():
                        print(f"  プロセス {pid} を停止中...")
                        subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                except Exception:
                    pass
            
            time.sleep(2)
            print("  [OK] 停止完了")
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
    env['FILE_SECRETARY_URL'] = 'http://127.0.0.1:5120'
    env['ORCHESTRATOR_URL'] = 'http://127.0.0.1:5106'
    
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
            response = httpx.get("http://127.0.0.1:5114/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    print("  [OK] サーバーが正常に起動しました")
                    
                    # 設定確認
                    test_response = httpx.get("http://127.0.0.1:5114/api/slack/test", timeout=5)
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
