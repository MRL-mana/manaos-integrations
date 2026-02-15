# 🎤 ManaOS 音声機能統合 - 実装済み機能一覧

## 概要

ManaOS音声機能統合は、**秘書レミ完全体**の最後のピースとして実装されました。
音声入力（STT）から音声出力（TTS）までの完全な会話ループを提供します。

---

## ✅ 実装済み機能

### フェーズ1: 基本機能（完了）

#### STT (Speech-to-Text)
- ✅ faster-whisper統合（高速・高精度）
- ✅ OpenAI Whisperフォールバック
- ✅ 複数モデルサイズ対応（tiny → large-v3）
- ✅ GPU/CPU自動切り替え
- ✅ 日本語最適化

#### TTS (Text-to-Speech)
- ✅ VOICEVOX統合（日本語自然音声）
- ✅ Style-Bert-VITS2対応（HTTP API経由）
- ✅ スピーカー選択機能
- ✅ 話速・音高・抑揚調整

#### 基本API
- ✅ `POST /api/voice/transcribe` - 音声認識
- ✅ `POST /api/voice/synthesize` - 音声合成
- ✅ `POST /api/voice/conversation` - 音声会話
- ✅ `GET /api/voice/speakers` - スピーカー一覧

---

### フェーズ2: 秘書化機能（完了）

#### ホットワード検出
- ✅ カスタマイズ可能なホットワード（デフォルト: 「レミ」）
- ✅ ホットワード除去機能
- ✅ ホットワード未検出時のスキップ

#### Intent Router統合
- ✅ 音声入力から意図自動分類
- ✅ 意図タイプに応じた処理分岐
- ✅ 信頼度スコア取得

#### タスク自動登録
- ✅ 会話からタスク自動生成
- ✅ タスクキューシステム統合
- ✅ 優先度自動設定

#### 会話履歴管理
- ✅ 会話履歴の自動保存
- ✅ Obsidian統合（ノート自動作成）
- ✅ Slack通知（オプション）
- ✅ 意図情報の記録

---

### フェーズ3: 完全体機能（完了）

#### 常時監視モード
- ✅ マイク入力の常時監視
- ✅ バックグラウンドスレッド処理
- ✅ 音声区間の自動検出

#### VAD (Voice Activity Detection)
- ✅ 無音判定の閾値設定
- ✅ 最小音声長の設定
- ✅ 音声区間の自動区切り

#### 統合機能
- ✅ LLMルーティング統合
- ✅ LFM 2.5フォールバック
- ✅ エラーハンドリング強化

---

## 📦 提供スクリプト

### 1. `voice_secretary_remi.py`
**秘書レミ完全体のメインスクリプト**

- ホットワード「レミ」で呼び出し可能
- Intent Router統合
- タスク自動登録
- 会話履歴自動保存

**使用方法**:
```powershell
python voice_secretary_remi.py
```

### 2. `scripts/voice/test_voice_conversation.py`
**音声会話テストスクリプト**

- 音声ファイルを読み込んで会話をテスト
- 応答音声をファイルに保存

**使用方法**:
```powershell
python scripts/voice/test_voice_conversation.py --audio test.wav --output response.wav
```

### 3. `scripts/voice/start_voice_secretary.bat`
**Windows用起動スクリプト**

- 環境変数の自動設定
- 簡単起動

**使用方法**:
```powershell
scripts\voice\start_voice_secretary.bat
```

---

## 🔧 設定オプション

### 環境変数

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `VOICE_STT_MODEL` | STTモデルサイズ | `large-v3` |
| `VOICE_STT_DEVICE` | デバイス（cuda/cpu） | `cuda` |
| `VOICE_STT_COMPUTE_TYPE` | 計算タイプ | `float16` |
| `VOICE_TTS_ENGINE` | TTSエンジン | `voicevox` |
| `VOICEVOX_URL` | VOICEVOX API URL | `http://127.0.0.1:50021` |
| `VOICEVOX_SPEAKER_ID` | スピーカーID | `3` |
| `INTENT_ROUTER_URL` | Intent Router URL | `http://127.0.0.1:5100` |
| `UNIFIED_API_URL` | 統合API URL | `http://127.0.0.1:9502` |
| `LLM_ROUTING_URL` | LLMルーティングURL | `http://127.0.0.1:5111` |

---

## 🎯 使用例

### 例1: 基本的な音声会話

```python
from voice_integration import create_stt_engine, create_tts_engine, VoiceConversationLoop

# エンジン初期化
stt_engine = create_stt_engine(model_size="large-v3", device="cuda")
tts_engine = create_tts_engine(engine="voicevox", speaker_id=3)

# LLMコールバック
def llm_callback(text: str) -> str:
    return f"「{text}」についてですね。了解しました。"

# 会話ループ作成
conversation_loop = VoiceConversationLoop(
    stt_engine=stt_engine,
    tts_engine=tts_engine,
    llm_callback=llm_callback,
    hotword="レミ"
)

# 音声ファイルを処理
with open("user_audio.wav", "rb") as f:
    audio_data = f.read()

response_audio = conversation_loop.process_audio(audio_data)
```

### 例2: Intent Router統合

```python
import httpx

def intent_router_callback(text: str) -> dict:
    """Intent Routerコールバック"""
    response = httpx.post(
        "http://127.0.0.1:5100/api/classify",
        json={"text": text}
    )
    return response.json()

conversation_loop = VoiceConversationLoop(
    stt_engine=stt_engine,
    tts_engine=tts_engine,
    llm_callback=llm_callback,
    hotword="レミ",
    intent_router_callback=intent_router_callback
)
```

### 例3: タスク自動登録

```python
def task_registration_callback(text: str, intent_result: dict) -> bool:
    """タスク登録コールバック"""
    if intent_result.get("intent_type") == "task_execution":
        # タスクキューに登録
        response = httpx.post(
            "http://127.0.0.1:9502/api/task/queue/add",
            json={"input_text": text, "priority": "medium"}
        )
        return response.status_code == 200
    return False

conversation_loop = VoiceConversationLoop(
    stt_engine=stt_engine,
    tts_engine=tts_engine,
    llm_callback=llm_callback,
    hotword="レミ",
    task_registration_callback=task_registration_callback
)
```

---

## 🚀 次のステップ

1. **Style-Bert-VITS2でレミ声固定** - 専用ボイスモデルの学習
2. **VAD改善** - より高精度な音声区間検出
3. **リアルタイム処理** - ストリーミング対応
4. **多言語対応** - 英語・中国語等の追加

---

**秘書レミ完全体、完成！** 🎉

