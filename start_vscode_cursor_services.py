#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS統合サービス自動起動マネージャー
VSCode/Cursorに接続するManaOSサービスを起動・管理
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from typing import List, Dict, Any
import time
import threading
import platform

class ManaOSServiceManager:
    """ManaOSサービスマネージャー"""
    
    SERVICES = [
        {
            "name": "MRL Memory",
            "module": "mrl_memory_integration",
            "port": 5105,
            "description": "記憶管理システム"
        },
        {
            "name": "Learning System",
            "module": "learning_system_api",
            "port": 5126,
            "description": "学習・自動改善システム"
        },
        {
            "name": "LLM Routing",
            "module": "llm_routing_mcp_server.server",
            "port": 5111,
            "description": "LLMルーティング"
        },
        {
            "name": "Unified API",
            "module": "unified_api_server",
            "port": 9502,
            "description": "統合API"
        },
        {
            "name": "Video Pipeline",
            "module": "video_pipeline_mcp_server.server",
            "port": 5112,
            "description": "動画生成パイプライン"
        }
    ]
    
    def __init__(self):
        self.manaos_path = Path(__file__).resolve().parent
        self.processes = {}

        # サービスログの保存先（stdout/stderr を PIPE にすると詰まり得るためファイルへ）
        self.logs_dir = self.manaos_path / "logs" / "services"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
    def start_service(self, service: Dict[str, Any], retries: int = 2) -> bool:
        """サービスを起動（リトライ付き）"""
        name = service["name"]
        module = service["module"]
        port = service["port"]
        
        for attempt in range(1, retries + 1):
            print(f"[START] {name} を起動中... (ポート: {port}, 試行 {attempt}/{retries})")
            
            try:
                # Pythonパス設定
                env = os.environ.copy()
                env["PYTHONPATH"] = str(self.manaos_path)
                # サービスが参照する標準的な PORT 環境変数をセット
                env["PORT"] = str(port)
            
                # プロセス起動（Windowsではウィンドウを非表示）
                creation_flags = 0
                if platform.system() == "Windows":
                    # CREATE_NO_WINDOW フラグでコンソールウィンドウを表示しない
                    creation_flags = subprocess.CREATE_NO_WINDOW

                log_path = self.logs_dir / f"{name.replace(' ', '_').lower()}.log"
                log_file = open(log_path, "a", encoding="utf-8", errors="replace")
            
                proc = subprocess.Popen(
                    [sys.executable, "-m", module],
                    cwd=str(self.manaos_path),
                    env=env,
                    stdout=log_file,
                    stderr=log_file,
                    creationflags=creation_flags
                )
            
                self.processes[name] = {
                    "process": proc,
                    "module": module,
                    "port": port,
                    "log_path": str(log_path),
                    "log_file": log_file,
                }
            
                print(f"[OK] {name} が起動しました (PID: {proc.pid})")
                return True
                
            except Exception as e:
                print(f"[ERROR] {name} の起動に失敗 (試行 {attempt}/{retries}): {e}")
                if attempt < retries:
                    time.sleep(2 ** attempt)  # exponential backoff
        
        return False
    
    def start_all_services(self) -> bool:
        """すべてのサービスを起動"""
        print("="*60)
        print("ManaOSサービスを起動中...")
        print("="*60)
        print()
        
        success_count = 0
        for service in self.SERVICES:
            if self.start_service(service):
                success_count += 1
            time.sleep(1)
        
        print()
        print(f"[OK] {success_count}/{len(self.SERVICES)} サービスが起動しました")
        print()
        
        return success_count == len(self.SERVICES)
    
    def stop_all_services(self):
        """すべてのサービスを停止"""
        print("\nサービスを停止中...")
        for name, info in self.processes.items():
            try:
                info["process"].terminate()
                info["process"].wait(timeout=5)
                print(f"[OK] {name} を停止しました")
            except Exception:
                info["process"].kill()
                print(f"[WARN] {name} を強制終了しました")

            try:
                log_file = info.get("log_file")
                if log_file:
                    log_file.close()
            except Exception:
                pass
    
    def monitor_services(self, enable_autonomous: bool = True):
        """
        サービスの状態を監視
        
        Args:
            enable_autonomous: 自律運用システムを有効化
        """
        print("\n" + "="*60)
        print("サービスの監視を開始しました (Ctrl+C で終了)")
        print("="*60)
        
        # 自律運用システムの初期化と起動
        autonomous = None
        if enable_autonomous:
            try:
                from autonomous_operations import AutonomousOperations
                autonomous = AutonomousOperations(
                    check_interval=60,  # 60秒ごとにヘルスチェック
                    enable_auto_recovery=False  # 自動復旧は無効（手動対応）
                )
                autonomous.start()
                print("[AUTO] 自律運用システム (System3) を起動しました")
            except Exception as e:
                print(f"[WARN] 自律運用システムの起動に失敗: {e}")
                print("   通常の監視モードで続行します")
        
        print()
        
        try:
            while True:
                # 各サービスのステータスを確認
                active = 0
                for name, info in self.processes.items():
                    if info["process"].poll() is None:
                        print(f"[OK] {name}: アクティブ (ポート: {info['port']})")
                        active += 1
                    else:
                        print(f"[ERROR] {name}: 停止 (PID: {info['process'].pid})")
                
                print(f"\n稼働中: {active}/{len(self.processes)}\n")
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n監視を終了します...")
        finally:
            # 自律運用システムの停止
            if autonomous:
                try:
                    autonomous.print_stats()
                    autonomous.stop()
                except Exception as e:
                    print(f"[WARN] 自律運用システムの停止エラー: {e}")
    
    def print_service_info(self):
        """サービス情報を表示"""
        print("\n" + "="*60)
        print("[INFO] ManaOSサービス情報")
        print("="*60)
        
        for i, service in enumerate(self.SERVICES, 1):
            print(f"\n{i}. {service['name']}")
            print(f"   モジュール: {service['module']}")
            print(f"   ポート: {service['port']}")
            print(f"   説明: {service['description']}")
        
        print("\n" + "="*60)
        print("[CONFIG] 設定ファイル:")
        print(f"  Cursor: ~/.cursor/mcp.json")
        print(f"  VSCode: ~/.vscode/settings.json")
        print(f"  ManaOS: {self.manaos_path}")
        
        print("\n" + "="*60)
        print("[CONNECT] 接続方法:")
        print("  1. 各サービスが自動で起動")
        print("  2. Cursor/VSCodeから MCPサーバーとして利用可能")
        print("  3. コード補完・エラー診断に メモリベースの提案が反映")
        
        print("\n" + "="*60)

def main():
    """メイン処理"""
    # Auto-startup 環境か判定（親プロセスが wscript.exe か svchost.exe の場合）
    import os
    parent_cmdline = ""
    try:
        import psutil
        parent = psutil.Process(os.getppid())
        parent_cmdline = parent.name().lower()
    except Exception:
        pass
    
    is_autostart = "wscript" in parent_cmdline or "task" in parent_cmdline.lower()
    
    manager = ManaOSServiceManager()
    
    # サービス情報を表示
    manager.print_service_info()
    
    # すべてのサービスを起動
    if manager.start_all_services():
        # ヘルスチェックを実行（起動完了待ちのため数秒待機）
        print("[WAIT] サービス初期化完了を待機中... (5秒)")
        time.sleep(5)
        
        try:
            # ヘルスチェックスクリプトを実行
            from check_services_health import check_all_services
            health_ok = check_all_services(retry_count=3, retry_delay=2)
            
            if not health_ok:
                print("[WARN] ヘルスチェックで一部のサービスが応答しませんでした")
                print("   サービスは起動していますが、初期化に時間がかかっている可能性があります")
        except Exception as e:
            print(f"[WARN] ヘルスチェック実行エラー: {e}")
        
        # Auto-startup 環境の場合はここで終了（バックグラウンドで実行続行）
        if is_autostart:
            print("[OK] Auto-startup: バックグラウンド実行に切り替わります (Exit)")
            sys.exit(0)
        
        # インタラクティブ実行の場合は監視を開始
        try:
            manager.monitor_services()
        except KeyboardInterrupt:
            print("\n\n停止シグナルを受け取りました...")
        finally:
            manager.stop_all_services()
            print("\n[OK] すべてのサービスを停止しました")
    else:
        print("[ERROR] サービスの起動に失敗しました")
        sys.exit(1)

if __name__ == "__main__":
    # Auto-startup mode: Redirect output to log file to suppress all console output
    import os
    try:
        parent_cmdline = ""
        try:
            import psutil
            parent = psutil.Process(os.getppid())
            parent_cmdline = parent.name().lower()
        except Exception:
            pass
        
        is_autostart = "wscript" in parent_cmdline or "task" in parent_cmdline.lower() or "start_manaos" in " ".join(sys.argv).lower()
        
        if is_autostart:
            # In auto-startup mode: completely suppress console output by redirecting to log
            log_path = Path("logs") / "start_vscode_cursor_services.log"
            log_path.parent.mkdir(exist_ok=True)
            try:
                log_file = open(log_path, "a", encoding="utf-8")
                sys.stdout = log_file
                sys.stderr = log_file
            except Exception:
                pass  # If cannot redirect, continue anyway
    except Exception:
        pass
    
    main()
