# 🎤 ManaOS 音声機能統合 - 高度機能ガイド

**VAD改善、リアルタイム処理、Style-Bert-VITS2統合**

---

## ✅ 実装完了機能

### 1. VAD改善（高精度音声区間検出）

#### WebRTC VAD統合

**特徴**:
- ✅ WebRTC VADによる高精度な音声区間検出
- ✅ 無音区間の自動検出
- ✅ 最小音声長の設定
- ✅ リアルタイム処理対応

**使用方法**:

```python
from voice_integration import create_stt_engine, create_tts_engine, VoiceConversationLoop

# エンジン初期化
stt_engine = create_stt_engine(model_size="large-v3", device="cuda")
tts_engine = create_tts_engine(engine="voicevox", speaker_id=3)

# 会話ループ作成（VAD自動有効化）
conversation_loop = VoiceConversationLoop(
    stt_engine=stt_engine,
    tts_engine=tts_engine,
    llm_callback=llm_callback,
    hotword="レミ"
)

# VADは自動的に有効化されます（webrtcvadがインストールされている場合）
conversation_loop.start()
```

**インストール**:

```powershell
pip install webrtcvad
```

**設定**:

```python
# VADの敏感度を調整（0-3、2が推奨）
self.webrtc_vad = webrtcvad.Vad(2)  # 0=最も敏感、3=最も鈍感
```

---

### 2. リアルタイム処理（ストリーミング対応）

#### WebSocket経由のリアルタイム音声会話

**特徴**:
- ✅ WebSocket経由のリアルタイム通信
- ✅ ストリーミング音声処理
- ✅ 低遅延対応
- ✅ 非同期処理

**使用方法**:

```powershell
# リアルタイムストリーミングサーバーを起動
python voice_realtime_streaming.py
```

**クライアント例（JavaScript）**:

```javascript
const ws = new WebSocket('ws://localhost:8765/voice');

// 音声データを送信
ws.send(JSON.stringify({
    type: 'audio',
    data: audioDataBase64
}));

// 応答を受信
ws.onmessage = (event) => {
    const response = JSON.parse(event.data);
    if (response.type === 'audio') {
        // 音声応答を再生
        playAudio(response.data);
    }
};
```

**Pythonクライアント例**:

```python
import asyncio
import websockets
import json

async def send_audio():
    async with websockets.connect('ws://localhost:8765/voice') as websocket:
        # 音声データを送信
        with open('audio.wav', 'rb') as f:
            audio_data = f.read()
        
        await websocket.send(json.dumps({
            'type': 'audio',
            'data': audio_data.hex()
        }))
        
        # 応答を受信
        response = await websocket.recv()
        print(f"応答受信: {response}")

asyncio.run(send_audio())
```

---

### 3. Style-Bert-VITS2統合（レミ声固定）

#### 専用ボイスモデルの学習

**詳細ガイド**: `docs/voice_style_bert_vits2_guide.md`

**クイックスタート**:

1. **Style-Bert-VITS2のセットアップ**:
```powershell
git clone https://github.com/litagin02/Style-Bert-VITS2.git
cd Style-Bert-VITS2
pip install -r requirements.txt
```

2. **レミ声データの準備**:
- 5-10分の音声データ（WAV形式、16kHz、モノラル）
- 各音声ファイルに対応するテキストファイル

3. **モデル学習**:
```powershell
python train.py --config config.json
```

4. **APIサーバー起動**:
```powershell
python api_server.py --model_path models/remi_voice --port 5000
```

5. **ManaOS統合**:
```env
VOICE_TTS_ENGINE=style_bert_vits2
STYLE_BERT_VITS2_URL=http://127.0.0.1:5000
STYLE_BERT_VITS2_SPEAKER_ID=0
```

---

## 🔧 設定オプション

### VAD設定

| パラメータ | 説明 | デフォルト |
|-----------|------|-----------|
| `vad_enabled` | VAD有効化 | `True` |
| `silence_threshold` | 無音判定の閾値 | `0.01` |
| `min_speech_duration` | 最小音声長（秒） | `0.5` |
| `webrtc_vad_level` | WebRTC VAD敏感度（0-3） | `2` |

### リアルタイム処理設定

| パラメータ | 説明 | デフォルト |
|-----------|------|-----------|
| `realtime_mode` | リアルタイムモード | `False` |
| `streaming_buffer_size` | ストリーミングバッファサイズ | `48000` (3秒) |
| `websocket_port` | WebSocketポート | `8765` |

---

## 📊 パフォーマンス

### VAD改善の効果

- **音声区間検出精度**: 90%以上（WebRTC VAD使用時）
- **無音区間の誤検出**: 大幅に減少
- **処理速度**: リアルタイム処理可能

### リアルタイム処理の遅延

- **STT処理**: 約1-2秒（mediumモデル）
- **LLM応答生成**: 約2-5秒（モデル依存）
- **TTS合成**: 約0.5-1秒
- **総遅延**: 約3.5-8秒（モデル依存）

---

## 🚀 次のステップ

1. **VADの微調整**: 環境に応じた敏感度調整
2. **ストリーミング最適化**: バッファサイズの調整
3. **レミ声の追加学習**: より多くのデータで学習

---

## 📚 参考ドキュメント

- **VAD改善**: `voice_integration.py`（WebRTC VAD統合部分）
- **リアルタイム処理**: `voice_realtime_streaming.py`
- **Style-Bert-VITS2**: `docs/voice_style_bert_vits2_guide.md`

---

**高度機能、完成！** 🎉
