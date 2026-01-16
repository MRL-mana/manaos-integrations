"""
ドキュメント整理スクリプト
プロジェクト内のマークダウンファイルをカテゴリ別に整理
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import hashlib
from collections import defaultdict
import json

# カテゴリ定義
CATEGORIES = {
    "completion_reports": {
        "keywords": ["COMPLETE", "完了", "COMPLETE", "FINAL", "COMPLETE", "ALL_COMPLETE", "COMPLETE_SUMMARY"],
        "patterns": ["*_COMPLETE*.md", "*_COMPLETE_*.md", "*完了*.md", "*_FINAL*.md"]
    },
    "guides": {
        "keywords": ["GUIDE", "README", "SETUP", "USAGE", "QUICK_START", "HOW_TO", "ガイド", "セットアップ"],
        "patterns": ["*_GUIDE*.md", "*_README*.md", "*_SETUP*.md", "*_USAGE*.md", "*_QUICK_START*.md"]
    },
    "status": {
        "keywords": ["STATUS", "REPORT", "CURRENT", "OPERATIONAL", "状態", "レポート"],
        "patterns": ["*_STATUS*.md", "*_REPORT*.md", "*_CURRENT*.md", "*_OPERATIONAL*.md"]
    },
    "troubleshooting": {
        "keywords": ["TROUBLESHOOTING", "FIX", "ERROR", "ISSUE", "PROBLEM", "トラブル", "修正", "エラー"],
        "patterns": ["*_TROUBLESHOOTING*.md", "*_FIX*.md", "*_ERROR*.md", "*_ISSUE*.md"]
    },
    "integration": {
        "keywords": ["INTEGRATION", "SETUP", "CONFIG", "統合", "設定"],
        "patterns": ["*_INTEGRATION*.md", "*_SETUP*.md", "*_CONFIG*.md"]
    },
    "optimization": {
        "keywords": ["OPTIMIZATION", "IMPROVEMENT", "ENHANCEMENT", "最適化", "改善"],
        "patterns": ["*_OPTIMIZATION*.md", "*_IMPROVEMENT*.md", "*_ENHANCEMENT*.md"]
    },
    "archive": {
        "keywords": ["OLD", "BACKUP", "TEMP", "古い", "バックアップ", "一時"],
        "patterns": ["*_OLD*.md", "*_BACKUP*.md", "*_TEMP*.md"]
    }
}

class DocumentOrganizer:
    """ドキュメント整理クラス"""
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.docs_dir = self.root_dir / "docs"
        self.archive_dir = self.docs_dir / "archive"
        self.stats = {
            "total_files": 0,
            "moved_files": 0,
            "duplicate_files": [],
            "categories": defaultdict(int)
        }
        self.file_hashes = {}  # 重複検出用
        
    def create_directories(self):
        """カテゴリ別ディレクトリを作成"""
        for category in CATEGORIES.keys():
            (self.docs_dir / category).mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        print(f"[完了] ディレクトリを作成しました: {self.docs_dir}")
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """ファイルのハッシュを計算（重複検出用）"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception as e:
            print(f"[警告] ハッシュ計算エラー: {file_path} - {e}")
            return ""
    
    def categorize_file(self, file_path: Path) -> Optional[str]:
        """ファイルをカテゴリに分類"""
        filename = file_path.name.upper()
        
        # キーワードベースの分類
        for category, config in CATEGORIES.items():
            for keyword in config["keywords"]:
                if keyword in filename:
                    return category
        
        # パターンベースの分類（簡易版）
        for category, config in CATEGORIES.items():
            for pattern in config["patterns"]:
                # 簡易パターンマッチング
                pattern_upper = pattern.upper().replace("*", "")
                if pattern_upper in filename:
                    return category
        
        return None
    
    def find_duplicates(self, md_files: List[Path]) -> List[Tuple[Path, Path]]:
        """重複ファイルを検出"""
        duplicates = []
        hash_to_files = defaultdict(list)
        
        print("[検索] 重複ファイルを検出中...")
        for file_path in md_files:
            file_hash = self.calculate_file_hash(file_path)
            if file_hash:
                hash_to_files[file_hash].append(file_path)
        
        # 同じハッシュを持つファイルを重複として記録
        for file_hash, files in hash_to_files.items():
            if len(files) > 1:
                duplicates.append(tuple(files))
                self.stats["duplicate_files"].extend([str(f) for f in files[1:]])
        
        return duplicates
    
    def organize_files(self, dry_run: bool = False):
        """ファイルを整理"""
        # マークダウンファイルを取得
        md_files = list(self.root_dir.glob("*.md"))
        self.stats["total_files"] = len(md_files)
        
        print(f"[情報] 見つかったマークダウンファイル: {len(md_files)}個")
        
        # 重複ファイルを検出
        duplicates = self.find_duplicates(md_files)
        if duplicates:
            print(f"[警告] 重複ファイルを検出: {len(duplicates)}組")
            for dup_group in duplicates[:5]:  # 最初の5組を表示
                print(f"   - {[f.name for f in dup_group]}")
        
        # ファイルを分類して移動
        moved_files = []
        for file_path in md_files:
            # 既にdocsディレクトリ内のファイルはスキップ
            if "docs" in str(file_path):
                continue
            
            category = self.categorize_file(file_path)
            
            if category:
                target_dir = self.docs_dir / category
                target_path = target_dir / file_path.name
                
                # 重複ファイルの場合はアーカイブに移動
                is_duplicate = any(str(file_path) in dup for dup in self.stats["duplicate_files"])
                if is_duplicate:
                    target_dir = self.archive_dir / "duplicates"
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target_path = target_dir / file_path.name
                
                if not dry_run:
                    try:
                        # 既に存在する場合は番号を付ける
                        if target_path.exists():
                            counter = 1
                            while target_path.exists():
                                stem = file_path.stem
                                suffix = file_path.suffix
                                target_path = target_dir / f"{stem}_{counter}{suffix}"
                                counter += 1
                        
                        shutil.move(str(file_path), str(target_path))
                        moved_files.append((str(file_path), str(target_path)))
                        self.stats["moved_files"] += 1
                        self.stats["categories"][category] += 1
                    except Exception as e:
                        print(f"[エラー] 移動エラー: {file_path} - {e}")
                else:
                    print(f"  [DRY RUN] {file_path.name} → {target_dir.name}/")
                    self.stats["moved_files"] += 1
                    self.stats["categories"][category] += 1
            else:
                # カテゴリが不明なファイルは未分類ディレクトリに
                if not dry_run:
                    unclassified_dir = self.docs_dir / "unclassified"
                    unclassified_dir.mkdir(parents=True, exist_ok=True)
                    target_path = unclassified_dir / file_path.name
                    try:
                        if target_path.exists():
                            counter = 1
                            while target_path.exists():
                                stem = file_path.stem
                                suffix = file_path.suffix
                                target_path = unclassified_dir / f"{stem}_{counter}{suffix}"
                                counter += 1
                        shutil.move(str(file_path), str(target_path))
                        self.stats["categories"]["unclassified"] += 1
                    except Exception as e:
                        print(f"[エラー] 移動エラー: {file_path} - {e}")
        
        return moved_files
    
    def generate_report(self) -> str:
        """整理結果レポートを生成"""
        total = self.stats["total_files"]
        moved = self.stats["moved_files"]
        dup_count = len(self.stats["duplicate_files"])
        
        report = f"""# ドキュメント整理レポート

**作成日時**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📊 整理統計

- **総ファイル数**: {total}個
- **移動ファイル数**: {moved}個
- **重複ファイル数**: {dup_count}個

## 📁 カテゴリ別ファイル数

"""
        for category, count in sorted(self.stats["categories"].items()):
            report += f"- **{category}**: {count}個\n"
        
        if self.stats["duplicate_files"]:
            report += f"\n## ⚠️ 重複ファイル\n\n"
            dup_count = len(self.stats["duplicate_files"])
            report += f"以下の{dup_count}個のファイルが重複として検出されました:\n\n"
            for dup_file in self.stats["duplicate_files"][:20]:  # 最初の20個を表示
                report += f"- {Path(dup_file).name}\n"
        
        report += f"\n## 📂 ディレクトリ構造\n\n"
        report += "```\n"
        report += "docs/\n"
        for category in CATEGORIES.keys():
            count = self.stats["categories"].get(category, 0)
            report += f"  ├── {category}/ ({count}個)\n"
        unclassified_count = self.stats["categories"].get("unclassified", 0)
        if unclassified_count > 0:
            report += f"  ├── unclassified/ ({unclassified_count}個)\n"
        report += f"  └── archive/ ({dup_count}個)\n"
        report += "```\n"
        
        return report


def main():
    """メイン処理"""
    import argparse
    import sys
    
    # Windowsでのエンコーディング設定
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    parser = argparse.ArgumentParser(description="ドキュメント整理スクリプト")
    parser.add_argument("--dry-run", action="store_true", help="実際には移動せず、結果を表示するだけ")
    parser.add_argument("--root", default=".", help="ルートディレクトリ")
    args = parser.parse_args()
    
    organizer = DocumentOrganizer(args.root)
    
    print("[開始] ドキュメント整理を開始します...")
    print(f"[情報] ルートディレクトリ: {organizer.root_dir.absolute()}")
    
    if args.dry_run:
        print("[DRY RUN] 実際にはファイルを移動しません\n")
    else:
        organizer.create_directories()
    
    moved_files = organizer.organize_files(dry_run=args.dry_run)
    
    # レポートを生成
    report = organizer.generate_report()
    print("\n" + "="*60)
    print(report)
    print("="*60)
    
    # レポートをファイルに保存
    report_path = organizer.root_dir / "docs" / "ORGANIZATION_REPORT.md"
    if not args.dry_run:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n[完了] レポートを保存しました: {report_path}")
    
    if args.dry_run:
        print("\n[ヒント] 実際に整理を実行するには、--dry-run オプションを外して実行してください")
    else:
        print(f"\n[完了] 整理が完了しました！ {organizer.stats['moved_files']}個のファイルを移動しました")


if __name__ == "__main__":
    main()
