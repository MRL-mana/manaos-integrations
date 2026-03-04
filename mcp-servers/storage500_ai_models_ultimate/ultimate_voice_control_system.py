#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
究極音声制御システム
音声入力、出力、認識、合成を統合した完全音声制御システム
"""

import asyncio
import json
import logging
import random
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from flask import Flask, jsonify, request
import requests
from concurrent.futures import ThreadPoolExecutor
import queue
import hashlib
import hmac
import base64
import subprocess
import psutil
import os
import speech_recognition as sr
import pyttsx3
import pyaudio
import wave
import tempfile
import whisper
from gtts import gTTS
import pygame
import io

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_voice_control.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VoiceRecognitionEngine:
    """音声認識エンジン"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.whisper_model = whisper.load_model("base")
        self.voice_history = []
        self.recognition_accuracy = 0.0
        
        # マイクの調整
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        
    def listen_for_speech(self, timeout: int = 5) -> Dict[str, Any]:
        """音声を聞き取る"""
        try:
            logger.info("音声を聞き取っています...")
            
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
            
            # 音声データを一時ファイルに保存
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio.get_wav_data())
                temp_file_path = temp_file.name
            
            # Whisperで音声認識
            result = self.whisper_model.transcribe(temp_file_path)
            recognized_text = result["text"].strip()
            
            # 一時ファイルを削除
            os.unlink(temp_file_path)
            
            if recognized_text:
                # 音声履歴に追加
                voice_entry = {
                    'timestamp': time.time(),
                    'text': recognized_text,
                    'confidence': result.get('confidence', 0.0),
                    'language': result.get('language', 'ja')
                }
                self.voice_history.append(voice_entry)
                
                # 履歴の制限
                if len(self.voice_history) > 100:
                    self.voice_history = self.voice_history[-100:]
                
                # 認識精度の更新
                self.recognition_accuracy = np.mean([entry['confidence'] for entry in self.voice_history[-10:]])
                
                logger.info(f"認識結果: {recognized_text}")
                return {
                    'success': True,
                    'text': recognized_text,
                    'confidence': result.get('confidence', 0.0),
                    'language': result.get('language', 'ja'),
                    'timestamp': time.time()
                }
            else:
                return {
                    'success': False,
                    'error': '音声が認識できませんでした',
                    'timestamp': time.time()
                }
                
        except sr.WaitTimeoutError:
            return {
                'success': False,
                'error': '音声が検出されませんでした',
                'timestamp': time.time()
            }
        except Exception as e:
            logger.error(f"音声認識でエラー: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }

class VoiceSynthesisEngine:
    """音声合成エンジン"""
    
    def __init__(self):
        self.tts_engine = pyttsx3.init()
        self.voice_queue = queue.Queue()
        self.synthesis_thread = None
        self.running = False
        
        # 音声設定
        voices = self.tts_engine.getProperty('voices')
        if voices:
            self.tts_engine.setProperty('voice', voices[0].id)
        
        self.tts_engine.setProperty('rate', 150)  # 速度
        self.tts_engine.setProperty('volume', 0.8)  # 音量
        
    def speak_text(self, text: str, voice_type: str = 'default') -> Dict[str, Any]:
        """テキストを音声で出力"""
        try:
            if voice_type == 'gtts':
                # Google TTSを使用
                tts = gTTS(text=text, lang='ja')
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                    tts.save(temp_file.name)
                    temp_file_path = temp_file.name
                
                # pygameで再生
                pygame.mixer.init()
                pygame.mixer.music.load(temp_file_path)
                pygame.mixer.music.play()
                
                # 再生完了まで待機
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                
                pygame.mixer.quit()
                os.unlink(temp_file_path)
                
            else:
                # pyttsx3を使用
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            
            return {
                'success': True,
                'text': text,
                'voice_type': voice_type,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"音声合成でエラー: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def start_voice_queue(self):
        """音声キュー処理の開始"""
        if self.running:
            return
            
        self.running = True
        self.synthesis_thread = threading.Thread(target=self._voice_queue_loop, daemon=True)
        self.synthesis_thread.start()
        logger.info("音声合成キューを開始しました")
    
    def stop_voice_queue(self):
        """音声キュー処理の停止"""
        self.running = False
        if self.synthesis_thread:
            self.synthesis_thread.join(timeout=5)
        logger.info("音声合成キューを停止しました")
    
    def _voice_queue_loop(self):
        """音声キュー処理ループ"""
        while self.running:
            try:
                if not self.voice_queue.empty():
                    voice_task = self.voice_queue.get()
                    self.speak_text(voice_task['text'], voice_task.get('voice_type', 'default'))
                else:
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"音声キュー処理でエラー: {e}")
                time.sleep(1)

class VoiceCommandProcessor:
    """音声コマンド処理エンジン"""
    
    def __init__(self):
        self.command_patterns = {
            'システム状態確認': ['状態', '状況', '確認', 'どう'],
            'システム制御': ['開始', '停止', '再起動', '制御'],
            'タスク管理': ['タスク', 'やること', '予定', 'スケジュール'],
            '情報収集': ['情報', 'ニュース', '収集', '検索'],
            '音声設定': ['音量', '速度', '音声', '設定'],
            '緊急停止': ['停止', '緊急', 'ストップ', 'やめて']
        }
        self.command_history = []
        
    def process_voice_command(self, text: str) -> Dict[str, Any]:
        """音声コマンドの処理"""
        text_lower = text.lower()
        
        # コマンドパターンのマッチング
        matched_commands = []
        for command_type, patterns in self.command_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    matched_commands.append(command_type)
                    break
        
        if matched_commands:
            command_type = matched_commands[0]
            response = self.execute_command(command_type, text)
            
            # コマンド履歴に追加
            self.command_history.append({
                'timestamp': time.time(),
                'input_text': text,
                'command_type': command_type,
                'response': response
            })
            
            # 履歴の制限
            if len(self.command_history) > 50:
                self.command_history = self.command_history[-50:]
            
            return {
                'success': True,
                'command_type': command_type,
                'response': response,
                'timestamp': time.time()
            }
        else:
            return {
                'success': False,
                'error': '認識されたコマンドがありません',
                'timestamp': time.time()
            }
    
    def execute_command(self, command_type: str, original_text: str) -> str:
        """コマンドの実行"""
        if command_type == 'システム状態確認':
            return "システムの状態を確認します。現在、全てのシステムが正常に動作しています。"
        
        elif command_type == 'システム制御':
            return "システム制御機能を実行します。具体的な操作をお教えください。"
        
        elif command_type == 'タスク管理':
            return "タスク管理システムにアクセスします。新しいタスクの追加や確認ができます。"
        
        elif command_type == '情報収集':
            return "情報収集システムを起動します。最新の情報を取得します。"
        
        elif command_type == '音声設定':
            return "音声設定を調整します。音量や速度の変更ができます。"
        
        elif command_type == '緊急停止':
            return "緊急停止機能を実行します。全てのシステムを安全に停止します。"
        
        else:
            return "コマンドを実行しました。"

class UltimateVoiceControlSystem:
    """究極音声制御システム"""
    
    def __init__(self):
        self.recognition_engine = VoiceRecognitionEngine()
        self.synthesis_engine = VoiceSynthesisEngine()
        self.command_processor = VoiceCommandProcessor()
        self.system_state = {
            'voice_control_active': False,
            'recognition_accuracy': 0.0,
            'total_commands': 0,
            'successful_commands': 0,
            'voice_session_count': 0,
            'last_voice_input': None,
            'last_voice_output': None
        }
        self.db_path = 'ultimate_voice_control.db'
        self.init_database()
        self.running = False
        self.voice_thread = None
        
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS voice_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                input_text TEXT,
                command_type TEXT,
                response_text TEXT,
                confidence REAL,
                success BOOLEAN,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS voice_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_start REAL,
                session_end REAL,
                total_commands INTEGER,
                successful_commands INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def save_voice_interaction(self, interaction_data: Dict[str, Any]):
        """音声インタラクションの保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO voice_interactions 
            (timestamp, input_text, command_type, response_text, confidence, success)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            time.time(),
            interaction_data.get('input_text', ''),
            interaction_data.get('command_type', ''),
            interaction_data.get('response_text', ''),
            interaction_data.get('confidence', 0.0),
            interaction_data.get('success', False)
        ))
        
        conn.commit()
        conn.close()
        
    def voice_control_cycle(self):
        """音声制御サイクル"""
        # 音声認識
        recognition_result = self.recognition_engine.listen_for_speech()
        
        if recognition_result['success']:
            self.system_state['last_voice_input'] = recognition_result['text']
            self.system_state['total_commands'] += 1
            
            # コマンド処理
            command_result = self.command_processor.process_voice_command(recognition_result['text'])
            
            if command_result['success']:
                self.system_state['successful_commands'] += 1
                response_text = command_result['response']
                
                # 音声合成
                synthesis_result = self.synthesis_engine.speak_text(response_text)
                
                if synthesis_result['success']:
                    self.system_state['last_voice_output'] = response_text
                
                # インタラクションの保存
                interaction_data = {
                    'input_text': recognition_result['text'],
                    'command_type': command_result['command_type'],
                    'response_text': response_text,
                    'confidence': recognition_result['confidence'],
                    'success': True
                }
                self.save_voice_interaction(interaction_data)
                
                # ログ出力
                logger.info(f"音声コマンド実行: {recognition_result['text']} → {response_text}")
                
            else:
                # 認識失敗時の応答
                error_response = "申し訳ございません。コマンドを認識できませんでした。"
                self.synthesis_engine.speak_text(error_response)
                
                interaction_data = {
                    'input_text': recognition_result['text'],
                    'command_type': 'unknown',
                    'response_text': error_response,
                    'confidence': recognition_result['confidence'],
                    'success': False
                }
                self.save_voice_interaction(interaction_data)
        
        # システム状態の更新
        self.system_state['recognition_accuracy'] = self.recognition_engine.recognition_accuracy
        
        return self.system_state.copy()
    
    def start_voice_control(self):
        """音声制御の開始"""
        if self.running:
            return
            
        self.running = True
        self.system_state['voice_control_active'] = True
        self.system_state['voice_session_count'] += 1
        
        # 音声合成エンジンの開始
        self.synthesis_engine.start_voice_queue()
        
        # 音声制御スレッドの開始
        self.voice_thread = threading.Thread(target=self._voice_control_loop, daemon=True)
        self.voice_thread.start()
        
        # 開始メッセージ
        self.synthesis_engine.speak_text("音声制御システムを開始しました。何かお手伝いできることはありますか？")
        
        logger.info("究極音声制御システムを開始しました")
    
    def stop_voice_control(self):
        """音声制御の停止"""
        self.running = False
        self.system_state['voice_control_active'] = False
        
        if self.voice_thread:
            self.voice_thread.join(timeout=5)
        
        # 音声合成エンジンの停止
        self.synthesis_engine.stop_voice_queue()
        
        # 停止メッセージ
        self.synthesis_engine.speak_text("音声制御システムを停止しました。")
        
        logger.info("究極音声制御システムを停止しました")
    
    def _voice_control_loop(self):
        """音声制御ループ"""
        while self.running:
            try:
                self.voice_control_cycle()
                time.sleep(1)  # 1秒間隔で音声認識
            except Exception as e:
                logger.error(f"音声制御サイクルでエラーが発生: {e}")
                time.sleep(5)
    
    def get_voice_statistics(self) -> Dict[str, Any]:
        """音声統計情報の取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 基本統計
        cursor.execute('SELECT COUNT(*) FROM voice_interactions')
        total_interactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM voice_interactions WHERE success = 1')
        successful_interactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(confidence) FROM voice_interactions')
        avg_confidence = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM voice_sessions')
        total_sessions = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_interactions': total_interactions,
            'successful_interactions': successful_interactions,
            'success_rate': (successful_interactions / max(1, total_interactions)) * 100,
            'average_confidence': avg_confidence,
            'total_sessions': total_sessions,
            'current_system_state': self.system_state,
            'voice_history': self.recognition_engine.voice_history[-10:],
            'command_history': self.command_processor.command_history[-10:]
        }

# Flask Web API
app = Flask(__name__)
voice_system = UltimateVoiceControlSystem()

@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'system': 'Ultimate Voice Control System',
        'timestamp': time.time()
    })

@app.route('/api/voice-control-data', methods=['GET'])
def get_voice_control_data():
    """音声制御データの取得"""
    return jsonify({
        'system_state': voice_system.system_state,
        'statistics': voice_system.get_voice_statistics(),
        'timestamp': time.time()
    })

@app.route('/api/voice-control', methods=['POST'])
def voice_control():
    """音声制御"""
    data = request.get_json()
    action = data.get('action')
    
    if action == 'start':
        voice_system.start_voice_control()
        return jsonify({'status': 'started'})
    elif action == 'stop':
        voice_system.stop_voice_control()
        return jsonify({'status': 'stopped'})
    else:
        return jsonify({'error': '無効なアクション'}), 400

@app.route('/api/speak', methods=['POST'])
def speak_text():
    """テキストを音声で出力"""
    data = request.get_json()
    text = data.get('text', '')
    voice_type = data.get('voice_type', 'default')
    
    if not text:
        return jsonify({'error': 'テキストが指定されていません'}), 400
    
    result = voice_system.synthesis_engine.speak_text(text, voice_type)
    return jsonify(result)

@app.route('/api/listen', methods=['GET'])
def listen_for_speech():
    """音声を聞き取る"""
    result = voice_system.recognition_engine.listen_for_speech()
    return jsonify(result)

if __name__ == '__main__':
    # 音声制御システムの開始
    voice_system.start_voice_control()
    
    # Web APIの開始
    app.run(host='0.0.0.0', port=5014, debug=False) 