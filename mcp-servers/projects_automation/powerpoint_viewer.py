#!/usr/bin/env python3
"""
PowerPoint Viewer - PowerPointファイルをWebブラウザで表示
Created: 2025-10-12
"""

from flask import Flask, render_template, send_file, jsonify
import os
from pathlib import Path
import subprocess

app = Flask(__name__)

POWERPOINT_DIR = Path("/root/powerpoint_files")
OUTPUT_DIR = Path("/root/powerpoint_viewer_output")
OUTPUT_DIR.mkdir(exist_ok=True)

def convert_pptx_to_images(pptx_path):
    """PowerPointファイルを画像に変換"""
    pptx_path = Path(pptx_path)
    pdf_path = OUTPUT_DIR / f"{pptx_path.stem}.pdf"
    image_prefix = OUTPUT_DIR / pptx_path.stem
    
    # Step 1: PPTX → PDF
    if not pdf_path.exists():
        cmd = [
            "libreoffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(OUTPUT_DIR),
            str(pptx_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    
    # Step 2: PDF → Images
    images = []
    try:
        # pdftoppm を使用
        cmd = [
            "pdftoppm",
            "-png",
            "-r", "150",  # 解像度150dpi
            str(pdf_path),
            str(image_prefix)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # 生成された画像を収集
        for img in sorted(OUTPUT_DIR.glob(f"{pptx_path.stem}-*.png")):
            images.append(img.name)
    except subprocess.SubprocessError:
        # pdftoppmが使えない場合はImageMagickを試す
        try:
            cmd = [
                "convert",
                "-density", "150",
                str(pdf_path),
                str(image_prefix / "slide.png")
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
            for img in sorted(OUTPUT_DIR.glob(f"{pptx_path.stem}/slide-*.png")):
                images.append(img.name)
        except Exception as e:
            print(f"画像変換失敗: {e}")
    
    return images

@app.route('/')
def index():
    """メインページ - PowerPointファイル一覧"""
    pptx_files = []
    for pptx in POWERPOINT_DIR.glob("*.pptx"):
        pptx_files.append({
            'name': pptx.name,
            'stem': pptx.stem,
            'size': pptx.stat().st_size,
            'path': str(pptx)
        })
    
    return render_template('powerpoint_viewer.html', files=pptx_files)

@app.route('/view/<filename>')
def view_pptx(filename):
    """PowerPointファイルを表示"""
    pptx_path = POWERPOINT_DIR / filename
    
    if not pptx_path.exists():
        return jsonify({'error': 'ファイルが見つかりません'}), 404
    
    # 画像に変換
    try:
        images = convert_pptx_to_images(pptx_path)
        
        return render_template('powerpoint_slides.html', 
                             filename=filename,
                             images=images,
                             total_slides=len(images))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/image/<filename>')
def get_image(filename):
    """画像ファイルを返す"""
    image_path = OUTPUT_DIR / filename
    if image_path.exists():
        return send_file(str(image_path), mimetype='image/png')
    return jsonify({'error': 'Image not found'}), 404

@app.route('/pdf/<filename>')
def get_pdf(filename):
    """PDFファイルを返す"""
    stem = Path(filename).stem
    pdf_path = OUTPUT_DIR / f"{stem}.pdf"
    if pdf_path.exists():
        return send_file(str(pdf_path), mimetype='application/pdf')
    return jsonify({'error': 'PDF not found'}), 404

if __name__ == '__main__':
    print("=" * 60)
    print("🎨 PowerPoint Viewer 起動")
    print("=" * 60)
    print(f"📁 PowerPointディレクトリ: {POWERPOINT_DIR}")
    print(f"📁 出力ディレクトリ: {OUTPUT_DIR}")
    print()
    print("アクセス方法:")
    print("  ローカル: http://localhost:5009")
    print("  外部: http://163.44.120.49:5009")
    print("  Tailscale: http://100.93.120.33:5009")
    print("=" * 60)
    
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

