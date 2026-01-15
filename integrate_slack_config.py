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
        except:
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
    
    # 1. 環境変数から取得
    env_config = get_env_vars()
    if env_config['webhook_url']:
        webhook_url = env_config['webhook_url']
        print(f"✅ 環境変数からWebhook URL取得")
    if env_config['verification_token']:
        verification_token = env_config['verification_token']
        print(f"✅ 環境変数からVerification Token取得")
    
    # 2. JSONファイルから取得
    if not webhook_url or not verification_token:
        json_config = get_config_from_json()
        if json_config.get('webhook_url') and not webhook_url:
            webhook_url = json_config['webhook_url']
            print(f"✅ JSONファイルからWebhook URL取得")
        if json_config.get('verification_token') and not verification_token:
            verification_token = json_config['verification_token']
            print(f"✅ JSONファイルからVerification Token取得")
    
    # 3. MDファイルから取得
    if not webhook_url:
        webhook_from_md = get_webhook_from_md()
        if webhook_from_md:
            webhook_url = webhook_from_md
            print(f"✅ MDファイルからWebhook URL取得")
    
    # 結果表示
    print("\n" + "=" * 60)
    print("取得した設定")
    print("=" * 60)
    print(f"Webhook URL: {'✅ 取得済み' if webhook_url else '❌ 未取得'}")
    if webhook_url:
        print(f"  {webhook_url[:50]}...")
    print(f"Verification Token: {'✅ 取得済み' if verification_token else '❌ 未取得'}")
    
    # 環境変数設定スクリプト生成
    if webhook_url or verification_token:
        print("\n" + "=" * 60)
        print("環境変数設定コマンド")
        print("=" * 60)
        
        print("\n# PowerShellで実行:")
        print("cd C:\\Users\\mana4\\Desktop\\manaos_integrations")
        if webhook_url:
            print(f'$env:SLACK_WEBHOOK_URL = "{webhook_url}"')
        if verification_token:
            print(f'$env:SLACK_VERIFICATION_TOKEN = "{verification_token}"')
        print('$env:PORT = "5114"')
        print('$env:FILE_SECRETARY_URL = "http://localhost:5120"')
        print('python slack_integration.py')
        
        # バッチファイル生成
        batch_file = Path("start_slack_integration_with_config.ps1")
        with open(batch_file, 'w', encoding='utf-8') as f:
            f.write("# Slack Integration起動スクリプト（設定統合版）\n")
            f.write("cd C:\\Users\\mana4\\Desktop\\manaos_integrations\n\n")
            if webhook_url:
                f.write(f'$env:SLACK_WEBHOOK_URL = "{webhook_url}"\n')
            if verification_token:
                f.write(f'$env:SLACK_VERIFICATION_TOKEN = "{verification_token}"\n')
            f.write('$env:PORT = "5114"\n')
            f.write('$env:FILE_SECRETARY_URL = "http://localhost:5120"\n')
            f.write('$env:ORCHESTRATOR_URL = "http://localhost:5106"\n')
            f.write('\n')
            f.write('Write-Host "Slack Integration起動中..." -ForegroundColor Cyan\n')
            f.write('python slack_integration.py\n')
        
        print(f"\n✅ 起動スクリプト作成: {batch_file}")
        print(f"   実行方法: .\\{batch_file}")

if __name__ == '__main__':
    main()






















