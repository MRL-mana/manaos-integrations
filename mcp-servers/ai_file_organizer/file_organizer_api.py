#!/usr/bin/env python3
"""
AIファイル自動整理APIサーバー
ファイル分析・重複検出・自動整理をAPI化
"""

import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
from datetime import datetime
import json
import shutil
from file_analyzer import FileAnalyzer

app = Flask(__name__)
CORS(app)

analyzer = FileAnalyzer()

# ディレクトリ設定
WORK_DIR = Path("/root/ai_file_organizer")
REPORTS_DIR = WORK_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "service": "AI File Organizer API",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/analyze/file', methods=['POST'])
def analyze_file():
    """単一ファイル分析"""
    try:
        data = request.json
        file_path = data.get('path')
        
        if not file_path:
            return jsonify({"success": False, "error": "pathが必要です"}), 400
        
        log(f"ファイル分析: {file_path}")
        result = analyzer.analyze_file(file_path)
        
        if "error" in result:
            return jsonify({"success": False, "error": result["error"]}), 404
        
        return jsonify({"success": True, "file_info": result})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/analyze/directory', methods=['POST'])
def analyze_directory():
    """ディレクトリ一括分析"""
    try:
        data = request.json
        directory = data.get('path')
        max_files = data.get('max_files', 1000)
        
        if not directory:
            return jsonify({"success": False, "error": "pathが必要です"}), 400
        
        log(f"ディレクトリ分析: {directory}")
        result = analyzer.batch_analyze(directory, max_files=max_files)
        
        # レポート保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = REPORTS_DIR / f"analysis_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        log(f"✅ レポート保存: {report_file.name}")
        
        return jsonify({
            "success": True,
            "total_files": result["total_count"],
            "category_stats": result["category_stats"],
            "report_file": str(report_file)
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/duplicates/find', methods=['POST'])
def find_duplicates():
    """重複ファイル検出"""
    try:
        data = request.json
        directory = data.get('path')
        
        if not directory:
            return jsonify({"success": False, "error": "pathが必要です"}), 400
        
        log(f"重複検出: {directory}")
        result = analyzer.find_duplicates(directory)
        
        # レポート保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = REPORTS_DIR / f"duplicates_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        log(f"✅ 重複レポート保存: {report_file.name}")
        
        return jsonify({
            "success": True,
            "total_duplicates": result["total_duplicates"],
            "total_wasted_mb": result["total_wasted_mb"],
            "duplicates": result["duplicates"][:20],  # 最大20組
            "report_file": str(report_file)
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/organize/preview', methods=['POST'])
def organize_preview():
    """整理プレビュー（実行しない）"""
    try:
        data = request.json
        directory = data.get('path')
        
        if not directory:
            return jsonify({"success": False, "error": "pathが必要です"}), 400
        
        log(f"整理プレビュー: {directory}")
        result = analyzer.batch_analyze(directory, max_files=500)
        
        # 移動プラン作成
        organize_plan = []
        for file_info in result["files"]:
            suggested_folder = file_info["suggested_folder"]
            current_path = file_info["path"]
            new_path = str(Path(directory) / suggested_folder / Path(current_path).name)
            
            if current_path != new_path:
                organize_plan.append({
                    "from": current_path,
                    "to": new_path,
                    "category": file_info["category"],
                    "tags": file_info["tags"]
                })
        
        return jsonify({
            "success": True,
            "total_files": result["total_count"],
            "files_to_move": len(organize_plan),
            "organize_plan": organize_plan[:50]  # 最大50件
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/organize/execute', methods=['POST'])
def organize_execute():
    """自動整理実行"""
    try:
        data = request.json
        directory = data.get('path')
        dry_run = data.get('dry_run', True)  # デフォルトはdry_run
        
        if not directory:
            return jsonify({"success": False, "error": "pathが必要です"}), 400
        
        log(f"自動整理{'（ドライラン）' if dry_run else '（実行）'}: {directory}")
        result = analyzer.batch_analyze(directory, max_files=500)
        
        moved_count = 0
        errors = []
        
        for file_info in result["files"]:
            try:
                suggested_folder = file_info["suggested_folder"]
                current_path = Path(file_info["path"])
                new_dir = Path(directory) / suggested_folder
                new_path = new_dir / current_path.name
                
                if str(current_path) != str(new_path):
                    if not dry_run:
                        new_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(current_path), str(new_path))
                        log(f"移動: {current_path.name} → {suggested_folder}")
                    moved_count += 1
            except Exception as e:
                errors.append({"file": str(current_path), "error": str(e)})
        
        return jsonify({
            "success": True,
            "dry_run": dry_run,
            "total_files": result["total_count"],
            "moved_count": moved_count,
            "errors": errors
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    log("=" * 60)
    log("🗂️ AIファイル自動整理API起動")
    log("=" * 60)
    log("API起動中... (http://0.0.0.0:5016)")
    log("Ctrl+C で停止")
    
    app.run(host='0.0.0.0', port=5016, debug=os.getenv("DEBUG", "False").lower() == "true")

