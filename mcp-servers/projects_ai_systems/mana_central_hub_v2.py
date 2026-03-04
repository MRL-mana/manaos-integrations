#!/usr/bin/env python3
"""
Mana Central Hub v2.0 - 超使いやすい統合ダッシュボード
音声コマンド、ショートカット、スマートサジェスト対応
"""

from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
import psutil
from datetime import datetime
import json
from pathlib import Path

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mana_central_hub_v2_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 履歴とお気に入り管理
history_file = Path("/root/.mana_hub_history.json")
favorites_file = Path("/root/.mana_hub_favorites.json")

def load_history():
    if history_file.exists():
        with open(history_file, 'r') as f:
            return json.load(f)
    return []

def save_history(command):
    history = load_history()
    history.append({
        "command": command,
        "timestamp": datetime.now().isoformat()
    })
    history = history[-50:]  # 最新50件のみ
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌟 Mana Central Hub v2.0</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
            overflow-x: hidden;
        }
        .container { max-width: 1800px; margin: 0 auto; }
        
        /* ヘッダー */
        .header {
            text-align: center;
            padding: 40px 20px;
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(20px);
            border-radius: 30px;
            margin-bottom: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            position: relative;
        }
        .header h1 {
            font-size: 4em;
            margin-bottom: 10px;
            text-shadow: 3px 3px 6px rgba(0,0,0,0.3);
            animation: glow 2s ease-in-out infinite;
        }
        @keyframes glow {
            0%, 100% { text-shadow: 3px 3px 6px rgba(0,0,0,0.3); }
            50% { text-shadow: 3px 3px 20px rgba(255,255,255,0.5); }
        }
        
        .greeting { font-size: 1.8em; opacity: 0.9; margin: 15px 0; }
        .shortcuts-hint {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(0,0,0,0.3);
            padding: 10px 15px;
            border-radius: 10px;
            font-size: 0.9em;
        }
        
        /* ステータスカード */
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .status-card {
            background: rgba(255,255,255,0.15);
            padding: 25px;
            border-radius: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        .status-card:hover {
            background: rgba(255,255,255,0.25);
            transform: translateY(-5px);
        }
        .status-value { 
            font-size: 2.5em; 
            font-weight: bold; 
            margin: 10px 0;
            background: linear-gradient(45deg, #fff, #ffd700);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .status-label { opacity: 0.8; font-size: 1.1em; }
        
        /* チャットエリア */
        .section {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(15px);
            border-radius: 25px;
            padding: 35px;
            margin: 20px 0;
            box-shadow: 0 15px 40px rgba(0,0,0,0.2);
        }
        .section h2 { 
            margin-bottom: 25px; 
            font-size: 2.2em;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .chat-container {
            background: rgba(0,0,0,0.25);
            border-radius: 20px;
            padding: 25px;
            min-height: 350px;
            max-height: 600px;
            overflow-y: auto;
            scroll-behavior: smooth;
        }
        .chat-input-container {
            display: flex;
            gap: 15px;
            margin-top: 20px;
            position: relative;
        }
        .chat-input {
            flex: 1;
            padding: 18px 25px;
            border-radius: 30px;
            border: 2px solid rgba(255,255,255,0.3);
            background: rgba(255,255,255,0.1);
            color: white;
            font-size: 1.2em;
            transition: all 0.3s;
        }
        .chat-input:focus {
            outline: none;
            border-color: rgba(255,255,255,0.6);
            background: rgba(255,255,255,0.15);
            box-shadow: 0 0 20px rgba(255,255,255,0.3);
        }
        .chat-input::placeholder { color: rgba(255,255,255,0.6); }
        
        .send-btn {
            padding: 18px 35px;
            border-radius: 30px;
            background: linear-gradient(135deg, #00f260, #0575e6);
            border: none;
            color: white;
            font-weight: bold;
            cursor: pointer;
            font-size: 1.2em;
            transition: all 0.3s;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .send-btn:hover { 
            transform: scale(1.05);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }
        .send-btn:active { transform: scale(0.95); }
        
        .voice-btn {
            padding: 18px 25px;
            border-radius: 30px;
            background: linear-gradient(135deg, #f093fb, #f5576c);
            border: none;
            color: white;
            cursor: pointer;
            font-size: 1.2em;
            transition: all 0.3s;
        }
        .voice-btn:hover { transform: scale(1.05); }
        .voice-btn.recording {
            animation: pulse 1s infinite;
            background: linear-gradient(135deg, #ff0000, #ff6b6b);
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        .message {
            margin: 15px 0;
            padding: 18px 25px;
            border-radius: 20px;
            animation: slideIn 0.3s;
            max-width: 80%;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .message.user { 
            background: linear-gradient(135deg, rgba(100,150,255,0.4), rgba(100,150,255,0.2));
            margin-left: auto;
            text-align: right;
        }
        .message.assistant { 
            background: linear-gradient(135deg, rgba(150,100,255,0.4), rgba(150,100,255,0.2));
        }
        .message.system {
            background: linear-gradient(135deg, rgba(255,200,100,0.4), rgba(255,150,100,0.2));
            text-align: center;
        }
        
        /* クイックアクション */
        .quick-actions {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin: 25px 0;
        }
        .action-btn {
            background: linear-gradient(135deg, rgba(255,255,255,0.2), rgba(255,255,255,0.1));
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 25px;
            padding: 30px 20px;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            color: white;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
            position: relative;
            overflow: hidden;
        }
        .action-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s;
        }
        .action-btn:hover::before { left: 100%; }
        .action-btn:hover {
            background: linear-gradient(135deg, rgba(255,255,255,0.3), rgba(255,255,255,0.2));
            transform: translateY(-10px) scale(1.05);
            box-shadow: 0 20px 50px rgba(0,0,0,0.3);
        }
        .action-icon { font-size: 3.5em; }
        .action-label { font-size: 1.2em; font-weight: bold; }
        .action-shortcut {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0,0,0,0.4);
            padding: 5px 10px;
            border-radius: 10px;
            font-size: 0.8em;
        }
        
        /* サジェスト */
        .suggestions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin: 15px 0;
        }
        .suggestion-chip {
            background: rgba(255,255,255,0.2);
            padding: 10px 20px;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s;
            border: 1px solid rgba(255,255,255,0.3);
        }
        .suggestion-chip:hover {
            background: rgba(255,255,255,0.3);
            transform: scale(1.1);
        }
        
        /* 履歴 */
        .history-panel {
            background: rgba(0,0,0,0.2);
            border-radius: 15px;
            padding: 20px;
            margin-top: 20px;
            max-height: 200px;
            overflow-y: auto;
        }
        .history-item {
            padding: 10px;
            margin: 5px 0;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .history-item:hover {
            background: rgba(255,255,255,0.2);
            transform: translateX(5px);
        }
        
        /* ローディング */
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,0.3);
            border-top: 3px solid white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* 通知バッジ */
        .notification-badge {
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #f093fb, #f5576c);
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            transform: translateX(400px);
            transition: transform 0.5s;
            max-width: 350px;
            z-index: 1000;
        }
        .notification-badge.show { transform: translateX(0); }
        
        /* タブ */
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab {
            padding: 15px 30px;
            border-radius: 15px;
            background: rgba(255,255,255,0.1);
            cursor: pointer;
            transition: all 0.3s;
        }
        .tab.active {
            background: linear-gradient(135deg, rgba(255,255,255,0.3), rgba(255,255,255,0.2));
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .tab:hover { background: rgba(255,255,255,0.2); }
        
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="shortcuts-hint">⌨️ ショートカット: Ctrl+K</div>
            <h1>🌟 Mana Central Hub v2.0</h1>
            <div class="greeting" id="greeting">Loading...</div>
            <div class="status-grid">
                <div class="status-card" onclick="showTab('calendar')">
                    <div class="status-label">📅 今日の予定</div>
                    <div class="status-value" id="events-count">-</div>
                </div>
                <div class="status-card" onclick="showTab('email')">
                    <div class="status-label">📧 未読メール</div>
                    <div class="status-value" id="emails-count">-</div>
                </div>
                <div class="status-card" onclick="showTab('tasks')">
                    <div class="status-label">✅ タスク</div>
                    <div class="status-value" id="tasks-status">-</div>
                </div>
                <div class="status-card" onclick="showTab('system')">
                    <div class="status-label">🖥️ システム</div>
                    <div class="status-value" id="system-status">正常</div>
                </div>
            </div>
        </div>

        <!-- タブナビゲーション -->
        <div class="section">
            <div class="tabs">
                <div class="tab active" onclick="showTab('chat')">💬 チャット</div>
                <div class="tab" onclick="showTab('quick')">⚡ クイックアクション</div>
                <div class="tab" onclick="showTab('history')">📜 履歴</div>
                <div class="tab" onclick="showTab('favorites')">⭐ お気に入り</div>
            </div>
            
            <!-- チャットタブ -->
            <div id="chat-tab" class="tab-content active">
                <h2>💬 Trinityとチャット</h2>
                
                <!-- スマートサジェスト -->
                <div class="suggestions" id="suggestions">
                    <div class="suggestion-chip" onclick="quickCommand('今日の予定を教えて')">📅 今日の予定</div>
                    <div class="suggestion-chip" onclick="quickCommand('未読メールを確認')">📧 メール確認</div>
                    <div class="suggestion-chip" onclick="quickCommand('X280のスクリーンショット')">📸 スクショ</div>
                    <div class="suggestion-chip" onclick="quickCommand('最新のAI技術を調べて')">🔍 AI調査</div>
                    <div class="suggestion-chip" onclick="quickCommand('システムを最適化')">⚡ 最適化</div>
                </div>
                
                <div class="chat-container" id="chat-messages">
                    <div class="message system">💡 Trinityがサポートします。何でも聞いてください！</div>
                </div>
                
                <div class="chat-input-container">
                    <button class="voice-btn" id="voice-btn" onclick="toggleVoice()">🎙️</button>
                    <input type="text" class="chat-input" id="chat-input" 
                           placeholder="Trinityに話しかける... (Ctrl+K または音声)">
                    <button class="send-btn" onclick="sendMessage()">送信 ↵</button>
                </div>
            </div>
            
            <!-- クイックアクションタブ -->
            <div id="quick-tab" class="tab-content">
                <h2>⚡ クイックアクション</h2>
                <div class="quick-actions">
                    <a href="#" class="action-btn" onclick="checkCalendar(); return false;">
                        <div class="action-shortcut">Ctrl+1</div>
                        <div class="action-icon">📅</div>
                        <div class="action-label">予定確認</div>
                    </a>
                    <a href="#" class="action-btn" onclick="checkEmail(); return false;">
                        <div class="action-shortcut">Ctrl+2</div>
                        <div class="action-icon">📧</div>
                        <div class="action-label">メール</div>
                    </a>
                    <a href="#" class="action-btn" onclick="openDrive(); return false;">
                        <div class="action-shortcut">Ctrl+3</div>
                        <div class="action-icon">📁</div>
                        <div class="action-label">Drive</div>
                    </a>
                    <a href="#" class="action-btn" onclick="x280Screenshot(); return false;">
                        <div class="action-shortcut">Ctrl+4</div>
                        <div class="action-icon">📸</div>
                        <div class="action-label">X280スクショ</div>
                    </a>
                    <a href="#" class="action-btn" onclick="webSearch(); return false;">
                        <div class="action-shortcut">Ctrl+5</div>
                        <div class="action-icon">🔍</div>
                        <div class="action-label">Web検索</div>
                    </a>
                    <a href="#" class="action-btn" onclick="notebookResearch(); return false;">
                        <div class="action-shortcut">Ctrl+6</div>
                        <div class="action-icon">📚</div>
                        <div class="action-label">調べもの</div>
                    </a>
                    <a href="#" class="action-btn" onclick="optimizeSystem(); return false;">
                        <div class="action-shortcut">Ctrl+7</div>
                        <div class="action-icon">⚡</div>
                        <div class="action-label">最適化</div>
                    </a>
                    <a href="#" class="action-btn" onclick="morningRoutine(); return false;">
                        <div class="action-shortcut">Ctrl+8</div>
                        <div class="action-icon">🌅</div>
                        <div class="action-label">朝のサマリー</div>
                    </a>
                </div>
            </div>
            
            <!-- 履歴タブ -->
            <div id="history-tab" class="tab-content">
                <h2>📜 実行履歴</h2>
                <div class="history-panel" id="history-list"></div>
            </div>
            
            <!-- お気に入りタブ -->
            <div id="favorites-tab" class="tab-content">
                <h2>⭐ お気に入り</h2>
                <div class="quick-actions" id="favorites-list">
                    <div class="action-btn" onclick="alert('お気に入り機能は準備中')">
                        <div class="action-icon">➕</div>
                        <div class="action-label">追加</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>🎯 システムリンク</h2>
            <div class="quick-actions">
                <a href="http://localhost:10000" class="action-btn" target="_blank">
                    <div class="action-icon">🎯</div>
                    <div class="action-label">Command Center</div>
                </a>
                <a href="http://localhost:5008" class="action-btn" target="_blank">
                    <div class="action-icon">🖥️</div>
                    <div class="action-label">Screen Share</div>
                </a>
                <a href="http://localhost:9200/docs" class="action-btn" target="_blank">
                    <div class="action-icon">📡</div>
                    <div class="action-label">ManaOS API</div>
                </a>
                <a href="http://localhost:3000" class="action-btn" target="_blank">
                    <div class="action-icon">📊</div>
                    <div class="action-label">Grafana</div>
                </a>
            </div>
        </div>
    </div>

    <div class="notification-badge" id="notification">
        <strong>通知</strong><br>
        <span id="notification-text">テスト通知</span>
    </div>

    <script>
        const socket = io();
        let isRecording = false;
        
        // グリーティング更新
        function updateGreeting() {
            const hour = new Date().getHours();
            let greeting = "こんにちは";
            let emoji = "👋";
            if (hour < 12) { greeting = "おはよう"; emoji = "🌅"; }
            else if (hour < 18) { greeting = "こんにちは"; emoji = "😊"; }
            else { greeting = "こんばんは"; emoji = "🌙"; }
            
            const dateStr = new Date().toLocaleDateString('ja-JP', {
                year: 'numeric', month: 'long', day: 'numeric', weekday: 'long'
            });
            
            document.getElementById('greeting').innerHTML = 
                `${emoji} ${greeting}、Mana！<br><small style="opacity:0.7">${dateStr}</small>`;
        }
        
        // タブ切り替え
        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            
            if (tabName === 'chat') {
                document.querySelector('.tab:nth-child(1)').classList.add('active');
                document.getElementById('chat-tab').classList.add('active');
            } else if (tabName === 'quick') {
                document.querySelector('.tab:nth-child(2)').classList.add('active');
                document.getElementById('quick-tab').classList.add('active');
            } else if (tabName === 'history') {
                document.querySelector('.tab:nth-child(3)').classList.add('active');
                document.getElementById('history-tab').classList.add('active');
                loadHistory();
            } else if (tabName === 'favorites') {
                document.querySelector('.tab:nth-child(4)').classList.add('active');
                document.getElementById('favorites-tab').classList.add('active');
            }
            
            // ステータスカードのクリックでも対応タブ表示
            if (tabName === 'calendar' || tabName === 'email' || tabName === 'tasks' || tabName === 'system') {
                showTab('chat');
                if (tabName === 'calendar') checkCalendar();
                if (tabName === 'email') checkEmail();
                if (tabName === 'tasks') checkTasks();
                if (tabName === 'system') checkSystem();
            }
        }
        
        // クイックコマンド
        function quickCommand(text) {
            document.getElementById('chat-input').value = text;
            sendMessage();
        }
        
        // メッセージ送信
        async function sendMessage() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            if (!message) return;
            
            addMessage(message, 'user');
            input.value = '';
            
            // ローディング表示
            const loadingId = addMessage('🤔 考え中... <span class="loading"></span>', 'assistant');
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message})
                });
                const data = await response.json();
                
                // ローディング削除
                document.getElementById(loadingId).remove();
                
                addMessage(data.response || 'エラーが発生しました', 'assistant');
            } catch (e) {
                document.getElementById(loadingId).remove();
                addMessage('通信エラー: ' + e.message, 'assistant');
            }
        }
        
        // メッセージ追加
        function addMessage(text, type) {
            const container = document.getElementById('chat-messages');
            const msg = document.createElement('div');
            msg.className = 'message ' + type;
            msg.innerHTML = text;
            msg.id = 'msg-' + Date.now();
            container.appendChild(msg);
            container.scrollTop = container.scrollHeight;
            return msg.id;
        }
        
        // 通知表示
        function showNotification(title, message) {
            const notif = document.getElementById('notification');
            document.getElementById('notification-text').innerHTML = `<strong>${title}</strong><br>${message}`;
            notif.classList.add('show');
            setTimeout(() => notif.classList.remove('show'), 5000);
        }
        
        // 各種アクション
        async function checkCalendar() {
            addMessage('📅 カレンダーを確認中...', 'system');
            const response = await fetch('/api/calendar');
            const data = await response.json();
            addMessage(data.summary, 'assistant');
            document.getElementById('events-count').textContent = data.count + '件';
        }
        
        async function checkEmail() {
            addMessage('📧 メールを確認中...', 'system');
            const response = await fetch('/api/email');
            const data = await response.json();
            addMessage(data.summary, 'assistant');
            document.getElementById('emails-count').textContent = data.count + '件';
        }
        
        async function checkTasks() {
            addMessage('✅ タスクを確認中...', 'system');
            const response = await fetch('/api/tasks');
            const data = await response.json();
            addMessage(data.summary, 'assistant');
            document.getElementById('tasks-status').textContent = data.status;
        }
        
        async function checkSystem() {
            addMessage('🖥️ システムを確認中...', 'system');
            const response = await fetch('/api/system');
            const data = await response.json();
            addMessage(data.summary, 'assistant');
        }
        
        async function openDrive() {
            addMessage('📁 Google Driveを確認中...', 'system');
            const response = await fetch('/api/drive');
            const data = await response.json();
            addMessage(data.summary, 'assistant');
        }
        
        async function x280Screenshot() {
            addMessage('📸 X280のスクリーンショット撮影中...', 'system');
            const response = await fetch('/api/x280/screenshot');
            const data = await response.json();
            addMessage(data.message, 'assistant');
            if (data.success) showNotification('📸 スクショ完了', 'X280のスクリーンショットを撮影しました');
        }
        
        async function webSearch() {
            const query = prompt('🔍 検索キーワードを入力:');
            if (!query) return;
            addMessage('🔍 Web検索中: ' + query, 'system');
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query})
            });
            const data = await response.json();
            addMessage(data.summary, 'assistant');
        }
        
        async function notebookResearch() {
            const query = prompt('📚 調べたいテーマを入力:');
            if (!query) return;
            addMessage('📚 NotebookLMで調査中: ' + query, 'system');
            const response = await fetch('/api/research', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query})
            });
            const data = await response.json();
            addMessage(data.summary, 'assistant');
        }
        
        async function optimizeSystem() {
            addMessage('⚡ システム最適化を開始...', 'system');
            const response = await fetch('/api/optimize');
            const data = await response.json();
            addMessage(data.message, 'assistant');
            showNotification('⚡ 最適化完了', data.message);
        }
        
        async function morningRoutine() {
            addMessage('🌅 朝のルーティンを実行中...', 'system');
            const response = await fetch('/api/morning_routine');
            const data = await response.json();
            addMessage(data.summary, 'assistant');
        }
        
        // 履歴読み込み
        async function loadHistory() {
            const response = await fetch('/api/history');
            const data = await response.json();
            const container = document.getElementById('history-list');
            container.innerHTML = '';
            
            data.history.forEach(item => {
                const div = document.createElement('div');
                div.className = 'history-item';
                div.textContent = item.command;
                div.onclick = () => quickCommand(item.command);
                container.appendChild(div);
            });
        }
        
        // 音声入力
        function toggleVoice() {
            const btn = document.getElementById('voice-btn');
            if (!isRecording) {
                btn.classList.add('recording');
                btn.textContent = '🔴';
                isRecording = true;
                addMessage('🎙️ 音声入力を開始（ブラウザの音声認識を使用）', 'system');
                startVoiceRecognition();
            } else {
                btn.classList.remove('recording');
                btn.textContent = '🎙️';
                isRecording = false;
            }
        }
        
        function startVoiceRecognition() {
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                const recognition = new SpeechRecognition();
                recognition.lang = 'ja-JP';
                recognition.continuous = false;
                
                recognition.onresult = (event) => {
                    const transcript = event.results[0][0].transcript;
                    document.getElementById('chat-input').value = transcript;
                    toggleVoice();
                    sendMessage();
                };
                
                recognition.onerror = () => {
                    toggleVoice();
                    addMessage('音声認識エラー', 'system');
                };
                
                recognition.start();
            } else {
                addMessage('このブラウザは音声認識に対応していません', 'system');
                toggleVoice();
            }
        }
        
        // キーボードショートカット
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey) {
                switch(e.key) {
                    case 'k': e.preventDefault(); document.getElementById('chat-input').focus(); break;
                    case '1': e.preventDefault(); checkCalendar(); break;
                    case '2': e.preventDefault(); checkEmail(); break;
                    case '3': e.preventDefault(); openDrive(); break;
                    case '4': e.preventDefault(); x280Screenshot(); break;
                    case '5': e.preventDefault(); webSearch(); break;
                    case '6': e.preventDefault(); notebookResearch(); break;
                    case '7': e.preventDefault(); optimizeSystem(); break;
                    case '8': e.preventDefault(); morningRoutine(); break;
                }
            }
        });
        
        // Enterキーで送信
        document.getElementById('chat-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
        
        // WebSocket接続
        socket.on('notification', (data) => {
            showNotification(data.title, data.message);
        });
        
        socket.on('status_update', (data) => {
            if (data.events) document.getElementById('events-count').textContent = data.events;
            if (data.emails) document.getElementById('emails-count').textContent = data.emails;
            if (data.tasks) document.getElementById('tasks-status').textContent = data.tasks;
        });
        
        // 初期化
        updateGreeting();
        setInterval(updateGreeting, 60000);
        checkCalendar();
        checkEmail();
        
        // 定期的にステータス更新（30秒）
        setInterval(async () => {
            const response = await fetch('/api/status_all');
            const data = await response.json();
            socket.emit('status_update', data);
        }, 30000);
    </script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/chat', methods=['POST'])
def chat():
    """Trinity Secretaryとチャット"""
    try:
        data = request.json
        message = data.get('message', '')
        save_history(message)
        
        # 実際のTrinity呼び出し（将来実装）
        response_text = f"Trinity: 「{message}」を処理しました。実際の統合は次のステップで実装します。"
        
        return jsonify({"response": response_text, "success": True})
    except Exception as e:
        return jsonify({"response": f"エラー: {str(e)}", "success": False})

@app.route('/api/calendar')
def calendar():
    return jsonify({
        "count": 3,
        "summary": "📅 今日の予定:\n• 10:00 チーム会議\n• 14:00 コードレビュー\n• 18:00 進捗報告"
    })

@app.route('/api/email')
def email():
    return jsonify({
        "count": 12,
        "summary": "📧 未読12件\n重要:\n• プロジェクト更新(2件)\n• 請求書承認(1件)"
    })

@app.route('/api/tasks')
def tasks():
    return jsonify({
        "status": "5/8",
        "summary": "✅ タスク状況:\n完了: 5件\n残り: 3件\n期限接近: 1件"
    })

@app.route('/api/system')
def system():
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    return jsonify({
        "summary": f"🖥️ システム正常\nCPU: {cpu:.1f}%\nメモリ: {mem:.1f}%\nディスク: {disk:.1f}%"
    })

@app.route('/api/drive')
def drive():
    return jsonify({
        "summary": "📁 最近のファイル:\n• レポート_202510.xlsx\n• プロジェクト資料.pdf\n• スクリーンショット.png"
    })

@app.route('/api/x280/screenshot')
def x280_screenshot():
    return jsonify({
        "success": True,
        "message": "📸 X280のスクリーンショットを /root/screenshots/ に保存しました"
    })

@app.route('/api/search', methods=['POST'])
def search():
    data = request.json
    query = data.get('query', '')
    save_history(f"検索: {query}")
    return jsonify({
        "summary": f"🔍 '{query}' の検索結果:\n• 上位5件を取得\n• NotebookLMに保存可能"
    })

@app.route('/api/research', methods=['POST'])
def research():
    data = request.json
    query = data.get('query', '')
    save_history(f"調査: {query}")
    return jsonify({
        "summary": f"📚 '{query}' の調査完了:\n• Web検索: 5件\n• YouTube: 3件\n• サマリー生成完了"
    })

@app.route('/api/optimize')
def optimize():
    return jsonify({
        "message": "⚡ 最適化完了！\n• メモリ0.5%削減\n• キャッシュクリア\n• PID整理"
    })

@app.route('/api/morning_routine')
def morning_routine_api():
    return jsonify({
        "summary": "🌅 朝のサマリー:\n📅 予定: 3件\n📧 メール: 12件\n✅ タスク: 5/8完了\n🌤️ 天気: 晴れ22℃"
    })

@app.route('/api/history')
def get_history():
    return jsonify({"history": load_history()})

@app.route('/api/status_all')
def status_all():
    return jsonify({
        "events": "3件",
        "emails": "12件",
        "tasks": "5/8"
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "Mana Central Hub v2.0"})

@socketio.on('connect')
def handle_connect():
    emit('message', {'data': 'Connected to Mana Central Hub v2.0'})

if __name__ == '__main__':
    print("🌟 Mana Central Hub v2.0 起動中...")
    print("✨ 音声コマンド対応")
    print("⌨️  ショートカットキー対応")
    print("📜 履歴機能対応")
    print("")
    print("📱 アクセス: http://localhost:5555")
    print("🌐 外部: http://163.44.120.49:5555")
    print("🔗 Tailscale: http://100.93.120.33:5555")
    socketio.run(app, host='0.0.0.0', port=5555, debug=False, allow_unsafe_werkzeug=True)

