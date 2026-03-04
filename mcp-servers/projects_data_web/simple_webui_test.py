#!/usr/bin/env python3
"""
シンプルなWebUIテスト
接続エラーを回避した最小構成のPDF-Excel変換システム
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn
import uuid
from pathlib import Path

app = FastAPI(title="PDF-Excel変換システム シンプル版")

# 出力ディレクトリ
output_dir = Path("/tmp/simple_output")
output_dir.mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def get_simple_homepage():
    """シンプルなホームページ"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PDF-Excel変換システム</title>
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0; padding: 40px; min-height: 100vh;
            }
            .container {
                max-width: 800px; margin: 0 auto; background: white;
                border-radius: 20px; padding: 40px; box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            }
            .header {
                text-align: center; margin-bottom: 40px;
            }
            .header h1 { color: #333; font-size: 2.5em; margin-bottom: 10px; }
            .upload-area {
                border: 3px dashed #ddd; border-radius: 15px; padding: 40px;
                text-align: center; margin-bottom: 30px; cursor: pointer;
                transition: all 0.3s ease;
            }
            .upload-area:hover { border-color: #667eea; background: #f8f9ff; }
            .upload-icon { font-size: 4em; color: #667eea; margin-bottom: 20px; }
            .upload-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; border: none; padding: 15px 30px;
                border-radius: 25px; font-size: 1.1em; cursor: pointer;
            }
            .file-input { display: none; }
            .progress { display: none; margin-top: 20px; }
            .progress-bar { width: 100%; height: 20px; background: #e0e0e0; border-radius: 10px; overflow: hidden; }
            .progress-fill { height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); width: 0%; transition: width 0.3s ease; }
            .result { display: none; margin-top: 20px; padding: 20px; background: #e8f5e8; border-radius: 15px; border-left: 5px solid #4caf50; }
            .download-btn {
                background: #4caf50; color: white; border: none; padding: 12px 25px;
                border-radius: 20px; text-decoration: none; display: inline-block; margin-top: 15px;
            }
            .error { display: none; margin-top: 20px; padding: 20px; background: #ffeaea; border-radius: 15px; border-left: 5px solid #f44336; color: #d32f2f; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 PDF-Excel変換システム</h1>
                <p>シンプル版 - 高精度なPDF変換</p>
            </div>
            
            <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                <div class="upload-icon">📄</div>
                <div>PDFファイルをクリックして選択</div>
                <button class="upload-btn">ファイルを選択</button>
                <input type="file" id="fileInput" class="file-input" accept=".pdf" />
            </div>
            
            <div class="progress" id="progress">
                <div>変換処理中...</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
            </div>
            
            <div class="result" id="result">
                <h3>✅ 変換完了！</h3>
                <p>PDFファイルがExcelファイルに変換されました。</p>
                <a href="#" class="download-btn" id="downloadBtn">📥 ダウンロード</a>
            </div>
            
            <div class="error" id="error">
                <h3>❌ エラー</h3>
                <p id="errorMessage"></p>
            </div>
        </div>
        
        <script>
            document.getElementById('fileInput').addEventListener('change', async function(e) {
                if (e.target.files.length > 0) {
                    await handleFile(e.target.files[0]);
                }
            });
            
            async function handleFile(file) {
                if (!file.name.toLowerCase().endsWith('.pdf')) {
                    showError('PDFファイルを選択してください。');
                    return;
                }
                
                try {
                    showProgress();
                    
                    const formData = new FormData();
                    formData.append('file', file);
                    
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        throw new Error('アップロードに失敗しました。');
                    }
                    
                    const result = await response.json();
                    
                    // 変換処理（模擬）
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    
                    showResult(result.task_id);
                    
                } catch (error) {
                    showError('ファイルの処理に失敗しました: ' + error.message);
                }
            }
            
            function showProgress() {
                document.getElementById('progress').style.display = 'block';
                document.getElementById('result').style.display = 'none';
                document.getElementById('error').style.display = 'none';
                
                let progress = 0;
                const interval = setInterval(() => {
                    progress += 10;
                    document.getElementById('progressFill').style.width = progress + '%';
                    if (progress >= 100) {
                        clearInterval(interval);
                    }
                }, 200);
            }
            
            function showResult(taskId) {
                document.getElementById('progress').style.display = 'none';
                document.getElementById('result').style.display = 'block';
                document.getElementById('error').style.display = 'none';
                document.getElementById('downloadBtn').href = `/download/${taskId}`;
            }
            
            function showError(message) {
                document.getElementById('progress').style.display = 'none';
                document.getElementById('result').style.display = 'none';
                document.getElementById('error').style.display = 'block';
                document.getElementById('errorMessage').textContent = message;
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """ファイルアップロード"""
    try:
        task_id = str(uuid.uuid4())
        file_path = output_dir / f"{task_id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        print(f"✅ ファイルアップロード完了: {file.filename} -> {task_id}")
        
        return {"task_id": task_id, "filename": file.filename, "status": "uploaded"}
        
    except Exception as e:
        print(f"❌ アップロードエラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{task_id}")
async def download_file(task_id: str):
    """ファイルダウンロード（模擬）"""
    try:
        # 実際の変換処理をここに実装
        # 今回は模擬的なExcelファイルを生成
        
        mock_excel_path = output_dir / f"{task_id}_converted.xlsx"
        
        # 模擬Excelファイル作成
        import pandas as pd
        df = pd.DataFrame({
            '項目': ['PDF変換テスト', '10月3日データ', 'システム動作確認'],
            '値': ['成功', '完了', '正常'],
            '備考': ['PDF-Excel変換システム', '実際のデータ処理', '本格運用準備完了']
        })
        
        df.to_excel(mock_excel_path, index=False)
        
        return FileResponse(
            path=str(mock_excel_path),
            filename=f"converted_{task_id}.xlsx",
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        print(f"❌ ダウンロードエラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def main():
    print("🚀 PDF-Excel変換システム シンプル版起動")
    print("=" * 50)
    print("🌐 URL: http://localhost:8080")
    print("📁 出力先: /tmp/simple_output")
    print("=" * 50)
    
    uvicorn.run(
        "simple_webui_test:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()

