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

class ManaOSServiceManager:
    """ManaOSサービスマネージャー"""
    
    SERVICES = [
        {
            "name": "MRL Memory",
            "module": "mrl_memory_integration",
            "port": 5103,
            "description": "記憶管理システム"
        },
        {
            "name": "Learning System",
            "module": "learning_system_api",
            "port": 5104,
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
            "port": 9500,
            "description": "統合API"
        }
    ]
    
    def __init__(self):
        self.manaos_path = Path("c:\\Users\\mana4\\Desktop\\manaos_integrations")
        self.processes = {}
        
    def start_service(self, service: Dict[str, Any]) -> bool:
        """サービスを起動"""
        name = service["name"]
        module = service["module"]
        port = service["port"]
        
        print(f"🚀 {name} を起動中... (ポート: {port})")
        
        try:
            # Pythonパス設定
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.manaos_path)
            # サービスが参照する標準的な PORT 環境変数をセット
            env["PORT"] = str(port)
            
            # プロセス起動
            proc = subprocess.Popen(
                [sys.executable, "-m", module],
                cwd=str(self.manaos_path),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            self.processes[name] = {
                "process": proc,
                "module": module,
                "port": port
            }
            
            print(f"✅ {name} が起動しました (PID: {proc.pid})")
            return True
            
        except Exception as e:
            print(f"❌ {name} の起動に失敗: {e}")
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
        print(f"✅ {success_count}/{len(self.SERVICES)} サービスが起動しました")
        print()
        
        return success_count == len(self.SERVICES)
    
    def stop_all_services(self):
        """すべてのサービスを停止"""
        print("\nサービスを停止中...")
        for name, info in self.processes.items():
            try:
                info["process"].terminate()
                info["process"].wait(timeout=5)
                print(f"✅ {name} を停止しました")
            except:
                info["process"].kill()
                print(f"⚠️  {name} を強制終了しました")
    
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
                print("🤖 自律運用システム (System3) を起動しました")
            except Exception as e:
                print(f"⚠️ 自律運用システムの起動に失敗: {e}")
                print("   通常の監視モードで続行します")
        
        print()
        
        try:
            while True:
                # 各サービスのステータスを確認
                active = 0
                for name, info in self.processes.items():
                    if info["process"].poll() is None:
                        print(f"✅ {name}: アクティブ (ポート: {info['port']})")
                        active += 1
                    else:
                        print(f"❌ {name}: 停止 (PID: {info['process'].pid})")
                
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
                    print(f"⚠️ 自律運用システムの停止エラー: {e}")
    
    def print_service_info(self):
        """サービス情報を表示"""
        print("\n" + "="*60)
        print("🔧 ManaOSサービス情報")
        print("="*60)
        
        for i, service in enumerate(self.SERVICES, 1):
            print(f"\n{i}. {service['name']}")
            print(f"   モジュール: {service['module']}")
            print(f"   ポート: {service['port']}")
            print(f"   説明: {service['description']}")
        
        print("\n" + "="*60)
        print("💾 設定ファイル:")
        print(f"  Cursor: ~/.cursor/mcp.json")
        print(f"  VSCode: ~/.vscode/settings.json")
        print(f"  ManaOS: {self.manaos_path}")
        
        print("\n" + "="*60)
        print("🔌 接続方法:")
        print("  1. 各サービスが自動で起動")
        print("  2. Cursor/VSCodeから MCPサーバーとして利用可能")
        print("  3. コード補完・エラー診断に メモリベースの提案が反映")
        
        print("\n" + "="*60)

def main():
    """メイン処理"""
    manager = ManaOSServiceManager()
    
    # サービス情報を表示
    manager.print_service_info()
    
    # すべてのサービスを起動
    if manager.start_all_services():
        # ヘルスチェックを実行（起動完了待ちのため数秒待機）
        print("⏳ サービス初期化完了を待機中... (5秒)")
        time.sleep(5)
        
        try:
            # ヘルスチェックスクリプトを実行
            from check_services_health import check_all_services
            health_ok = check_all_services(retry_count=3, retry_delay=2)
            
            if not health_ok:
                print("⚠️ ヘルスチェックで一部のサービスが応答しませんでした")
                print("   サービスは起動していますが、初期化に時間がかかっている可能性があります")
        except Exception as e:
            print(f"⚠️ ヘルスチェック実行エラー: {e}")
        
        # サービスの監視を開始
        try:
            manager.monitor_services()
        except KeyboardInterrupt:
            print("\n\n停止シグナルを受け取りました...")
        finally:
            manager.stop_all_services()
            print("\n✅ すべてのサービスを停止しました")
    else:
        print("❌ サービスの起動に失敗しました")
        sys.exit(1)

if __name__ == "__main__":
    main()
