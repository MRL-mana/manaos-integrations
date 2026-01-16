#!/usr/bin/env python3
"""
MCPサーバーヘルスチェック・修復スクリプト
赤・黄色の状態を解決して正常稼働させる
"""

import subprocess
import requests
import time
from datetime import datetime
import os

class MCPServerHealthChecker:
    def __init__(self):
        self.health_log = os.path.join(os.getenv("HOME", "/root"), "mcp_health_check.log")
        self.mcp_config_path = os.path.join(os.getenv("HOME", "/root"), ".cursor/mcp.json")
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)
        
        with open(self.health_log, "a", encoding="utf-8") as f:
            f.write(log_message + "\n")
    
    def run_command(self, command):
        """コマンド実行"""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)
    
    def check_server_health(self, name, port, health_endpoint="/health"):
        """サーバーのヘルスチェック"""
        try:
            url = f"http://localhost:{port}{health_endpoint}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                return {"status": "healthy", "response": response.json()}
            else:
                return {"status": "error", "code": response.status_code, "text": response.text}
        except requests.exceptions.ConnectionError:
            return {"status": "connection_error"}
        except requests.exceptions.Timeout:
            return {"status": "timeout"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def restart_mcp_server(self, server_name, script_path):
        """MCPサーバーの再起動"""
        self.log(f"サーバー再起動: {server_name}")
        
        # 既存プロセスを停止
        success, stdout, stderr = self.run_command(f"pkill -f {script_path}")
        
        # 少し待機
        time.sleep(2)
        
        # サーバーを再起動
        success, stdout, stderr = self.run_command(f"nohup python3 {script_path} > /dev/null 2>&1 &")
        
        if success:
            self.log(f"✅ {server_name} 再起動成功")
            return True
        else:
            self.log(f"❌ {server_name} 再起動失敗: {stderr}", "ERROR")
            return False
    
    def fix_unified_mcp(self):
        """unified-mcpサーバーの修復"""
        self.log("unified-mcpサーバーを修復中...")
        
        # プロセス確認
        success, stdout, stderr = self.run_command("ps aux | grep unified_mcp_server.py | grep -v grep")
        
        if success and stdout:
            self.log("unified-mcpプロセスは稼働中")
        else:
            self.log("unified-mcpプロセスが見つからない、再起動します")
            self.restart_mcp_server("unified-mcp", os.path.join(os.getenv("HOME", "/root"), "unified_mcp_server.py"))
        
        # ヘルスチェック
        health = self.check_server_health("unified-mcp", 8891)
        if health["status"] == "healthy":
            self.log("✅ unified-mcp: 正常稼働")
        else:
            self.log(f"⚠️ unified-mcp: {health}", "WARNING")
    
    def fix_trinity_manaos(self):
        """trinity-manaosサーバーの修復"""
        self.log("trinity-manaosサーバーを修復中...")
        
        # プロセス確認
        success, stdout, stderr = self.run_command("ps aux | grep trinity_mcp_server.py | grep -v grep")
        
        if success and stdout:
            self.log("trinity-manaosプロセスは稼働中")
        else:
            self.log("trinity-manaosプロセスが見つからない、再起動します")
            self.restart_mcp_server("trinity-manaos", os.path.join(os.getenv("HOME", "/root"), "trinity_mcp_server.py"))
        
        # ポート確認
        success, stdout, stderr = self.run_command("netstat -tlnp | grep trinity_mcp_server")
        if success and stdout:
            self.log("✅ trinity-manaos: ポート稼働中")
        else:
            self.log("⚠️ trinity-manaos: ポート未稼働", "WARNING")
    
    def fix_powerpoint_creator(self):
        """powerpoint-creatorサーバーの修復"""
        self.log("powerpoint-creatorサーバーを修復中...")
        
        # プロセス確認
        success, stdout, stderr = self.run_command("ps aux | grep powerpoint_mcp_server.py | grep -v grep")
        
        if success and stdout:
            self.log("powerpoint-creatorプロセスは稼働中")
        else:
            self.log("powerpoint-creatorプロセスが見つからない、再起動します")
            self.restart_mcp_server("powerpoint-creator", os.path.join(os.getenv("HOME", "/root"), "powerpoint_mcp_server.py"))
        
        # ヘルスチェック
        health = self.check_server_health("powerpoint-creator", 5025)
        if health["status"] == "healthy":
            self.log("✅ powerpoint-creator: 正常稼働")
        else:
            self.log(f"⚠️ powerpoint-creator: {health}", "WARNING")
    
    def fix_chrome_automation(self):
        """chrome-automationサーバーの修復"""
        self.log("chrome-automationサーバーを修復中...")
        
        # プロセス確認
        success, stdout, stderr = self.run_command("ps aux | grep chrome_mcp_server.py | grep -v grep")
        
        if success and stdout:
            self.log("chrome-automationプロセスは稼働中")
        else:
            self.log("chrome-automationプロセスが見つからない、再起動します")
            self.restart_mcp_server("chrome-automation", os.path.join(os.getenv("HOME", "/root"), "organized_workspace/mcp_servers/chrome_mcp_server.py"))
        
        # ヘルスチェック
        health = self.check_server_health("chrome-automation", 6000)
        if health["status"] == "healthy":
            self.log("✅ chrome-automation: 正常稼働")
        else:
            self.log(f"⚠️ chrome-automation: {health}", "WARNING")
    
    def fix_chatgpt_mcp(self):
        """chatgpt-mcpサーバーの修復"""
        self.log("chatgpt-mcpサーバーを修復中...")
        
        # プロセス確認
        success, stdout, stderr = self.run_command("ps aux | grep chatgpt_mcp_server.py | grep -v grep")
        
        if success and stdout:
            self.log("chatgpt-mcpプロセスは稼働中")
        else:
            self.log("chatgpt-mcpプロセスが見つからない、再起動します")
            self.restart_mcp_server("chatgpt-mcp", os.path.join(os.getenv("HOME", "/root"), "hybrid_ai_integration/chatgpt/chatgpt_mcp_server.py"))
        
        # ヘルスチェック
        health = self.check_server_health("chatgpt-mcp", 9101)
        if health["status"] == "healthy":
            self.log("✅ chatgpt-mcp: 正常稼働")
        else:
            self.log(f"⚠️ chatgpt-mcp: {health}", "WARNING")
    
    def run_health_check(self):
        """ヘルスチェック実行"""
        self.log("=" * 60)
        self.log("MCPサーバーヘルスチェック・修復開始")
        self.log("=" * 60)
        
        # 各サーバーの修復
        self.fix_unified_mcp()
        self.fix_trinity_manaos()
        self.fix_powerpoint_creator()
        self.fix_chrome_automation()
        self.fix_chatgpt_mcp()
        
        # 最終確認
        self.log("=" * 60)
        self.log("最終ヘルスチェック")
        self.log("=" * 60)
        
        servers = [
            ("unified-mcp", 8891),
            ("chrome-automation", 6000),
            ("chatgpt-mcp", 9101),
            ("powerpoint-creator", 5025)
        ]
        
        healthy_count = 0
        for name, port in servers:
            health = self.check_server_health(name, port)
            if health["status"] == "healthy":
                self.log(f"✅ {name}: 正常")
                healthy_count += 1
            else:
                self.log(f"❌ {name}: {health['status']}", "ERROR")
        
        self.log("=" * 60)
        self.log(f"ヘルスチェック完了: {healthy_count}/{len(servers)} サーバー正常")
        self.log("=" * 60)
        
        return healthy_count, len(servers)

if __name__ == "__main__":
    checker = MCPServerHealthChecker()
    healthy, total = checker.run_health_check()
    
    print("\n📊 ヘルスチェック結果:")
    print(f"正常稼働: {healthy}/{total} サーバー")
    
    if healthy == total:
        print("🎉 すべてのMCPサーバーが正常稼働中！")
    else:
        print(f"⚠️ {total - healthy}個のサーバーに問題があります")

