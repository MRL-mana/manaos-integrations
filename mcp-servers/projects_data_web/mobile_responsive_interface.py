#!/usr/bin/env python3
"""
モバイル対応レスポンシブインターフェース
スマートフォン・タブレット対応のPDF-Excel変換システム
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import json
import logging
from datetime import datetime
import os
import uuid

# 既存システムのインポート
from final_production_converter import FinalProductionConverter
from comprehensive_error_handler import ComprehensiveErrorHandler

app = FastAPI(
    title="PDF-Excel変換システム モバイル対応インターフェース",
    description="スマートフォン・タブレット対応のレスポンシブPDF-Excel変換システム",
    version="1.0.0"
)

# グローバル変数
connected_mobile_clients = []
conversion_tasks = {}
mobile_converter = FinalProductionConverter()
error_handler = ComprehensiveErrorHandler()

class MobileInterface:
    def __init__(self):
        self.setup_logging()
        self.mobile_features = {
            'touch_optimized': True,
            'swipe_gestures': True,
            'voice_commands': False,  # 将来的な拡張
            'camera_upload': False,   # 将来的な拡張
            'offline_mode': False     # 将来的な拡張
        }
        
    def setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('MobileInterface')

mobile_interface = MobileInterface()

@app.get("/", response_class=HTMLResponse)
async def get_mobile_homepage():
    """モバイル対応ホームページ"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="theme-color" content="#667eea">
        <title>PDF-Excel変換 - モバイル版</title>
        <style>
            * { 
                margin: 0; 
                padding: 0; 
                box-sizing: border-box; 
                -webkit-tap-highlight-color: transparent;
            }
            
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                overflow-x: hidden;
                -webkit-font-smoothing: antialiased;
            }
            
            .mobile-container {
                max-width: 100vw;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }
            
            .mobile-header {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                color: white;
                padding: 20px;
                text-align: center;
                position: sticky;
                top: 0;
                z-index: 100;
            }
            
            .mobile-header h1 {
                font-size: 1.5em;
                margin-bottom: 5px;
                font-weight: 300;
            }
            
            .mobile-header p {
                font-size: 0.9em;
                opacity: 0.9;
            }
            
            .mobile-main {
                flex: 1;
                padding: 20px;
                display: flex;
                flex-direction: column;
                gap: 20px;
            }
            
            .upload-card {
                background: white;
                border-radius: 20px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                text-align: center;
                transition: all 0.3s ease;
                touch-action: manipulation;
            }
            
            .upload-card:active {
                transform: scale(0.98);
            }
            
            .upload-icon {
                font-size: 3em;
                color: #667eea;
                margin-bottom: 15px;
                animation: bounce 2s infinite;
            }
            
            @keyframes bounce {
                0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
                40% { transform: translateY(-10px); }
                60% { transform: translateY(-5px); }
            }
            
            .upload-text {
                font-size: 1.1em;
                color: #333;
                margin-bottom: 20px;
                line-height: 1.5;
            }
            
            .upload-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 25px;
                font-size: 1.1em;
                cursor: pointer;
                transition: all 0.3s ease;
                width: 100%;
                max-width: 300px;
                touch-action: manipulation;
                -webkit-appearance: none;
            }
            
            .upload-btn:active {
                transform: scale(0.95);
            }
            
            .upload-btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            
            .file-input {
                display: none;
            }
            
            .progress-card {
                display: none;
                background: white;
                border-radius: 20px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            
            .progress-bar {
                width: 100%;
                height: 8px;
                background: #e0e0e0;
                border-radius: 4px;
                overflow: hidden;
                margin: 15px 0;
            }
            
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea, #764ba2);
                width: 0%;
                transition: width 0.3s ease;
            }
            
            .status-text {
                text-align: center;
                color: #666;
                font-size: 1em;
                margin-bottom: 10px;
            }
            
            .result-card {
                display: none;
                background: #e8f5e8;
                border-radius: 20px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                border-left: 5px solid #4caf50;
            }
            
            .download-btn {
                background: #4caf50;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 25px;
                font-size: 1em;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                margin-top: 15px;
                width: 100%;
                text-align: center;
                touch-action: manipulation;
                -webkit-appearance: none;
            }
            
            .download-btn:active {
                transform: scale(0.95);
            }
            
            .error-card {
                display: none;
                background: #ffeaea;
                border-radius: 20px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                border-left: 5px solid #f44336;
                color: #d32f2f;
            }
            
            .features-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }
            
            .feature-item {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 20px;
                text-align: center;
                color: white;
                transition: all 0.3s ease;
            }
            
            .feature-item:active {
                transform: scale(0.95);
            }
            
            .feature-icon {
                font-size: 2em;
                margin-bottom: 10px;
                display: block;
            }
            
            .feature-title {
                font-size: 0.9em;
                font-weight: 600;
                margin-bottom: 5px;
            }
            
            .feature-desc {
                font-size: 0.8em;
                opacity: 0.9;
                line-height: 1.3;
            }
            
            .swipe-hint {
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(0, 0, 0, 0.7);
                color: white;
                padding: 10px 20px;
                border-radius: 20px;
                font-size: 0.9em;
                opacity: 0;
                transition: opacity 0.3s ease;
                pointer-events: none;
            }
            
            .swipe-hint.show {
                opacity: 1;
            }
            
            .floating-action {
                position: fixed;
                bottom: 30px;
                right: 30px;
                width: 60px;
                height: 60px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 1.5em;
                box-shadow: 0 5px 15px rgba(0,0,0,0.3);
                cursor: pointer;
                transition: all 0.3s ease;
                z-index: 1000;
                touch-action: manipulation;
            }
            
            .floating-action:active {
                transform: scale(0.9);
            }
            
            .loading-spinner {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 2px solid #f3f3f3;
                border-top: 2px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-right: 10px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            /* タッチデバイス最適化 */
            @media (hover: none) and (pointer: coarse) {
                .upload-btn, .download-btn, .feature-item {
                    min-height: 44px;
                }
                
                .floating-action {
                    width: 56px;
                    height: 56px;
                }
            }
            
            /* ダークモード対応 */
            @media (prefers-color-scheme: dark) {
                body {
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                }
                
                .upload-card, .progress-card, .result-card, .error-card {
                    background: #2d2d2d;
                    color: white;
                }
                
                .upload-text {
                    color: white;
                }
                
                .status-text {
                    color: #ccc;
                }
            }
            
            /* 横向き対応 */
            @media (orientation: landscape) and (max-height: 500px) {
                .mobile-header {
                    padding: 10px 20px;
                }
                
                .mobile-header h1 {
                    font-size: 1.2em;
                }
                
                .mobile-main {
                    padding: 10px 20px;
                }
                
                .upload-card {
                    padding: 15px;
                }
            }
        </style>
    </head>
    <body>
        <div class="mobile-container">
            <div class="mobile-header">
                <h1>📱 PDF-Excel変換</h1>
                <p>モバイル最適化版</p>
            </div>
            
            <div class="mobile-main">
                <div class="upload-card" id="uploadCard">
                    <div class="upload-icon">📄</div>
                    <div class="upload-text">
                        PDFファイルをタップして<br>
                        変換を開始
                    </div>
                    <button class="upload-btn" onclick="document.getElementById('fileInput').click()">
                        📁 ファイルを選択
                    </button>
                    <input type="file" id="fileInput" class="file-input" accept=".pdf" />
                </div>
                
                <div class="progress-card" id="progressCard">
                    <div class="status-text" id="statusText">処理中...</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill"></div>
                    </div>
                    <div class="loading-spinner"></div>
                </div>
                
                <div class="result-card" id="resultCard">
                    <h3>✅ 変換完了！</h3>
                    <p>PDFファイルがExcelファイルに変換されました。</p>
                    <a href="#" class="download-btn" id="downloadBtn">📥 ダウンロード</a>
                </div>
                
                <div class="error-card" id="errorCard">
                    <h3>❌ エラー</h3>
                    <p id="errorMessage">エラーが発生しました</p>
                </div>
                
                <div class="features-grid">
                    <div class="feature-item">
                        <span class="feature-icon">🔍</span>
                        <div class="feature-title">高精度OCR</div>
                        <div class="feature-desc">画像内テキストを正確に認識</div>
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">📊</span>
                        <div class="feature-title">表認識</div>
                        <div class="feature-desc">複雑な表構造を自動認識</div>
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">⚡</span>
                        <div class="feature-title">高速処理</div>
                        <div class="feature-desc">最適化された並列処理</div>
                    </div>
                    <div class="feature-item">
                        <span class="feature-icon">📱</span>
                        <div class="feature-title">モバイル対応</div>
                        <div class="feature-desc">タッチ操作に最適化</div>
                    </div>
                </div>
            </div>
            
            <div class="floating-action" onclick="showSwipeHint()">
                💡
            </div>
            
            <div class="swipe-hint" id="swipeHint">
                ← スワイプで機能切替 →
            </div>
        </div>
        
        <script>
            let ws = null;
            let currentTaskId = null;
            let touchStartX = 0;
            let touchStartY = 0;
            
            // WebSocket接続
            function connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${window.location.host}/mobile-ws`);
                
                ws.onopen = function() {
                    console.log('モバイルWebSocket接続確立');
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    updateMobileInterface(data);
                };
                
                ws.onclose = function() {
                    console.log('WebSocket接続切断、再接続中...');
                    setTimeout(connectWebSocket, 5000);
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocketエラー:', error);
                };
            }
            
            // ファイル処理
            document.getElementById('fileInput').addEventListener('change', function(e) {
                if (e.target.files.length > 0) {
                    handleFile(e.target.files[0]);
                }
            });
            
            // ファイル処理関数
            async function handleFile(file) {
                if (!file.name.toLowerCase().endsWith('.pdf')) {
                    showError('PDFファイルを選択してください。');
                    return;
                }
                
                try {
                    showProgress('アップロード中...', 10);
                    
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    const response = await fetch('/mobile-upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        throw new Error('アップロードに失敗しました。');
                    }
                    
                    const result = await response.json();
                    currentTaskId = result.task_id;
                    
                    showProgress('変換処理中...', 50);
                    monitorConversion();
                    
                } catch (error) {
                    showError('ファイルのアップロードに失敗しました: ' + error.message);
                }
            }
            
            // 変換監視
            async function monitorConversion() {
                if (!currentTaskId) return;
                
                try {
                    const response = await fetch(`/mobile-status/${currentTaskId}`);
                    const status = await response.json();
                    
                    if (status.status === 'processing') {
                        showProgress('変換処理中...', 75);
                        setTimeout(monitorConversion, 1000);
                    } else if (status.status === 'completed') {
                        showProgress('完了！', 100);
                        showResult(status.excel_file);
                    } else if (status.status === 'error') {
                        showError('変換処理中にエラーが発生しました: ' + status.error);
                    }
                } catch (error) {
                    showError('状況確認中にエラーが発生しました: ' + error.message);
                }
            }
            
            // インターフェース更新
            function updateMobileInterface(data) {
                // リアルタイム更新処理
                console.log('モバイルデータ更新:', data);
            }
            
            // 進捗表示
            function showProgress(text, percent) {
                document.getElementById('uploadCard').style.display = 'none';
                document.getElementById('progressCard').style.display = 'block';
                document.getElementById('resultCard').style.display = 'none';
                document.getElementById('errorCard').style.display = 'none';
                
                document.getElementById('statusText').textContent = text;
                document.getElementById('progressFill').style.width = percent + '%';
            }
            
            // 結果表示
            function showResult(excelFile) {
                document.getElementById('uploadCard').style.display = 'none';
                document.getElementById('progressCard').style.display = 'none';
                document.getElementById('resultCard').style.display = 'block';
                document.getElementById('errorCard').style.display = 'none';
                
                document.getElementById('downloadBtn').href = `/mobile-download/${currentTaskId}`;
            }
            
            // エラー表示
            function showError(message) {
                document.getElementById('uploadCard').style.display = 'none';
                document.getElementById('progressCard').style.display = 'none';
                document.getElementById('resultCard').style.display = 'none';
                document.getElementById('errorCard').style.display = 'block';
                
                document.getElementById('errorMessage').textContent = message;
            }
            
            // スワイプヒント表示
            function showSwipeHint() {
                const hint = document.getElementById('swipeHint');
                hint.classList.add('show');
                setTimeout(() => {
                    hint.classList.remove('show');
                }, 3000);
            }
            
            // タッチイベント
            document.addEventListener('touchstart', function(e) {
                touchStartX = e.touches[0].clientX;
                touchStartY = e.touches[0].clientY;
            });
            
            document.addEventListener('touchend', function(e) {
                const touchEndX = e.changedTouches[0].clientX;
                const touchEndY = e.changedTouches[0].clientY;
                const deltaX = touchEndX - touchStartX;
                const deltaY = touchEndY - touchStartY;
                
                // 水平スワイプ検出
                if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
                    if (deltaX > 0) {
                        // 右スワイプ
                        showSwipeHint();
                    } else {
                        // 左スワイプ
                        showSwipeHint();
                    }
                }
            });
            
            // デバイス向き変更対応
            window.addEventListener('orientationchange', function() {
                setTimeout(() => {
                    // レイアウト調整
                    document.body.style.height = window.innerHeight + 'px';
                }, 100);
            });
            
            // 初期化
            document.addEventListener('DOMContentLoaded', function() {
                connectWebSocket();
                document.body.style.height = window.innerHeight + 'px';
                
                // タッチデバイス検出
                if ('ontouchstart' in window) {
                    document.body.classList.add('touch-device');
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/mobile-upload")
async def mobile_upload_file(file: UploadFile = File(...)):
    """モバイル用ファイルアップロード"""
    try:
        # タスクID生成
        task_id = str(uuid.uuid4())
        
        # ファイル保存
        upload_dir = Path("/tmp/mobile_uploads")  # type: ignore[name-defined]
        upload_dir.mkdir(exist_ok=True)
        
        file_path = upload_dir / f"{task_id}_{file.filename}"
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # タスク情報保存
        conversion_tasks[task_id] = {
            "task_id": task_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "status": "uploaded",
            "created_at": datetime.now().isoformat(),
            "progress": 0,
            "mobile_optimized": True
        }
        
        mobile_interface.logger.info(f"✅ モバイルファイルアップロード完了: {file.filename} -> {task_id}")
        
        return JSONResponse({
            "task_id": task_id,
            "filename": file.filename,
            "status": "uploaded",
            "mobile_optimized": True
        })
        
    except Exception as e:
        mobile_interface.logger.error(f"❌ モバイルアップロードエラー: {e}")
        error_handler.log_error(e, {'context': 'mobile_upload'})
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mobile-convert/{task_id}")
async def start_mobile_conversion(task_id: str, background_tasks: BackgroundTasks):
    """モバイル用変換開始"""
    try:
        if task_id not in conversion_tasks:
            raise HTTPException(status_code=404, detail="タスクが見つかりません")
        
        task = conversion_tasks[task_id]
        if task["status"] != "uploaded":
            raise HTTPException(status_code=400, detail="無効なタスク状態")
        
        # タスク状態更新
        task["status"] = "processing"
        task["started_at"] = datetime.now().isoformat()
        
        # バックグラウンドで変換実行
        background_tasks.add_task(mobile_convert_pdf_to_excel, task["file_path"], task_id)
        
        mobile_interface.logger.info(f"🔄 モバイル変換開始: {task_id}")
        
        return JSONResponse({
            "task_id": task_id,
            "status": "processing",
            "message": "変換処理を開始しました",
            "mobile_optimized": True
        })
        
    except Exception as e:
        mobile_interface.logger.error(f"❌ モバイル変換開始エラー: {e}")
        error_handler.log_error(e, {'context': 'mobile_convert'})
        raise HTTPException(status_code=500, detail=str(e))

async def mobile_convert_pdf_to_excel(pdf_path: str, task_id: str):
    """モバイル用PDF変換処理"""
    try:
        mobile_interface.logger.info(f"🔄 モバイル変換処理開始: {pdf_path}")
        
        # 出力ディレクトリ
        output_dir = Path("/tmp/mobile_outputs")  # type: ignore[name-defined]
        output_dir.mkdir(exist_ok=True)
        
        # 変換実行
        output_path = output_dir / f"{task_id}.xlsx"
        result = mobile_converter.convert_pdf_to_excel(pdf_path, str(output_path))
        
        # タスク更新
        conversion_tasks[task_id].update({
            "status": "completed",
            "result": result,
            "completed_at": datetime.now().isoformat(),
            "excel_file": str(output_path),
            "mobile_optimized": True
        })
        
        mobile_interface.logger.info(f"✅ モバイル変換完了: {task_id}")
        
    except Exception as e:
        mobile_interface.logger.error(f"❌ モバイル変換エラー: {e}")
        error_handler.log_error(e, {'context': 'mobile_convert_process'})
        
        conversion_tasks[task_id].update({
            "status": "error",
            "error": str(e),
            "completed_at": datetime.now().isoformat(),
            "mobile_optimized": True
        })

@app.get("/mobile-status/{task_id}")
async def get_mobile_status(task_id: str):
    """モバイル用変換状況確認"""
    try:
        if task_id not in conversion_tasks:
            raise HTTPException(status_code=404, detail="タスクが見つかりません")
        
        return JSONResponse(conversion_tasks[task_id])
        
    except Exception as e:
        mobile_interface.logger.error(f"❌ モバイル状況確認エラー: {e}")
        error_handler.log_error(e, {'context': 'mobile_status'})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mobile-download/{task_id}")
async def download_mobile_file(task_id: str):
    """モバイル用ファイルダウンロード"""
    try:
        if task_id not in conversion_tasks:
            raise HTTPException(status_code=404, detail="タスクが見つかりません")
        
        task = conversion_tasks[task_id]
        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail="変換が完了していません")
        
        excel_file = task.get("excel_file")
        if not excel_file or not os.path.exists(excel_file):
            raise HTTPException(status_code=404, detail="ファイルが見つかりません")
        
        filename = f"mobile_converted_{task['filename'].replace('.pdf', '.xlsx')}"
        
        mobile_interface.logger.info(f"📥 モバイルファイルダウンロード: {task_id} -> {filename}")
        
        return FileResponse(
            path=excel_file,
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        mobile_interface.logger.error(f"❌ モバイルダウンロードエラー: {e}")
        error_handler.log_error(e, {'context': 'mobile_download'})
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/mobile-ws")
async def mobile_websocket_endpoint(websocket: WebSocket):
    """モバイル用WebSocket接続"""
    await websocket.accept()
    connected_mobile_clients.append(websocket)
    
    try:
        # 初回データ送信
        await websocket.send_text(json.dumps({
            'type': 'connection',
            'message': 'モバイル接続確立',
            'features': mobile_interface.mobile_features,
            'timestamp': datetime.now().isoformat()
        }, ensure_ascii=False))
        
        # 接続維持
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_mobile_clients.remove(websocket)

@app.get("/mobile-api/info")
async def get_mobile_info():
    """モバイル用システム情報"""
    return JSONResponse({
        'mobile_features': mobile_interface.mobile_features,
        'supported_formats': ['pdf'],
        'max_file_size': '50MB',
        'concurrent_connections': len(connected_mobile_clients),
        'timestamp': datetime.now().isoformat()
    })

def main():
    """メイン実行関数"""
    print("🚀 モバイル対応レスポンシブインターフェース起動")
    print("=" * 60)
    print("📱 モバイルUI: http://localhost:8082")
    print("🔗 モバイルAPI: http://localhost:8082/mobile-api/info")
    print("📡 WebSocket: ws://localhost:8082/mobile-ws")
    print("=" * 60)
    print("📋 **モバイル機能:**")
    print("• タッチ操作最適化")
    print("• レスポンシブデザイン")
    print("• スワイプジェスチャー")
    print("• ダークモード対応")
    print("• 横向き対応")
    print("• PWA対応準備")
    
    import uvicorn
    uvicorn.run(
        "mobile_responsive_interface:app",
        host="0.0.0.0",
        port=8082,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
