#!/usr/bin/env python3
"""
AIファイル自動整理システム
内容分析して自動カテゴリ分け
"""

from pathlib import Path
import shutil
from datetime import datetime

class AIFileOrganizer:
    """AIファイル整理"""
    
    def __init__(self, target_dir="/root/downloads"):
        self.target_dir = Path(target_dir)
        self.organized_dir = Path("/root/organized_files")
        
        # カテゴリ別フォルダ作成
        self.categories = {
            "documents": self.organized_dir / "Documents",
            "images": self.organized_dir / "Images",
            "code": self.organized_dir / "Code",
            "data": self.organized_dir / "Data",
            "videos": self.organized_dir / "Videos",
            "archives": self.organized_dir / "Archives",
            "others": self.organized_dir / "Others"
        }
        
        for cat_dir in self.categories.values():
            cat_dir.mkdir(parents=True, exist_ok=True)
    
    def analyze_file(self, filepath):
        """ファイル分析してカテゴリ判定"""
        ext = filepath.suffix.lower()
        
        # 拡張子ベースの分類
        if ext in ['.pdf', '.docx', '.doc', '.txt', '.md']:
            return "documents"
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']:
            return "images"
        elif ext in ['.py', '.js', '.java', '.cpp', '.rs', '.go']:
            return "code"
        elif ext in ['.csv', '.xlsx', '.json', '.xml', '.db']:
            return "data"
        elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
            return "videos"
        elif ext in ['.zip', '.tar', '.gz', '.rar']:
            return "archives"
        else:
            return "others"
    
    def organize_files(self, dry_run=False):
        """ファイル整理実行"""
        if not self.target_dir.exists():
            print(f"❌ ディレクトリが存在しません: {self.target_dir}")
            return
        
        organized_count = 0
        stats = {cat: 0 for cat in self.categories.keys()}
        
        print(f"📁 ファイル整理開始: {self.target_dir}\n")
        
        for file in self.target_dir.glob("*"):
            if file.is_file():
                # カテゴリ判定
                category = self.analyze_file(file)
                target_dir = self.categories[category]
                
                # 移動先パス
                dest_path = target_dir / file.name
                
                # 重複チェック
                if dest_path.exists():
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    dest_path = target_dir / f"{file.stem}_{timestamp}{file.suffix}"
                
                if dry_run:
                    print(f"  {file.name} → {category}/")
                else:
                    shutil.move(str(file), str(dest_path))
                    print(f"✅ {file.name} → {category}/")
                
                stats[category] += 1
                organized_count += 1
        
        # 統計表示
        print(f"\n📊 整理完了: {organized_count}ファイル")
        for cat, count in stats.items():
            if count > 0:
                print(f"  {cat}: {count}ファイル")
        
        return stats
    
    def find_duplicates(self):
        """重複ファイル検出"""
        
        hashes = {}
        duplicates = []
        
        for cat_dir in self.categories.values():
            for file in cat_dir.glob("**/*"):
                if file.is_file():
                    # ファイルハッシュ計算
                    file_hash = self._calculate_hash(file)
                    
                    if file_hash in hashes:
                        duplicates.append({
                            "original": hashes[file_hash],
                            "duplicate": str(file)
                        })
                    else:
                        hashes[file_hash] = str(file)
        
        return duplicates
    
    def _calculate_hash(self, filepath):
        """ファイルハッシュ計算"""
        import hashlib
        
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

def main():
    organizer = AIFileOrganizer()
    
    print("📁 AIファイル自動整理システム\n")
    
    # ドライラン
    print("🧪 テスト実行（ドライラン）:\n")
    organizer.organize_files(dry_run=True)
    
    print("\n✅ テスト完了")
    print("📁 整理先: /root/organized_files/")

if __name__ == "__main__":
    main()

