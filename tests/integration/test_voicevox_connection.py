#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VOICEVOX接続確認スクリプト
"""

import requests
import os
import sys

# Windowsコンソールのエンコーディング設定
if sys.platform == "win32":
    import io
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

def test_voicevox():
    """VOICEVOX APIの接続確認"""
    voicevox_url = os.getenv('VOICEVOX_API_URL', 'http://127.0.0.1:50021')

    print("=" * 60)
    print("VOICEVOX 接続確認")
    print("=" * 60)
    print(f"接続先: {voicevox_url}")
    print()

    try:
        # スピーカー一覧を取得
        print("[1] スピーカー一覧を取得中...")
        r = requests.get(f'{voicevox_url}/speakers', timeout=30)
        r.raise_for_status()
        speakers = r.json()
        print(f"OK: {len(speakers)} 個のスピーカーが見つかりました")

        # 最初のスピーカーの情報を表示
        if speakers:
            first_speaker = speakers[0]
            print(f"  例: {first_speaker.get('name', 'Unknown')} (ID: {first_speaker.get('speaker_uuid', 'Unknown')})")

        print()
        print("[2] 音声合成テスト...")
        # 簡単な音声合成テスト
        test_text = "こんにちは、レミです。"
        print(f"  テキスト: {test_text}")

        # 音声クエリを生成
        speaker_id = 3  # デフォルトスピーカー（四国めたん）
        query_url = f'{voicevox_url}/audio_query'
        query_params = {'text': test_text, 'speaker': speaker_id}

        query_r = requests.post(query_url, params=query_params, timeout=10)
        query_r.raise_for_status()
        print("  OK: 音声クエリ生成成功")

        # 音声合成
        synthesis_url = f'{voicevox_url}/synthesis'
        synthesis_r = requests.post(synthesis_url, params={'speaker': speaker_id}, json=query_r.json(), timeout=10)
        synthesis_r.raise_for_status()

        # 音声ファイルを保存
        output_file = 'test_voicevox_output.wav'
        with open(output_file, 'wb') as f:
            f.write(synthesis_r.content)
        print(f"  OK: 音声ファイルを生成しました: {output_file}")
        print(f"  ファイルサイズ: {len(synthesis_r.content)} bytes")

        print()
        print("=" * 60)
        print("OK: VOICEVOX は正常に動作しています！")
        print("=" * 60)
        return True

    except requests.exceptions.ConnectionError:
        print("NG: VOICEVOXに接続できません")
        print("  確認事項:")
        print("  1. VOICEVOXが起動しているか確認")
        print("  2. ポート50021でリッスンしているか確認")
        print("  3. ファイアウォールの設定を確認")
        return False
    except requests.exceptions.Timeout:
        print("NG: タイムアウトしました")
        print("  VOICEVOXの応答が遅い可能性があります")
        return False
    except Exception as e:
        print(f"NG: エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False

