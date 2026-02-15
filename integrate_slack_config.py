#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存のSlack設定を統合
現在使用中のSlack設定をSlack Integrationに適用
"""

import os
import re
import json
from pathlib import Path


def mask_secret(value: str, *, keep_start: int = 6, keep_end: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= keep_start + keep_end + 3:
        return "***"
    return f"{value[:keep_start]}...{value[-keep_end:]}"

def get_webhook_from_md():
    """SLACK_WEBHOOK_URL.mdからWebhook URLを取得"""
    md_file = Path("SLACK_WEBHOOK_URL.md")
    if md_file.exists():
        content = md_file.read_text(encoding='utf-8')
        # Webhook URLを抽出
        match = re.search(r'https://hooks\.slack\.com/services/[^\s`]+', content)
        if match:
            return match.group(0)
    return None

def get_config_from_json():
    """notification_system_state.jsonから設定を取得"""
    json_file = Path("notification_system_state.json")
    if json_file.exists():
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    'webhook_url': data.get('slack_webhook_url'),
                    'verification_token': data.get('slack_verification_token')
                }
        except Exception:
            pass
    return {}

def get_env_vars():
    """環境変数から設定を取得"""
    return {
        'webhook_url': os.getenv('SLACK_WEBHOOK_URL', ''),
        'verification_token': os.getenv('SLACK_VERIFICATION_TOKEN', '')
    }

def main():
    """メイン処理"""
    print("=" * 60)
    print("既存のSlack設定を統合")
    print("=" * 60)
    
    # 設定を収集
    webhook_url = None
    verification_token = None
    webhook_source = None
    verification_token_source = None
    
    # 1. 環境変数から取得
    env_config = get_env_vars()
    if env_config['webhook_url']:
        webhook_url = env_config['webhook_url']
        webhook_source = "env"
        print(f"✅ 環境変数からWebhook URL取得")
    if env_config['verification_token']:
        verification_token = env_config['verification_token']
        verification_token_source = "env"
        print(f"✅ 環境変数からVerification Token取得")
    
    # 2. JSONファイルから取得
    if not webhook_url or not verification_token:
        json_config = get_config_from_json()
        if json_config.get('webhook_url') and not webhook_url:
            webhook_url = json_config['webhook_url']
            webhook_source = "json"
            print(f"✅ JSONファイルからWebhook URL取得")
        if json_config.get('verification_token') and not verification_token:
            verification_token = json_config['verification_token']
            verification_token_source = "json"
            print(f"✅ JSONファイルからVerification Token取得")
    
    # 3. MDファイルから取得
    if not webhook_url:
        webhook_from_md = get_webhook_from_md()
        if webhook_from_md:
            webhook_url = webhook_from_md
            webhook_source = "md"
            print(f"✅ MDファイルからWebhook URL取得")
    
    # 結果表示
    print("\n" + "=" * 60)
    print("取得した設定")
    print("=" * 60)
    print(f"Webhook URL: {'✅ 取得済み' if webhook_url else '❌ 未取得'}")
    if webhook_url:
        print(f"  {mask_secret(webhook_url)}")
    print(f"Verification Token: {'✅ 取得済み' if verification_token else '❌ 未取得'}")
    if verification_token:
        print(f"  {mask_secret(verification_token)}")
    
    # 環境変数設定スクリプト生成
    if webhook_url or verification_token:
        print("\n" + "=" * 60)
        print("環境変数設定コマンド")
        print("=" * 60)
        
        print("\n# PowerShellで実行:")
        print("cd C:\\Users\\mana4\\Desktop\\manaos_integrations")
        if webhook_url and webhook_source != "env":
            print('$env:SLACK_WEBHOOK_URL = "<your_webhook_url>"  # 値は安全のため表示しません')
        if verification_token and verification_token_source != "env":
            print('$env:SLACK_VERIFICATION_TOKEN = "<your_verification_token>"  # 値は安全のため表示しません')
        print('$env:PORT = "5114"')
        print('$env:FILE_SECRETARY_URL = "http://127.0.0.1:5120"')
        print('python slack_integration.py')
        
        # 起動スクリプト生成（秘密情報は保存しない）
        batch_file = Path("start_slack_integration_with_config.ps1")
        with open(batch_file, 'w', encoding='utf-8') as f:
            f.write("# Slack Integration起動スクリプト（設定統合版）\n")
            f.write("cd C:\\Users\\mana4\\Desktop\\manaos_integrations\n\n")
            f.write('$env:PORT = "5114"\n')
            f.write('$env:FILE_SECRETARY_URL = "http://127.0.0.1:5120"\n')
            f.write('$env:ORCHESTRATOR_URL = "http://127.0.0.1:5106"\n')
            f.write('\n')
            f.write('if (-not $env:SLACK_WEBHOOK_URL -and -not $env:SLACK_VERIFICATION_TOKEN) {\n')
            f.write('  Write-Error "SLACK_WEBHOOK_URL または SLACK_VERIFICATION_TOKEN を環境変数に設定してください（スクリプトは安全のため値を保存しません）"\n')
            f.write('  exit 1\n')
            f.write('}\n')
            f.write('\n')
            f.write('Write-Host "Slack Integration起動中..." -ForegroundColor Cyan\n')
            f.write('python slack_integration.py\n')
        
        print(f"\n✅ 起動スクリプト作成: {batch_file}")
        print(f"   実行方法: .\\{batch_file}")

if __name__ == '__main__':
    main()






















