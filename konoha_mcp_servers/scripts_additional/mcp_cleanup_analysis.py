#!/usr/bin/env python3
"""
MCPサーバー整理・重複削除スクリプト
稼働中のプロセスと設定ファイルを分析して重複を特定
"""

import json
import subprocess
import os
from datetime import datetime

class MCPCleanupAnalyzer:
    def __init__(self):
        self.mcp_config_path = "/root/.cursor/mcp.json"
        self.analysis_log = "/root/mcp_cleanup_analysis.log"
        
    def log(self, message):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        with open(self.analysis_log, "a", encoding="utf-8") as f:
            f.write(log_message + "\n")
    
    def get_running_mcp_processes(self):
        """稼働中のMCPプロセスを取得"""
        try:
            result = subprocess.run(
                "ps aux | grep -E '(mcp|trinity).*\.py' | grep -v grep",
                shell=True, capture_output=True, text=True
            )
            
            processes = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) > 10:
                        pid = parts[1]
                        cmd = ' '.join(parts[10:])
                        processes.append({
                            'pid': pid,
                            'command': cmd,
                            'script': self.extract_script_name(cmd)
                        })
            
            return processes
        except Exception as e:
            self.log(f"プロセス取得エラー: {e}")
            return []
    
    def extract_script_name(self, cmd):
        """コマンドからスクリプト名を抽出"""
        if 'trinity_mcp_server.py' in cmd:
            return 'trinity_mcp_server.py'
        elif 'unified_mcp_server.py' in cmd:
            return 'unified_mcp_server.py'
        elif 'chrome_mcp_server.py' in cmd:
            return 'chrome_mcp_server.py'
        elif 'powerpoint_mcp_server.py' in cmd:
            return 'powerpoint_mcp_server.py'
        else:
            return 'unknown'
    
    def load_mcp_config(self):
        """MCP設定ファイルを読み込み"""
        try:
            with open(self.mcp_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.log(f"MCP設定読み込みエラー: {e}")
            return {}
    
    def analyze_duplicates(self):
        """重複を分析"""
        self.log("MCPサーバー重複分析開始")
        
        # 稼働中のプロセス
        running_processes = self.get_running_mcp_processes()
        self.log(f"稼働中のMCPプロセス: {len(running_processes)}個")
        
        # 設定ファイル
        mcp_config = self.load_mcp_config()
        configured_servers = mcp_config.get('mcpServers', {})
        self.log(f"設定されたMCPサーバー: {len(configured_servers)}個")
        
        # 重複分析
        duplicates = []
        issues = []
        
        # プロセス重複チェック
        script_counts = {}
        for process in running_processes:
            script = process['script']
            if script in script_counts:
                script_counts[script] += 1
                duplicates.append(f"重複プロセス: {script} (PID: {process['pid']})")
            else:
                script_counts[script] = 1
        
        # 設定ファイルの問題
        for server_name, config in configured_servers.items():
            if config.get('disabled', False):
                issues.append(f"無効化されたサーバー: {server_name}")
            
            # ファイル存在チェック
            if 'args' in config and config['args']:
                script_path = config['args'][0]
                if not os.path.exists(script_path):
                    issues.append(f"存在しないスクリプト: {server_name} -> {script_path}")
        
        return {
            'running_processes': running_processes,
            'configured_servers': configured_servers,
            'duplicates': duplicates,
            'issues': issues,
            'script_counts': script_counts
        }
    
    def generate_cleanup_plan(self, analysis):
        """クリーンアッププランを生成"""
        self.log("クリーンアッププラン生成中...")
        
        plan = {
            'timestamp': datetime.now().isoformat(),
            'recommendations': [],
            'actions': []
        }
        
        # 重複プロセスの停止
        for script, count in analysis['script_counts'].items():
            if count > 1:
                plan['recommendations'].append(f"重複プロセス停止: {script} ({count}個)")
                plan['actions'].append(f"pkill -f {script}")
        
        # 無効化されたサーバーの削除
        for issue in analysis['issues']:
            if '無効化されたサーバー' in issue:
                server_name = issue.split(': ')[1]
                plan['recommendations'].append(f"無効化サーバー削除: {server_name}")
        
        # 存在しないスクリプトの設定削除
        for issue in analysis['issues']:
            if '存在しないスクリプト' in issue:
                server_name = issue.split(' -> ')[0].split(': ')[1]
                plan['recommendations'].append(f"無効設定削除: {server_name}")
        
        return plan
    
    def create_optimized_config(self, analysis):
        """最適化されたMCP設定を作成"""
        self.log("最適化されたMCP設定を作成中...")
        
        # 有効なサーバーのみを保持
        optimized_servers = {}
        
        for server_name, config in analysis['configured_servers'].items():
            # 無効化されたサーバーをスキップ
            if config.get('disabled', False):
                continue
            
            # 存在しないスクリプトをスキップ
            if 'args' in config and config['args']:
                script_path = config['args'][0]
                if not os.path.exists(script_path):
                    continue
            
            # 重複を避ける
            if server_name in ['trinity', 'trinity-manaos']:
                # Trinity系は1つだけ保持
                if 'trinity' not in optimized_servers:
                    optimized_servers[server_name] = config
            else:
                optimized_servers[server_name] = config
        
        return {
            'mcpServers': optimized_servers
        }
    
    def run_cleanup(self):
        """クリーンアップ実行"""
        self.log("=" * 60)
        self.log("MCPサーバー整理・重複削除開始")
        self.log("=" * 60)
        
        # 分析実行
        analysis = self.analyze_duplicates()
        
        # 結果表示
        self.log(f"稼働中プロセス: {len(analysis['running_processes'])}個")
        self.log(f"設定済みサーバー: {len(analysis['configured_servers'])}個")
        self.log(f"重複: {len(analysis['duplicates'])}件")
        self.log(f"問題: {len(analysis['issues'])}件")
        
        # 重複プロセス停止
        for script, count in analysis['script_counts'].items():
            if count > 1:
                self.log(f"重複プロセス停止: {script} ({count}個)")
                subprocess.run(f"pkill -f {script}", shell=True)
        
        # 最適化された設定を作成
        optimized_config = self.create_optimized_config(analysis)
        
        # バックアップ作成
        backup_path = f"/root/.cursor/mcp.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        subprocess.run(f"cp {self.mcp_config_path} {backup_path}", shell=True)
        self.log(f"設定バックアップ作成: {backup_path}")
        
        # 最適化された設定を保存
        with open(self.mcp_config_path, 'w', encoding='utf-8') as f:
            json.dump(optimized_config, f, indent=2, ensure_ascii=False)
        
        self.log("最適化されたMCP設定を保存しました")
        self.log("=" * 60)
        self.log("MCPサーバー整理完了")
        self.log("=" * 60)
        
        return analysis

if __name__ == "__main__":
    analyzer = MCPCleanupAnalyzer()
    result = analyzer.run_cleanup()
    
    print("\n📊 整理結果:")
    print(f"稼働中プロセス: {len(result['running_processes'])}個")
    print(f"設定済みサーバー: {len(result['configured_servers'])}個")
    print(f"重複: {len(result['duplicates'])}件")
    print(f"問題: {len(result['issues'])}件")

