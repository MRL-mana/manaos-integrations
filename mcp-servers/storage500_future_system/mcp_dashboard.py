#!/usr/bin/env python3
# MCPシステム監視ダッシュボード

import os
import json
import requests
import psutil
import time
from datetime import datetime
from typing import Dict, List

class MCPDashboard:
    """MCPシステム監視ダッシュボード"""
    
    def __init__(self):
        self.mcp_dir = os.path.expanduser("~/mrl-mcp")
        self.pid_dir = os.path.join(self.mcp_dir, "pids")
        self.log_dir = os.path.join(self.mcp_dir, "logs")
        
        self.servers = {
            "claude": {"url": "http://localhost:8421/health", "port": 8421},
            "luna": {"url": "http://localhost:8422/health", "port": 8422},
            "command": {"url": "http://localhost:8423/health", "port": 8423}
        }
    
    def get_system_status(self) -> Dict:
        """システム全体の状態を取得"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "servers": {},
            "processes": {},
            "logs": {},
            "storage": {}
        }
        
        # サーバー状態チェック
        for name, config in self.servers.items():
            try:
                response = requests.get(config["url"], timeout=5)
                status["servers"][name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds(),
                    "port": config["port"]
                }
            except Exception as e:
                status["servers"][name] = {
                    "status": "error",
                    "error": str(e),
                    "port": config["port"]
                }
        
        # プロセス状態チェック
        for pid_file in os.listdir(self.pid_dir):
            if pid_file.endswith('.pid'):
                service = pid_file.replace('.pid', '')
                pid_path = os.path.join(self.pid_dir, pid_file)
                
                try:
                    with open(pid_path, 'r') as f:
                        pid = int(f.read().strip())
                    
                    if psutil.pid_exists(pid):
                        process = psutil.Process(pid)
                        status["processes"][service] = {
                            "status": "running",
                            "pid": pid,
                            "cpu_percent": process.cpu_percent(),
                            "memory_mb": process.memory_info().rss / 1024 / 1024,
                            "create_time": datetime.fromtimestamp(process.create_time()).isoformat()
                        }
                    else:
                        status["processes"][service] = {
                            "status": "stopped",
                            "pid": pid
                        }
                except Exception as e:
                    status["processes"][service] = {
                        "status": "error",
                        "error": str(e)
                    }
        
        # ログファイル情報
        if os.path.exists(self.log_dir):
            for log_file in os.listdir(self.log_dir):
                if log_file.endswith('.log'):
                    log_path = os.path.join(self.log_dir, log_file)
                    try:
                        stat = os.stat(log_path)
                        status["logs"][log_file] = {
                            "size_mb": stat.st_size / 1024 / 1024,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "lines": sum(1 for _ in open(log_path))
                        }
                    except Exception as e:
                        status["logs"][log_file] = {"error": str(e)}
        
        # ストレージ情報
        try:
            disk_usage = psutil.disk_usage(self.mcp_dir)
            status["storage"] = {
                "total_gb": disk_usage.total / 1024 / 1024 / 1024,
                "used_gb": disk_usage.used / 1024 / 1024 / 1024,
                "free_gb": disk_usage.free / 1024 / 1024 / 1024,
                "percent": disk_usage.percent
            }
        except Exception as e:
            status["storage"]["error"] = str(e)
        
        return status
    
    def print_dashboard(self):
        """ダッシュボードを表示"""
        status = self.get_system_status()
        
        print("=" * 80)
        print("🎯 MCPシステム監視ダッシュボード")
        print("=" * 80)
        print(f"📅 更新時刻: {status['timestamp']}")
        print()
        
        # サーバー状態
        print("🌐 サーバー状態:")
        for name, info in status["servers"].items():
            if info["status"] == "healthy":
                print(f"  ✅ {name.upper()} Server - {info['response_time']:.3f}s")
            else:
                print(f"  ❌ {name.upper()} Server - {info.get('error', 'Unknown error')}")
        print()
        
        # プロセス状態
        print("⚙️ プロセス状態:")
        for name, info in status["processes"].items():
            if info["status"] == "running":
                print(f"  ✅ {name.upper()} - PID: {info['pid']} - CPU: {info['cpu_percent']:.1f}% - RAM: {info['memory_mb']:.1f}MB")
            else:
                print(f"  ❌ {name.upper()} - {info['status']}")
        print()
        
        # ログ情報
        print("📝 ログファイル:")
        for name, info in status["logs"].items():
            if "error" not in info:
                print(f"  📄 {name} - {info['size_mb']:.2f}MB - {info['lines']}行")
            else:
                print(f"  ❌ {name} - {info['error']}")
        print()
        
        # ストレージ情報
        if "error" not in status["storage"]:
            print("💾 ストレージ使用量:")
            print(f"  使用中: {status['storage']['used_gb']:.1f}GB / {status['storage']['total_gb']:.1f}GB")
            print(f"  空き容量: {status['storage']['free_gb']:.1f}GB ({status['storage']['percent']:.1f}%)")
        else:
            print(f"❌ ストレージ情報取得エラー: {status['storage']['error']}")
        print()
        
        # 監視ディレクトリ情報
        print("📁 監視ディレクトリ:")
        claude_dir = os.path.expanduser("~/claude_exports")
        gemini_dir = os.path.expanduser("~/gemini_exports")
        
        if os.path.exists(claude_dir):
            claude_files = len([f for f in os.listdir(claude_dir) if f.endswith('.txt')])
            print(f"  📂 Claude Exports: {claude_files}個のファイル")
        else:
            print("  ❌ Claude Exports: ディレクトリが存在しません")
        
        if os.path.exists(gemini_dir):
            gemini_files = len([f for f in os.listdir(gemini_dir) if f.endswith('.txt')])
            print(f"  📂 Gemini Exports: {gemini_files}個のファイル")
        else:
            print("  ❌ Gemini Exports: ディレクトリが存在しません")
        print()
        
        print("=" * 80)
    
    def save_status(self, filename: str = None):
        """状態をJSONファイルに保存"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.mcp_dir, f"dashboard_status_{timestamp}.json")
        
        status = self.get_system_status()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
        
        print(f"💾 ダッシュボード状態を保存しました: {filename}")

def main():
    """メイン関数"""
    dashboard = MCPDashboard()
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--save":
        dashboard.save_status()
    else:
        dashboard.print_dashboard()

if __name__ == "__main__":
    main() 