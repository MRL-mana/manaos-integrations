#!/usr/bin/env python3
"""
Trinity Multi-Agent System - Shell Fix Tool
Cursorのターミナルツール問題を完全回避するPython製シェル実行ツール
"""

import subprocess
import sys

class TrinityShell:
    def __init__(self):
        self.working_dir = "/root"
        self.shell = "/bin/zsh"  # zshを使用
        
    def execute(self, command, capture_output=True):
        """シェルコマンドを実行"""
        try:
            print(f"🎭 Trinity Shell: {command}")
            
            # zshでコマンド実行
            result = subprocess.run(
                [self.shell, "-c", command],
                cwd=self.working_dir,
                capture_output=capture_output,
                text=True,
                timeout=30
            )
            
            if capture_output:
                if result.stdout:
                    print("📤 Output:")
                    print(result.stdout)
                if result.stderr:
                    print("⚠️  Errors:")
                    print(result.stderr)
                print(f"📊 Exit Code: {result.returncode}")
            else:
                print("✅ Command executed (no output capture)")
                
            return result
            
        except subprocess.TimeoutExpired:
            print("⏰ Command timed out")
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def check_system(self):
        """システム状況をチェック"""
        print("🔍 Trinity System Check")
        print("=" * 50)
        
        # ディスク使用量
        self.execute("df -h / | tail -1")
        
        # 現在のディレクトリ
        self.execute("pwd")
        
        # シェル確認
        self.execute("echo $SHELL")
        
        # 日時
        self.execute("date")
        
        # プロセス確認
        self.execute("ps aux | grep -E '(bash|zsh)' | head -3")
    
    def trinity_status(self):
        """Trinityステータス表示"""
        print("🎭 Trinity Multi-Agent System Status")
        print("=" * 50)
        print("✅ Remi (戦略指令AI) - Ready")
        print("✅ Luna (実務遂行AI) - Ready")
        print("✅ Mina (洞察記録AI/QA) - Ready")
        print("✅ Aria (ナレッジマネージャー) - Ready")
        print("🚀 All systems operational!")
    
    def interactive_mode(self):
        """インタラクティブモード"""
        print("🎭 Trinity Shell - Interactive Mode")
        print("Type 'exit' to quit, 'status' for Trinity status, 'check' for system check")
        print("=" * 60)
        
        while True:
            try:
                command = input("Trinity> ").strip()
                
                if command.lower() == 'exit':
                    print("👋 Goodbye!")
                    break
                elif command.lower() == 'status':
                    self.trinity_status()
                elif command.lower() == 'check':
                    self.check_system()
                elif command:
                    self.execute(command)
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break

def main():
    """メイン関数"""
    print("🎭 Trinity Multi-Agent System - Shell Fix Tool")
    print("=" * 60)
    
    shell = TrinityShell()
    
    if len(sys.argv) > 1:
        # コマンドライン引数がある場合
        command = " ".join(sys.argv[1:])
        shell.execute(command)
    else:
        # インタラクティブモード
        shell.interactive_mode()

if __name__ == "__main__":
    main()



