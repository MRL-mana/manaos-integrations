#!/usr/bin/env python3
"""
Mana Log Manager
ログ管理・クリーンアップ・フィルタリングシステム
エラー・警告の大量発生を防ぐ
"""

import re
import gzip
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaLogManager:
    def __init__(self):
        self.log_dir = Path("/root/logs")
        self.archive_dir = Path("/root/logs_archive")
        self.archive_dir.mkdir(exist_ok=True)
        
        # ログローテーション設定
        self.config = {
            "max_log_size_mb": 50,        # 50MBでローテーション
            "keep_days": 7,                # 7日間保持
            "compress_after_days": 3,      # 3日後に圧縮
            "delete_after_days": 30,       # 30日後に削除
            "suppress_duplicates": True,   # 重複警告を抑制
            "filter_flask_warnings": True  # Flask警告フィルタ
        }
        
        # 除外パターン（ログに記録しない）
        self.suppression_patterns = [
            r'WARNING: This is a development server',
            r'Use a production WSGI server instead',
            r'\[Errno 98\] error while attempting to bind',  # ポート競合の繰り返し
            r'Application startup complete',  # 情報のみ
            r'Application shutdown complete'  # 情報のみ
        ]
        
        logger.info("📝 Mana Log Manager 初期化完了")
    
    def rotate_logs(self) -> Dict[str, Any]:
        """ログローテーション実行"""
        logger.info("🔄 ログローテーション開始")
        
        rotated = []
        compressed = []
        deleted = []
        
        if not self.log_dir.exists():
            return {"error": "Log directory not found"}
        
        for log_file in self.log_dir.glob("*.log"):
            try:
                # ファイルサイズチェック
                size_mb = log_file.stat().st_size / (1024 * 1024)
                age_days = (datetime.now() - datetime.fromtimestamp(log_file.stat().st_mtime)).days
                
                # 大きすぎる場合はローテーション
                if size_mb > self.config["max_log_size_mb"]:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    archive_name = f"{log_file.stem}_{timestamp}.log"
                    archive_path = self.archive_dir / archive_name
                    
                    shutil.move(str(log_file), str(archive_path))
                    rotated.append(str(log_file.name))
                    
                    # 新しいログファイル作成
                    log_file.touch()
                    logger.info(f"ローテーション: {log_file.name} → {archive_name}")
                
                # 古いファイルは圧縮
                elif age_days > self.config["compress_after_days"] and not log_file.suffix == '.gz':
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(f"{log_file}.gz", 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    log_file.unlink()
                    compressed.append(str(log_file.name))
                    logger.info(f"圧縮: {log_file.name}")
                    
            except Exception as e:
                logger.error(f"ローテーションエラー ({log_file}): {e}")
        
        # 古いアーカイブを削除
        for archive_file in self.archive_dir.glob("*"):
            try:
                age_days = (datetime.now() - datetime.fromtimestamp(archive_file.stat().st_mtime)).days
                
                if age_days > self.config["delete_after_days"]:
                    archive_file.unlink()
                    deleted.append(str(archive_file.name))
                    logger.info(f"削除: {archive_file.name}")
                    
            except Exception as e:
                logger.error(f"削除エラー ({archive_file}): {e}")
        
        result = {
            "rotated": len(rotated),
            "compressed": len(compressed),
            "deleted": len(deleted),
            "files": {
                "rotated": rotated,
                "compressed": compressed,
                "deleted": deleted
            }
        }
        
        logger.info(f"✅ ローテーション完了: ローテ{len(rotated)}、圧縮{len(compressed)}、削除{len(deleted)}")
        return result
    
    def clean_log_content(self, log_file: Path) -> Dict[str, Any]:
        """ログ内容をクリーンアップ（重複・不要警告削除）"""
        try:
            if not log_file.exists():
                return {"error": "File not found"}
            
            # ログを読み込み
            with open(log_file, 'r', errors='ignore') as f:
                lines = f.readlines()
            
            original_count = len(lines)
            
            # フィルタリング
            filtered_lines = []
            seen_messages = set()
            removed_count = 0
            
            for line in lines:
                # 抑制パターンチェック
                if any(re.search(pattern, line) for pattern in self.suppression_patterns):
                    removed_count += 1
                    continue
                
                # 重複チェック（同じメッセージは1回のみ記録）
                if self.config["suppress_duplicates"]:
                    # メッセージ部分を抽出（タイムスタンプを除く）
                    message = re.sub(r'^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}[,\.]?\d*\s*', '', line)
                    
                    if message in seen_messages:
                        removed_count += 1
                        continue
                    
                    seen_messages.add(message)
                
                filtered_lines.append(line)
            
            # クリーン版を保存
            if removed_count > 0:
                # バックアップ
                backup_file = f"{log_file}.backup"
                shutil.copy(str(log_file), backup_file)
                
                # クリーン版を書き込み
                with open(log_file, 'w') as f:
                    f.writelines(filtered_lines)
                
                logger.info(f"クリーンアップ: {log_file.name} - {removed_count}行削除")
            
            return {
                "success": True,
                "file": str(log_file.name),
                "original_lines": original_count,
                "filtered_lines": len(filtered_lines),
                "removed_lines": removed_count,
                "reduction_percent": round(removed_count / original_count * 100, 1) if original_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"ログクリーンアップエラー ({log_file}): {e}")
            return {"success": False, "error": str(e)}
    
    def clean_all_logs(self) -> Dict[str, Any]:
        """全ログファイルをクリーンアップ"""
        logger.info("🧹 全ログファイルをクリーンアップ中...")
        
        results = []
        total_removed = 0
        
        for log_file in self.log_dir.glob("*.log"):
            result = self.clean_log_content(log_file)
            if result.get("success"):
                results.append(result)
                total_removed += result.get("removed_lines", 0)
        
        logger.info(f"✅ クリーンアップ完了: {len(results)}ファイル、{total_removed}行削除")
        
        return {
            "files_processed": len(results),
            "total_removed_lines": total_removed,
            "results": results
        }
    
    def setup_logrotate_config(self) -> str:
        """logrotate設定ファイル作成"""
        config_content = f"""
# ManaOS ログローテーション設定
/root/logs/*.log {{
    daily                    # 毎日チェック
    rotate 7                 # 7世代保持
    compress                 # 圧縮
    delaycompress           # 1日後に圧縮
    missingok               # ファイルがなくてもOK
    notifempty              # 空ファイルはローテートしない
    size {self.config['max_log_size_mb']}M  # サイズ制限
    create 0644 root root   # 新ファイル作成
    postrotate
        # ローテーション後にサービス通知（必要に応じて）
    endscript
}}
        """.strip()
        
        config_file = "/etc/logrotate.d/manaos"
        
        try:
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            logger.info(f"✅ logrotate設定作成: {config_file}")
            return config_file
        except Exception as e:
            logger.error(f"設定作成エラー: {e}")
            # rootディレクトリにフォールバック
            fallback_file = "/root/manaos_logrotate.conf"
            with open(fallback_file, 'w') as f:
                f.write(config_content)
            logger.info(f"⚠️ Fallback: {fallback_file}")
            return fallback_file
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """ログ統計取得"""
        stats = {
            "total_files": 0,
            "total_size_mb": 0,
            "by_file": []
        }
        
        for log_file in self.log_dir.glob("*.log"):
            size_mb = log_file.stat().st_size / (1024 * 1024)
            line_count = sum(1 for _ in open(log_file, errors='ignore'))
            
            stats["total_files"] += 1
            stats["total_size_mb"] += size_mb
            stats["by_file"].append({
                "file": log_file.name,
                "size_mb": round(size_mb, 2),
                "lines": line_count
            })
        
        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        stats["by_file"].sort(key=lambda x: x["size_mb"], reverse=True)
        
        return stats

def main():
    manager = ManaLogManager()
    
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "rotate":
            result = manager.rotate_logs()
            print(f"✅ ローテーション: {result['rotated']}ファイル")
            print(f"✅ 圧縮: {result['compressed']}ファイル")
            print(f"✅ 削除: {result['deleted']}ファイル")
        
        elif command == "clean":
            result = manager.clean_all_logs()
            print(f"✅ クリーンアップ: {result['files_processed']}ファイル")
            print(f"✅ 削除行数: {result['total_removed_lines']:,}行")
        
        elif command == "setup":
            config_file = manager.setup_logrotate_config()
            print(f"✅ logrotate設定作成: {config_file}")
        
        elif command == "stats":
            stats = manager.get_log_statistics()
            print("\n📊 ログ統計")
            print(f"ファイル数: {stats['total_files']}")
            print(f"合計サイズ: {stats['total_size_mb']}MB")
            print("\n大きなログファイルTOP 10:")
            for item in stats['by_file'][:10]:
                print(f"  {item['file']}: {item['size_mb']}MB ({item['lines']:,}行)")
        
        else:
            print("Usage: mana_log_manager.py [rotate|clean|setup|stats]")
    else:
        # デフォルトは統計表示
        stats = manager.get_log_statistics()
        print(f"\n📊 ログ統計: {stats['total_files']}ファイル, {stats['total_size_mb']}MB")

if __name__ == "__main__":
    main()

