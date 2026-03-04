#!/usr/bin/env python3
"""
AIファイル分析エンジン
画像、テキスト、PDF、ドキュメントを自動分析＋分類
"""

import hashlib
from pathlib import Path
from datetime import datetime
from PIL import Image
import json
import magic
from collections import defaultdict


class FileAnalyzer:
    """ファイル分析クラス"""
    
    def __init__(self):
        self.mime = magic.Magic(mime=True)
        self.file_categories = defaultdict(list)
    
    def analyze_file(self, file_path):
        """
        ファイルを分析して詳細情報を返す
        
        Returns:
            dict: ファイル情報
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"error": "File not found"}
        
        stat = file_path.stat()
        
        info = {
            "path": str(file_path),
            "name": file_path.name,
            "size": stat.st_size,
            "size_mb": stat.st_size / (1024 * 1024),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": file_path.suffix.lower(),
            "mime_type": self.mime.from_file(str(file_path)),
            "hash_md5": self.calculate_hash(file_path),
        }
        
        # ファイルタイプ別の詳細分析
        if info["mime_type"].startswith("image/"):
            info.update(self.analyze_image(file_path))
            info["category"] = "image"
        elif info["mime_type"].startswith("text/"):
            info.update(self.analyze_text(file_path))
            info["category"] = "text"
        elif info["extension"] in [".pdf"]:
            info["category"] = "pdf"
        elif info["extension"] in [".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]:
            info["category"] = "document"
        elif info["extension"] in [".mp4", ".avi", ".mov", ".mkv"]:
            info["category"] = "video"
        elif info["extension"] in [".mp3", ".wav", ".flac", ".m4a"]:
            info["category"] = "audio"
        elif info["extension"] in [".zip", ".tar", ".gz", ".7z", ".rar"]:
            info["category"] = "archive"
        else:
            info["category"] = "other"
        
        # AI推奨フォルダ
        info["suggested_folder"] = self.suggest_folder(info)
        
        # タグ生成
        info["tags"] = self.generate_tags(info)
        
        return info
    
    def calculate_hash(self, file_path):
        """MD5ハッシュ計算（重複検出用）"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return None
    
    def analyze_image(self, file_path):
        """画像ファイル分析"""
        try:
            with Image.open(file_path) as img:
                return {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                    "megapixels": (img.width * img.height) / 1000000
                }
        except:
            return {}
    
    def analyze_text(self, file_path):
        """テキストファイル分析"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(10000)  # 最初の10KB
                lines = content.split('\n')
                
                return {
                    "line_count": len(lines),
                    "char_count": len(content),
                    "word_count": len(content.split()),
                    "preview": content[:200]
                }
        except:
            return {}
    
    def suggest_folder(self, info):
        """AI推奨フォルダ名を生成"""
        category = info["category"]
        extension = info["extension"]
        size_mb = info["size_mb"]
        
        # カテゴリベースの基本分類
        folder_map = {
            "image": "📷 Images",
            "text": "📝 Documents/Text",
            "pdf": "📄 Documents/PDF",
            "document": "📊 Documents/Office",
            "video": "🎬 Videos",
            "audio": "🎵 Audio",
            "archive": "📦 Archives"
        }
        
        base_folder = folder_map.get(category, "📁 Others")
        
        # サイズによるサブフォルダ
        if size_mb > 100:
            base_folder += "/Large Files"
        elif size_mb < 0.1:
            base_folder += "/Small Files"
        
        # 画像の場合は解像度による分類
        if category == "image" and "width" in info:
            if info["width"] >= 3000 or info["height"] >= 3000:
                base_folder = "📷 Images/High Resolution"
            elif info["width"] < 800:
                base_folder = "📷 Images/Thumbnails"
        
        return base_folder
    
    def generate_tags(self, info):
        """自動タグ生成"""
        tags = []
        
        # カテゴリタグ
        tags.append(info["category"])
        
        # 拡張子タグ
        if info["extension"]:
            tags.append(info["extension"][1:])  # .pngremove
        
        # サイズタグ
        size_mb = info["size_mb"]
        if size_mb < 0.1:
            tags.append("tiny")
        elif size_mb < 1:
            tags.append("small")
        elif size_mb < 10:
            tags.append("medium")
        elif size_mb < 100:
            tags.append("large")
        else:
            tags.append("huge")
        
        # 日付タグ（最終更新）
        modified_date = datetime.fromisoformat(info["modified"])
        tags.append(modified_date.strftime("%Y-%m"))
        
        # 画像特有のタグ
        if info["category"] == "image" and "width" in info:
            if info["megapixels"] >= 10:
                tags.append("high_res")
            if info["width"] > info["height"]:
                tags.append("landscape")
            else:
                tags.append("portrait")
        
        return list(set(tags))
    
    def find_duplicates(self, directory):
        """重複ファイル検出"""
        hash_map = defaultdict(list)
        duplicates = []
        
        directory = Path(directory)
        
        print(f"🔍 重複ファイル検索中: {directory}")
        
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                file_hash = self.calculate_hash(file_path)
                if file_hash:
                    hash_map[file_hash].append(str(file_path))
        
        # 重複を抽出
        for file_hash, paths in hash_map.items():
            if len(paths) > 1:
                # サイズ情報も追加
                size = Path(paths[0]).stat().st_size
                duplicates.append({
                    "hash": file_hash,
                    "paths": paths,
                    "count": len(paths),
                    "size": size,
                    "size_mb": size / (1024 * 1024),
                    "total_wasted_mb": (size * (len(paths) - 1)) / (1024 * 1024)
                })
        
        # サイズ順でソート
        duplicates.sort(key=lambda x: x["total_wasted_mb"], reverse=True)
        
        total_wasted = sum(d["total_wasted_mb"] for d in duplicates)
        
        print(f"✅ 検索完了: {len(duplicates)}組の重複ファイル発見")
        print(f"💾 無駄な容量: {total_wasted:.2f} MB")
        
        return {
            "duplicates": duplicates,
            "total_duplicates": len(duplicates),
            "total_wasted_mb": total_wasted
        }
    
    def batch_analyze(self, directory, max_files=1000):
        """ディレクトリ内の全ファイルを一括分析"""
        directory = Path(directory)
        results = []
        count = 0
        
        print(f"📁 ディレクトリ分析中: {directory}")
        
        for file_path in directory.rglob("*"):
            if file_path.is_file() and count < max_files:
                info = self.analyze_file(file_path)
                results.append(info)
                count += 1
                
                if count % 100 == 0:
                    print(f"  分析済み: {count}ファイル...")
        
        print(f"✅ 分析完了: {count}ファイル")
        
        # カテゴリ別集計
        category_stats = defaultdict(lambda: {"count": 0, "size_mb": 0})
        for info in results:
            cat = info.get("category", "other")
            category_stats[cat]["count"] += 1
            category_stats[cat]["size_mb"] += info.get("size_mb", 0)
        
        return {
            "files": results,
            "total_count": count,
            "category_stats": dict(category_stats)
        }


# ===== CLI実行 =====

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='AIファイル分析エンジン')
    parser.add_argument('--analyze', type=str, help='単一ファイル分析')
    parser.add_argument('--batch', type=str, help='ディレクトリ一括分析')
    parser.add_argument('--duplicates', type=str, help='重複ファイル検出')
    parser.add_argument('--output', type=str, help='結果保存先JSON')
    
    args = parser.parse_args()
    
    analyzer = FileAnalyzer()
    
    if args.analyze:
        print(f"📄 ファイル分析: {args.analyze}")
        result = analyzer.analyze_file(args.analyze)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.batch:
        result = analyzer.batch_analyze(args.batch)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"✅ 結果保存: {args.output}")
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.duplicates:
        result = analyzer.find_duplicates(args.duplicates)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"✅ 結果保存: {args.output}")
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
    
    else:
        parser.print_help()

