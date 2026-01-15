#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slack統合テスト
"""

import sys
import httpx
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from file_secretary_templates import (
    parse_command, extract_search_query,
    template_inbox_status, template_done, template_restore,
    template_search, template_error
)

def test_command_parsing():
    """コマンド解析テスト"""
    print("=== コマンド解析テスト ===\n")
    
    test_cases = [
        "Inboxどう？",
        "終わった",
        "戻して",
        "探して：日報",
        "今日は放置",
        "不明なコマンド"
    ]
    
    for text in test_cases:
        cmd = parse_command(text)
        query = extract_search_query(text) if cmd == "search" else None
        print(f"入力: \"{text}\"")
        print(f"  コマンド: {cmd}")
        if query:
            print(f"  検索クエリ: {query}")
        print()

def test_templates():
    """テンプレートテスト"""
    print("=== テンプレートテスト ===\n")
    
    # INBOX状況テンプレート
    print("1. INBOX状況テンプレート:")
    status_text = template_inbox_status(
        new_count=3,
        old_count=12,
        long_term_count=7,
        summary="日報っぽい5、画像素材4、その他3",
        candidates=[
            {"original_name": "scan_001.pdf", "tags": ["日報っぽい"]},
            {"original_name": "IMG_1234.png", "tags": ["クーポンっぽい"]}
        ]
    )
    print(status_text)
    print()
    
    # 整理完了テンプレート
    print("2. 整理完了テンプレート:")
    done_text = template_done([
        {"original_name": "scan_001.pdf", "alias_name": "2026-01-03_日報_実績_確定.pdf"},
        {"original_name": "IMG_1234.png", "alias_name": "2026-01-03_洗車_クーポン_案A.png"}
    ])
    print(done_text)
    print()
    
    # 復元テンプレート
    print("3. 復元テンプレート:")
    restore_text = template_restore([
        {"original_name": "scan_001.pdf", "alias_name": "2026-01-03_日報_実績_確定.pdf"}
    ])
    print(restore_text)
    print()
    
    # 検索テンプレート
    print("4. 検索テンプレート:")
    search_text = template_search("日報", [
        {"original_name": "scan_001.pdf", "alias_name": "2026-01-03_日報_実績_確定.pdf", "summary": "1月の実績データ"}
    ])
    print(search_text)
    print()

def test_api_integration():
    """API統合テスト"""
    print("=== API統合テスト ===\n")
    
    api_url = "http://localhost:5120"
    
    try:
        # ヘルスチェック
        response = httpx.get(f"{api_url}/health", timeout=5.0)
        print(f"1. Health check: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
        print()
        
        # INBOX状況取得
        response = httpx.get(f"{api_url}/api/inbox/status", timeout=5.0)
        print(f"2. INBOX status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   New: {data.get('summary', {}).get('new_count', 0)}")
            print(f"   Old: {data.get('summary', {}).get('old_count', 0)}")
        print()
        
        # Slack統合エンドポイント
        response = httpx.post(
            f"{api_url}/api/slack/handle",
            json={
                "text": "Inboxどう？",
                "user": "test_user",
                "channel": "test_channel",
                "thread_ts": None,
                "files": []
            },
            timeout=5.0
        )
        print(f"3. Slack handle (Inboxどう？): {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response text: {data.get('response_text', '')[:100]}...")
        print()
        
    except httpx.ConnectError:
        print("⚠️ APIサーバーに接続できません（起動していない可能性があります）")
    except Exception as e:
        print(f"❌ エラー: {e}")

def main():
    """メイン処理"""
    test_command_parsing()
    test_templates()
    test_api_integration()

if __name__ == '__main__':
    main()






















