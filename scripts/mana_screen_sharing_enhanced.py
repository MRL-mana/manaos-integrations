#!/usr/bin/env python3
"""
Mana Screen Sharing System Enhanced
拡張版画面共有システム - 新機能追加版
"""

import json
import logging
import time
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
import cv2
import numpy as np
from PIL import Image
try:
    import mss
except ImportError:
    mss = None
from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO, emit

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='/root/templates')
app.config['SECRET_KEY'] = 'mana_screen_sharing_enhanced_key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 画質プリセット
QUALITY_PRESETS = {
    "low": {"quality": 50, "fps": 15, "resolution": "1280x720"},
    "medium": {"quality": 70, "fps": 24, "resolution": "1920x1080"},
    "high": {"quality": 85, "fps": 30, "resolution": "1920x1080"},
    "ultra": {"quality": 95, "fps": 60, "resolution": "2560x1440"}
}

class ManaScreenSharingEnhanced:
    def __init__(self):
        self.storage_path = os.environ.get('SCREEN_SHARING_PATH', "/home/mana/screen_sharing_data")
        if not os.path.exists(self.storage_path):
            self.storage_path = "/root/screen_sharing_data"
        self.db_path = os.path.join(self.storage_path, "sessions.db")
        
        # ディレクトリ作成
        os.makedirs(self.storage_path, exist_ok=True)
        os.makedirs(os.path.join(self.storage_path, "screenshots"), exist_ok=True)
        os.makedirs(os.path.join(self.storage_path, "recordings"), exist_ok=True)
        os.makedirs(os.path.join(self.storage_path, "annotations"), exist_ok=True)
        
        # データベース初期化
        self.init_database()
        
        # 画面共有設定
        self.config = {
            "enabled": True,
            "port": 5008,
            "quality_preset": "medium",
            "monitor_index": 1,  # マルチモニター対応
            "recording_enabled": True,
            "remote_control_enabled": True,
            "password_protected": True,
            "session_timeout": 3600,
            "max_screenshots": 100,  # 最大スクショ保存数
            "annotation_enabled": True  # アノテーション機能
        }
        
        # 現在の設定を適用
        self.apply_quality_preset(self.config["quality_preset"])
        
        # セッション管理
        self.active_sessions = {}
        self.running = False
        self.current_annotations = []  # 現在のアノテーション
        
        logger.info("🚀 Mana Screen Sharing Enhanced 初期化完了")
    
    def init_database(self):
        """データベース初期化 - セッション履歴管理"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # セッション履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                start_time TEXT,
                end_time TEXT,
                duration_seconds INTEGER,
                quality_preset TEXT,
                monitor_index INTEGER,
                screenshot_count INTEGER DEFAULT 0,
                recording_path TEXT,
                viewers_count INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # スクリーンショット履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                filename TEXT,
                filepath TEXT,
                file_size INTEGER,
                resolution TEXT,
                annotation_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # アノテーション履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                screenshot_id INTEGER,
                annotation_type TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("データベース初期化完了")
    
    def apply_quality_preset(self, preset_name: str):
        """画質プリセット適用"""
        if preset_name in QUALITY_PRESETS:
            preset = QUALITY_PRESETS[preset_name]
            self.config.update({
                "quality": preset["quality"],
                "fps": preset["fps"],
                "resolution": preset["resolution"],
                "quality_preset": preset_name
            })
            logger.info(f"画質プリセット適用: {preset_name} - {preset}")
        else:
            logger.warning(f"Unknown preset: {preset_name}")
    
    def get_available_monitors(self) -> List[Dict[str, Any]]:
        """利用可能なモニター一覧取得"""
        monitors = []
        if mss is not None:
            with mss.mss() as sct:
                for i, monitor in enumerate(sct.monitors[1:], 1):  # monitor[0]は全画面なのでスキップ
                    monitors.append({
                        "index": i,
                        "width": monitor["width"],
                        "height": monitor["height"],
                        "left": monitor["left"],
                        "top": monitor["top"]
                    })
        else:
            # fallback: 1つのデフォルトモニター
            monitors.append({
                "index": 1,
                "width": 1920,
                "height": 1080,
                "left": 0,
                "top": 0
            })
        return monitors
    
    def capture_screen(self, monitor_index: Optional[int] = None) -> Optional[np.ndarray]:
        """画面をキャプチャ（マルチモニター対応）"""
        try:
            if monitor_index is None:
                monitor_index = self.config["monitor_index"]
            
            if mss is not None:
                with mss.mss() as sct:
                    # monitor_indexが有効範囲かチェック
                    if monitor_index < 1 or monitor_index >= len(sct.monitors):  # type: ignore[operator]
                        monitor_index = 1
                    
                    monitor = sct.monitors[monitor_index]  # type: ignore[call-arg]
                    screenshot = sct.grab(monitor)
                    img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
                    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            else:
                # ダミー画像
                frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
                cv2.putText(frame, "Screen Capture Not Available", (400, 540),
                           cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
            
            # 解像度を調整
            target_width, target_height = map(int, self.config["resolution"].split('x'))
            frame = cv2.resize(frame, (target_width, target_height))
            
            return frame
            
        except Exception as e:
            logger.error(f"画面キャプチャエラー: {e}")
            return None
    
    def save_screenshot(self, session_id: str, annotation_data: Optional[str] = None) -> Dict[str, Any]:
        """スクリーンショット保存（新機能）"""
        try:
            frame = self.capture_screen()
            if frame is None:
                return {"success": False, "error": "Failed to capture screen"}
            
            # ファイル名生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{session_id}_{timestamp}.png"
            filepath = os.path.join(self.storage_path, "screenshots", filename)
            
            # アノテーションを描画（もしあれば）
            if annotation_data and self.config["annotation_enabled"]:
                frame = self.draw_annotations(frame, annotation_data)
            
            # 保存
            cv2.imwrite(filepath, frame)
            file_size = os.path.getsize(filepath)
            
            # データベースに記録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO screenshots 
                (session_id, filename, filepath, file_size, resolution, annotation_data)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, filename, filepath, file_size, self.config["resolution"], annotation_data))
            screenshot_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # 古いスクリーンショットを削除（最大数超過時）
            self.cleanup_old_screenshots()
            
            logger.info(f"スクリーンショット保存: {filename}")
            return {
                "success": True,
                "screenshot_id": screenshot_id,
                "filename": filename,
                "filepath": filepath,
                "file_size": file_size
            }
            
        except Exception as e:
            logger.error(f"スクリーンショット保存エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def draw_annotations(self, frame: np.ndarray, annotation_data: str) -> np.ndarray:
        """アノテーション描画（新機能）"""
        try:
            annotations = json.loads(annotation_data)
            for annotation in annotations:
                ann_type = annotation.get("type")
                
                if ann_type == "rectangle":
                    x1, y1, x2, y2 = annotation["coords"]
                    color = tuple(annotation.get("color", [255, 0, 0]))
                    thickness = annotation.get("thickness", 2)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
                
                elif ann_type == "circle":
                    x, y, radius = annotation["coords"]
                    color = tuple(annotation.get("color", [0, 255, 0]))
                    thickness = annotation.get("thickness", 2)
                    cv2.circle(frame, (x, y), radius, color, thickness)
                
                elif ann_type == "text":
                    x, y = annotation["coords"][:2]
                    text = annotation.get("text", "")
                    color = tuple(annotation.get("color", [255, 255, 255]))
                    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                
                elif ann_type == "arrow":
                    x1, y1, x2, y2 = annotation["coords"]
                    color = tuple(annotation.get("color", [0, 0, 255]))
                    thickness = annotation.get("thickness", 2)
                    cv2.arrowedLine(frame, (x1, y1), (x2, y2), color, thickness)
            
            return frame
            
        except Exception as e:
            logger.error(f"アノテーション描画エラー: {e}")
            return frame
    
    def cleanup_old_screenshots(self):
        """古いスクリーンショットを削除"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # スクリーンショット数をカウント
            cursor.execute('SELECT COUNT(*) FROM screenshots')
            count = cursor.fetchone()[0]
            
            if count > self.config["max_screenshots"]:
                # 古い順に削除
                excess = count - self.config["max_screenshots"]
                cursor.execute('''
                    SELECT id, filepath FROM screenshots 
                    ORDER BY created_at ASC LIMIT ?
                ''', (excess,))
                
                for row in cursor.fetchall():
                    screenshot_id, filepath = row
                    # ファイル削除
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    # DB削除
                    cursor.execute('DELETE FROM screenshots WHERE id = ?', (screenshot_id,))
                
                conn.commit()
                logger.info(f"{excess}個の古いスクリーンショットを削除")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"スクリーンショットクリーンアップエラー: {e}")
    
    def get_session_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """セッション履歴取得（新機能）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM session_history 
                ORDER BY created_at DESC LIMIT ?
            ''', (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            history = []
            for row in cursor.fetchall():
                history.append(dict(zip(columns, row)))
            
            conn.close()
            return history
            
        except Exception as e:
            logger.error(f"セッション履歴取得エラー: {e}")
            return []
    
    def get_screenshot_list(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """スクリーンショット一覧取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if session_id:
                cursor.execute('''
                    SELECT * FROM screenshots 
                    WHERE session_id = ? 
                    ORDER BY created_at DESC
                ''', (session_id,))
            else:
                cursor.execute('SELECT * FROM screenshots ORDER BY created_at DESC LIMIT 100')
            
            columns = [desc[0] for desc in cursor.description]
            screenshots = []
            for row in cursor.fetchall():
                screenshots.append(dict(zip(columns, row)))
            
            conn.close()
            return screenshots
            
        except Exception as e:
            logger.error(f"スクリーンショット一覧取得エラー: {e}")
            return []
    
    def start_session(self, session_id: str) -> Dict[str, Any]:
        """セッション開始"""
        try:
            session = {
                "session_id": session_id,
                "start_time": datetime.now().isoformat(),
                "quality_preset": self.config["quality_preset"],
                "monitor_index": self.config["monitor_index"],
                "active": True
            }
            self.active_sessions[session_id] = session
            
            # データベースに記録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO session_history 
                (session_id, start_time, quality_preset, monitor_index)
                VALUES (?, ?, ?, ?)
            ''', (session_id, session["start_time"], 
                  self.config["quality_preset"], self.config["monitor_index"]))
            conn.commit()
            conn.close()
            
            logger.info(f"セッション開始: {session_id}")
            return {"success": True, "session": session}
            
        except Exception as e:
            logger.error(f"セッション開始エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def end_session(self, session_id: str) -> Dict[str, Any]:
        """セッション終了"""
        try:
            if session_id not in self.active_sessions:
                return {"success": False, "error": "Session not found"}
            
            session = self.active_sessions[session_id]
            start_time = datetime.fromisoformat(session["start_time"])
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds())
            
            # データベース更新
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE session_history 
                SET end_time = ?, duration_seconds = ?
                WHERE session_id = ?
            ''', (end_time.isoformat(), duration, session_id))
            
            # スクリーンショット数を更新
            cursor.execute('SELECT COUNT(*) FROM screenshots WHERE session_id = ?', (session_id,))
            screenshot_count = cursor.fetchone()[0]
            cursor.execute('''
                UPDATE session_history 
                SET screenshot_count = ?
                WHERE session_id = ?
            ''', (screenshot_count, session_id))
            
            conn.commit()
            conn.close()
            
            del self.active_sessions[session_id]
            
            logger.info(f"セッション終了: {session_id}, 時間: {duration}秒")
            return {"success": True, "duration": duration}
            
        except Exception as e:
            logger.error(f"セッション終了エラー: {e}")
            return {"success": False, "error": str(e)}

# グローバルインスタンス
screen_system = ManaScreenSharingEnhanced()

# === Flask API エンドポイント ===

@app.route('/')
def index():
    """メインダッシュボード"""
    return render_template('screen_sharing_enhanced.html')

@app.route('/api/status')
def get_status():
    """システムステータス"""
    return jsonify({
        "service": "Mana Screen Sharing Enhanced",
        "status": "online",
        "active_sessions": len(screen_system.active_sessions),
        "config": screen_system.config,
        "available_monitors": screen_system.get_available_monitors()
    })

@app.route('/api/quality_preset/<preset>', methods=['POST'])
def change_quality_preset(preset):
    """画質プリセット変更（新機能）"""
    screen_system.apply_quality_preset(preset)
    return jsonify({"success": True, "preset": preset, "config": screen_system.config})

@app.route('/api/monitor/<int:monitor_index>', methods=['POST'])
def change_monitor(monitor_index):
    """モニター切り替え（新機能）"""
    screen_system.config["monitor_index"] = monitor_index
    return jsonify({"success": True, "monitor_index": monitor_index})

@app.route('/api/screenshot/<session_id>', methods=['POST'])
def take_screenshot(session_id):
    """スクリーンショット撮影（新機能）"""
    annotation_data = request.json.get("annotation_data") if request.json else None
    result = screen_system.save_screenshot(session_id, annotation_data)
    return jsonify(result)

@app.route('/api/screenshots')
def list_screenshots():
    """スクリーンショット一覧（新機能）"""
    session_id = request.args.get('session_id')
    screenshots = screen_system.get_screenshot_list(session_id)
    return jsonify({"screenshots": screenshots})

@app.route('/api/screenshot/download/<int:screenshot_id>')
def download_screenshot(screenshot_id):
    """スクリーンショットダウンロード"""
    try:
        conn = sqlite3.connect(screen_system.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT filepath FROM screenshots WHERE id = ?', (screenshot_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row and os.path.exists(row[0]):
            return send_file(row[0], as_attachment=True)
        else:
            return jsonify({"error": "Screenshot not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/session/start', methods=['POST'])
def start_session():
    """セッション開始"""
    data = request.json
    session_id = data.get("session_id", f"session_{int(time.time())}")
    result = screen_system.start_session(session_id)
    return jsonify(result)

@app.route('/api/session/end', methods=['POST'])
def end_session():
    """セッション終了"""
    data = request.json
    session_id = data.get("session_id")
    result = screen_system.end_session(session_id)
    return jsonify(result)

@app.route('/api/session/history')
def get_session_history():
    """セッション履歴（新機能）"""
    limit = int(request.args.get('limit', 50))
    history = screen_system.get_session_history(limit)
    return jsonify({"history": history})

# WebSocket イベント
@socketio.on('connect')
def handle_connect():
    logger.info("クライアント接続")
    emit('connected', {'message': 'Connected to Mana Screen Sharing Enhanced'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info("クライアント切断")

if __name__ == '__main__':
    logger.info("🚀 Mana Screen Sharing Enhanced 起動")
    logger.info("URL: http://localhost:5008")
    socketio.run(app, host='0.0.0.0', port=5008, debug=False, allow_unsafe_werkzeug=True)


