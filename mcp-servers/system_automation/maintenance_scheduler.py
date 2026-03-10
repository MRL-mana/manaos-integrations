#!/usr/bin/env python3
"""
メンテナンス自動化システム
定期メンテナンス、ログローテーション、自動クリーンアップ
"""

import os
import shutil
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MaintenanceScheduler:
    """メンテナンス自動化システム"""
    
    def __init__(self, base_path: str = "/root"):
        self.base_path = Path(base_path)
        self.config_path = self.base_path / ".maintenance_config.json"
        self.log_path = self.base_path / "logs" / "maintenance.log"
        
        # デフォルト設定
        self.default_config = {
            "enabled": True,
            "schedule": {
                "daily": True,
                "weekly": True,
                "monthly": True
            },
            "tasks": {
                "log_rotation": {
                    "enabled": True,
                    "max_size_mb": 100,
                    "keep_days": 30
                },
                "temp_cleanup": {
                    "enabled": True,
                    "patterns": ["*.tmp", "*.log", "*.cache"],
                    "max_age_days": 7
                },
                "disk_cleanup": {
                    "enabled": True,
                    "min_free_space_gb": 10
                },
                "database_optimization": {
                    "enabled": True,
                    "databases": ["ai_enhanced.db", "mana_*.db"]
                },
                "system_update": {
                    "enabled": False,
                    "auto_update": False
                }
            }
        }
        
        self.config = self.load_config()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
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
    
    def log(self, message: str, level: str = "INFO"):
        """ログを記録"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}\n"
        
        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(log_message)
        except Exception as e:
            logger.error(f"ログ書き込みエラー: {e}")
        
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)
    
    def rotate_logs(self) -> Dict:
        """ログローテーション"""
        self.log("ログローテーション開始")
        
        results = {
            "rotated": 0,
            "deleted": 0,
            "freed_space_mb": 0
        }
        
        log_dir = self.log_path.parent
        max_size = self.config["tasks"]["log_rotation"]["max_size_mb"] * 1024 * 1024
        keep_days = self.config["tasks"]["log_rotation"]["keep_days"]
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        for log_file in log_dir.glob("*.log"):
            try:
                # サイズチェック
                if log_file.stat().st_size > max_size:
                    # ローテート
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    rotated_name = f"{log_file.stem}_{timestamp}.log"
                    rotated_path = log_dir / rotated_name
                    
                    shutil.move(str(log_file), str(rotated_path))
                    self.log(f"ログローテーション: {log_file.name} -> {rotated_name}")
                    results["rotated"] += 1
                
                # 古いログ削除
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff_date:
                    size_mb = log_file.stat().st_size / (1024 * 1024)
                    log_file.unlink()
                    self.log(f"古いログ削除: {log_file.name}")
                    results["deleted"] += 1
                    results["freed_space_mb"] += size_mb  # type: ignore
            
            except Exception as e:
                self.log(f"ログローテーションエラー {log_file}: {e}", "ERROR")
        
        self.log(f"ログローテーション完了: {results['rotated']}個ローテート, {results['deleted']}個削除")
        return results
    
    def cleanup_temp_files(self) -> Dict:
        """一時ファイルクリーンアップ"""
        self.log("一時ファイルクリーンアップ開始")
        
        results = {
            "deleted": 0,
            "freed_space_mb": 0
        }
        
        max_age_days = self.config["tasks"]["temp_cleanup"]["max_age_days"]
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        patterns = self.config["tasks"]["temp_cleanup"]["patterns"]
        
        for root, dirs, files in os.walk(self.base_path):
            # 除外ディレクトリ
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv"]]
            
            for file in files:
                file_path = Path(root) / file
                
                # パターンマッチング
                if any(file_path.match(pattern) for pattern in patterns):
                    try:
                        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        
                        if mtime < cutoff_date:
                            size_mb = file_path.stat().st_size / (1024 * 1024)
                            file_path.unlink()
                            results["deleted"] += 1
                            results["freed_space_mb"] += size_mb  # type: ignore
                    
                    except Exception as e:
                        self.log(f"クリーンアップエラー {file_path}: {e}", "ERROR")
        
        self.log(f"一時ファイルクリーンアップ完了: {results['deleted']}個削除, {results['freed_space_mb']:.2f} MB解放")
        return results
    
    def check_disk_space(self) -> Dict:
        """ディスク容量チェック"""
        self.log("ディスク容量チェック")
        
        try:
            result = subprocess.run(
                ["df", "-h", str(self.base_path)],
                capture_output=True,
                text=True
            )
            
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                total = parts[1]
                used = parts[2]
                available = parts[3]
                use_percent = parts[4].rstrip('%')
                
                self.log(f"ディスク使用状況: {used}/{total} ({use_percent}%)")
                
                return {
                    "total": total,
                    "used": used,
                    "available": available,
                    "use_percent": float(use_percent)
                }
        
        except Exception as e:
            self.log(f"ディスク容量チェックエラー: {e}", "ERROR")
        
        return {}
    
    def optimize_databases(self) -> Dict:
        """データベース最適化"""
        self.log("データベース最適化開始")
        
        results = {
            "optimized": 0,
            "errors": 0
        }
        
        patterns = self.config["tasks"]["database_optimization"]["databases"]
        
        for pattern in patterns:
            for db_file in self.base_path.glob(pattern):
                try:
                    # SQLite最適化
                    import sqlite3
                    
                    conn = sqlite3.connect(str(db_file))
                    cursor = conn.cursor()
                    
                    # VACUUM
                    cursor.execute("VACUUM")
                    
                    # ANALYZE
                    cursor.execute("ANALYZE")
                    
                    conn.close()
                    
                    self.log(f"データベース最適化完了: {db_file.name}")
                    results["optimized"] += 1
                
                except Exception as e:
                    self.log(f"データベース最適化エラー {db_file}: {e}", "ERROR")
                    results["errors"] += 1
        
        self.log(f"データベース最適化完了: {results['optimized']}個最適化")
        return results
    
    def run_daily_maintenance(self) -> Dict:
        """日次メンテナンス実行"""
        self.log("=" * 60)
        self.log("日次メンテナンス開始")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "tasks": {}
        }
        
        # ログローテーション
        if self.config["tasks"]["log_rotation"]["enabled"]:
            results["tasks"]["log_rotation"] = self.rotate_logs()
        
        # 一時ファイルクリーンアップ
        if self.config["tasks"]["temp_cleanup"]["enabled"]:
            results["tasks"]["temp_cleanup"] = self.cleanup_temp_files()
        
        # ディスク容量チェック
        if self.config["tasks"]["disk_cleanup"]["enabled"]:
            results["tasks"]["disk_usage"] = self.check_disk_space()
        
        self.log("日次メンテナンス完了")
        self.log("=" * 60)
        
        return results
    
    def run_weekly_maintenance(self) -> Dict:
        """週次メンテナンス実行"""
        self.log("=" * 60)
        self.log("週次メンテナンス開始")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "tasks": {}
        }
        
        # データベース最適化
        if self.config["tasks"]["database_optimization"]["enabled"]:
            results["tasks"]["database_optimization"] = self.optimize_databases()
        
        # 日次メンテナンスも実行
        daily_results = self.run_daily_maintenance()
        results["tasks"]["daily"] = daily_results["tasks"]
        
        self.log("週次メンテナンス完了")
        self.log("=" * 60)
        
        return results
    
    def get_status(self) -> Dict:
        """システムステータス取得"""
        disk_info = self.check_disk_space()
        
        return {
            "enabled": self.config["enabled"],
            "last_maintenance": self.get_last_maintenance_time(),
            "disk_usage": disk_info,
            "config": self.config
        }
    
    def get_last_maintenance_time(self) -> str:
        """最後のメンテナンス実行時刻を取得"""
        if self.log_path.exists():
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in reversed(lines):
                        if "メンテナンス完了" in line:
                            return line.split(']')[0].lstrip('[')
            except IOError:
                pass
        return "未実行"


def main():
    """メイン実行"""
    scheduler = MaintenanceScheduler()
    
    print("=" * 60)
    print("🔧 メンテナンス自動化システム")
    print("=" * 60)
    
    # ステータス表示
    status = scheduler.get_status()
    print("\n📊 システムステータス:")
    print(f"  有効: {'✅' if status['enabled'] else '❌'}")
    print(f"  最終実行: {status['last_maintenance']}")
    
    if status['disk_usage']:
        print(f"  ディスク使用率: {status['disk_usage']['use_percent']:.1f}%")
    
    # メニュー
    print("\n実行するメンテナンスを選択:")
    print("  1. 日次メンテナンス")
    print("  2. 週次メンテナンス")
    print("  3. ログローテーションのみ")
    print("  4. 一時ファイルクリーンアップのみ")
    print("  5. データベース最適化のみ")
    print("  0. 終了")
    
    choice = input("\n選択 (0-5): ").strip()
    
    if choice == "1":
        print("\n🚀 日次メンテナンス実行中...")
        results = scheduler.run_daily_maintenance()
        print("\n✅ 日次メンテナンス完了")
    
    elif choice == "2":
        print("\n🚀 週次メンテナンス実行中...")
        results = scheduler.run_weekly_maintenance()
        print("\n✅ 週次メンテナンス完了")
    
    elif choice == "3":
        print("\n🚀 ログローテーション実行中...")
        results = scheduler.rotate_logs()
        print(f"\n✅ ログローテーション完了: {results['rotated']}個ローテート")
    
    elif choice == "4":
        print("\n🚀 一時ファイルクリーンアップ実行中...")
        results = scheduler.cleanup_temp_files()
        print(f"\n✅ クリーンアップ完了: {results['deleted']}個削除")
    
    elif choice == "5":
        print("\n🚀 データベース最適化実行中...")
        results = scheduler.optimize_databases()
        print(f"\n✅ データベース最適化完了: {results['optimized']}個最適化")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

