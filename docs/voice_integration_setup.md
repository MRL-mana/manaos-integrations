# 🎤 ManaOS 音声機能統合 セットアップガイド

秘書レミ完全体の最後のピース - 音声入力（STT）と音声生成（TTS）の統合

---

## 📋 目次

1. [概要](#概要)
2. [フェーズ1: 最短で動かす（推奨）](#フェーズ1-最短で動かす推奨)
3. [フェーズ2: 秘書化](#フェーズ2-秘書化)
4. [フェーズ3: 完全体](#フェーズ3-完全体)
5. [トラブルシューティング](#トラブルシューティング)

---

## 概要

ManaOS音声機能統合は、以下の3つのコンポーネントで構成されています：

- **STT (Speech-to-Text)**: 音声をテキストに変換（Whisper系）
- **TTS (Text-to-Speech)**: テキストを音声に変換（VOICEVOX / Style-Bert-VITS2）
- **会話ループ**: STT → LLM → TTS の自動循環

---

## フェーズ1: 最短で動かす（推奨）

### 1. 依存関係のインストール

#### Windows（マナの母艦）

```powershell
# Python環境をアクティベート
# （仮想環境を使用している場合）

# 基本パッケージ
pip install faster-whisper
pip install openai-whisper
pip install numpy

# マイク入力（Windows）
# 方法1: pipwinを使用（推奨）
pip install pipwin
pipwin install pyaudio

# 方法2: condaを使用
conda install pyaudio

# 方法3: ビルド済みwheelを使用
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio からダウンロード
```

#### Linux / macOS

```bash
# システム依存関係（Linux）
sudo apt-get install portaudio19-dev python3-pyaudio

# macOS
brew install portaudio

# Pythonパッケージ
pip install faster-whisper
pip install openai-whisper
pip install pyaudio
pip install numpy
```

### 2. VOICEVOXのインストールと起動

#### Windows

1. **VOICEVOX公式サイトからダウンロード**
   - https://voicevox.hiroshiba.jp/
   - 最新版をダウンロードしてインストール

2. **VOICEVOXを起動**
   ```powershell
   # VOICEVOXを起動（デフォルトポート: 50021）
   # 起動後、http://127.0.0.1:50021 でAPIが利用可能
   ```

#### Docker（推奨）

```bash
docker run --rm -it -p 50021:50021 voicevox/voicevox_engine:cpu-ubuntu20.04-latest
```

### 3. 環境変数の設定

`.env`ファイルに以下を追加：

```env
# 音声機能統合設定
VOICE_STT_MODEL=large-v3          # STTモデルサイズ（tiny, base, small, medium, large-v3）
VOICE_STT_DEVICE=cuda              # デバイス（cuda, cpu）
VOICE_STT_COMPUTE_TYPE=float16     # 計算タイプ（float16, int8, int8_float16）

VOICE_TTS_ENGINE=voicevox          # TTSエンジン（voicevox, style_bert_vits2）
VOICEVOX_URL=http://127.0.0.1:50021
VOICEVOX_SPEAKER_ID=3              # スピーカーID（VOICEVOX用）
```

### 4. ManaOS統合APIサーバーの起動

```powershell
python unified_api_server.py
```

### 5. 動作確認

#### 音声認識（STT）テスト

```powershell
# 音声ファイル（WAV形式）を用意してテスト
curl -X POST http://127.0.0.1:9502/api/voice/transcribe `
  -F "audio=@test_audio.wav" `
  -F "sample_rate=16000"
```

#### 音声合成（TTS）テスト

```powershell
curl -X POST http://127.0.0.1:9502/api/voice/synthesize `
  -H "Content-Type: application/json" `
  -d "{\"text\": \"こんにちは、レミです。\"}"
```

#### 音声会話テスト

```powershell
# 音声ファイルを送信して、音声応答を取得
curl -X POST http://127.0.0.1:9502/api/voice/conversation `
  -F "audio=@user_audio.wav" `
  -F "sample_rate=16000" `
  -o response.wav
```

---

## フェーズ2: 秘書化

### ホットワード機能の実装

音声会話ループにホットワード（「レミ」）を追加：

```python
from voice_integration import create_voice_conversation_loop, create_stt_engine, create_tts_engine

# エンジン初期化
stt_engine = create_stt_engine(model_size="large-v3", device="cuda")
tts_engine = create_tts_engine(engine="voicevox", speaker_id=3)

# LLMコールバック（既存のLLMルーティングを使用）
def llm_callback(text: str) -> str:
    # 既存のLLMルーティングを使用
    llm_router = integrations.get("llm_routing")
    result = llm_router.route(task_type="conversation", prompt=text)
    return result.get("response", "")

# 会話ループ作成（ホットワード: "レミ"）
conversation_loop = create_voice_conversation_loop(
    stt_engine=stt_engine,
    tts_engine=tts_engine,
    llm_callback=llm_callback,
    hotword="レミ"
)

# 開始
conversation_loop.start()
```

### Intent Routerとの統合

音声入力から意図を分類して、適切なアクションを実行：

```python
# 音声認識 → 意図分類 → ツール実行 → 応答生成 → 音声合成
```

### Notion/Slackログ同期

会話履歴を自動的にNotionやSlackに保存：

```python
# conversation_loop.conversation_history を定期的に保存
```

---

## フェーズ3: 完全体

### Style-Bert-VITS2でレミ声固定

1. **Style-Bert-VITS2のセットアップ**
   - https://github.com/litagin02/Style-Bert-VITS2
   - レミの声データで学習

2. **環境変数の更新**

```env
VOICE_TTS_ENGINE=style_bert_vits2
STYLE_BERT_VITS2_URL=http://127.0.0.1:5000
```

### 常時監視モード

イヤホン運用で常時ON：

```python
# マイク入力の常時監視
# VAD（Voice Activity Detection）で音声区間を検出
# ホットワード検出 → 会話開始
```

### 会話からタスク化の自動登録

音声会話から自動的にタスクを生成：

```python
# 「明日の会議の準備をして」→ タスク自動登録
```

---

## トラブルシューティング

### STT（音声認識）の問題

#### 問題: faster-whisperがインストールできない

**解決策**:
```powershell
# CUDA対応版をインストール
pip install faster-whisper[cuda]

# CPU版のみ
pip install faster-whisper[cpu]
```

#### 問題: モデルダウンロードが遅い

**解決策**:
```powershell
# 事前にモデルをダウンロード
python -c "from faster_whisper import WhisperModel; WhisperModel('large-v3')"
```

#### 問題: 認識精度が低い

**解決策**:
- モデルサイズを大きくする（`medium` → `large-v3`）
- サンプリングレートを確認（16000Hz推奨）
- ノイズ除去を実施

### TTS（音声合成）の問題

#### 問題: VOICEVOXが起動しない

**解決策**:
```powershell
# ポートが使用中でないか確認
netstat -ano | findstr :50021

# VOICEVOXを再起動
```

#### 問題: 音声が生成されない

**解決策**:
- VOICEVOX APIの状態を確認: `http://127.0.0.1:50021/docs`
- スピーカーIDが正しいか確認: `/api/voice/speakers`

### マイク入力の問題

#### 問題: pyaudioがインストールできない（Windows）

**解決策**:
```powershell
# pipwinを使用（推奨）
pip install pipwin
pipwin install pyaudio

# または、condaを使用
conda install pyaudio
```

#### 問題: マイクが認識されない

**解決策**:
```python
# 利用可能なマイクデバイスを確認
import pyaudio
p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    print(f"{i}: {info['name']}")
```

### パフォーマンスの問題

#### 問題: STTが遅い

**解決策**:
- モデルサイズを小さくする（`large-v3` → `medium`）
- `compute_type`を調整（`float16` → `int8`）
- GPU使用を確認

#### 問題: メモリ使用量が高い

**解決策**:
- モデルサイズを小さくする
- CPUモードに切り替え（`VOICE_STT_DEVICE=cpu`）

---

## 次のステップ

1. **フェーズ1を完了** → 基本的な音声機能が動作
2. **フェーズ2を実装** → ホットワードとIntent Router統合
3. **フェーズ3を実装** → 完全体秘書レミ

---

## 参考リンク

- [faster-whisper GitHub](https://github.com/guillaumekln/faster-whisper)
- [VOICEVOX公式サイト](https://voicevox.hiroshiba.jp/)
- [Style-Bert-VITS2 GitHub](https://github.com/litagin02/Style-Bert-VITS2)
- [Whisperモデル一覧](https://github.com/openai/whisper#available-models-and-languages)

---

**質問や問題があれば、ManaOSのログを確認してください！** 🚀

