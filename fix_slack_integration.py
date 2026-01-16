#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slack統合の修復スクリプト
"""

import os
import httpx
import subprocess
import time
from pathlib import Path

def main():
    print("=" * 60)
    print("Slack統合の修復")
    print("=" * 60)
    
    # 1. 環境変数から認証情報を読み込み
    print("\n[1/5] 環境変数から認証情報を読み込み中...")
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    verification_token = os.environ.get("SLACK_VERIFICATION_TOKEN")

    print(f"  Webhook URL: {'設定済み' if webhook_url else '未設定'}")
    print(f"  Bot Token: {'設定済み' if bot_token else '未設定'}")
    print(f"  Verification Token: {'設定済み' if verification_token else '未設定'}")

    # 2. 環境変数を設定（値の直書き/ファイル走査はしない）
    print("\n[2/5] 環境変数を設定中...")
    
    if webhook_url:
        os.environ["SLACK_WEBHOOK_URL"] = webhook_url
        print("  [OK] SLACK_WEBHOOK_URL: 設定済み")
    else:
        print("  [WARN] SLACK_WEBHOOK_URL: 未設定")
    
    if bot_token:
        os.environ["SLACK_BOT_TOKEN"] = bot_token
        print("  [OK] SLACK_BOT_TOKEN: 設定済み")
    else:
        print("  [WARN] SLACK_BOT_TOKEN: 未設定")
    
    if verification_token:
        os.environ["SLACK_VERIFICATION_TOKEN"] = verification_token
        print("  [OK] SLACK_VERIFICATION_TOKEN: 設定済み")
    else:
        print("  [WARN] SLACK_VERIFICATION_TOKEN: 未設定")
    
    # その他の必要な環境変数
    os.environ["PORT"] = "5114"
    os.environ["FILE_SECRETARY_URL"] = "http://localhost:5120"
    os.environ["ORCHESTRATOR_URL"] = "http://localhost:5106"
    
    # 4. 既存のSlack統合サーバーを停止
    print("\n[4/5] 既存のSlack統合サーバーを停止中...")
    
    try:
        # Windows環境でポート5114を使用しているプロセスを確認
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
                    # プロセスがslack_integration.pyか確認
                    proc = subprocess.run(
                        ["powershell", "-Command", f"Get-WmiObject Win32_Process -Filter 'ProcessId = {pid}' | Select-Object -ExpandProperty CommandLine"],
                        capture_output=True,
                        text=True
                    )
                    if "slack_integration" in proc.stdout.lower():
                        print(f"  [INFO] プロセス {pid} を停止中...")
                        subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                except Exception as e:
                    print(f"  [WARN] プロセス {pid} の停止に失敗: {e}")
            
            time.sleep(2)
            print("  [OK] 既存のプロセスを停止しました")
        else:
            print("  [INFO] 実行中のプロセスは見つかりませんでした")
    except Exception as e:
        print(f"  [WARN] プロセス確認エラー: {e}")
    
    # 5. Slack統合サーバーを起動
    print("\n[5/5] Slack統合サーバーを起動中...")
    
    script_path = Path("slack_integration.py")
    if script_path.exists():
        # バックグラウンドで起動
        print("  [INFO] サーバーを起動中...")
        process = subprocess.Popen(
            ["python", str(script_path)],
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        time.sleep(3)
        
        # 起動確認
        try:
            response = httpx.get("http://localhost:5114/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    print("  [OK] Slack統合サーバーが正常に起動しました")
                    print("  URL: http://localhost:5114")
        except Exception as e:
            print(f"  [WARN] 起動確認に失敗しました（起動中かもしれません）: {e}")
            print("  数秒後に再度確認してください: curl http://localhost:5114/health")
    else:
        print(f"  [ERROR] スクリプトが見つかりません: {script_path}")
        return
    
    # 6. テスト
    print("\n[6/6] 接続テスト中...")
    try:
        response = httpx.get("http://localhost:5114/api/slack/test", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("  [OK] 接続テスト成功")
            print(f"  Orchestrator URL: {data.get('orchestrator_url')}")
            print(f"  Webhook URL設定: {data.get('slack_webhook_configured')}")
            print(f"  Verification Token設定: {data.get('slack_verification_token_configured')}")
    except Exception as e:
        print(f"  [WARN] 接続テストに失敗しました: {e}")
    
    print("\n" + "=" * 60)
    print("修復完了")
    print("=" * 60)
    
    print("\n設定された環境変数:")
    print(f"  SLACK_WEBHOOK_URL: {'設定済み' if webhook_url else '未設定'}")
    print(f"  SLACK_BOT_TOKEN: {'設定済み' if bot_token else '未設定'}")
    print(f"  SLACK_VERIFICATION_TOKEN: {'設定済み' if verification_token else '未設定'}")
    
    print("\n注意: 環境変数は現在のプロセスでのみ有効です")
    print("永続的に設定する場合は、システム環境変数に設定するか、.envファイルを使用してください")

if __name__ == "__main__":
    main()
