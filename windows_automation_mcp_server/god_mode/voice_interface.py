#!/usr/bin/env python3
"""
音声インターフェース基盤 - 喋りかけるだけでAIと対話
Whisper（音声認識）+ TTS（音声合成）基盤
"""

import json
import time
from pathlib import Path
from typing import Optional, Dict
import subprocess
import queue

class VoiceInterface:
    """音声インターフェース"""
    
    def __init__(self):
        self.config_file = Path("/root/.mana_vault/voice_config.json")
        self.config = self._load_config()
        
        self.audio_dir = Path("/root/god_mode/voice_data")
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        self.command_queue = queue.Queue()
        self.is_listening = False
    
    def _load_config(self) -> Dict:
        """設定読み込み"""
        default_config = {
            "enabled": False,
            "wake_word": "マナ",
            "language": "ja",
            "whisper_model": "base",
            "tts_engine": "espeak",  # espeak, piper, bark
            "continuous_mode": False
        }
        
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                default_config.update(config)
        
        return default_config
    
    def check_dependencies(self) -> Dict:
        """依存関係チェック"""
        deps = {
            "ffmpeg": self._check_command("ffmpeg"),
            "espeak": self._check_command("espeak"),
            "sox": self._check_command("sox"),
            "whisper": False,  # Pythonパッケージ
            "piper": False     # オプション
        }
        
        # Whisperチェック（Pythonパッケージ）
        try:
            import whisper
            deps["whisper"] = True
        except ImportError:
            pass
        
        return deps
    
    def _check_command(self, command: str) -> bool:
        """コマンド存在確認"""
        try:
            subprocess.run(
                ["which", command],
                capture_output=True,
                check=True
            )
            return True
        except:
            return False
    
    def install_dependencies(self):
        """依存関係インストール"""
        print("📦 音声インターフェース依存関係インストール...")
        
        commands = [
            # システムパッケージ
            "apt-get update",
            "apt-get install -y ffmpeg espeak sox libsox-fmt-all",
            
            # Pythonパッケージ
            "pip3 install openai-whisper sounddevice soundfile numpy"
        ]
        
        for cmd in commands:
            print(f"  実行中: {cmd}")
            try:
                subprocess.run(
                    cmd,
                    shell=True,
                    check=True,
                    capture_output=True
                )
                print("  ✅ 完了")
            except Exception as e:
                print(f"  ⚠️  スキップ: {e}")
    
    def speak(self, text: str, save_audio: bool = False) -> bool:
        """音声合成（TTS）"""
        if not self.config.get('enabled', False):
            print(f"[Voice] {text}")
            return True
        
        try:
            if self.config['tts_engine'] == 'espeak':
                # espeak使用
                cmd = [
                    "espeak",
                    "-v", "ja",
                    "-s", "150",  # 速度
                    text
                ]
                
                if save_audio:
                    audio_file = self.audio_dir / f"tts_{int(time.time())}.wav"
                    cmd.extend(["-w", str(audio_file)])
                
                subprocess.run(cmd, check=True, capture_output=True)
                return True
            
            else:
                # 他のTTSエンジン（未実装）
                print(f"[Voice] {text}")
                return True
        
        except Exception as e:
            print(f"[Voice Error] {e}: {text}")
            return False
    
    def listen(self, duration: int = 5) -> Optional[str]:
        """音声認識（Whisper）"""
        if not self.config.get('enabled', False):
            return None
        
        try:
            import whisper
            import sounddevice as sd
            import soundfile as sf
            import numpy as np
            
            # 録音
            print("🎤 聞いています...")
            sample_rate = 16000
            audio = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype=np.float32
            )
            sd.wait()
            
            # 一時ファイル保存
            temp_file = self.audio_dir / f"input_{int(time.time())}.wav"
            sf.write(temp_file, audio, sample_rate)
            
            # Whisper認識
            print("🧠 認識中...")
            model = whisper.load_model(self.config['whisper_model'])
            result = model.transcribe(
                str(temp_file),
                language=self.config['language']
            )
            
            text = result['text'].strip()
            print(f"📝 認識結果: {text}")
            
            return text
        
        except Exception as e:
            print(f"❌ 音声認識エラー: {e}")
            return None
    
    def process_voice_command(self, command: str) -> str:
        """音声コマンド処理"""
        command = command.lower()
        
        # 簡易コマンドマッチング
        if "ステータス" in command or "状態" in command:
            try:
                from god_mode.lightweight_monitor import get_monitor
                monitor = get_monitor()
                status = monitor.get_current_status()
                
                health = status['health_score']
                response = f"現在の健全性スコアは{health}点です。"
                
                if health >= 80:
                    response += "システムは正常に動作しています。"
                else:
                    response += "注意が必要です。"
                
                return response
            except:
                return "ステータス取得に失敗しました。"
        
        elif "レベル3" in command or "レベルスリー" in command:
            try:
                from level3.level3_master_controller import Level3MasterController
                controller = Level3MasterController()
                status = controller.get_status()
                
                running = sum(1 for s in status['processes'].values() if s['running'])
                total = len(status['processes'])
                
                return f"レベル3システムは{total}個中{running}個が稼働中です。"
            except:
                return "レベル3ステータス取得に失敗しました。"
        
        elif "おはよう" in command:
            return "おはようございます。今日も頑張りましょう。"
        
        elif "おやすみ" in command:
            return "おやすみなさい。良い夢を。"
        
        else:
            return f"コマンド「{command}」は認識できませんでした。"
    
    def start_continuous_listening(self):
        """連続聴取モード"""
        print("\n🎤 連続聴取モード開始")
        print(f"   ウェイクワード: {self.config['wake_word']}")
        print("   Ctrl+C で停止\n")
        
        self.is_listening = True
        
        try:
            while self.is_listening:
                # 音声入力待ち
                text = self.listen(duration=3)
                
                if text and self.config['wake_word'] in text:
                    self.speak("はい、どうぞ。")
                    
                    # コマンド聴取
                    command = self.listen(duration=5)
                    
                    if command:
                        # コマンド処理
                        response = self.process_voice_command(command)
                        self.speak(response)
                    else:
                        self.speak("聞き取れませんでした。")
                
                time.sleep(0.5)
        
        except KeyboardInterrupt:
            print("\n\n🛑 連続聴取モード停止")
            self.is_listening = False
    
    def demo_mode(self):
        """デモモード（依存関係なしでテスト）"""
        print("\n" + "=" * 70)
        print("🎤 音声インターフェース - デモモード")
        print("=" * 70)
        
        test_commands = [
            "ステータスを教えて",
            "レベル3の状態は？",
            "おはよう"
        ]
        
        for command in test_commands:
            print(f"\n[入力] {command}")
            response = self.process_voice_command(command)
            print(f"[応答] {response}")
            self.speak(response)
        
        print("\n" + "=" * 70)

# グローバルインスタンス
_voice = None

def get_voice_interface() -> VoiceInterface:
    """グローバル音声インターフェース取得"""
    global _voice
    if _voice is None:
        _voice = VoiceInterface()
    return _voice

# テスト実行
if __name__ == "__main__":
    import sys
    
    voice = VoiceInterface()
    
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        # 依存関係インストール
        voice.install_dependencies()
    
    elif len(sys.argv) > 1 and sys.argv[1] == "listen":
        # 連続聴取モード
        voice.start_continuous_listening()
    
    else:
        # デモモード
        print("\n" + "=" * 70)
        print("🎤 音声インターフェース基盤")
        print("=" * 70)
        
        print("\n[依存関係チェック]")
        deps = voice.check_dependencies()
        for name, available in deps.items():
            status = "✅" if available else "❌"
            print(f"  {status} {name}")
        
        print("\n[設定]")
        print(f"  有効: {voice.config['enabled']}")
        print(f"  ウェイクワード: {voice.config['wake_word']}")
        print(f"  言語: {voice.config['language']}")
        print(f"  TTSエンジン: {voice.config['tts_engine']}")
        
        print("\n" + "=" * 70)
        print("💡 使い方:")
        print("  # 依存関係インストール")
        print("  python3 voice_interface.py install")
        print("")
        print("  # デモモード")
        print("  python3 voice_interface.py")
        print("")
        print("  # 連続聴取モード")
        print("  python3 voice_interface.py listen")
        print("=" * 70)
        
        # デモ実行
        voice.demo_mode()

