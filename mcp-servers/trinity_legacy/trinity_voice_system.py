#!/usr/bin/env python3
"""
🎤 Trinity Voice System
Whisper音声認識 + TTS音声合成システム

音声で秘書に指示！音声で返答！
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

import whisper
import pyttsx3
import sounddevice as sd
from scipy.io.wavfile import write as write_wav

# 設定
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TrinityVoiceSystem:
    """Trinity音声システム"""
    
    def __init__(
        self,
        whisper_model: str = "base",  # tiny, base, small, medium, large
        sample_rate: int = 16000,
        record_duration: int = 10
    ):
        """
        初期化
        
        Args:
            whisper_model: Whisperモデルサイズ
            sample_rate: サンプリングレート
            record_duration: 録音時間（秒）
        """
        logger.info("🎤 Trinity Voice System 初期化中...")
        
        # Whisper音声認識モデル
        logger.info(f"   Whisperモデル読み込み中: {whisper_model}")
        self.whisper_model = whisper.load_model(whisper_model)
        
        # TTS音声合成エンジン
        logger.info("   TTSエンジン初期化中...")
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 150)  # 速度
        self.tts_engine.setProperty('volume', 0.9)  # 音量
        
        # 音声設定
        self.sample_rate = sample_rate
        self.record_duration = record_duration
        
        # 一時ファイルディレクトリ
        self.temp_dir = Path("/root/logs/voice_temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 統計
        self.transcriptions_count = 0
        self.tts_count = 0
        
        logger.info("✅ Trinity Voice System 初期化完了！")
    
    def record_audio(self, duration: Optional[int] = None) -> str:
        """
        音声を録音
        
        Args:
            duration: 録音時間（省略時はデフォルト値）
            
        Returns:
            録音ファイルのパス
        """
        duration = duration or self.record_duration
        
        logger.info(f"🎤 録音開始... ({duration}秒)")
        
        try:
            # 録音
            audio_data = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype='int16'
            )
            sd.wait()
            
            # ファイル保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_path = self.temp_dir / f"recording_{timestamp}.wav"
            write_wav(str(audio_path), self.sample_rate, audio_data)
            
            logger.info(f"✅ 録音完了: {audio_path}")
            return str(audio_path)
            
        except Exception as e:
            logger.error(f"❌ 録音エラー: {e}")
            raise
    
    def transcribe(self, audio_path: str, language: str = "ja") -> Dict[str, Any]:
        """
        音声をテキストに変換
        
        Args:
            audio_path: 音声ファイルパス
            language: 言語コード (ja=日本語, en=英語)
            
        Returns:
            {
                "text": "認識されたテキスト",
                "language": "ja",
                "confidence": 0.95
            }
        """
        logger.info(f"🔄 音声認識中: {audio_path}")
        
        try:
            # Whisperで文字起こし
            result = self.whisper_model.transcribe(
                audio_path,
                language=language,
                fp16=False  # CPU使用時はFalse
            )
            
            text = result["text"].strip()
            logger.info(f"✅ 認識結果: {text}")
            
            self.transcriptions_count += 1
            
            return {
                "text": text,
                "language": result.get("language", language),
                "confidence": 1.0,  # Whisperは信頼度を返さない
                "segments": result.get("segments", [])
            }
            
        except Exception as e:
            logger.error(f"❌ 音声認識エラー: {e}")
            raise
    
    def speak(self, text: str, save_to_file: Optional[str] = None) -> bool:
        """
        テキストを音声で読み上げ
        
        Args:
            text: 読み上げるテキスト
            save_to_file: ファイルに保存する場合のパス
            
        Returns:
            成功したかどうか
        """
        logger.info(f"🔊 読み上げ中: {text[:50]}...")
        
        try:
            if save_to_file:
                self.tts_engine.save_to_file(text, save_to_file)
                self.tts_engine.runAndWait()
            else:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            
            self.tts_count += 1
            logger.info("✅ 読み上げ完了")
            return True
            
        except Exception as e:
            logger.error(f"❌ 読み上げエラー: {e}")
            return False
    
    async def voice_conversation(self, trinity_client=None):
        """
        音声会話セッション
        
        Args:
            trinity_client: Trinity秘書クライアント（オプション）
        """
        print("\n" + "="*60)
        print("🎤 Trinity Voice Conversation")
        print("="*60)
        print("\n操作:")
        print("  Enter   - 録音開始（10秒間）")
        print("  Ctrl+C  - 終了")
        print("\n" + "="*60 + "\n")
        
        try:
            while True:
                # 録音開始待ち
                input("✨ 準備ができたらEnterを押してください... ")
                
                # 録音
                print("🎤 録音中... (10秒間話してください)")
                audio_path = self.record_audio()
                
                # 認識
                print("🔄 音声認識中...")
                result = self.transcribe(audio_path)
                text = result["text"]
                
                print(f"\n📝 あなた: {text}\n")
                
                # Trinity秘書に送信（実装されている場合）
                if trinity_client:
                    response = await trinity_client.send_message(text)
                    response_text = response.get("response", "応答がありません")
                else:
                    response_text = f"「{text}」を承りました。Trinity秘書との連携は未実装です。"
                
                print(f"🤖 Trinity: {response_text}\n")
                
                # 読み上げ
                self.speak(response_text)
                
                print("-" * 60 + "\n")
                
        except KeyboardInterrupt:
            print("\n\n👋 音声会話を終了します。\n")
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報取得"""
        return {
            "transcriptions": self.transcriptions_count,
            "tts_count": self.tts_count,
            "model": "whisper-base",
            "sample_rate": self.sample_rate
        }


# テスト用関数
async def test_voice_system():
    """音声システムのテスト"""
    print("\n" + "="*60)
    print("🎤 Trinity Voice System テスト")
    print("="*60 + "\n")
    
    # 初期化
    voice = TrinityVoiceSystem(whisper_model="base")
    
    # テスト1: TTS読み上げ
    print("📢 テスト1: TTS読み上げ\n")
    test_texts = [
        "こんにちは！Trinityです。",
        "音声システムのテストを開始します。",
        "日本語の音声認識と音声合成が動作しています。"
    ]
    
    for text in test_texts:
        print(f"   🔊 読み上げ: {text}")
        voice.speak(text)
        await asyncio.sleep(1)
    
    print("\n" + "-"*60 + "\n")
    
    # テスト2: 音声認識（オプション）
    print("📢 テスト2: 音声認識（オプション）\n")
    print("   音声認識をテストしますか？ (y/n): ", end="")
    
    try:
        response = input().lower()
        if response == 'y':
            print("\n   🎤 10秒間で何か話してください...")
            audio_path = voice.record_audio(duration=10)
            
            print("   🔄 音声認識中...")
            result = voice.transcribe(audio_path)
            
            print(f"\n   ✅ 認識結果: {result['text']}\n")
            print(f"   📊 言語: {result['language']}")
            
            # 認識結果を読み上げ
            print("\n   🔊 認識結果を読み上げます...")
            voice.speak(f"認識結果は、{result['text']}、です。")
    
    except KeyboardInterrupt:
        print("\n   スキップしました。")
    
    print("\n" + "-"*60 + "\n")
    
    # 統計表示
    stats = voice.get_stats()
    print("📊 統計:")
    print(f"   音声認識回数: {stats['transcriptions']}")
    print(f"   音声合成回数: {stats['tts_count']}")
    print(f"   モデル: {stats['model']}")
    print(f"   サンプリングレート: {stats['sample_rate']} Hz")
    
    print("\n" + "="*60 + "\n")


# 音声会話モード
async def voice_conversation_mode():
    """音声会話モード起動"""
    voice = TrinityVoiceSystem(whisper_model="base")
    await voice.voice_conversation()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "conversation":
        # 音声会話モード
        asyncio.run(voice_conversation_mode())
    else:
        # テストモード
        asyncio.run(test_voice_system())

