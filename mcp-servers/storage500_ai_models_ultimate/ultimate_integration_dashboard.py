#!/usr/bin/env python3
"""
究極統合ダッシュボード（修正・最適化版）
Obsidian-Notionミラーリング、Gemini API、音声制御を統合管理
"""

import asyncio
import logging
import yaml
import json
import time
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import sqlite3
import psutil
import signal
import threading
from concurrent.futures import ThreadPoolExecutor

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_integration_dashboard_fixed.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FixedUltimateIntegrationDashboard:
    """究極統合ダッシュボード（修正・最適化版）"""
    
    def __init__(self):
        self.obsidian_vault_path = "/root/obsidian_vault"
        self.systems = {
            "obsidian_notion_mirror": {
                "name": "Obsidian-Notionミラーリング",
                "status": "unknown",
                "last_check": None,
                "log_file": "obsidian_notion_mirror.log",
                "process": None
            },
            "gemini_api_fix": {
                "name": "Gemini API無料枠対応",
                "status": "unknown",
                "last_check": None,
                "log_file": "gemini_api_fix.log",
                "process": None
            },
            "voice_control": {
                "name": "音声制御システム",
                "status": "unknown",
                "last_check": None,
                "log_file": "voice_control_integration.log",
                "process": None
            }
        }
        self.db_path = "ultimate_integration_dashboard_fixed.db"
        self.is_running = False
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # シグナルハンドラー設定
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # データベース初期化
        self._init_database()
        
        logger.info("究極統合ダッシュボード（修正・最適化版）初期化完了")
    
    def _signal_handler(self, signum, frame):
        """シグナルハンドラー"""
        logger.info(f"シグナル {signum} を受信しました。ダッシュボードを停止します。")
        self.stop()
        sys.exit(0)
    
    def _init_database(self):
        """データベース初期化（修正版）"""
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
        
        # インデックス作成
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_status ON system_status(system_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dashboard_log_timestamp ON dashboard_log(timestamp)')
        
        conn.commit()
        conn.close()
    
    def _log_action(self, action: str, system_name: str = None, details: str = ""):  # type: ignore
        """アクションをログに記録（修正版）"""
        try:
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
        except Exception as e:
            logger.error(f"ログ記録エラー: {e}")
    
    def check_system_status(self, system_name: str) -> Dict[str, Any]:
        """システムステータスをチェック（修正版）"""
        try:
            if system_name not in self.systems:
                return {"success": False, "error": "Unknown system"}
            
            system_info = self.systems[system_name]
            log_file = system_info["log_file"]
            
            # ログファイルの存在確認
            if not os.path.exists(log_file):
                system_info["status"] = "stopped"
                system_info["last_check"] = datetime.now()
                return {"success": True, "status": "stopped", "reason": "Log file not found"}
            
            # プロセス確認
            process_running = False
            if system_info["process"]:
                try:
                    process = psutil.Process(system_info["process"].pid)
                    if process.is_running():
                        process_running = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # ログファイルの最終更新時刻確認
            try:
                mtime = os.path.getmtime(log_file)
                last_modified = datetime.fromtimestamp(mtime)
                time_diff = datetime.now() - last_modified
                
                if time_diff.total_seconds() < 300:  # 5分以内
                    system_info["status"] = "running"
                elif process_running:
                    system_info["status"] = "running"
                else:
                    system_info["status"] = "stopped"
                    
            except Exception as e:
                system_info["status"] = "error"
                logger.error(f"ステータス確認エラー: {system_name} - {e}")
            
            system_info["last_check"] = datetime.now()
            
            # データベースに保存
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO system_status (system_name, status, last_check)
                VALUES (?, ?, ?)
            ''', (
                system_name,
                system_info["status"],
                system_info["last_check"].isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            self._log_action("status_check", system_name, f"Status: {system_info['status']}")
            
            return {
                "success": True,
                "status": system_info["status"],
                "last_check": system_info["last_check"].isoformat()
            }
            
        except Exception as e:
            logger.error(f"システムステータス確認エラー: {system_name} - {e}")
            return {"success": False, "error": str(e)}
    
    def start_system(self, system_name: str) -> Dict[str, Any]:
        """システムを開始（修正版）"""
        try:
            if system_name not in self.systems:
                return {"success": False, "error": "Unknown system"}
            
            system_info = self.systems[system_name]
            
            # 既存プロセスの確認
            if system_info["process"]:
                try:
                    process = psutil.Process(system_info["process"].pid)
                    if process.is_running():
                        return {"success": True, "status": "already_running"}
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # システム開始コマンド
            system_commands = {
                "obsidian_notion_mirror": "python3 obsidian_notion_mirror_system.py",
                "gemini_api_fix": "python3 gemini_api_fix.py",
                "voice_control": "python3 voice_control_integration.py"
            }
            
            if system_name not in system_commands:
                return {"success": False, "error": "No command defined for system"}
            
            # プロセス開始
            import subprocess
            process = subprocess.Popen(
                system_commands[system_name].split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            system_info["process"] = process
            system_info["status"] = "starting"
            
            self._log_action("start_system", system_name, f"PID: {process.pid}")
            
            return {"success": True, "status": "started", "pid": process.pid}
            
        except Exception as e:
            logger.error(f"システム開始エラー: {system_name} - {e}")
            return {"success": False, "error": str(e)}
    
    def stop_system(self, system_name: str) -> Dict[str, Any]:
        """システムを停止（修正版）"""
        try:
            if system_name not in self.systems:
                return {"success": False, "error": "Unknown system"}
            
            system_info = self.systems[system_name]
            
            if system_info["process"]:
                try:
                    process = psutil.Process(system_info["process"].pid)
                    process.terminate()
                    
                    # 5秒待機してから強制終了
                    try:
                        process.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        process.kill()
                    
                    system_info["status"] = "stopped"
                    system_info["process"] = None
                    
                    self._log_action("stop_system", system_name, f"PID: {process.pid}")
                    
                    return {"success": True, "status": "stopped"}
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    system_info["status"] = "stopped"
                    system_info["process"] = None
                    return {"success": True, "status": "already_stopped"}
            
            return {"success": True, "status": "already_stopped"}
            
        except Exception as e:
            logger.error(f"システム停止エラー: {system_name} - {e}")
            return {"success": False, "error": str(e)}
    
    def get_obsidian_stats(self) -> Dict[str, Any]:
        """Obsidian統計を取得（修正版）"""
        try:
            if not os.path.exists(self.obsidian_vault_path):
                return {"error": "Obsidian vault not found"}
            
            vault_path = Path(self.obsidian_vault_path)
            
            # ファイル統計
            daily_files = list(vault_path.glob("Daily/*.md"))
            project_files = list(vault_path.glob("Projects/*.md"))
            all_files = list(vault_path.rglob("*.md"))
            
            # 最近のファイル
            recent_files = []
            for file_path in all_files:
                try:
                    mtime = os.path.getmtime(file_path)
                    if (datetime.now().timestamp() - mtime) < 86400:  # 24時間以内
                        recent_files.append(file_path.name)
                except:
                    pass
            
            return {
                "daily_files": len(daily_files),
                "project_files": len(project_files),
                "total_files": len(all_files),
                "recent_files": recent_files[:5]  # 最新5件
            }
            
        except Exception as e:
            logger.error(f"Obsidian統計取得エラー: {e}")
            return {"error": str(e)}
    
    def get_system_summary(self) -> Dict[str, Any]:
        """システムサマリーを取得（修正版）"""
        summary = {
            "systems": {},
            "obsidian_stats": self.get_obsidian_stats()
        }
        
        for system_name, system_info in self.systems.items():
            summary["systems"][system_name] = {
                "name": system_info["name"],
                "status": system_info["status"],
                "last_check": system_info["last_check"].isoformat() if system_info["last_check"] else None
            }
        
        return summary
    
    def display_dashboard(self):
        """ダッシュボードを表示（修正版）"""
        try:
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print("🎯 究極統合ダッシュボード（修正・最適化版）")
            print("=" * 60)
            print(f"📅 現在時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"💻 システム負荷: CPU {psutil.cpu_percent()}%, メモリ {psutil.virtual_memory().percent}%")
            print()
            
            # システムステータス
            print("🔄 システム状況:")
            summary = self.get_system_summary()
            
            for system_name, system_info in summary["systems"].items():
                status_icon = {
                    "running": "✅",
                    "stopped": "❌",
                    "error": "💥",
                    "unknown": "❓",
                    "starting": "🔄"
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
            
            print("\n" + "=" * 60)
            
        except Exception as e:
            logger.error(f"ダッシュボード表示エラー: {e}")
            print(f"❌ ダッシュボード表示エラー: {e}")
    
    def _safe_input(self, prompt: str) -> str:
        """安全な入力処理（修正版）"""
        try:
            return input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return "6"  # 終了コマンド
    
    async def run_dashboard(self):
        """ダッシュボードを実行（修正版）"""
        print("🚀 究極統合ダッシュボード（修正・最適化版）を開始しました")
        
        self.is_running = True
        
        while self.is_running:
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
                
                choice = self._safe_input("\n選択してください (1-6): ")
                
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
                print(f"❌ エラーが発生しました: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """ダッシュボード停止（修正版）"""
        self.is_running = False
        
        # 全システム停止
        for system_name in self.systems:
            self.stop_system(system_name)
        
        # スレッドプール停止
        if self.executor:
            self.executor.shutdown(wait=True)
        
        logger.info("究極統合ダッシュボード（修正・最適化版）停止")

async def main():
    """メイン関数（修正版）"""
    try:
        dashboard = FixedUltimateIntegrationDashboard()
        await dashboard.run_dashboard()
    except Exception as e:
        logger.error(f"メイン関数エラー: {e}")
        print(f"❌ システムエラー: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 