#!/usr/bin/env python3
"""
Trinity Multi-Agent System - AI Shell Wrapper
AIアシスタントがシェルコマンドを実行するための完全なラッパー
Cursorのターミナルツール問題を完全回避
"""

import subprocess
import sys
import json
import os
from datetime import datetime
from pathlib import Path

class AIShellWrapper:
    def __init__(self):
        self.log_file = Path("/root/ai_shell_log.txt")
        
    def log(self, message):
        """ログ記録"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def execute(self, command, cwd="/root", timeout=60, shell="/bin/bash"):
        """
        コマンドを実行
        
        Args:
            command: 実行するコマンド
            cwd: 作業ディレクトリ
            timeout: タイムアウト（秒）
            shell: 使用するシェル
        
        Returns:
            dict: 実行結果
        """
        self.log(f"Executing: {command}")
        self.log(f"Working directory: {cwd}")
        
        try:
            result = subprocess.run(
                [shell, "-c", command],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=os.environ.copy()
            )
            
            response = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exit_code': result.returncode,
                'command': command,
                'cwd': cwd
            }
            
            self.log(f"Exit code: {result.returncode}")
            if result.stdout:
                self.log(f"Stdout length: {len(result.stdout)} bytes")
            if result.stderr:
                self.log(f"Stderr length: {len(result.stderr)} bytes")
            
            return response
            
        except subprocess.TimeoutExpired:
            response = {
                'success': False,
                'stdout': '',
                'stderr': f'Command timed out after {timeout} seconds',
                'exit_code': -1,
                'command': command,
                'cwd': cwd
            }
            self.log(f"Timeout: {timeout}s")
            return response
            
        except Exception as e:
            response = {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'exit_code': -1,
                'command': command,
                'cwd': cwd
            }
            self.log(f"Error: {e}")
            return response
    
    def format_output(self, result, format_type='text'):
        """結果をフォーマット"""
        if format_type == 'json':
            return json.dumps(result, indent=2, ensure_ascii=False)
        
        # テキスト形式
        output = []
        
        if result['stdout']:
            output.append("=== OUTPUT ===")
            output.append(result['stdout'])
        
        if result['stderr']:
            output.append("=== ERROR ===")
            output.append(result['stderr'])
        
        output.append("=== RESULT ===")
        output.append(f"Exit Code: {result['exit_code']}")
        output.append(f"Success: {result['success']}")
        
        return "\n".join(output)

def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("AI Shell Wrapper - Usage:")
        print("  python3 ai_shell_wrapper.py <command>")
        print("  python3 ai_shell_wrapper.py --json <command>")
        print()
        print("Examples:")
        print("  python3 ai_shell_wrapper.py 'df -h /'")
        print("  python3 ai_shell_wrapper.py --json 'ls -la'")
        return 1
    
    wrapper = AIShellWrapper()
    
    # 引数解析
    format_type = 'text'
    command_start = 1
    
    if sys.argv[1] == '--json':
        format_type = 'json'
        command_start = 2
        if len(sys.argv) < 3:
            print("Error: No command specified")
            return 1
    
    command = " ".join(sys.argv[command_start:])
    
    # コマンド実行
    result = wrapper.execute(command)
    
    # 結果出力
    print(wrapper.format_output(result, format_type))
    
    return result['exit_code']

if __name__ == "__main__":
    exit(main())




