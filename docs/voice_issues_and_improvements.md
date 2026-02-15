# 音声統合：問題点・改善点・強化ポイント

## 1. 問題点（要対応）

### 1.1 音声アップロードのサイズ制限なし ✅ 対応済
- **場所**: `unified_api_server.py` の `/api/voice/transcribe`, `/api/voice/conversation`
- **内容**: `audio_file.read()` でそのまま全読み込み。巨大ファイルでメモリ圧迫・DoSのリスクあり。
- **対応**: `VOICE_AUDIO_MAX_BYTES`（デフォルト 10MB）と `VOICE_AUDIO_MAX_SECONDS`（60秒）で制限。超えたら 400 を返す。

### 1.2 Style-Bert-VITS2 の `get_speakers` 未実装 ✅ 対応済
- **場所**: `voice_integration.py` の `TTSEngine.get_speakers()`
- **内容**: Style-Bert-VITS2 使用時は空リストを返す（コメントで「実装が必要」）。`/api/voice/speakers` が空になる。
- **対応**: 「レミ」「デフォルト」の固定リストを返すように変更。API一覧があれば今後拡張可能。

### 1.3 リアルタイムストリーミングの LLM がハードコード ✅ 対応済
- **場所**: `voice_realtime_streaming.py` の `main()`
- **内容**: `llm_callback` が「「{text}」についてですね。了解しました。」の固定応答のみ。Intent Router / LLM ルーティングと未連携。
- **対応**: `voice_secretary_remi.create_llm_callback()` を利用。失敗時は従来の固定応答にフォールバック。

### 1.4 WebSocket 送受信フォーマットの不整合 ✅ 対応済
- **場所**: `voice_realtime_streaming.py` の `handle_websocket`
- **内容**: 受信は `base64.b64decode`、送信は `response_audio.hex()`。クライアントが Base64 を期待すると再生できない。
- **対応**: 送信を Base64 に統一（`base64.b64encode(response_audio).decode("utf-8")`）。

### 1.5 音声会話 API のエラー時フォールバック不足 ✅ 対応済
- **場所**: `unified_api_server.py` の `voice_conversation()`
- **内容**: LLM 応答が空の場合に 500 を返すのみ。リトライや「申し訳ありません、再度お願いします」などのフォールバック音声がない。
- **対応**: 空応答時は「申し訳ありません、再度お願いします。」を TTS して 200 で返す。ログに warning を出力。

---

## 2. 改善点（推奨）

### 2.1 音声アップロードの制限追加 ✅ 対応済
- 1.1 と同一。最大 10MB / 60秒、超えたら 400。

### 2.2 入口の整理（Web 音声 vs 秘書レミ） ✅ 対応済
- **対応**: [docs/voice_entry_points.md](voice_entry_points.md) を追加。Web音声（Orchestrator）と秘書レミ（Unified API）の役割・環境変数・使い分けを明記。

### 2.3 STT/TTS の部分利用 ✅ 対応済
- **対応**: 初期化で STT と TTS を別々に try。片方だけ成功した場合は `available` を `stt_only` / `tts_only` に。transcribe は stt_engine があれば 200、synthesize/speakers は tts_engine があれば 200、conversation は両方必要。

### 2.4 webrtcvad の位置づけ ✅ 対応済
- 現状: オプション。未インストール時は従来の閾値判定のみ。
- 改善: **webrtcvad は音声区間検出の推奨オプション**。インストール手順は [voice_webrtcvad_install_guide.md](voice_webrtcvad_install_guide.md) を参照。

### 2.5 タイムアウトの明文化 ✅ 対応済
- **対応**: `manaos_timeout_config` に `voice_tts`, `voice_stt`, `voice_speakers`, `voice_intent_router` を追加。`voice_integration` では `_voice_timeout()` で取得、統合APIの Intent Router 呼び出しでは `timeout_config.get("voice_intent_router", 10.0)` を使用。環境変数 `MANAOS_TIMEOUT_VOICE_TTS` 等で上書き可能。

---

## 3. 強化ポイント（中長期）

### 3.1 音声ヘルスチェック API ✅ 対応済
- **新規**: `GET /api/voice/health`
- **対応**: STT/TTS の生存確認を返す。`status`, `stt`, `tts` を返却。監視・オートヒーリングに利用可能。

### 3.2 リトライの導入 ✅ 対応済
- **対応**: `voice_integration.py` に `_voice_request_with_retry()` を追加。VOICEVOX の audio_query / synthesis と Style-Bert-VITS2 の /voice、および get_speakers で最大2回リトライ（指数バックオフ 1s, 2s）。

### 3.3 メトリクス ✅ 対応済
- **対応**: `GET /api/voice/metrics` を追加。`transcribe_count`, `synthesize_count`, `conversation_count`, `error_count` を返却。

### 3.4 TTS ストリーミング応答 ✅ 対応済
- **対応**: `POST /api/voice/synthesize/stream` を追加。テキストを。！？\n で文分割し、各文を TTS してストリーム返却。形式は 4 バイト長（LE）+ WAV バイナリの繰り返し。ヘッダー `X-Voice-Stream-Format: length-prefixed-wav`。

### 3.5 E2E テスト ✅ 対応済
- **対応**: `scripts/voice/test_voice_e2e.py` を追加。`/api/voice/health`, `/api/voice/metrics`, `/api/voice/synthesize` を実行。`--audio` で WAV を指定すると transcribe / conversation も実行。`python scripts/voice/test_voice_e2e.py --base http://127.0.0.1:9502`

### 3.6 設定の一元化 ✅ 対応済
- **対応**: 起動時に `voice_config.json` または `config/voice_config.json` を読み、`voice` セクションのキーを環境変数に反映。`voice_config.json.example` を参照。環境変数が未設定の場合のみ上書きする設計も可能（現状は上書き）。

---

## 4. 優先度の目安

| 項目 | 優先度 | 理由 |
|------|--------|------|
| 1.1 アップロード制限 | 高 | セキュリティ・安定性 |
| 1.4 WebSocket Base64 統一 | 高 | クライアント動作に直結 |
| 1.3 リアルタイムの LLM 連携 | 高 | 実用性 |
| 1.2 Style-Bert get_speakers | 中 | UI でスピーカー選択する場合 |
| 1.5 フォールバック応答 | 中 | UX |
| 3.1 音声ヘルスチェック | 中 | 運用・監視 |
| 2.2 入口の整理 | 低 | ドキュメント・設計の明確化 |
| 3.2 リトライ / 3.3 メトリクス | 低 | 信頼性・可観測性の向上 |

---

---

## 5. 実施した修正（サマリ）

| 項目 | 修正内容 |
|------|----------|
| 1.1 | `VOICE_AUDIO_MAX_BYTES` / `VOICE_AUDIO_MAX_SECONDS` を追加し、transcribe/conversation でチェック |
| 1.2 | Style-Bert-VITS2 の `get_speakers()` で「レミ」「デフォルト」の固定リストを返す |
| 1.3 | `voice_realtime_streaming.main()` で `create_llm_callback()` を利用（失敗時は固定応答） |
| 1.4 | WebSocket 応答を `response_audio.hex()` から Base64 に変更 |
| 1.5 | LLM 応答が空のときフォールバック文言を TTS して 200 で返す |
| 2.1 | 1.1 と同一のため対応済みマーク |
| 2.3 | STT/TTS を別々に初期化し、片方だけでも利用可能（stt_only / tts_only） |
| 3.4 | `POST /api/voice/synthesize/stream` で文単位 TTS ストリーミング |

*最終更新: 問題点・改善点・強化ポイントは対応済み。*

