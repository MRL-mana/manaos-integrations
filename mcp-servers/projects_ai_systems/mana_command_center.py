#!/usr/bin/env python3
"""
🎯 Mana Command Center
全ダッシュボードの統合起動・管理システム
"""
import os
import sys
import subprocess
import signal
from pathlib import Path
import time
from datetime import datetime

class ManaCommandCenter:
    """統合コマンドセンター"""
    
    def __init__(self):
        self.dashboards = {
            '1': {
                'name': 'Security Monitor Dashboard',
                'script': '/root/security_monitor_dashboard.py',
                'port': 5011,
                'description': 'セキュリティ監視ダッシュボード（リスクヒートマップ、Vault状態、脅威ログ）'
            },
            '2': {
                'name': 'Trinity AI Sync Dashboard',
                'script': '/root/scripts/trinity_sync_dashboard.py',
                'port': 5012,
                'description': 'Trinity統合監視（Telegram/Slack/RunPod/ManaOS v3）'
            },
            '3': {
                'name': 'Mana Guard AI',
                'script': '/root/mana_guard_ai.py',
                'port': None,
                'description': '自動セキュリティ監査AI（改善提案生成）'
            },
            '4': {
                'name': 'Security Vault v2 Manager',
                'script': '/root/security_vault_v2.py',
                'port': None,
                'description': '二重暗号化Vault管理（GPG + Fernet）'
            }
        }
        
        self.processes = {}
        self.log_dir = Path('/root/logs/command_center')
        self.log_dir.mkdir(exist_ok=True)
    
    def print_banner(self):
        """バナーを表示"""
        banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        🎯 MANA COMMAND CENTER 🎯                              ║
║                                                               ║
║        統合コマンド・制御システム                               ║
║        Integrated Command & Control System                    ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
        print(banner)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"👤 User: {os.getenv('USER', 'unknown')}")
        print(f"🖥️  Host: {os.uname().nodename}")  # type: ignore[attr-defined]
        print("=" * 65)
    
    def print_menu(self):
        """メニューを表示"""
        print("\n🎛️  Available Systems:\n")
        
        for key, dashboard in self.dashboards.items():
            status = '🟢 Running' if key in self.processes else '⚪ Stopped'
            port_info = f"Port: {dashboard['port']}" if dashboard['port'] else "CLI Tool"
            
            print(f"  [{key}] {dashboard['name']:<30} {status}")
            print(f"      {dashboard['description']}")
            print(f"      {port_info}")
            print()
        
        print("=" * 65)
        print("\n⚡ Actions:\n")
        print("  [s] Start a service")
        print("  [t] Stop a service")
        print("  [a] Start all dashboards")
        print("  [x] Stop all services")
        print("  [r] Restart a service")
        print("  [l] View logs")
        print("  [h] Run health check")
        print("  [g] Run Mana Guard AI audit")
        print("  [v] Vault management")
        print("  [q] Quit")
        print("=" * 65)
    
    def start_service(self, service_id):
        """サービスを起動"""
        if service_id not in self.dashboards:
            print(f"❌ Invalid service ID: {service_id}")
            return False
        
        dashboard = self.dashboards[service_id]
        
        if service_id in self.processes:
            print(f"⚠️  {dashboard['name']} is already running (PID: {self.processes[service_id].pid})")
            return False
        
        print(f"🚀 Starting {dashboard['name']}...")
        
        # ログファイル
        log_file = self.log_dir / f"{service_id}_{dashboard['name'].replace(' ', '_')}.log"
        
        try:
            with open(log_file, 'a') as log:
                if dashboard['port']:
                    # Streamlitダッシュボード
                    process = subprocess.Popen(
                        ['streamlit', 'run', dashboard['script'], 
                         '--server.port', str(dashboard['port']),
                         '--server.headless', 'true',
                         '--browser.gatherUsageStats', 'false'],
                        stdout=log,
                        stderr=log,
                        preexec_fn=os.setsid  # type: ignore[attr-defined]
                    )
                else:
                    # CLIツール（対話モードではなくバックグラウンド実行）
                    print(f"ℹ️  {dashboard['name']} is a CLI tool, not a daemon service")
                    return False
                
                self.processes[service_id] = process
                time.sleep(2)  # 起動待ち
                
                if process.poll() is None:
                    print(f"✅ {dashboard['name']} started successfully!")
                    print(f"   PID: {process.pid}")
                    if dashboard['port']:
                        print(f"   URL: http://localhost:{dashboard['port']}")
                        print(f"   External: http://163.44.120.49:{dashboard['port']}")
                    print(f"   Log: {log_file}")
                    return True
                else:
                    print(f"❌ {dashboard['name']} failed to start")
                    del self.processes[service_id]
                    return False
        
        except Exception as e:
            print(f"❌ Error starting {dashboard['name']}: {e}")
            return False
    
    def stop_service(self, service_id):
        """サービスを停止"""
        if service_id not in self.processes:
            print(f"⚠️  Service {service_id} is not running")
            return False
        
        dashboard = self.dashboards[service_id]
        process = self.processes[service_id]
        
        print(f"🛑 Stopping {dashboard['name']} (PID: {process.pid})...")
        
        try:
            # プロセスグループ全体を終了
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)  # type: ignore[attr-defined]
            process.wait(timeout=10)
            print(f"✅ {dashboard['name']} stopped successfully")
            del self.processes[service_id]
            return True
        
        except subprocess.TimeoutExpired:
            print(f"⚠️  Force killing {dashboard['name']}...")
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)  # type: ignore[attr-defined]
            del self.processes[service_id]
            return True
        
        except Exception as e:
            print(f"❌ Error stopping {dashboard['name']}: {e}")
            return False
    
    def start_all_dashboards(self):
        """全ダッシュボードを起動"""
        print("🚀 Starting all dashboards...\n")
        
        for service_id, dashboard in self.dashboards.items():
            if dashboard['port']:  # ダッシュボードのみ
                self.start_service(service_id)
                time.sleep(2)
        
        print("\n✅ All dashboards started!")
    
    def stop_all_services(self):
        """全サービスを停止"""
        print("🛑 Stopping all services...\n")
        
        for service_id in list(self.processes.keys()):
            self.stop_service(service_id)
        
        print("\n✅ All services stopped!")
    
    def view_logs(self, service_id):
        """ログを表示"""
        if service_id not in self.dashboards:
            print(f"❌ Invalid service ID: {service_id}")
            return
        
        dashboard = self.dashboards[service_id]
        log_file = self.log_dir / f"{service_id}_{dashboard['name'].replace(' ', '_')}.log"
        
        if log_file.exists():
            print(f"\n📜 Last 50 lines of {dashboard['name']} log:\n")
            subprocess.run(['tail', '-50', str(log_file)])
        else:
            print(f"⚠️  No log file found for {dashboard['name']}")
    
    def health_check(self):
        """ヘルスチェックを実行"""
        print("\n🏥 Running health check...\n")
        
        results = []
        
        for service_id, dashboard in self.dashboards.items():
            status = '🟢 Running' if service_id in self.processes else '🔴 Stopped'
            
            if service_id in self.processes:
                process = self.processes[service_id]
                if process.poll() is not None:
                    status = '💀 Dead (exited)'
                    del self.processes[service_id]
            
            results.append({
                'Service': dashboard['name'],
                'Status': status,
                'Port': dashboard['port'] or 'N/A'
            })
        
        # 結果を表示
        print(f"{'Service':<35} {'Status':<20} {'Port':<10}")
        print("-" * 65)
        for r in results:
            print(f"{r['Service']:<35} {r['Status']:<20} {r['Port']:<10}")
        
        print("\n✅ Health check completed")
    
    def run_mana_guard(self):
        """Mana Guard AI を実行"""
        print("\n🤖 Running Mana Guard AI audit...\n")
        
        try:
            subprocess.run(['python3', '/root/mana_guard_ai.py', 'full'])
            print("\n✅ Mana Guard AI audit completed")
        except Exception as e:
            print(f"❌ Error running Mana Guard AI: {e}")
    
    def vault_management(self):
        """Vault管理メニュー"""
        print("\n🔐 Vault Management\n")
        print("  [1] List all keys")
        print("  [2] Get key info")
        print("  [3] Integrity check")
        print("  [4] Export backup")
        print("  [0] Back to main menu")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            subprocess.run(['python3', '/root/security_vault_v2.py', 'list'])
        elif choice == '2':
            key_name = input("Enter key name: ").strip()
            subprocess.run(['python3', '/root/security_vault_v2.py', 'info', key_name])
        elif choice == '3':
            subprocess.run(['python3', '/root/security_vault_v2.py', 'integrity'])
        elif choice == '4':
            backup_path = input("Enter backup path: ").strip()
            subprocess.run(['python3', '/root/security_vault_v2.py', 'backup', backup_path])
    
    def run(self):
        """メインループ"""
        self.print_banner()
        
        # シグナルハンドラ
        def signal_handler(sig, frame):
            print("\n\n🛑 Shutting down Command Center...")
            self.stop_all_services()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        while True:
            self.print_menu()
            choice = input("\n👉 Select option: ").strip().lower()
            
            if choice == 's':
                service_id = input("Enter service ID: ").strip()
                self.start_service(service_id)
            
            elif choice == 't':
                service_id = input("Enter service ID: ").strip()
                self.stop_service(service_id)
            
            elif choice == 'a':
                self.start_all_dashboards()
            
            elif choice == 'x':
                self.stop_all_services()
            
            elif choice == 'r':
                service_id = input("Enter service ID: ").strip()
                self.stop_service(service_id)
                time.sleep(2)
                self.start_service(service_id)
            
            elif choice == 'l':
                service_id = input("Enter service ID: ").strip()
                self.view_logs(service_id)
            
            elif choice == 'h':
                self.health_check()
            
            elif choice == 'g':
                self.run_mana_guard()
            
            elif choice == 'v':
                self.vault_management()
            
            elif choice == 'q':
                print("\n👋 Goodbye!")
                self.stop_all_services()
                break
            
            else:
                print("❌ Invalid option")
            
            input("\nPress Enter to continue...")

if __name__ == "__main__":
    center = ManaCommandCenter()
    center.run()

