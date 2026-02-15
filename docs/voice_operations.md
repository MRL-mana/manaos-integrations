# 音声機能 運用開始ガイド

## クイックスタート（運用開始まで最短）

1. **VOICEVOX を起動**（http://127.0.0.1:50021）
2. **統合APIを起動**: `python unified_api_server.py`（プロジェクトルートで）
3. **運用開始確認**: `scripts\voice\check_voice_ready.bat` を実行し「運用開始可能です。」を確認

設定ファイルで管理する場合は、先に `scripts\voice\setup_voice_config.bat` で `voice_config.json` を生成し編集。

---

## 1. 前提条件

- **VOICEVOX** または **Style-Bert-VITS2** が起動している（TTS用）
- **faster-whisper** または **openai-whisper** が利用可能（STT用）
- **Unified API Server** を起動すると音声APIが有効になる

## 2. 初回セットアップ

### 2.1 音声設定（任意）

環境変数で十分な場合は不要。設定ファイルで一元管理する場合:

```powershell
# プロジェクトルートで
copy voice_config.json.example voice_config.json
# voice_config.json を編集（VOICEVOX_URL, スピーカーID 等）
```

### 2.2 依存関係

```powershell
pip install faster-whisper requests httpx
# VAD改善（推奨）
pip install webrtcvad
```

### 2.3 VOICEVOX の起動

- VOICEVOX を起動し、エンジンが `http://127.0.0.1:50021` で応答することを確認
- ブラウザで `http://127.0.0.1:50021/docs` でAPIドキュメント表示を確認してもよい

## 3. 起動手順

### 3.1 統合API（音声API含む）の起動

```powershell
cd c:\Users\mana4\Desktop\manaos_integrations
python unified_api_server.py
```

- 起動ログに「✅ 音声機能統合を初期化タスクに追加しました」が出ていれば音声は有効
- デフォルトで `http://127.0.0.1:9510` で待ち受け
- **TTSストリーミング**: `POST /api/voice/synthesize/stream` で長文を文単位でストリーム返却（先頭から再生可能）

### 3.2 秘書レミ（スタンドアロン）の起動

統合APIとは別に、マイクから直接「レミ」で会話する場合:

```powershell
cd c:\Users\mana4\Desktop\manaos_integrations
scripts\voice\start_voice_secretary.bat
# または
python voice_secretary_remi.py
```

- 事前に **Unified API** と **VOICEVOX** が起動していること
- 環境変数: `UNIFIED_API_URL`, `LLM_ROUTING_URL`, `INTENT_ROUTER_URL`, `VOICEVOX_URL` 等

### 3.3 Web音声インターフェースの起動

ブラウザから音声でワークフロー実行する場合:

```powershell
python web_voice_interface.py
```

- Orchestrator が `ORCHESTRATOR_URL`（デフォルト 5106）で起動していること

### 3.4 リアルタイムWebSocket音声の起動

```powershell
python voice_realtime_streaming.py
```

- デフォルトで `ws://0.0.0.0:8765`。環境変数 `VOICE_WEBSOCKET_PORT`, `VOICE_WEBSOCKET_HOST` で変更可能
- **クライアント**: PC のブラウザやアプリがマイク音声を WebSocket で送ると、STT → LLM → TTS の応答が返る
- **Pixel 7 ＋ 母艦**: Pixel 7 単体ではなく母艦とセットで使う想定。母艦で **`scripts\voice\start_pixel7_realtime_voice.bat`** を実行すると WebSocket 8765 とクライアント配信 8766 を一括起動。または手動で `python voice_realtime_streaming.py` と `python scripts/voice/serve_voice_client.py`。Pixel 7 のブラウザで `http://<母艦>:8766` を開き、WebSocket URL に `ws://<母艦>:8765` を指定して「開始」すると端末のマイクからリアルタイム会話が可能。バッチのみの場合は `POST /api/pixel7/tts` と `POST /api/pixel7/transcribe` を利用。

## 4. 運用開始の確認

### 4.1 ヘルスチェック

```powershell
# 統合APIが起動している前提
curl http://127.0.0.1:9510/api/voice/health
```

期待例: `{"status":"ok","stt":"ok","tts":"ok"}`

### 4.2 メトリクス確認

```powershell
curl http://127.0.0.1:9510/api/voice/metrics
```

### 4.3 動作確認スクリプト（推奨）

```powershell
python scripts\voice\check_voice_ready.py --base http://127.0.0.1:9510
```

- ヘルス・メトリクス・TTS 1回を実行し、運用開始可能か判定

### 4.4 E2Eテスト

```powershell
python scripts\voice\test_voice_e2e.py --base http://127.0.0.1:9510
# 音声ファイルで会話まで確認する場合
python scripts\voice\test_voice_e2e.py --base http://127.0.0.1:9510 --audio path\to\sample.wav
```

## 5. 運用開始チェックリスト

| # | 項目 | 確認方法 |
|---|------|----------|
| 1 | VOICEVOX（または Style-Bert-VITS2）起動 | ブラウザで `http://127.0.0.1:50021/speakers` 等にアクセス |
| 2 | 統合API起動 | `curl http://127.0.0.1:9510/health` が 200 |
| 3 | 音声ヘルス OK | `curl http://127.0.0.1:9510/api/voice/health` で `status: ok` |
| 4 | TTS 動作 | `test_voice_e2e.py` の synthesize が成功 |
| 5 | （任意）秘書レミ | `voice_secretary_remi.py` 起動後マイクで「レミ」で応答 |
| 6 | （任意）webrtcvad | `python -c "import webrtcvad; print('OK')"` |

## 6. トラブルシュート

- **503 音声機能統合が利用できません**
  - `voice_integration` のインポート失敗。faster-whisper / whisper / requests をインストール
- **503 音声機能統合が初期化されていません**
  - 起動時の音声初期化で例外が発生。ログの「音声機能統合の初期化準備エラー」を確認
- **TTS が失敗する**
  - VOICEVOX の URL とポートを確認。`VOICEVOX_URL` または `voice_config.json` の `voicevox_url`
- **STT が遅い / 失敗**
  - `VOICE_STT_DEVICE=cpu` にすると遅いが安定する。`VOICE_STT_MODEL=medium` で軽量化可能

## 7. スクリプト一覧

| 用途 | コマンド |
|------|----------|
| 運用開始可否チェック | `scripts\voice\check_voice_ready.bat` または `python scripts/voice/check_voice_ready.py --base http://127.0.0.1:9510` |
| E2Eテスト | `scripts\voice\run_voice_e2e.bat` または `python scripts/voice/test_voice_e2e.py --base http://127.0.0.1:9510` |
| 音声設定の初回セットアップ | `scripts\voice\setup_voice_config.bat` |
| 統合API起動（案内付き） | `scripts\voice\start_unified_api_with_voice.bat` |
| 秘書レミ起動 | `scripts\voice\start_voice_secretary.bat` |
| モジュール・API・VOICEVOX確認 | `python scripts/voice/check_voice_integration.py` |

詳細: `scripts/voice/README.md`

## 8. 関連ドキュメント

- [音声の入口整理（Web音声 vs 秘書レミ）](voice_entry_points.md)
- [音声の問題点・改善点・強化ポイント](voice_issues_and_improvements.md)
- [webrtcvad インストール](voice_webrtcvad_install_guide.md)
- [Style-Bert-VITS2 ガイド](voice_style_bert_vits2_guide.md)

