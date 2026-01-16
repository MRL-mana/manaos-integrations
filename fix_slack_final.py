#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slack統合の最終修復スクリプト
"""

import os
import subprocess
import time
import httpx
from pathlib import Path

def main():
    print("=" * 60)
    print("Slack統合の最終修復")
    print("=" * 60)
    
    # 1. すべてのSlack統合プロセスを停止
    print("\n[1/4] すべてのSlack統合プロセスを停止中...")
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
                    if "slack_integration" in proc.stdout.lower() or "python" in proc.stdout.lower():
                        print(f"  プロセス {pid} を停止中...")
                        subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                except:
                    pass
            
            time.sleep(3)
            print("  [OK] すべてのプロセスを停止しました")
        else:
            print("  [INFO] 実行中のプロセスは見つかりませんでした")
    except Exception as e:
        print(f"  [WARN] 停止エラー: {e}")
    
    # 2. 設定を読み込み（Secretsは環境変数/.env（ローカル）から供給する）
    print("\n[2/4] 環境変数から認証情報を読み込み中...")
    config = {
        "webhook_url": os.environ.get("SLACK_WEBHOOK_URL"),
        "bot_token": os.environ.get("SLACK_BOT_TOKEN"),
        "verification_token": os.environ.get("SLACK_VERIFICATION_TOKEN"),
    }
    print(f"  Webhook URL: {'✅ 設定済み' if config.get('webhook_url') else '❌ 未設定'}")
    print(f"  Bot Token: {'✅ 設定済み' if config.get('bot_token') else '❌ 未設定'}")
    print(f"  Verification Token: {'✅ 設定済み' if config.get('verification_token') else '❌ 未設定'}")
    
    # 3. 環境変数を設定してサーバーを起動
    print("\n[3/4] 環境変数を設定してサーバーを起動中...")
    
    env = os.environ.copy()
    if config.get('webhook_url'):
        env['SLACK_WEBHOOK_URL'] = config['webhook_url']
    if config.get('bot_token'):
        env['SLACK_BOT_TOKEN'] = config['bot_token']
    if config.get('verification_token'):
        env['SLACK_VERIFICATION_TOKEN'] = config['verification_token']
    
    env['PORT'] = '5114'
    env['FILE_SECRETARY_URL'] = 'http://localhost:5120'
    env['ORCHESTRATOR_URL'] = 'http://localhost:5106'
    
    # サーバーを起動
    script_path = Path("slack_integration.py")
    if script_path.exists():
        print("  サーバーを起動中...")
        process = subprocess.Popen(
            ["python", str(script_path)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        time.sleep(5)
        
        # 4. 起動確認
        print("\n[4/4] 起動確認中...")
        try:
            response = httpx.get("http://localhost:5114/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    print("  [OK] サーバーが正常に起動しました")
                    
                    # 設定確認
                    test_response = httpx.get("http://localhost:5114/api/slack/test", timeout=5)
                    if test_response.status_code == 200:
                        test_data = test_response.json()
                        print(f"\n設定確認:")
                        print(f"  Webhook URL: {'✅ 設定済み' if test_data.get('slack_webhook_configured') else '❌ 未設定'}")
                        print(f"  Verification Token: {'✅ 設定済み' if test_data.get('slack_verification_token_configured') else '❌ 未設定'}")
                        
                        if test_data.get('slack_webhook_configured') and test_data.get('slack_verification_token_configured'):
                            print("\n🎉 Slack統合が正常に動作しています！")
                        else:
                            print("\n⚠️ 一部の設定が未設定です")
                    return True
        except Exception as e:
            print(f"  [WARN] 起動確認エラー: {e}")
            return False
    else:
        print(f"  [ERROR] スクリプトが見つかりません: {script_path}")
        return False

if __name__ == "__main__":
    main()
