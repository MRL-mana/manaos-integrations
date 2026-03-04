#!/usr/bin/env python3
"""
システム完全ヘルスチェック
全マスターシステムと既存サービスの状態確認
"""

import requests
import psutil
from datetime import datetime
from pathlib import Path
import subprocess

class SystemHealthCheck:
    """システムヘルスチェック"""
    
    def __init__(self):
        self.results = []
        
    def check_all(self):
        """完全チェック"""
        print("=" * 70)
        print("🏥 Mana System Health Check")
        print("=" * 70)
        print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 1. マスターシステムチェック
        self.check_master_systems()
        
        # 2. 既存サービスチェック
        self.check_existing_services()
        
        # 3. リソースチェック
        self.check_resources()
        
        # 4. ファイルシステムチェック
        self.check_filesystems()
        
        # 5. データベースチェック
        self.check_databases()
        
        # レポート生成
        self.generate_report()
    
    def check_master_systems(self):
        """マスターシステムチェック"""
        print("\n🌟 マスターシステムチェック")
        print("-" * 70)
        
        systems = {
            "Knowledge Hub": "/root/mana_master_system/mana_knowledge_hub.py",
            "AI Suite": "/root/mana_master_system/mana_ai_suite.py",
            "Notification Master": "/root/mana_master_system/mana_notification_master.py",
            "Ultimate Hub": "/root/mana_master_system/mana_ultimate_hub.py",
        }
        
        for name, path in systems.items():
            exists = Path(path).exists()
            status = "✅" if exists else "❌"
            print(f"  {status} {name:20} - {path}")
            self.results.append({"system": name, "status": exists})
    
    def check_existing_services(self):
        """既存サービスチェック"""
        print("\n🖥️ 稼働中サービスチェック")
        print("-" * 70)
        
        services = {
            "ManaOS v3.0": "http://localhost:9200/health",
            "Trinity Secretary": "http://localhost:5007/health",
            "Command Center": "http://localhost:10000/health",
            "Screen Sharing": "http://localhost:5008/health",
            "Ultimate Dashboard": "http://localhost:8888/health",
        }
        
        for name, url in services.items():
            try:
                response = requests.get(url, timeout=3)
                status = "✅" if response.status_code == 200 else "⚠️"
                print(f"  {status} {name:20} - {url}")
                self.results.append({"service": name, "status": response.status_code == 200})
            except requests.RequestException:
                print(f"  ❌ {name:20} - {url} (未起動)")
                self.results.append({"service": name, "status": False})
    
    def check_resources(self):
        """リソースチェック"""
        print("\n💻 システムリソース")
        print("-" * 70)
        
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        print(f"  CPU使用率:    {cpu:5.1f}% {'✅' if cpu < 80 else '⚠️'}")
        print(f"  メモリ使用率: {memory.percent:5.1f}% {'✅' if memory.percent < 85 else '⚠️'}")
        print(f"  ディスク使用率: {disk.percent:5.1f}% {'✅' if disk.percent < 90 else '⚠️'}")
        print(f"  プロセス数:   {len(psutil.pids())} 個")
        
        self.results.append({
            "resources": {
                "cpu": cpu,
                "memory": memory.percent,
                "disk": disk.percent,
                "healthy": cpu < 80 and memory.percent < 85 and disk.percent < 90
            }
        })
    
    def check_filesystems(self):
        """ファイルシステムチェック"""
        print("\n📁 重要ディレクトリチェック")
        print("-" * 70)
        
        important_dirs = {
            "Obsidian Vault": "/root/obsidian_vault",
            "Master System": "/root/mana_master_system",
            "Backups": "/root/backups_automated",
            "Logs": "/root/logs",
            "Daily Reports": "/root/daily_reports",
        }
        
        for name, path in important_dirs.items():
            exists = Path(path).exists()
            if exists:
                size = self._get_dir_size(path)
                print(f"  ✅ {name:20} - {path} ({size})")
            else:
                print(f"  ❌ {name:20} - {path} (存在しない)")
    
    def check_databases(self):
        """データベースチェック"""
        print("\n💾 データベースチェック")
        print("-" * 70)
        
        databases = {
            "Tasks DB": "/root/.mana_tasks.json",
            "AI Memory": "/root/.ai_context_memory.json",
            "Hub History": "/root/.mana_hub_history.json",
        }
        
        for name, path in databases.items():
            db_path = Path(path)
            if db_path.exists():
                size = db_path.stat().st_size
                print(f"  ✅ {name:20} - {size:,} bytes")
            else:
                print(f"  ⚠️  {name:20} - 未作成（初回実行時に作成）")
    
    def generate_report(self):
        """ヘルスチェックレポート"""
        print("\n" + "=" * 70)
        print("📊 ヘルスチェック サマリー")
        print("=" * 70)
        
        total_checks = len(self.results)
        healthy = sum(1 for r in self.results if any(v == True or (isinstance(v, dict) and v.get('healthy')) for v in r.values()))
        
        print(f"\n総チェック数: {total_checks}")
        print(f"正常: {healthy}")
        print(f"健全性: {(healthy/total_checks*100):.1f}%")
        
        # 全体ステータス
        if healthy / total_checks > 0.9:
            print("\n✅ システム状態: 非常に良好")
        elif healthy / total_checks > 0.7:
            print("\n⚠️  システム状態: 良好（一部要確認）")
        else:
            print("\n❌ システム状態: 要対応")
        
        # レポート保存
        report_file = Path("/root/logs/health_check_report.json")
        with open(report_file, 'w') as f:
            import json
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "results": self.results,
                "summary": {
                    "total": total_checks,
                    "healthy": healthy,
                    "percentage": (healthy/total_checks*100)
                }
            }, f, indent=2)
        
        print(f"\n📄 詳細レポート: {report_file}")
        print("\n" + "=" * 70)
    
    def _get_dir_size(self, path):
        """ディレクトリサイズ取得"""
        try:
            result = subprocess.run(
                ["du", "-sh", path],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.split()[0] if result.returncode == 0 else "不明"
        except subprocess.SubprocessError:
            return "不明"

def main():
    checker = SystemHealthCheck()
    checker.check_all()

if __name__ == "__main__":
    main()

