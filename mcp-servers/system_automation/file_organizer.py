#!/usr/bin/env python3
"""
整理整頓システム - 自動ファイル整理
自動的にファイルを分類・整理・重複検出
"""

import os
import shutil
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict
import logging

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FileOrganizer:
    """自動ファイル整理システム"""
    
    def __init__(self, base_path: str = "/root"):
        self.base_path = Path(base_path)
        self.config_path = self.base_path / ".file_organizer_config.json"
        self.stats_path = self.base_path / ".file_organizer_stats.json"
        
        # デフォルト設定
        self.default_config = {
            "organize_enabled": True,
            "duplicate_detection": True,
            "auto_backup": True,
            "organize_rules": {
                "images": {
                    "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
                    "target_dir": "organized/images"
                },
                "documents": {
                    "extensions": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md"],
                    "target_dir": "organized/documents"
                },
                "videos": {
                    "extensions": [".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm"],
                    "target_dir": "organized/videos"
                },
                "audio": {
                    "extensions": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
                    "target_dir": "organized/audio"
                },
                "archives": {
                    "extensions": [".zip", ".rar", ".7z", ".tar", ".gz"],
                    "target_dir": "organized/archives"
                },
                "code": {
                    "extensions": [".py", ".js", ".ts", ".html", ".css", ".json", ".yaml", ".yml"],
                    "target_dir": "organized/code"
                }
            },
            "exclude_dirs": [
                "node_modules", ".git", "__pycache__", ".venv",
                "venv", "backups", "organized", "logs",
                "Google Drive", "Downloads", "Desktop"
            ],
            "exclude_patterns": ["*.log", "*.tmp", "*.cache"]
        }
        
        self.config = self.load_config()
        self.stats = self.load_stats()
        
    def load_config(self) -> dict:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"設定読み込みエラー: {e}")
                return self.default_config
        return self.default_config
    
    def save_config(self):
        """設定を保存"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
    
    def load_stats(self) -> dict:
        """統計情報を読み込む"""
        if self.stats_path.exists():
            try:
                with open(self.stats_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"統計読み込みエラー: {e}")
                return self._init_stats()
        return self._init_stats()
    
    def _init_stats(self) -> dict:
        """統計情報初期化"""
        return {
            "total_files_organized": 0,
            "total_duplicates_found": 0,
            "total_space_saved": 0,
            "last_organization": None,
            "category_stats": {}
        }
    
    def save_stats(self):
        """統計情報を保存"""
        try:
            with open(self.stats_path, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"統計保存エラー: {e}")
    
    def should_exclude(self, path: Path) -> bool:
        """除外すべきパスかチェック"""
        # ディレクトリ除外
        for exclude_dir in self.config.get("exclude_dirs", []):
            if exclude_dir in path.parts:
                return True
        
        # パターン除外
        for pattern in self.config.get("exclude_patterns", []):
            if path.match(pattern):
                return True
        
        return False
    
    def get_file_category(self, file_path: Path) -> str:
        """ファイルのカテゴリを判定"""
        ext = file_path.suffix.lower()
        
        for category, rules in self.config.get("organize_rules", {}).items():
            if ext in rules.get("extensions", []):
                return category
        
        return "other"
    
    def organize_files(self, dry_run: bool = False) -> Dict:
        """ファイルを整理"""
        logger.info("ファイル整理を開始...")
        
        results = {
            "organized": 0,
            "skipped": 0,
            "errors": 0,
            "categories": {}
        }
        
        # 対象ディレクトリをスキャン
        for root, dirs, files in os.walk(self.base_path):
            root_path = Path(root)
            
            # 除外ディレクトリをスキップ
            if self.should_exclude(root_path):
                dirs[:] = []  # 再帰を停止
                continue
            
            for file in files:
                file_path = root_path / file
                
                # 除外チェック
                if self.should_exclude(file_path):
                    continue
                
                try:
                    category = self.get_file_category(file_path)
                    
                    if category == "other":
                        results["skipped"] += 1
                        continue
                    
                    # ターゲットディレクトリ
                    target_dir = self.base_path / self.config["organize_rules"][category]["target_dir"]
                    
                    if not dry_run:
                        target_dir.mkdir(parents=True, exist_ok=True)
                        
                        # ファイル移動
                        target_path = target_dir / file_path.name
                        
                        # 同名ファイルが存在する場合、リネーム
                        counter = 1
                        while target_path.exists():
                            stem = file_path.stem
                            suffix = file_path.suffix
                            target_path = target_dir / f"{stem}_{counter}{suffix}"
                            counter += 1
                        
                        shutil.move(str(file_path), str(target_path))
                        logger.info(f"移動: {file_path} -> {target_path}")
                    
                    results["organized"] += 1
                    
                    # カテゴリ統計
                    if category not in results["categories"]:
                        results["categories"][category] = 0
                    results["categories"][category] += 1
                    
                except Exception as e:
                    logger.error(f"整理エラー {file_path}: {e}")
                    results["errors"] += 1
        
        # 統計更新
        if not dry_run:
            self.stats["total_files_organized"] += results["organized"]
            self.stats["last_organization"] = datetime.now().isoformat()
            self.save_stats()
        
        logger.info(f"整理完了: {results['organized']}個のファイルを整理")
        return results
    
    def calculate_file_hash(self, file_path: Path, chunk_size: int = 8192) -> str:
        """ファイルのハッシュ値を計算"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for byte_block in iter(lambda: f.read(chunk_size), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"ハッシュ計算エラー {file_path}: {e}")
            return ""
    
    def find_duplicates(self) -> Dict:
        """重複ファイルを検出"""
        logger.info("重複ファイル検出を開始...")
        
        hash_map = {}
        duplicates = []
        
        for root, dirs, files in os.walk(self.base_path):
            root_path = Path(root)
            
            # 除外ディレクトリをスキップ
            if self.should_exclude(root_path):
                dirs[:] = []
                continue
            
            for file in files:
                file_path = root_path / file
                
                if self.should_exclude(file_path):
                    continue
                
                try:
                    file_hash = self.calculate_file_hash(file_path)
                    
                    if file_hash:
                        if file_hash in hash_map:
                            duplicates.append({
                                "hash": file_hash,
                                "files": [str(hash_map[file_hash]), str(file_path)]
                            })
                        else:
                            hash_map[file_hash] = file_path
                except Exception as e:
                    logger.error(f"重複検出エラー {file_path}: {e}")
        
        logger.info(f"重複検出完了: {len(duplicates)}組の重複を発見")
        return {
            "total_duplicates": len(duplicates),
            "duplicates": duplicates
        }
    
    def get_system_stats(self) -> Dict:
        """システム統計を取得"""
        total_size = 0
        file_count = 0
        
        for root, dirs, files in os.walk(self.base_path):
            root_path = Path(root)
            
            if self.should_exclude(root_path):
                dirs[:] = []
                continue
            
            for file in files:
                file_path = root_path / file
                if not self.should_exclude(file_path):
                    try:
                        total_size += file_path.stat().st_size
                        file_count += 1
                    except IOError:
                        pass
        
        return {
            "total_files": file_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "stats": self.stats
        }


def main():
    """メイン実行"""
    organizer = FileOrganizer()
    
    print("=" * 60)
    print("📁 整理整頓システム")
    print("=" * 60)
    
    # システム統計
    stats = organizer.get_system_stats()
    print("\n📊 システム統計:")
    print(f"  総ファイル数: {stats['total_files']:,}")
    print(f"  総サイズ: {stats['total_size_mb']:.2f} MB")
    
    # 重複検出
    print("\n🔍 重複ファイル検出中...")
    duplicates = organizer.find_duplicates()
    print(f"  重複ファイル組: {duplicates['total_duplicates']}組")
    
    if duplicates['total_duplicates'] > 0:
        print("\n  重複ファイル:")
        for dup in duplicates['duplicates'][:5]:  # 最初の5組
            print(f"    - {dup['files'][0]}")
            print(f"      {dup['files'][1]}")
    
    # ファイル整理
    print("\n📦 ファイル整理を実行しますか？ (y/n): ", end="")
    response = input().strip().lower()
    
    if response == 'y':
        # ドライラン
        print("\n🔍 ドライラン実行中...")
        dry_results = organizer.organize_files(dry_run=True)
        print(f"  整理予定: {dry_results['organized']}個")
        print(f"  スキップ: {dry_results['skipped']}個")
        
        print("\n実際に整理を実行しますか？ (y/n): ", end="")
        confirm = input().strip().lower()
        
        if confirm == 'y':
            print("\n🚀 ファイル整理実行中...")
            results = organizer.organize_files(dry_run=False)
            print("\n✅ 整理完了:")
            print(f"  整理: {results['organized']}個")
            print(f"  エラー: {results['errors']}個")
            print("\n  カテゴリ別:")
            for cat, count in results['categories'].items():
                print(f"    {cat}: {count}個")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

