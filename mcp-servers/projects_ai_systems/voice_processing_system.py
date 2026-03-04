#!/usr/bin/env python3
"""
🎤 Trinity Voice Processing System
音声メッセージ処理システム

機能:
- 音声→テキスト変換（Whisper API）
- 自動会話処理
- 音声コマンド認識
"""

import asyncio
import logging
from typing import Dict, Any, Optional
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceProcessingSystem:
    """音声処理システム"""
    
    def __init__(self):
        # API設定
        self.openai_key = os.getenv('OPENAI_API_KEY')
        
        logger.info("🎤 Voice Processing System initialized")
        logger.info(f"  🔑 OpenAI Whisper: {bool(self.openai_key)}")
    
    async def transcribe_voice(self, voice_file_path: str) -> Dict[str, Any]:
        """
        音声ファイルをテキストに変換
        
        Args:
            voice_file_path: 音声ファイルのパス
        
        Returns:
            変換結果
        """
        logger.info("🎤 Transcribing voice file...")
        
        # OpenAI Whisper API使用
        if self.openai_key:
            result = await self._transcribe_with_whisper(voice_file_path)
            if result:
                return result
        
        # フォールバック: ローカル処理（将来実装）
        return {
            'text': '',
            'confidence': 0,
            'method': 'none',
            'error': '音声認識APIが利用できません。OpenAI APIキーを設定してください。'
        }
    
    async def _transcribe_with_whisper(self, voice_file_path: str) -> Optional[Dict]:
        """OpenAI Whisper APIで音声認識"""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.openai_key)
            
            # 音声ファイルを開く
            with open(voice_file_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ja"  # 日本語指定
                )
            
            text = transcript.text
            
            logger.info("  ✅ Whisper transcription complete")
            logger.info(f"  📝 Transcribed: {text[:50]}...")
            
            return {
                'text': text,
                'confidence': 95,
                'method': 'whisper_api',
                'duration': 0  # APIは返さない
            }
            
        except Exception as e:
            logger.error(f"  ❌ Whisper API failed: {e}")
            return None
    
    def extract_command(self, text: str) -> Optional[str]:
        """音声テキストからコマンドを抽出"""
        # コマンド系キーワード
        command_patterns = {
            '検索': 'search',
            'システム': 'system',
            '予定': 'schedule',
            'タスク': 'tasks',
            '統計': 'stats',
            'リマインダー': 'reminders'
        }
        
        for keyword, command in command_patterns.items():
            if keyword in text:
                return command
        
        return None


# テスト用
async def test_voice_processing():
    """音声処理システムのテスト"""
    system = VoiceProcessingSystem()
    
    print("\n" + "="*60)
    print("🎤 Voice Processing System - Test")
    print("="*60)
    
    # テスト1: コマンド抽出
    print("\n📝 Test: Command extraction")
    
    test_texts = [
        "明日の予定を教えて",
        "システムの状態を確認して",
        "プロジェクトについて検索して"
    ]
    
    for text in test_texts:
        command = system.extract_command(text)
        print(f"  '{text}' → {command}")
    
    print("\n✅ Voice Processing System test complete")


if __name__ == '__main__':
    asyncio.run(test_voice_processing())



