#!/usr/bin/env python3
"""
PowerPoint Simple Viewer - シンプルな画像ビューアー
Created: 2025-10-12
"""

from flask import Flask, send_file, Response
import os
from pathlib import Path

app = Flask(__name__, template_folder='/root/templates')

POWERPOINT_DIR = Path("/root/powerpoint_files")
OUTPUT_DIR = Path("/root/powerpoint_viewer_output")
OUTPUT_DIR.mkdir(exist_ok=True)

def get_slides():
    """スライド画像のリストを取得"""
    slides = sorted(OUTPUT_DIR.glob("tire_exchange_ad_sample-*.png"))
    return slides

@app.route('/')
def index():
    """メインページ - スライド一覧をHTML表示"""
    slides = get_slides()
    
    html = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎨 PowerPoint Viewer - タイヤ交換広告</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        
        .header h1 {
            font-size: 3em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.3em;
            opacity: 0.9;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .slide {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            transition: transform 0.3s ease;
        }
        
        .slide:hover {
            transform: translateY(-5px);
        }
        
        .slide img {
            width: 100%;
            height: auto;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
        }
        
        .slide-number {
            text-align: center;
            font-size: 1.5em;
            color: #333;
            margin-bottom: 20px;
            font-weight: bold;
        }
        
        .download-section {
            text-align: center;
            margin-top: 40px;
        }
        
        .btn {
            display: inline-block;
            padding: 15px 40px;
            background: white;
            color: #667eea;
            text-decoration: none;
            border-radius: 10px;
            font-weight: bold;
            font-size: 1.2em;
            box-shadow: 0 5px 20px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
        }
        
        .btn:hover {
            transform: scale(1.05);
            box-shadow: 0 8px 30px rgba(0,0,0,0.4);
        }
        
        .info-box {
            background: rgba(255,255,255,0.2);
            padding: 20px;
            border-radius: 10px;
            color: white;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .info-box h2 {
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎨 タイヤ交換広告サンプル</h1>
        <p>tire_exchange_ad_sample.pptx</p>
    </div>
    
    <div class="container">
        <div class="info-box">
            <h2>📊 スライド総数: """ + str(len(slides)) + """枚</h2>
            <p>高解像度PNG形式で変換済み（150dpi）</p>
        </div>
        
        <div class="download-section">
            <a href="/pdf" class="btn">📄 PDF版をダウンロード</a>
        </div>
"""
    
    # 各スライドを表示
    for i, slide in enumerate(slides, 1):
        html += f"""
        <div class="slide">
            <div class="slide-number">📄 スライド {i}</div>
            <img src="/slide/{slide.name}" alt="Slide {i}">
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    
    return Response(html, mimetype='text/html')

@app.route('/slide/<filename>')
def get_slide(filename):
    """個別スライド画像を返す"""
    slide_path = OUTPUT_DIR / filename
    if slide_path.exists():
        return send_file(str(slide_path), mimetype='image/png')
    return "Image not found", 404

@app.route('/pdf')
def get_pdf():
    """PDF版を返す"""
    pdf_path = POWERPOINT_DIR / "tire_exchange_ad_sample.pdf"
    if pdf_path.exists():
        return send_file(str(pdf_path), 
                        mimetype='application/pdf',
                        as_attachment=True,
                        download_name='tire_exchange_ad_sample.pdf')
    return "PDF not found", 404

if __name__ == '__main__':
    print("=" * 60)
    print("🎨 PowerPoint Simple Viewer 起動")
    print("=" * 60)
    print(f"📁 PowerPointディレクトリ: {POWERPOINT_DIR}")
    print(f"📁 画像ディレクトリ: {OUTPUT_DIR}")
    print(f"📊 スライド数: {len(list(get_slides()))}枚")
    print()
    print("🌐 アクセス方法:")
    print("  ローカル: http://localhost:5024")
    print("  外部: http://163.44.120.49:5024")
    print("  Tailscale: http://100.93.120.33:5024")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5024, debug=os.getenv("DEBUG", "False").lower() == "true")

