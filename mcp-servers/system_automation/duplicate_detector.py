#!/usr/bin/env python3
"""
重複ファイル検出システム
ハッシュベースで重複ファイルを検出し、削除候補を提示
"""

import os
import hashlib
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DuplicateDetector:
    """重複ファイル検出システム"""
    
    def __init__(self, base_path: str = "/root"):
        self.base_path = Path(base_path)
        self.cache_path = self.base_path / ".duplicate_cache.json"
        self.results_path = self.base_path / ".duplicate_results.json"
        
    def calculate_hash(self, file_path: Path, chunk_size: int = 8192) -> str:
        """ファイルのSHA256ハッシュを計算"""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"ハッシュ計算エラー {file_path}: {e}")
            return ""
    
    def scan_duplicates(self, exclude_dirs: List[str] = None) -> Dict:  # type: ignore
        """重複ファイルをスキャン"""
        logger.info("重複ファイルスキャン開始...")
        
        if exclude_dirs is None:
            exclude_dirs = ["node_modules", ".git", "__pycache__", ".venv", "backups"]
        
        hash_map = {}
        file_info = {}
        
        total_files = 0
        processed_files = 0
        
        for root, dirs, files in os.walk(self.base_path):
            # 除外ディレクトリをスキップ
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            root_path = Path(root)
            if any(exclude in root_path.parts for exclude in exclude_dirs):
                continue
            
            for file in files:
                total_files += 1
                file_path = root_path / file
                
                try:
                    # ファイルサイズでフィルタ（1KB未満はスキップ）
                    if file_path.stat().st_size < 1024:
                        continue
                    
                    file_hash = self.calculate_hash(file_path)
                    
                    if file_hash:
                        file_size = file_path.stat().st_size
                        
                        if file_hash in hash_map:
                            # 重複発見
                            if file_hash not in file_info:
                                file_info[file_hash] = {
                                    "files": [],
                                    "size": file_size,
                                    "count": 0
                                }
                            
                            file_info[file_hash]["files"].append({
                                "path": str(file_path),
                                "size": file_size,
                                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                            })
                            file_info[file_hash]["count"] += 1
                        else:
                            hash_map[file_hash] = file_path
                    
                    processed_files += 1
                    
                    if processed_files % 100 == 0:
                        logger.info(f"処理中: {processed_files}/{total_files} ファイル")
                
                except Exception as e:
                    logger.error(f"スキャンエラー {file_path}: {e}")
        
        # 重複のみを抽出
        duplicates = {
            hash_val: info for hash_val, info in file_info.items()
            if info["count"] > 1
        }
        
        results = {
            "scan_time": datetime.now().isoformat(),
            "total_files": total_files,
            "processed_files": processed_files,
            "unique_files": len(hash_map),
            "duplicate_groups": len(duplicates),
            "total_duplicate_files": sum(info["count"] for info in duplicates.values()),
            "wasted_space": sum(info["size"] * (info["count"] - 1) for info in duplicates.values()),
            "duplicates": duplicates
        }
        
        # 結果を保存
        self.save_results(results)
        
        logger.info(f"スキャン完了: {results['duplicate_groups']}組の重複を発見")
        logger.info(f"無駄な容量: {results['wasted_space'] / (1024**3):.2f} GB")
        
        return results
    
    def save_results(self, results: Dict):
        """結果を保存"""
        try:
            with open(self.results_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"結果保存エラー: {e}")
    
    def load_results(self) -> Dict:
        """結果を読み込み"""
        if self.results_path.exists():
            try:
                with open(self.results_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"結果読み込みエラー: {e}")
        return {}
    
    def get_duplicate_summary(self) -> Dict:
        """重複ファイルのサマリーを取得"""
        results = self.load_results()
        
        if not results:
            return {"message": "スキャン結果がありません"}
        
        summary = {
            "total_groups": results.get("duplicate_groups", 0),
            "total_files": results.get("total_duplicate_files", 0),
            "wasted_space_gb": round(results.get("wasted_space", 0) / (1024**3), 2),
            "top_duplicates": []
        }
        
        # トップ10の重複を取得
        duplicates = results.get("duplicates", {})
        sorted_dups = sorted(
            duplicates.items(),
            key=lambda x: x[1]["size"] * x[1]["count"],
            reverse=True
        )[:10]
        
        for hash_val, info in sorted_dups:
            summary["top_duplicates"].append({
                "size_mb": round(info["size"] / (1024**2), 2),
                "count": info["count"],
                "files": [f["path"] for f in info["files"][:3]]  # 最初の3つ
            })
        
        return summary
    
    def delete_duplicates(self, keep_oldest: bool = True, dry_run: bool = True) -> Dict:
        """重複ファイルを削除"""
        results = self.load_results()
        
        if not results:
            return {"error": "スキャン結果がありません"}
        
        deleted = []
        freed_space = 0
        
        for hash_val, info in results.get("duplicates", {}).items():
            files = info["files"]
            
            if len(files) <= 1:
                continue
            
            # 保持するファイルを決定
            if keep_oldest:
                # 最も古いファイルを保持
                files_sorted = sorted(files, key=lambda x: x["modified"])
                keep_file = files_sorted[0]
                delete_files = files_sorted[1:]
            else:
                # 最初のファイルを保持
                keep_file = files[0]
                delete_files = files[1:]
            
            # 削除実行
            for file_info in delete_files:
                file_path = Path(file_info["path"])
                
                try:
                    if not dry_run and file_path.exists():
                        file_path.unlink()
                        logger.info(f"削除: {file_path}")
                    
                    deleted.append({
                        "path": str(file_path),
                        "size": file_info["size"],
                        "kept": str(Path(keep_file["path"]))
                    })
                    freed_space += file_info["size"]
                
                except Exception as e:
                    logger.error(f"削除エラー {file_path}: {e}")
        
        return {
            "dry_run": dry_run,
            "deleted_count": len(deleted),
            "freed_space_gb": round(freed_space / (1024**3), 2),
            "deleted_files": deleted
        }


def main():
    """メイン実行"""
    detector = DuplicateDetector()
    
    print("=" * 60)
    print("🔍 重複ファイル検出システム")
    print("=" * 60)
    
    # スキャン実行
    print("\n🔍 重複ファイルスキャンを開始しますか？ (y/n): ", end="")
    response = input().strip().lower()
    
    if response == 'y':
        print("\n⏳ スキャン中...")
        results = detector.scan_duplicates()
        
        print("\n✅ スキャン完了:")
        print(f"  総ファイル数: {results['total_files']:,}")
        print(f"  重複グループ: {results['duplicate_groups']}組")
        print(f"  重複ファイル数: {results['total_duplicate_files']}個")
        print(f"  無駄な容量: {results['wasted_space'] / (1024**3):.2f} GB")
    
    # サマリー表示
    print("\n📊 重複ファイルサマリー:")
    summary = detector.get_duplicate_summary()
    
    if "message" not in summary:
        print(f"  重複グループ: {summary['total_groups']}組")
        print(f"  重複ファイル数: {summary['total_files']}個")
        print(f"  無駄な容量: {summary['wasted_space_gb']} GB")
        
        if summary['top_duplicates']:
            print("\n  トップ5の重複:")
            for i, dup in enumerate(summary['top_duplicates'][:5], 1):
                print(f"    {i}. {dup['size_mb']} MB × {dup['count']}個")
                for file in dup['files'][:2]:
                    print(f"       - {file}")
    
    # 削除実行
    print("\n🗑️  重複ファイルを削除しますか？ (y/n): ", end="")
    response = input().strip().lower()
    
    if response == 'y':
        print("\n🔍 ドライラン実行中...")
        dry_results = detector.delete_duplicates(dry_run=True)
        print(f"  削除予定: {dry_results['deleted_count']}個")
        print(f"  解放容量: {dry_results['freed_space_gb']} GB")
        
        print("\n実際に削除を実行しますか？ (y/n): ", end="")
        confirm = input().strip().lower()
        
        if confirm == 'y':
            print("\n🚀 削除実行中...")
            results = detector.delete_duplicates(dry_run=False)
            print("\n✅ 削除完了:")
            print(f"  削除: {results['deleted_count']}個")
            print(f"  解放容量: {results['freed_space_gb']} GB")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

