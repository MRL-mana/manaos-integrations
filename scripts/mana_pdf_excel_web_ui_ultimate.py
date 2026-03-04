#!/usr/bin/env python3
"""
Mana PDF Excel AI Ultimate Web UI
リアルタイム進捗表示 + WebSocket + 自動化ダッシュボード
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
import aiofiles
from mana_pdf_excel_ai_ultimate import get_ultimate_converter, pdf_to_excel_ai, batch_pdf_to_excel_ai

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ManaPDFExcelWebUI")

# FastAPI アプリケーション
app = FastAPI(
    title="Mana PDF Excel AI Ultimate",
    description="AI統合PDF→Excel変換システム",
    version="2.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket接続管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket接続: {len(self.active_connections)}接続")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket切断: {len(self.active_connections)}接続")

    async def send_progress(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                self.active_connections.remove(connection)

manager = ConnectionManager()

# データモデル
class ConversionRequest(BaseModel):
    use_multi_ai: bool = True
    upload_to_drive: bool = False

class BatchConversionRequest(BaseModel):
    pdf_paths: List[str]
    use_multi_ai: bool = True

class AutomationConfig(BaseModel):
    daily_conversion: bool = False
    hourly_monitoring: bool = False
    watch_directory: str = "/root/automation_input"

# 静的ファイル配信
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """メインダッシュボード"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mana PDF Excel AI Ultimate</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                text-align: center;
                color: white;
                margin-bottom: 30px;
            }
            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .header p {
                font-size: 1.2em;
                opacity: 0.9;
            }
            .dashboard {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 30px;
            }
            .card {
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                transition: transform 0.3s ease;
            }
            .card:hover {
                transform: translateY(-5px);
            }
            .card h2 {
                color: #667eea;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .upload-area {
                border: 3px dashed #667eea;
                border-radius: 10px;
                padding: 40px;
                text-align: center;
                background: #f8f9ff;
                transition: all 0.3s ease;
                cursor: pointer;
            }
            .upload-area:hover {
                background: #e8f0ff;
                border-color: #5a6fd8;
            }
            .upload-area.dragover {
                background: #e0e7ff;
                border-color: #4f46e5;
            }
            .btn {
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
                transition: all 0.3s ease;
                margin: 5px;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            .btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            .progress-bar {
                width: 100%;
                height: 20px;
                background: #e0e0e0;
                border-radius: 10px;
                overflow: hidden;
                margin: 10px 0;
            }
            .progress-fill {
                height: 100%;
                background: linear-gradient(45deg, #667eea, #764ba2);
                width: 0%;
                transition: width 0.3s ease;
            }
            .status {
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
                font-weight: bold;
            }
            .status.success { background: #d4edda; color: #155724; }
            .status.error { background: #f8d7da; color: #721c24; }
            .status.info { background: #d1ecf1; color: #0c5460; }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .stat-item {
                background: #f8f9ff;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
            }
            .stat-number {
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
            }
            .stat-label {
                color: #666;
                margin-top: 5px;
            }
            .log-container {
                background: #1e1e1e;
                color: #00ff00;
                padding: 20px;
                border-radius: 10px;
                font-family: 'Courier New', monospace;
                height: 300px;
                overflow-y: auto;
                margin: 20px 0;
            }
            .ai-status {
                display: flex;
                gap: 20px;
                margin: 20px 0;
            }
            .ai-item {
                flex: 1;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
            }
            .ai-item.enabled { background: #d4edda; color: #155724; }
            .ai-item.disabled { background: #f8d7da; color: #721c24; }
            .automation-panel {
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
            }
            .file-list {
                max-height: 200px;
                overflow-y: auto;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                background: #f9f9f9;
            }
            .file-item {
                padding: 5px;
                border-bottom: 1px solid #eee;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .file-item:last-child {
                border-bottom: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Mana PDF Excel AI Ultimate</h1>
                <p>AI統合PDF→Excel変換システム</p>
            </div>

            <div class="dashboard">
                <!-- アップロードエリア -->
                <div class="card">
                    <h2>📄 PDF アップロード</h2>
                    <div class="upload-area" id="uploadArea">
                        <p>📁 PDFファイルをドラッグ&ドロップ</p>
                        <p>または</p>
                        <input type="file" id="fileInput" accept=".pdf" multiple style="display: none;">
                        <button class="btn" onclick="document.getElementById('fileInput').click()">
                            ファイルを選択
                        </button>
                    </div>

                    <div style="margin-top: 20px;">
                        <label>
                            <input type="checkbox" id="useMultiAI" checked>
                            🤖 マルチAI解析を使用
                        </label>
                    </div>

                    <div style="margin-top: 20px;">
                        <label>
                            <input type="checkbox" id="uploadToDrive">
                            ☁️ Google Driveにアップロード
                        </label>
                    </div>

                    <button class="btn" id="convertBtn" onclick="startConversion()" disabled>
                        🚀 変換開始
                    </button>

                    <div class="progress-bar" id="progressBar" style="display: none;">
                        <div class="progress-fill" id="progressFill"></div>
                    </div>

                    <div id="status" style="display: none;"></div>
                </div>

                <!-- 統計情報 -->
                <div class="card">
                    <h2>📊 システム統計</h2>
                    <div class="ai-status" id="aiStatus">
                        <div class="ai-item" id="geminiStatus">
                            <div>🤖 Gemini</div>
                            <div id="geminiEnabled">確認中...</div>
                        </div>
                        <div class="ai-item" id="openaiStatus">
                            <div>🧠 OpenAI</div>
                            <div id="openaiEnabled">確認中...</div>
                        </div>
                    </div>

                    <div class="stats-grid" id="statsGrid">
                        <!-- 統計情報が動的に挿入される -->
                    </div>
                </div>
            </div>

            <!-- 自動化パネル -->
            <div class="card">
                <h2>⏰ 自動化設定</h2>
                <div class="automation-panel">
                    <div style="margin-bottom: 15px;">
                        <label>
                            <input type="checkbox" id="dailyConversion">
                            🌅 日次自動変換 (09:00)
                        </label>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <label>
                            <input type="checkbox" id="hourlyMonitoring">
                            👁️ 時間毎監視
                        </label>
                    </div>
                    <button class="btn" onclick="updateAutomation()">
                        ⚙️ 自動化設定更新
                    </button>
                </div>
            </div>

            <!-- ファイル一覧 -->
            <div class="card">
                <h2>📁 出力ファイル一覧</h2>
                <div class="file-list" id="fileList">
                    <!-- ファイル一覧が動的に挿入される -->
                </div>
            </div>

            <!-- ログ表示 -->
            <div class="card">
                <h2>📝 リアルタイムログ</h2>
                <div class="log-container" id="logContainer">
                    <div>🚀 システム起動完了</div>
                    <div>📡 WebSocket接続中...</div>
                </div>
            </div>
        </div>

        <script>
            let ws = null;
            let selectedFiles = [];

            // WebSocket接続
            function connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

                ws.onopen = function(event) {
                    addLog('✅ WebSocket接続完了');
                };

                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    handleWebSocketMessage(data);
                };

                ws.onclose = function(event) {
                    addLog('❌ WebSocket接続切断');
                    setTimeout(connectWebSocket, 3000);
                };

                ws.onerror = function(error) {
                    addLog('❌ WebSocketエラー: ' + error);
                };
            }

            // WebSocketメッセージ処理
            function handleWebSocketMessage(data) {
                switch(data.type) {
                    case 'progress':
                        updateProgress(data.progress);
                        addLog(`📊 進捗: ${data.message}`);
                        break;
                    case 'status':
                        updateStatus(data.status, data.message);
                        addLog(`📢 ステータス: ${data.message}`);
                        break;
                    case 'complete':
                        updateStatus('success', `✅ 変換完了: ${data.result.excel_file}`);
                        hideProgress();
                        loadFileList();
                        loadStats();
                        break;
                    case 'error':
                        updateStatus('error', `❌ エラー: ${data.error}`);
                        hideProgress();
                        break;
                }
            }

            // ファイル選択処理
            document.getElementById('fileInput').addEventListener('change', function(e) {
                selectedFiles = Array.from(e.target.files);
                updateFileSelection();
            });

            // ドラッグ&ドロップ処理
            const uploadArea = document.getElementById('uploadArea');

            uploadArea.addEventListener('dragover', function(e) {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });

            uploadArea.addEventListener('dragleave', function(e) {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
            });

            uploadArea.addEventListener('drop', function(e) {
                e.preventDefault();
                uploadArea.classList.remove('dragover');

                const files = Array.from(e.dataTransfer.files).filter(file =>
                    file.type === 'application/pdf'
                );
                selectedFiles = files;
                updateFileSelection();
            });

            // ファイル選択更新
            function updateFileSelection() {
                const convertBtn = document.getElementById('convertBtn');
                if (selectedFiles.length > 0) {
                    convertBtn.disabled = false;
                    convertBtn.textContent = `🚀 変換開始 (${selectedFiles.length}ファイル)`;
                } else {
                    convertBtn.disabled = true;
                    convertBtn.textContent = '🚀 変換開始';
                }
            }

            // 変換開始
            async function startConversion() {
                if (selectedFiles.length === 0) return;

                const formData = new FormData();
                selectedFiles.forEach(file => {
                    formData.append('files', file);
                });

                formData.append('use_multi_ai', document.getElementById('useMultiAI').checked);
                formData.append('upload_to_drive', document.getElementById('uploadToDrive').checked);

                showProgress();
                updateStatus('info', '🚀 変換処理開始...');

                try {
                    const response = await fetch('/convert', {
                        method: 'POST',
                        body: formData
                    });

                    const result = await response.json();

                    if (result.success) {
                        updateStatus('success', `✅ 変換完了: ${result.excel_file}`);
                        loadFileList();
                        loadStats();
                    } else {
                        updateStatus('error', `❌ 変換失敗: ${result.error}`);
                    }
                } catch (error) {
                    updateStatus('error', `❌ 通信エラー: ${error}`);
                } finally {
                    hideProgress();
                }
            }

            // 進捗表示
            function showProgress() {
                document.getElementById('progressBar').style.display = 'block';
                document.getElementById('status').style.display = 'block';
            }

            function hideProgress() {
                document.getElementById('progressBar').style.display = 'none';
            }

            function updateProgress(progress) {
                document.getElementById('progressFill').style.width = progress + '%';
            }

            function updateStatus(type, message) {
                const statusDiv = document.getElementById('status');
                statusDiv.className = `status ${type}`;
                statusDiv.textContent = message;
                statusDiv.style.display = 'block';
            }

            function addLog(message) {
                const logContainer = document.getElementById('logContainer');
                const timestamp = new Date().toLocaleTimeString();
                logContainer.innerHTML += `<div>[${timestamp}] ${message}</div>`;
                logContainer.scrollTop = logContainer.scrollHeight;
            }

            // 統計情報読み込み
            async function loadStats() {
                try {
                    const response = await fetch('/stats');
                    const stats = await response.json();

                    // AI状態更新
                    const geminiEnabled = stats.system_info.ai_models.gemini;
                    const openaiEnabled = stats.system_info.ai_models.openai;

                    document.getElementById('geminiEnabled').textContent =
                        geminiEnabled ? '✅ 有効' : '❌ 無効';
                    document.getElementById('geminiStatus').className =
                        `ai-item ${geminiEnabled ? 'enabled' : 'disabled'}`;

                    document.getElementById('openaiEnabled').textContent =
                        openaiEnabled ? '✅ 有効' : '❌ 無効';
                    document.getElementById('openaiStatus').className =
                        `ai-item ${openaiEnabled ? 'enabled' : 'disabled'}`;

                    // 統計情報更新
                    const statsGrid = document.getElementById('statsGrid');
                    statsGrid.innerHTML = `
                        <div class="stat-item">
                            <div class="stat-number">${stats.conversion_stats.total_conversions}</div>
                            <div class="stat-label">総変換数</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-number">${stats.conversion_stats.successful_conversions}</div>
                            <div class="stat-label">成功数</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-number">${stats.conversion_stats.total_pages_processed}</div>
                            <div class="stat-label">処理ページ数</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-number">${stats.conversion_stats.ai_analysis_count}</div>
                            <div class="stat-label">AI解析回数</div>
                        </div>
                    `;
                } catch (error) {
                    addLog('❌ 統計情報読み込みエラー: ' + error);
                }
            }

            // ファイル一覧読み込み
            async function loadFileList() {
                try {
                    const response = await fetch('/files');
                    const files = await response.json();

                    const fileList = document.getElementById('fileList');
                    if (files.length === 0) {
                        fileList.innerHTML = '<div>ファイルがありません</div>';
                    } else {
                        fileList.innerHTML = files.map(file => `
                            <div class="file-item">
                                <span>📊 ${file.name}</span>
                                <div>
                                    <span style="color: #666; font-size: 0.9em;">${file.size}</span>
                                    <button class="btn" onclick="downloadFile('${file.name}')" style="margin-left: 10px; padding: 5px 10px; font-size: 12px;">
                                        📥 ダウンロード
                                    </button>
                                </div>
                            </div>
                        `).join('');
                    }
                } catch (error) {
                    addLog('❌ ファイル一覧読み込みエラー: ' + error);
                }
            }

            // ファイルダウンロード
            function downloadFile(filename) {
                window.open(`/download/${filename}`, '_blank');
            }

            // 自動化設定更新
            async function updateAutomation() {
                const config = {
                    daily_conversion: document.getElementById('dailyConversion').checked,
                    hourly_monitoring: document.getElementById('hourlyMonitoring').checked,
                    watch_directory: '/root/automation_input'
                };

                try {
                    const response = await fetch('/automation', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(config)
                    });

                    if (response.ok) {
                        updateStatus('success', '✅ 自動化設定更新完了');
                    } else {
                        updateStatus('error', '❌ 自動化設定更新失敗');
                    }
                } catch (error) {
                    updateStatus('error', '❌ 自動化設定更新エラー: ' + error);
                }
            }

            // 初期化
            document.addEventListener('DOMContentLoaded', function() {
                connectWebSocket();
                loadStats();
                loadFileList();

                // 定期的に統計情報を更新
                setInterval(loadStats, 30000);
                setInterval(loadFileList, 60000);
            });
        </script>
    </body>
    </html>
    """
    return html_content

# WebSocket接続
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ファイルアップロード・変換
@app.post("/convert")
async def convert_pdf(
    files: List[UploadFile] = File(...),
    use_multi_ai: bool = True,
    use_ocr: bool = True,
    upload_to_drive: bool = False
):
    """PDF変換エンドポイント"""
    try:
        # ファイル保存
        temp_files = []
        for file in files:
            if not file.filename.endswith('.pdf'):
                raise HTTPException(status_code=400, detail="PDFファイルのみ対応")

            temp_path = f"/tmp/{file.filename}"
            async with aiofiles.open(temp_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            temp_files.append(temp_path)

        # 進捗コールバックを設定したコンバーターを作成
        async def progress_callback(progress_data: Dict[str, Any]):
            """進捗をWebSocket経由で送信"""
            await manager.send_progress(progress_data)

        from mana_pdf_excel_ai_ultimate import ManaPDFExcelAIUltimate
        converter = ManaPDFExcelAIUltimate(progress_callback=lambda data: asyncio.create_task(progress_callback(data)))

        # 変換実行
        if len(temp_files) == 1:
            result = await converter.convert_pdf_to_excel_ai(temp_files[0], use_multi_ai, use_ocr=use_ocr)
        else:
            result = await converter.batch_convert_ai(temp_files, use_multi_ai)

        # 変換完了通知
        await manager.send_progress({
            "type": "complete",
            "result": {
                "excel_file": result.get("excel_file", ""),
                "success": result.get("success", False)
            }
        })

        # 一時ファイル削除
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except Exception:
                pass

        return result

    except Exception as e:
        logger.error(f"変換エラー: {e}")
        await manager.send_progress({
            "type": "error",
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))

# 統計情報取得
@app.get("/stats")
async def get_stats():
    """統計情報取得"""
    converter = get_ultimate_converter()
    return converter.get_stats()

# ファイル一覧取得
@app.get("/files")
async def get_files():
    """出力ファイル一覧取得"""
    output_dirs = [
        (Path("/root/excel_output_ultimate"), "AI統合"),
        (Path("/root/excel_output_easyocr"), "構造化 (EasyOCR)")
    ]

    files: List[Dict[str, Any]] = []

    for directory, label in output_dirs:
        if directory.exists():
            for file_path in directory.glob("*.xlsx"):
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "size": f"{stat.st_size / 1024:.1f} KB",
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "category": label
                })

    files.sort(key=lambda x: x["modified"], reverse=True)
    return files

# ファイルダウンロード
@app.get("/download/{filename:path}")
async def download_file(filename: str):
    """ファイルダウンロード（日本語ファイル名対応）"""
    import urllib.parse

    # URLデコード（日本語ファイル名対応）
    filename = urllib.parse.unquote(filename)

    search_dirs = [
        Path("/root/excel_output_ultimate"),
        Path("/root/excel_output_easyocr")
    ]

    file_path = None
    for directory in search_dirs:
        candidate = directory / filename
        if candidate.exists():
            file_path = candidate
            break

    if file_path is None:
        raise HTTPException(status_code=404, detail=f"ファイルが見つかりません: {filename}")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            "Content-Disposition": f'attachment; filename*=UTF-8\'\'{urllib.parse.quote(filename)}'
        }
    )

# 自動化設定
@app.post("/automation")
async def update_automation(config: AutomationConfig):
    """自動化設定更新"""
    try:
        converter = get_ultimate_converter()
        converter.setup_automation(config.dict())

        return {"success": True, "message": "自動化設定更新完了"}

    except Exception as e:
        logger.error(f"自動化設定エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# バッチ変換
@app.post("/batch")
async def batch_convert(request: BatchConversionRequest):
    """バッチ変換"""
    try:
        result = await batch_pdf_to_excel_ai(request.pdf_paths, request.use_multi_ai)
        return result

    except Exception as e:
        logger.error(f"バッチ変換エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 Mana PDF Excel AI Ultimate Web UI 起動中...")
    print("📊 ダッシュボード: http://localhost:5026")
    print("📚 API文書: http://localhost:5026/docs")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5026,
        log_level="info"
    )



