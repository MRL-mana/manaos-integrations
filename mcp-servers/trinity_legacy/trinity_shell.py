#!/usr/bin/env python3
"""
Trinity Multi-Agent System用シェル実行ツール
Cursor MCPのターミナルツールが動作しない場合の代替ツール
"""

import subprocess
import sys
import os
import json
from datetime import datetime

class TrinityShell:
    def __init__(self):
        self.workspace = "/root/trinity_workspace"
        self.shared = f"{self.workspace}/shared"
        self.agents = f"{self.workspace}/agents"
        self.logs = f"{self.workspace}/logs"
        
    def run_command(self, command, cwd=None, shell=True):
        """コマンドを実行して結果を返す"""
        try:
            if cwd is None:
                cwd = "/root"
                
            result = subprocess.run(
                command,
                shell=shell,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": command
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timeout (30 seconds)",
                "command": command
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": command
            }
    
    def status(self):
        """Trinityのステータスを表示"""
        print("🎭 Trinity Multi-Agent System Status")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📁 Workspace: {self.workspace}")
        print(f"📊 Current Directory: {os.getcwd()}")
        print(f"👤 User: {os.getenv('USER', 'unknown')}")
        print(f"🖥️  System: {os.uname().sysname}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        tasks_file = f"{self.shared}/tasks.json"
        if os.path.exists(tasks_file):
            try:
                with open(tasks_file, 'r') as f:
                    tasks = json.load(f)
                    print(f"📋 Tasks: {len(tasks.get('tasks', []))} tasks")
            except IOError:
                print("⚠️  tasks.json読み込みエラー")
    
    def check(self):
        """Trinity環境をチェック"""
        print("🔍 Trinity環境チェック")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # ディレクトリチェック
        for dir_path in [self.workspace, self.shared, self.agents, self.logs]:
            if os.path.exists(dir_path):
                print(f"✅ {dir_path}")
            else:
                print(f"❌ {dir_path} (存在しません)")
        
        # 重要ファイルチェック
        print("\n📄 重要ファイル:")
        for filename in ["strategy.md", "tasks.json", "knowledge.md", "sync_status.json"]:
            file_path = f"{self.shared}/{filename}"
            if os.path.exists(file_path):
                print(f"✅ {filename}")
            else:
                print(f"⚠️  {filename} (存在しません)")
    
    def init(self):
        """Trinity環境を初期化"""
        print("🚀 Trinity環境を初期化中...")
        
        # ディレクトリ作成
        os.makedirs(self.workspace, exist_ok=True)
        os.makedirs(self.shared, exist_ok=True)
        os.makedirs(self.agents, exist_ok=True)
        os.makedirs(self.logs, exist_ok=True)
        
        # 基本ファイル作成
        tasks_file = f"{self.shared}/tasks.json"
        if not os.path.exists(tasks_file):
            with open(tasks_file, 'w') as f:
                json.dump({"tasks": []}, f, indent=2)
        
        sync_file = f"{self.shared}/sync_status.json"
        if not os.path.exists(sync_file):
            with open(sync_file, 'w') as f:
                json.dump({
                    "last_sync": datetime.now().isoformat(),
                    "status": "ready"
                }, f, indent=2)
        
        print("✅ Trinity環境の初期化完了")
        self.check()

def main():
    trinity = TrinityShell()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 trinity_shell.py status     - ステータス確認")
        print("  python3 trinity_shell.py check      - 環境チェック")
        print("  python3 trinity_shell.py init       - 環境初期化")
        print("  python3 trinity_shell.py run <cmd>  - コマンド実行")
        print("  python3 trinity_shell.py shell      - インタラクティブシェル")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        trinity.status()
    elif command == "check":
        trinity.check()
    elif command == "init":
        trinity.init()
    elif command == "run" and len(sys.argv) > 2:
        cmd = " ".join(sys.argv[2:])
        result = trinity.run_command(cmd)
        
        if result["success"]:
            print(result["stdout"], end="")
            if result["stderr"]:
                print(result["stderr"], file=sys.stderr, end="")
        else:
            print(f"Error: {result.get('error', result.get('stderr', 'Unknown error'))}", file=sys.stderr)
            sys.exit(result.get("returncode", 1))
    elif command == "shell":
        print("🎭 Trinity Interactive Shell")
        print("Type 'exit' to quit")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        while True:
            try:
                cmd = input("trinity> ")
                if cmd.strip() in ["exit", "quit"]:
                    break
                if cmd.strip():
                    result = trinity.run_command(cmd)
                    if result["stdout"]:
                        print(result["stdout"], end="")
                    if result["stderr"]:
                        print(result["stderr"], file=sys.stderr, end="")
            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except EOFError:
                break
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()

