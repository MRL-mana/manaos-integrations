#!/usr/bin/env python3
"""
Trinity Multi-Agent System - Hybrid Shell Executor
MCP + Python Subprocess + ファイル経由のハイブリッドシステム
"""

import subprocess
import sys
import os
import json
from pathlib import Path
from datetime import datetime

class TrinityHybridShell:
    """
    3つの方法でコマンドを実行できるハイブリッドシェル
    1. MCP Filesystem経由（ファイル操作）
    2. Python Subprocess経由（シェルコマンド）
    3. ファイル経由（結果を保存して後で読み取り）
    """
    
    def __init__(self):
        self.root_dir = Path("/root")
        self.commands_dir = self.root_dir / ".trinity_commands"
        self.results_dir = self.root_dir / ".trinity_results"
        self.log_file = self.root_dir / "trinity_hybrid_shell.log"
        
        # ディレクトリ作成
        self.commands_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
    
    def log(self, message):
        """ログ記録"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(self.log_file, "a") as f:
            f.write(log_msg + "\n")
    
    def execute_direct(self, command, cwd="/root", timeout=60):
        """
        方法1: Python Subprocess経由で直接実行
        最も高速だが、Cursorのツールからは使えない
        """
        self.log(f"[DIRECT] Executing: {command}")
        
        try:
            result = subprocess.run(
                ["/bin/bash", "-c", command],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=os.environ.copy()
            )
            
            response = {
                'method': 'direct',
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exit_code': result.returncode,
                'command': command
            }
            
            self.log(f"[DIRECT] Exit code: {result.returncode}")
            return response
            
        except subprocess.TimeoutExpired:
            self.log(f"[DIRECT] Timeout: {timeout}s")
            return {
                'method': 'direct',
                'success': False,
                'stdout': '',
                'stderr': f'Command timed out after {timeout} seconds',
                'exit_code': -1,
                'command': command
            }
        except Exception as e:
            self.log(f"[DIRECT] Error: {e}")
            return {
                'method': 'direct',
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'exit_code': -1,
                'command': command
            }
    
    def queue_command(self, command, command_id=None):
        """
        方法2: ファイル経由でコマンドをキューに追加
        Cursorからでも使える（ファイル書き込みのみ）
        """
        if command_id is None:
            command_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        self.log(f"[QUEUE] Command ID: {command_id}")
        
        command_file = self.commands_dir / f"{command_id}.json"
        
        command_data = {
            'id': command_id,
            'command': command,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        with open(command_file, 'w') as f:
            json.dump(command_data, f, indent=2)
        
        self.log(f"[QUEUE] Saved to: {command_file}")
        return command_id
    
    def execute_queued(self, command_id):
        """
        キューに追加されたコマンドを実行
        """
        command_file = self.commands_dir / f"{command_id}.json"
        result_file = self.results_dir / f"{command_id}.json"
        
        if not command_file.exists():
            return {
                'method': 'queued',
                'success': False,
                'stdout': '',
                'stderr': f'Command file not found: {command_id}',
                'exit_code': -1
            }
        
        # コマンド読み込み
        with open(command_file, 'r') as f:
            command_data = json.load(f)
        
        command = command_data['command']
        self.log(f"[QUEUED] Executing: {command}")
        
        # 実行
        result = self.execute_direct(command)
        result['method'] = 'queued'
        result['command_id'] = command_id
        
        # 結果保存
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        # コマンドファイル削除
        command_file.unlink()
        
        self.log(f"[QUEUED] Result saved to: {result_file}")
        return result
    
    def get_result(self, command_id):
        """
        実行結果を取得
        """
        result_file = self.results_dir / f"{command_id}.json"
        
        if not result_file.exists():
            return {
                'method': 'queued',
                'success': False,
                'stdout': '',
                'stderr': f'Result not found: {command_id}',
                'exit_code': -1
            }
        
        with open(result_file, 'r') as f:
            return json.load(f)
    
    def process_all_queued(self):
        """
        キューに追加された全コマンドを実行
        """
        self.log("[BATCH] Processing all queued commands...")
        
        command_files = sorted(self.commands_dir.glob("*.json"))
        
        if not command_files:
            self.log("[BATCH] No commands in queue")
            return []
        
        results = []
        for command_file in command_files:
            command_id = command_file.stem
            result = self.execute_queued(command_id)
            results.append(result)
        
        self.log(f"[BATCH] Processed {len(results)} commands")
        return results
    
    def list_queued(self):
        """
        キューに追加されたコマンド一覧
        """
        command_files = sorted(self.commands_dir.glob("*.json"))
        
        commands = []
        for command_file in command_files:
            with open(command_file, 'r') as f:
                commands.append(json.load(f))
        
        return commands
    
    def list_results(self):
        """
        実行結果一覧
        """
        result_files = sorted(self.results_dir.glob("*.json"))
        
        results = []
        for result_file in result_files:
            with open(result_file, 'r') as f:
                results.append(json.load(f))
        
        return results
    
    def clean_results(self, keep_last=10):
        """
        古い結果を削除
        """
        result_files = sorted(self.results_dir.glob("*.json"))
        
        if len(result_files) > keep_last:
            for result_file in result_files[:-keep_last]:
                result_file.unlink()
                self.log(f"[CLEAN] Deleted: {result_file.name}")

def main():
    """メイン処理"""
    shell = TrinityHybridShell()
    
    if len(sys.argv) < 2:
        print("Trinity Hybrid Shell - Usage:")
        print()
        print("  Direct execution:")
        print("    python3 trinity_hybrid_shell.py exec <command>")
        print()
        print("  Queue command:")
        print("    python3 trinity_hybrid_shell.py queue <command>")
        print()
        print("  Process queued commands:")
        print("    python3 trinity_hybrid_shell.py process")
        print()
        print("  List queued commands:")
        print("    python3 trinity_hybrid_shell.py list-queue")
        print()
        print("  List results:")
        print("    python3 trinity_hybrid_shell.py list-results")
        print()
        print("  Get result:")
        print("    python3 trinity_hybrid_shell.py get-result <command_id>")
        print()
        print("Examples:")
        print("  python3 trinity_hybrid_shell.py exec 'df -h /'")
        print("  python3 trinity_hybrid_shell.py queue 'ls -la'")
        print("  python3 trinity_hybrid_shell.py process")
        return 1
    
    action = sys.argv[1]
    
    if action == 'exec':
        if len(sys.argv) < 3:
            print("Error: No command specified")
            return 1
        command = " ".join(sys.argv[2:])
        result = shell.execute_direct(command)
        
        if result['stdout']:
            print(result['stdout'], end='')
        if result['stderr']:
            print(result['stderr'], file=sys.stderr, end='')
        
        return result['exit_code']
    
    elif action == 'queue':
        if len(sys.argv) < 3:
            print("Error: No command specified")
            return 1
        command = " ".join(sys.argv[2:])
        command_id = shell.queue_command(command)
        print(f"Command queued: {command_id}")
        return 0
    
    elif action == 'process':
        results = shell.process_all_queued()
        print(f"Processed {len(results)} commands")
        for result in results:
            print(f"\n{'='*60}")
            print(f"Command ID: {result.get('command_id', 'unknown')}")
            print(f"Command: {result['command']}")
            print(f"Exit Code: {result['exit_code']}")
            if result['stdout']:
                print(f"Output:\n{result['stdout']}")
            if result['stderr']:
                print(f"Error:\n{result['stderr']}")
        return 0
    
    elif action == 'list-queue':
        commands = shell.list_queued()
        print(f"Queued commands: {len(commands)}")
        for cmd in commands:
            print(f"  [{cmd['id']}] {cmd['command']}")
        return 0
    
    elif action == 'list-results':
        results = shell.list_results()
        print(f"Results available: {len(results)}")
        for result in results:
            status = "✅" if result['success'] else "❌"
            print(f"  {status} [{result.get('command_id', 'unknown')}] Exit: {result['exit_code']}")
        return 0
    
    elif action == 'get-result':
        if len(sys.argv) < 3:
            print("Error: No command_id specified")
            return 1
        command_id = sys.argv[2]
        result = shell.get_result(command_id)
        
        print(f"Command: {result.get('command', 'unknown')}")
        print(f"Exit Code: {result['exit_code']}")
        if result['stdout']:
            print(f"\nOutput:\n{result['stdout']}")
        if result['stderr']:
            print(f"\nError:\n{result['stderr']}")
        
        return result['exit_code']
    
    else:
        print(f"Unknown action: {action}")
        return 1

if __name__ == "__main__":
    exit(main())




