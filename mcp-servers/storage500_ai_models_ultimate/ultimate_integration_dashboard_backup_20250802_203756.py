#!/usr/bin/env python3
"""
究極統合ダッシュボード
Obsidian-Notionミラーリング、Gemini API、音声制御を統合管理
"""

import asyncio
import logging
import yaml
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import sqlite3
import psutil
import os

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_integration_dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UltimateIntegrationDashboard:
    """究極統合ダッシュボード"""
    
    def __init__(self):
        self.obsidian_vault_path = "/root/obsidian_vault"
        self.systems = {
            "obsidian_notion_mirror": {
                "name": "Obsidian-Notionミラーリング",
                "status": "unknown",
                "last_check": None,
                "log_file": "obsidian_notion_mirror.log"
            },
            "gemini_api_fix": {
                "name": "Gemini API無料枠対応",
                "status": "unknown",
                "last_check": None,
                "log_file": "gemini_api_fix.log"
            },
            "voice_control": {
                "name": "音声制御システム",
                "status": "unknown",
                "last_check": None,
                "log_file": "voice_control_integration.log"
            }
        }
        self.db_path = "ultimate_integration_dashboard.db"
        
        # データベース初期化
        self._init_database()
        
        logger.info("究極統合ダッシュボード初期化完了")
    
    def _init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_status (
                system_name TEXT PRIMARY KEY,
                status TEXT,
                last_check TEXT,
                error_count INTEGER DEFAULT 0,
                last_error TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dashboard_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                action TEXT,
                system_name TEXT,
                details TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _log_action(self, action: str, system_name: str = None, details: str = ""):  # type: ignore
        """アクションをログに記録"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO dashboard_log (timestamp, action, system_name, details)
            VALUES (?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            action,
            system_name,
            details
        ))
        
        conn.commit()
        conn.close()
    
    def check_system_status(self, system_name: str) -> Dict[str, Any]:
        """システム状況をチェック"""
        system = self.systems.get(system_name)
        if not system:
            return {"status": "unknown", "error": "システムが見つかりません"}
        
        try:
            # プロセスチェック
            process_found = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'python' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline'])
                        if system_name.replace('_', '') in cmdline:
                            process_found = True
                            break
                except:
                    continue
            
            # ログファイルチェック
            log_file = Path(system['log_file'])
            log_updated = log_file.exists() and (time.time() - log_file.stat().st_mtime) < 300  # 5分以内
            
            # 状況判定
            if process_found and log_updated:
                status = "running"
            elif process_found:
                status = "warning"
            elif log_updated:
                status = "partial"
            else:
                status = "stopped"
            
            # データベースに保存
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO system_status 
                (system_name, status, last_check)
                VALUES (?, ?, ?)
            ''', (system_name, status, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            # システム情報更新
            system['status'] = status
            system['last_check'] = datetime.now()
            
            self._log_action("status_check", system_name, f"Status: {status}")
            
            return {
                "status": status,
                "process_found": process_found,
                "log_updated": log_updated,
                "last_check": system['last_check']
            }
            
        except Exception as e:
            error_msg = str(e)
            self._log_action("status_check", system_name, f"Error: {error_msg}")
            return {"status": "error", "error": error_msg}
    
    def start_system(self, system_name: str) -> Dict[str, Any]:
        """システムを開始"""
        try:
            if system_name == "obsidian_notion_mirror":
                cmd = ["python3", "obsidian_notion_mirror_system.py"]
            elif system_name == "gemini_api_fix":
                cmd = ["python3", "gemini_api_fix.py"]
            elif system_name == "voice_control":
                cmd = ["python3", "voice_control_integration.py"]
            else:
                return {"success": False, "error": "未対応のシステム"}
            
            import subprocess
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 少し待ってから状況チェック
            time.sleep(2)
            status = self.check_system_status(system_name)
            
            if status["status"] in ["running", "partial"]:
                self._log_action("start_system", system_name, "Success")
                return {"success": True, "status": status}
            else:
                self._log_action("start_system", system_name, "Failed")
                return {"success": False, "error": "システム開始に失敗"}
                
        except Exception as e:
            error_msg = str(e)
            self._log_action("start_system", system_name, f"Error: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def stop_system(self, system_name: str) -> Dict[str, Any]:
        """システムを停止"""
        try:
            import subprocess
            
            # プロセスを検索して停止
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'python' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline'])
                        if system_name.replace('_', '') in cmdline:
                            proc.terminate()
                            proc.wait(timeout=5)
                            break
                except:
                    continue
            
            time.sleep(1)
            status = self.check_system_status(system_name)
            
            self._log_action("stop_system", system_name, "Success")
            return {"success": True, "status": status}
            
        except Exception as e:
            error_msg = str(e)
            self._log_action("stop_system", system_name, f"Error: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def get_obsidian_stats(self) -> Dict[str, Any]:
        """Obsidian統計情報を取得"""
        try:
            daily_path = Path(self.obsidian_vault_path) / "Daily"
            projects_path = Path(self.obsidian_vault_path) / "Projects"
            
            stats = {
                "daily_files": len(list(daily_path.glob("*.md"))),
                "project_files": len(list(projects_path.glob("*.md"))),
                "total_files": 0,
                "recent_files": []
            }
            
            # 全ファイル数を計算
            for folder in ["Daily", "Projects", "Notes", "Journal", "Ideas"]:
                folder_path = Path(self.obsidian_vault_path) / folder
                if folder_path.exists():
                    stats["total_files"] += len(list(folder_path.glob("*.md")))
            
            # 最近のファイルを取得
            all_files = []
            for folder in ["Daily", "Projects", "Notes", "Journal", "Ideas"]:
                folder_path = Path(self.obsidian_vault_path) / folder
                if folder_path.exists():
                    for file_path in folder_path.glob("*.md"):
                        all_files.append((file_path, file_path.stat().st_mtime))
            
            # 最新の5ファイルを取得
            all_files.sort(key=lambda x: x[1], reverse=True)
            stats["recent_files"] = [f[0].name for f in all_files[:5]]
            
            return stats
            
        except Exception as e:
            logger.error(f"Obsidian統計取得エラー: {e}")
            return {"error": str(e)}
    
    def get_system_summary(self) -> Dict[str, Any]:
        """システム概要を取得"""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "systems": {},
            "obsidian_stats": self.get_obsidian_stats(),
            "system_resources": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            }
        }
        
        # 各システムの状況をチェック
        for system_name in self.systems:
            status = self.check_system_status(system_name)
            summary["systems"][system_name] = {
                "name": self.systems[system_name]["name"],
                "status": status["status"],
                "last_check": status.get("last_check")
            }
        
        return summary
    
    def display_dashboard(self):
        """ダッシュボードを表示"""
        summary = self.get_system_summary()
        
        print("\n" + "="*60)
        print("🚀 究極統合ダッシュボード")
        print("="*60)
        print(f"📅 時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"💻 CPU使用率: {summary['system_resources']['cpu_percent']:.1f}%")
        print(f"🧠 メモリ使用率: {summary['system_resources']['memory_percent']:.1f}%")
        print(f"💾 ディスク使用率: {summary['system_resources']['disk_usage']:.1f}%")
        
        print("\n📊 システム状況:")
        for system_name, system_info in summary["systems"].items():
            status_icon = {
                "running": "✅",
                "warning": "⚠️",
                "partial": "🔄",
                "stopped": "❌",
                "error": "💥",
                "unknown": "❓"
            }.get(system_info["status"], "❓")
            
            print(f"   {status_icon} {system_info['name']}: {system_info['status']}")
        
        print("\n📁 Obsidian統計:")
        obsidian_stats = summary["obsidian_stats"]
        if "error" not in obsidian_stats:
            print(f"   📝 Dailyファイル: {obsidian_stats['daily_files']}個")
            print(f"   📋 Projectファイル: {obsidian_stats['project_files']}個")
            print(f"   📚 総ファイル数: {obsidian_stats['total_files']}個")
            
            if obsidian_stats['recent_files']:
                print(f"   🕒 最近のファイル:")
                for file_name in obsidian_stats['recent_files']:
                    print(f"      - {file_name}")
        else:
            print(f"   ❌ エラー: {obsidian_stats['error']}")
        
        print("\n" + "="*60)
    
    async def run_dashboard(self):
        """ダッシュボードを実行"""
        print("🚀 究極統合ダッシュボードを開始しました")
        
        while True:
            try:
                self.display_dashboard()
                
                # コマンド入力
                print("\n📋 コマンド:")
                print("   1: システム状況更新")
                print("   2: Obsidian-Notionミラーリング開始")
                print("   3: Gemini APIシステム開始")
                print("   4: 音声制御システム開始")
                print("   5: 全システム停止")
                print("   6: 終了")
                
                choice = input("\n選択してください (1-6): ").strip()
                
                if choice == "1":
                    print("🔄 システム状況を更新中...")
                    for system_name in self.systems:
                        self.check_system_status(system_name)
                
                elif choice == "2":
                    print("🔄 Obsidian-Notionミラーリングを開始中...")
                    result = self.start_system("obsidian_notion_mirror")
                    if result["success"]:
                        print("✅ 開始しました")
                    else:
                        print(f"❌ エラー: {result['error']}")
                
                elif choice == "3":
                    print("🔄 Gemini APIシステムを開始中...")
                    result = self.start_system("gemini_api_fix")
                    if result["success"]:
                        print("✅ 開始しました")
                    else:
                        print(f"❌ エラー: {result['error']}")
                
                elif choice == "4":
                    print("🔄 音声制御システムを開始中...")
                    result = self.start_system("voice_control")
                    if result["success"]:
                        print("✅ 開始しました")
                    else:
                        print(f"❌ エラー: {result['error']}")
                
                elif choice == "5":
                    print("🛑 全システムを停止中...")
                    for system_name in self.systems:
                        self.stop_system(system_name)
                    print("✅ 全システムを停止しました")
                
                elif choice == "6":
                    print("👋 ダッシュボードを終了します")
                    break
                
                else:
                    print("❌ 無効な選択です")
                
                await asyncio.sleep(2)
                
            except KeyboardInterrupt:
                print("\n👋 ダッシュボードを終了します")
                break
            except Exception as e:
                logger.error(f"ダッシュボードエラー: {e}")
                await asyncio.sleep(5)

async def main():
    """メイン関数"""
    dashboard = UltimateIntegrationDashboard()
    await dashboard.run_dashboard()

if __name__ == "__main__":
    asyncio.run(main()) 