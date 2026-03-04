#!/usr/bin/env python3
"""
Trinity v2.0 音声インターフェース
=================================

音声でTrinityを操作できるシステム

Author: Luna & Mina
Created: 2025-10-18
License: MIT
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
from db_manager import DatabaseManager

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    print("⚠️ speech_recognition not installed. Install with: pip install SpeechRecognition pyaudio")


class VoiceInterface:
    """
    Trinity音声インターフェース
    
    機能:
    - 音声認識（Google Speech Recognition）
    - 音声コマンド解析
    - タスク自動作成
    - 音声フィードバック
    
    使用例:
    ```python
    voice = VoiceInterface()
    await voice.start_listening()
    ```
    """
    
    def __init__(self):
        """初期化"""
        self.db = DatabaseManager()
        self.recognizer = sr.Recognizer() if SPEECH_RECOGNITION_AVAILABLE else None
        self.running = False
        
        # コマンドパターン
        self.command_patterns = {
            'create_task': ['タスク作成', 'タスクを作る', 'create task', 'new task'],
            'list_tasks': ['タスク一覧', 'タスクを見せて', 'list tasks', 'show tasks'],
            'status': ['ステータス', '状態', 'status'],
            'help': ['ヘルプ', '使い方', 'help'],
            'stop': ['停止', 'ストップ', 'stop', 'exit']
        }
    
    async def start_listening(self):
        """音声リスニング開始"""
        print("=" * 60)
        print("🎤 Trinity 音声インターフェース")
        print("=" * 60)
        print()
        
        if not SPEECH_RECOGNITION_AVAILABLE:
            print("❌ 音声認識ライブラリがインストールされていません")
            print("📦 インストール: pip install SpeechRecognition pyaudio")
            print()
            print("📝 テキストモードで起動します...")
            await self._text_mode()
            return
        
        print("🎤 音声認識開始...")
        print("💡 「ヘルプ」と言ってコマンドを確認")
        print("🛑 「停止」と言って終了")
        print()
        
        self.running = True
        
        while self.running:
            try:
                await self._listen_and_process()
            except KeyboardInterrupt:
                print("\n⚠️ 音声認識を停止します")
                break
            except Exception as e:
                print(f"❌ エラー: {e}")
                await asyncio.sleep(1)
        
        print("\n✅ 音声インターフェース終了")
    
    async def _listen_and_process(self):
        """音声を聞いて処理"""
        with sr.Microphone() as source:
            print("🎤 聞いています... (話してください)")
            
            # ノイズ調整
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            try:
                # 音声録音
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                print("🔄 認識中...")
                
                # Google Speech Recognition
                text = self.recognizer.recognize_google(audio, language='ja-JP')
                
                print(f"✅ 認識結果: {text}")
                print()
                
                # コマンド処理
                await self._process_command(text)
                
            except sr.WaitTimeoutError:
                print("⏰ タイムアウト（音声が聞こえませんでした）")
            except sr.UnknownValueError:
                print("❓ 音声を認識できませんでした")
            except sr.RequestError as e:
                print(f"❌ 音声認識サービスエラー: {e}")
    
    async def _process_command(self, text: str):
        """コマンド処理"""
        text_lower = text.lower()
        
        # コマンド判定
        if any(keyword in text_lower for keyword in self.command_patterns['help']):
            self._show_help()
        
        elif any(keyword in text_lower for keyword in self.command_patterns['stop']):
            print("🛑 音声認識を停止します")
            self.running = False
        
        elif any(keyword in text_lower for keyword in self.command_patterns['status']):
            await self._show_status()
        
        elif any(keyword in text_lower for keyword in self.command_patterns['list_tasks']):
            await self._list_tasks()
        
        elif any(keyword in text_lower for keyword in self.command_patterns['create_task']):
            await self._create_task_from_voice(text)
        
        else:
            # 自動タスク作成
            print(f"💡 自動タスク作成モード")
            await self._create_task_from_voice(text)
    
    def _show_help(self):
        """ヘルプ表示"""
        print("=" * 60)
        print("📖 Trinity 音声コマンド")
        print("=" * 60)
        print()
        print("🎤 利用可能なコマンド:")
        print("  • 「タスク作成」 - 新しいタスクを作成")
        print("  • 「タスク一覧」 - タスク一覧を表示")
        print("  • 「ステータス」 - システム状態を表示")
        print("  • 「ヘルプ」 - このヘルプを表示")
        print("  • 「停止」 - 音声認識を終了")
        print()
        print("💡 自然な言葉で話してもOK:")
        print("  • 「ECサイトを作る」")
        print("  • 「バグを修正して」")
        print("  • 「ドキュメントを書いて」")
        print()
    
    async def _show_status(self):
        """ステータス表示"""
        stats = self.db.get_statistics()
        
        print("=" * 60)
        print("📊 Trinity システムステータス")
        print("=" * 60)
        print()
        print(f"  総タスク数: {stats['total_tasks']}")
        print(f"  完了: {stats['completed_tasks']} ({stats['completion_rate']:.1f}%)")
        print(f"  進行中: {stats['in_progress_tasks']}")
        print(f"  未着手: {stats['todo_tasks']}")
        print()
    
    async def _list_tasks(self):
        """タスク一覧表示"""
        tasks = self.db.get_tasks(limit=5)
        
        print("=" * 60)
        print("📋 最近のタスク（最新5件）")
        print("=" * 60)
        print()
        
        for i, task in enumerate(tasks, 1):
            status_icon = {
                'todo': '⏳',
                'in_progress': '🔄',
                'review': '👀',
                'done': '✅',
                'blocked': '🚫'
            }.get(task['status'], '❓')
            
            print(f"{i}. {status_icon} {task['id']}: {task['title'][:50]}")
            print(f"   担当: {task.get('assigned_to', 'N/A')} | 優先度: {task.get('priority', 'N/A')}")
        print()
    
    async def _create_task_from_voice(self, text: str):
        """音声からタスク作成"""
        print(f"📝 タスク作成中: {text}")
        
        # タスクデータ生成
        task_id = f"VOICE-{int(datetime.now().timestamp())}"
        task_data = {
            'id': task_id,
            'title': text,
            'status': 'todo',
            'priority': 'medium',
            'assigned_to': 'Luna',
            'created_by': 'VoiceInterface',
            'created_at': datetime.now().isoformat(),
            'tags': ['voice-created']
        }
        
        # タスク作成
        success = self.db.create_task(task_data)
        
        if success:
            print(f"✅ タスク作成完了: {task_id}")
            print(f"   タイトル: {text}")
            print(f"   担当: Luna")
            print()
        else:
            print(f"❌ タスク作成失敗")
    
    async def _text_mode(self):
        """テキストモード（音声認識なし）"""
        print()
        print("📝 テキストモードで起動しました")
        print("💡 コマンドを入力してください（'help' でヘルプ）")
        print()
        
        while True:
            try:
                user_input = input("🎤 >>> ")
                
                if not user_input.strip():
                    continue
                
                if user_input.lower() in ['exit', 'quit', '停止', 'ストップ']:
                    break
                
                await self._process_command(user_input)
                
            except KeyboardInterrupt:
                print("\n\n✅ テキストモード終了")
                break
            except Exception as e:
                print(f"❌ エラー: {e}")


async def main():
    """メイン関数"""
    voice = VoiceInterface()
    await voice.start_listening()


if __name__ == "__main__":
    asyncio.run(main())

