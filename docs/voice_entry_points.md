# 音声機能の入口整理（Web音声 vs 秘書レミ）

## 2系統の入口

| 入口 | URL/ポート | 用途 | 連携先 |
|------|------------|------|--------|
| **Web音声インターフェース** | `ORCHESTRATOR_URL`（デフォルト 5106） | ブラウザから音声→テキスト→**ワークフロー実行** | Unified Orchestrator `/api/execute` |
| **秘書レミ / 統合API音声** | `UNIFIED_API_URL`（デフォルト 9500） | 音声会話・**意図分類・タスク登録・会話保存** | Intent Router, LLM Routing, タスクキュー, Obsidian/Slack |

## 使い分け

- **「音声でコマンドを実行したい」** → Web音声インターフェース（`web_voice_interface.py`）
  - テキストは Orchestrator の `execute` に渡され、ワークフローとして実行される。
- **「音声で会話・タスク登録・メモ保存したい」** → 秘書レミ（`voice_secretary_remi.py`）または統合APIの `/api/voice/conversation`
  - 意図分類・タスクキュー・Obsidian/Slack と連携。

## 音声専用エンドポイント（統合API）

Unified API Server（9500）で以下を提供。どちらの入口からも利用可能。

- `POST /api/voice/transcribe` - STT
- `POST /api/voice/synthesize` - TTS
- `POST /api/voice/synthesize/stream` - TTSストリーミング（文単位、先頭から再生可能）
- `POST /api/voice/conversation` - STT → Intent/LLM → TTS
- `GET /api/voice/speakers` - スピーカー一覧
- `GET /api/voice/health` - 音声サブシステムの生存確認
- `GET /api/voice/metrics` - 音声リクエスト数・エラー数など

## 環境変数

- `ORCHESTRATOR_URL` - Web音声が叩くオーケストレータ（例: http://localhost:5106）
- `UNIFIED_API_URL` - 秘書レミ・音声APIのベース（例: http://localhost:9500）
- `INTENT_ROUTER_URL` - 意図分類（例: http://localhost:5100）
- `LLM_ROUTING_URL` - LLMルーティング（例: http://localhost:5110）

## 運用開始

- **起動手順・確認・チェックリスト**: [音声運用開始ガイド](voice_operations.md)
- **運用開始可否チェック**: `scripts\voice\check_voice_ready.bat` または `python scripts/voice/check_voice_ready.py --base http://localhost:9500`
