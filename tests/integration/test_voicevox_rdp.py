#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VOICEVOX接続確認スクリプト（RDP対応）
"""

import requests
import os
import sys
import socket

# Windowsコンソールのエンコーディング設定
if sys.platform == "win32":
    import io
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

def test_voicevox_rdp():
    """VOICEVOX APIの接続確認（RDP対応）"""
    print("=" * 60)
    print("VOICEVOX 接続確認（RDP対応）")
    print("=" * 60)

    # ホスト名とIPアドレスを取得
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "127.0.0.1"

    print(f"ホスト名: {hostname}")
    print(f"ローカルIP: {local_ip}")
    print()

    # 複数のURLを試す
    test_urls = [
        "http://127.0.0.1:50021",
        "http://127.0.0.1:50021",
        f"http://{local_ip}:50021",
    ]

    # 環境変数から取得
    env_url = os.getenv('VOICEVOX_API_URL')
    if env_url:
        test_urls.insert(0, env_url)

    success = False

    for voicevox_url in test_urls:
        print(f"試行中: {voicevox_url}")
        try:
            # スピーカー一覧を取得
            r = requests.get(f'{voicevox_url}/speakers', timeout=10)
            r.raise_for_status()
            speakers = r.json()
            print(f"  OK: {len(speakers)} 個のスピーカーが見つかりました")

            # 最初のスピーカーの情報を表示
            if speakers:
                first_speaker = speakers[0]
                speaker_name = first_speaker.get('name', 'Unknown')
                print(f"  例: {speaker_name}")

            print()
            print("=" * 60)
            print(f"OK: VOICEVOX は正常に動作しています！")
            print(f"接続URL: {voicevox_url}")
            print("=" * 60)

            # 環境変数を設定することを推奨
            if voicevox_url != "http://127.0.0.1:50021":
                print()
                print("推奨: 環境変数を設定してください")
                print(f'  $env:VOICEVOX_API_URL = "{voicevox_url}"')
                print("  または、.envファイルに記述:")
                print(f'  VOICEVOX_API_URL={voicevox_url}')

            success = True
            break

        except requests.exceptions.ConnectionError:
            print(f"  NG: 接続できません")
            continue
        except requests.exceptions.Timeout:
            print(f"  NG: タイムアウト")
            continue
        except Exception as e:
            print(f"  NG: {e}")
            continue

    if not success:
        print()
        print("=" * 60)
        print("NG: すべての接続方法が失敗しました")
        print("=" * 60)
        print()
        print("確認事項:")
        print("1. VOICEVOXが起動しているか確認")
        print("2. ポート50021でリッスンしているか確認")
        print("   netstat -an | findstr 50021")
        print("3. ファイアウォールの設定を確認")
        print("4. RDP接続の場合、ネットワーク設定を確認")
        print()
        print("手動確認:")
        print("  ブラウザで http://127.0.0.1:50021/speakers を開く")

    return success

