#!/usr/bin/env python3
"""
ManaOS Log Manager - ログローテーション・クリーンアップ・集約システム
"""
import os
import sys
import shutil
import gzip
from pathlib import Path
from datetime import datetime, timedelta
import json
import argparse


class LogManager:
    """ログファイルの管理と最適化を行うクラス"""
    
    def __init__(self, logs_dir: str = "logs", config_file: str = "log_manager_config.json"):
        self.logs_dir = Path(logs_dir)
        self.config_file = Path(config_file)
        self.config = self._load_config()
        
    def _load_config(self) -> dict:
        """設定ファイルを読み込む"""
        default_config = {
            "retention_days": 30,              # ログ保持期間（日）
            "archive_days": 7,                 # アーカイブ対象日数（日）
            "max_log_size_mb": 100,            # 個別ログファイルの最大サイズ（MB）
            "compress_archives": True,         # アーカイブを圧縮するか
            "exclude_patterns": [              # 除外するパターン
                "archive/",
                "audit/",
                "*.json"
            ],
            "critical_logs": [                 # 削除しない重要ログ
                "manaos_core_api.log",
                "unified_api_server.log",
                "mrl_memory_integration.log",
                "learning_system.log",
                "llm_routing.log"
            ]
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    default_config.update(loaded)
            except Exception as e:
                print(f"⚠️ 設定ファイル読み込みエラー: {e}")
        
        return default_config
    
    def get_log_files(self) -> list[Path]:
        """ログファイル一覧を取得（除外パターン適用）"""
        if not self.logs_dir.exists():
            return []
        
        all_files = []
        for item in self.logs_dir.rglob("*.log"):
            # 除外パターンチェック
            skip = False
            for pattern in self.config["exclude_patterns"]:
                if pattern in str(item.relative_to(self.logs_dir)):
                    skip = True
                    break
            if not skip:
                all_files.append(item)
        
        return all_files
    
    def analyze_logs(self) -> dict:
        """ログファイルの状態を分析"""
        files = self.get_log_files()
        
        stats = {
            "total_files": len(files),
            "total_size_mb": 0,
            "old_files": [],
            "large_files": [],
            "archive_candidates": []
        }
        
        now = datetime.now()
        retention_date = now - timedelta(days=self.config["retention_days"])
        archive_date = now - timedelta(days=self.config["archive_days"])
        max_size_bytes = self.config["max_log_size_mb"] * 1024 * 1024
        
        for file in files:
            try:
                file_stat = file.stat()
                size_mb = file_stat.st_size / (1024 * 1024)
                stats["total_size_mb"] += size_mb
                
                mod_time = datetime.fromtimestamp(file_stat.st_mtime)
                
                # 古いファイル（削除候補）
                if mod_time < retention_date and file.name not in self.config["critical_logs"]:
                    stats["old_files"].append({
                        "path": str(file),
                        "age_days": (now - mod_time).days,
                        "size_mb": round(size_mb, 2)
                    })
                
                # 大きなファイル（ローテーション候補）
                if file_stat.st_size > max_size_bytes:
                    stats["large_files"].append({
                        "path": str(file),
                        "size_mb": round(size_mb, 2)
                    })
                
                # アーカイブ候補
                if archive_date < mod_time < retention_date:
                    stats["archive_candidates"].append({
                        "path": str(file),
                        "age_days": (now - mod_time).days,
                        "size_mb": round(size_mb, 2)
                    })
            
            except Exception as e:
                print(f"⚠️ ファイル分析エラー ({file}): {e}")
        
        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        return stats
    
    def archive_old_logs(self, dry_run: bool = True) -> int:
        """古いログをアーカイブディレクトリに移動"""
        archive_dir = self.logs_dir / "archive" / datetime.now().strftime("%Y-%m")
        
        if not dry_run and not archive_dir.exists():
            archive_dir.mkdir(parents=True, exist_ok=True)
        
        stats = self.analyze_logs()
        archived_count = 0
        
        for candidate in stats["archive_candidates"]:
            file_path = Path(candidate["path"])
            
            if dry_run:
                print(f"  [DRY RUN] アーカイブ予定: {file_path.name} ({candidate['size_mb']} MB)")
            else:
                try:
                    # 圧縮してアーカイブ
                    if self.config["compress_archives"]:
                        archive_path = archive_dir / f"{file_path.name}.gz"
                        with open(file_path, 'rb') as f_in:
                            with gzip.open(archive_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        file_path.unlink()
                        print(f"  ✅ 圧縮アーカイブ: {file_path.name} → {archive_path}")
                    else:
                        archive_path = archive_dir / file_path.name
                        shutil.move(str(file_path), str(archive_path))
                        print(f"  ✅ アーカイブ: {file_path.name} → {archive_path}")
                    
                    archived_count += 1
                
                except Exception as e:
                    print(f"  ❌ アーカイブ失敗 ({file_path.name}): {e}")
        
        return archived_count
    
    def cleanup_old_logs(self, dry_run: bool = True) -> int:
        """保持期間を過ぎたログを削除"""
        stats = self.analyze_logs()
        deleted_count = 0
        
        for old_file in stats["old_files"]:
            file_path = Path(old_file["path"])
            
            if dry_run:
                print(f"  [DRY RUN] 削除予定: {file_path.name} ({old_file['age_days']}日前, {old_file['size_mb']} MB)")
            else:
                try:
                    file_path.unlink()
                    print(f"  ✅ 削除: {file_path.name}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  ❌ 削除失敗 ({file_path.name}): {e}")
        
        return deleted_count
    
    def rotate_large_logs(self, dry_run: bool = True) -> int:
        """大きなログファイルをローテーション"""
        stats = self.analyze_logs()
        rotated_count = 0
        
        for large_file in stats["large_files"]:
            file_path = Path(large_file["path"])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_path = file_path.with_suffix(f".{timestamp}.log")
            
            if dry_run:
                print(f"  [DRY RUN] ローテーション予定: {file_path.name} → {rotated_path.name}")
            else:
                try:
                    shutil.move(str(file_path), str(rotated_path))
                    # 新しい空ファイルを作成
                    file_path.touch()
                    print(f"  ✅ ローテーション: {file_path.name} → {rotated_path.name}")
                    rotated_count += 1
                except Exception as e:
                    print(f"  ❌ ローテーション失敗 ({file_path.name}): {e}")
        
        return rotated_count
    
    def print_report(self):
        """ログ状態レポートを出力"""
        stats = self.analyze_logs()
        
        print("\n" + "="*70)
        print("📊 ManaOS ログ状態レポート")
        print("="*70)
        print(f"📁 ログディレクトリ: {self.logs_dir.absolute()}")
        print(f"📝 総ログファイル数: {stats['total_files']}")
        print(f"💾 総ログサイズ: {stats['total_size_mb']} MB")
        print()
        print(f"🗄️  アーカイブ候補: {len(stats['archive_candidates'])} ファイル")
        print(f"🗑️  削除候補（{self.config['retention_days']}日超過）: {len(stats['old_files'])} ファイル")
        print(f"⚠️  大容量ファイル（{self.config['max_log_size_mb']}MB超過）: {len(stats['large_files'])} ファイル")
        
        if stats["old_files"]:
            print("\n削除候補ファイル（上位10件）:")
            for item in sorted(stats["old_files"], key=lambda x: x["age_days"], reverse=True)[:10]:
                print(f"  • {Path(item['path']).name} - {item['age_days']}日前 ({item['size_mb']} MB)")
        
        if stats["large_files"]:
            print("\n大容量ファイル:")
            for item in sorted(stats["large_files"], key=lambda x: x["size_mb"], reverse=True):
                print(f"  • {Path(item['path']).name} - {item['size_mb']} MB")
        
        print("="*70 + "\n")
    
    def run_maintenance(self, dry_run: bool = True):
        """全メンテナンスタスクを実行"""
        print("\n🔧 ManaOS ログメンテナンス開始\n")
        
        if dry_run:
            print("⚠️ DRY RUNモード（実際の変更は行いません）\n")
        else:
            print("⚠️ 実行モード（実際にファイルを変更します）\n")
        
        print("📦 Step 1: 古いログをアーカイブ中...")
        archived = self.archive_old_logs(dry_run)
        print(f"  → {archived} ファイルをアーカイブ\n")
        
        print("♻️  Step 2: 保持期間超過ログを削除中...")
        deleted = self.cleanup_old_logs(dry_run)
        print(f"  → {deleted} ファイルを削除\n")
        
        print("🔄 Step 3: 大容量ログをローテーション中...")
        rotated = self.rotate_large_logs(dry_run)
        print(f"  → {rotated} ファイルをローテーション\n")
        
        print("✅ ログメンテナンス完了\n")


def main():
    parser = argparse.ArgumentParser(description="ManaOS Log Manager")
    parser.add_argument("--logs-dir", default="logs", help="ログディレクトリパス")
    parser.add_argument("--config", default="log_manager_config.json", help="設定ファイルパス")
    parser.add_argument("--report", action="store_true", help="ログ状態レポートのみ表示")
    parser.add_argument("--dry-run", action="store_true", help="DRY RUNモード（実行せずシミュレート）")
    parser.add_argument("--execute", action="store_true", help="実際にメンテナンスを実行")
    
    args = parser.parse_args()
    
    manager = LogManager(logs_dir=args.logs_dir, config_file=args.config)
    
    if args.report:
        manager.print_report()
    elif args.execute:
        manager.print_report()
        manager.run_maintenance(dry_run=False)
    else:
        manager.print_report()
        manager.run_maintenance(dry_run=True)


if __name__ == "__main__":
    main()
