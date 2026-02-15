# 音声関連スクリプト

## 運用開始

| スクリプト | 説明 |
|------------|------|
| `check_voice_ready.bat` / `check_voice_ready.py` | 音声運用開始可否チェック（ヘルス＋メトリクス＋TTS 1回） |
| `run_voice_e2e.bat` | E2Eテスト実行 |
| `start_unified_api_with_voice.bat` | 統合API起動の案内付き起動 |
| `start_voice_secretary.bat` | 秘書レミ（スタンドアロン）起動 |
| `setup_voice_config.bat` / `setup_voice_config.ps1` | voice_config.json の初回セットアップ（example をコピー） |
| **Pixel 7 ＋ 母艦** | |
| `start_pixel7_realtime_voice.bat` | **母艦で一括起動**: WebSocket 8765 ＋ クライアント配信 8766 を2窓で起動。あとは Pixel 7 で `http://<母艦IP>:8766` を開く |
| `realtime_client.html` | リアルタイム音声のブラウザクライアント（母艦 WebSocket に接続） |
| `serve_voice_client.py` | 母艦で上記 HTML を配信（`http://<母艦>:8766` を Pixel 7 で開く） |
| **Pixel 7 コンパニオンモード** | |
| 統合API `/companion` | **母艦で統合API(9500)起動後**、Pixel 7 で `http://<母艦IP>:9502/companion` を開く。テキスト＋音声＋TTS＋デバイス操作＋Obsidian＋n8n |
| `pixel7_companion_client.html` | コンパニオンモード用クライアント（PWA・オフラインバッファ・デバイス状態・クイックアクション対応） |
| `companion_manifest.json` | PWA manifest（ホーム画面追加用） |
| `companion_sw.js` | Service Worker（オフラインキャッシュ） |

## 確認・テスト

| スクリプト | 説明 |
|------------|------|
| `check_voice_integration.py` | モジュール・統合API・VOICEVOX の動作確認 |
| `test_voice_e2e.py` | 音声API E2Eテスト（health, metrics, synthesize, 任意で transcribe/conversation） |
| `test_voice_conversation.py` | 音声会話テスト（WAV ファイル指定、ローカルエンジン使用） |

## インストール

| スクリプト | 説明 |
|------------|------|
| `auto_install_webrtcvad.py` | webrtcvad の自動インストール試行 |
| `install_webrtcvad.bat` / `install_webrtcvad_simple.bat` | webrtcvad インストール（Windows） |
| `install_voice_dependencies.bat` | 音声依存関係のインストール |

詳細は **docs/voice_operations.md**（運用開始ガイド）を参照してください。
