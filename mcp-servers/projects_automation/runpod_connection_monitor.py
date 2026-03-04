#!/usr/bin/env python3
"""
RunPod接続監視システム
RunPodインスタンスの起動完了を自動監視する
"""

import subprocess
import time
import requests
from datetime import datetime
import json

class RunPodConnectionMonitor:
    def __init__(self):
        self.runpod_ip = "213.181.111.2"
        self.ports = {
            "ssh": 26105,
            "web_terminal": 19123,
            "jupyter": 8888,
            "api_server": 7860
        }
        self.check_interval = 30  # 30秒間隔
        self.max_wait_time = 600  # 最大10分待機
        
    def check_port(self, port, timeout=5):
        """ポート接続確認"""
        try:
            result = subprocess.run([
                'nc', '-z', '-w', str(timeout), self.runpod_ip, str(port)
            ], capture_output=True, text=True)
            return result.returncode == 0
        except subprocess.SubprocessError:
            return False
    
    def check_web_service(self, port, timeout=5):
        """Webサービス確認"""
        try:
            response = requests.get(f"http://{self.runpod_ip}:{port}", timeout=timeout)
            return response.status_code in [200, 401, 403]
        except requests.RequestException:
            return False
    
    def test_ssh_connection(self):
        """SSH接続テスト"""
        try:
            result = subprocess.run([
                'ssh', '-o', 'ConnectTimeout=10', '-o', 'BatchMode=yes',
                f'root@{self.runpod_ip}', '-p', str(self.ports['ssh']),
                'echo "SSH connection test"'
            ], capture_output=True, text=True, timeout=15)
            return result.returncode == 0
        except subprocess.SubprocessError:
            return False
    
    def check_all_services(self):
        """全サービスの状態確認"""
        status = {}
        
        # SSH接続テスト
        status['ssh_port'] = self.check_port(self.ports['ssh'])
        status['ssh_connection'] = self.test_ssh_connection()
        
        # Webサービス確認
        status['web_terminal'] = self.check_web_service(self.ports['web_terminal'])
        status['jupyter'] = self.check_web_service(self.ports['jupyter'])
        status['api_server'] = self.check_web_service(self.ports['api_server'])
        
        return status
    
    def print_status(self, status, iteration):
        """状態表示"""
        print(f"\n=== 監視結果 #{iteration} ({datetime.now().strftime('%H:%M:%S')}) ===")
        
        # SSH状態
        ssh_status = "✅" if status['ssh_connection'] else ("⚠️" if status['ssh_port'] else "❌")
        print(f"🔌 SSH (26105): {ssh_status}")
        
        # Web Terminal状態
        wt_status = "✅" if status['web_terminal'] else "❌"
        print(f"🌐 Web Terminal (19123): {wt_status}")
        
        # Jupyter状態
        jp_status = "✅" if status['jupyter'] else "❌"
        print(f"📓 Jupyter (8888): {jp_status}")
        
        # API Server状態
        api_status = "✅" if status['api_server'] else "❌"
        print(f"🔧 API Server (7860): {api_status}")
        
        # 全体的な状態
        all_ready = all([
            status['ssh_connection'],
            status['web_terminal'],
            status['jupyter']
        ])
        
        if all_ready:
            print("\n🎉 すべてのサービスが準備完了！")
            return True
        else:
            ready_count = sum([status['ssh_connection'], status['web_terminal'], status['jupyter']])
            print(f"\n⏳ 準備完了: {ready_count}/3 サービス")
            return False
    
    def monitor(self):
        """監視開始"""
        print("🔍 RunPod接続監視開始")
        print("=" * 50)
        print(f"🎯 監視対象: {self.runpod_ip}")
        print(f"⏱️ チェック間隔: {self.check_interval}秒")
        print(f"⏰ 最大待機時間: {self.max_wait_time}秒")
        print()
        
        start_time = time.time()
        iteration = 0
        
        while time.time() - start_time < self.max_wait_time:
            iteration += 1
            status = self.check_all_services()
            
            if self.print_status(status, iteration):
                print("\n🚀 接続可能なサービス:")
                if status['ssh_connection']:
                    print(f"   🔌 SSH: ssh root@{self.runpod_ip} -p {self.ports['ssh']}")
                if status['web_terminal']:
                    print(f"   🌐 Web Terminal: http://{self.runpod_ip}:{self.ports['web_terminal']}")
                if status['jupyter']:
                    print(f"   📓 Jupyter: http://{self.runpod_ip}:{self.ports['jupyter']}")
                if status['api_server']:
                    print(f"   🔧 API Server: http://{self.runpod_ip}:{self.ports['api_server']}")
                
                # 結果をファイルに保存
                self.save_results(status, iteration)
                return True
            
            # 次のチェックまで待機
            if time.time() - start_time < self.max_wait_time:
                print(f"\n⏳ {self.check_interval}秒後に再チェック...")
                time.sleep(self.check_interval)
        
        print(f"\n⏰ 最大待機時間 ({self.max_wait_time}秒) に達しました")
        print("💡 RunPodダッシュボードでインスタンス状態を確認してください")
        return False
    
    def save_results(self, status, iteration):
        """結果をファイルに保存"""
        results = {
            "monitor_time": datetime.now().isoformat(),
            "iteration": iteration,
            "runpod_ip": self.runpod_ip,
            "status": status,
            "accessible_services": []
        }
        
        if status['ssh_connection']:
            results["accessible_services"].append({
                "service": "SSH",
                "port": self.ports['ssh'],
                "command": f"ssh root@{self.runpod_ip} -p {self.ports['ssh']}"
            })
        
        if status['web_terminal']:
            results["accessible_services"].append({
                "service": "Web Terminal",
                "port": self.ports['web_terminal'],
                "url": f"http://{self.runpod_ip}:{self.ports['web_terminal']}"
            })
        
        if status['jupyter']:
            results["accessible_services"].append({
                "service": "Jupyter",
                "port": self.ports['jupyter'],
                "url": f"http://{self.runpod_ip}:{self.ports['jupyter']}"
            })
        
        if status['api_server']:
            results["accessible_services"].append({
                "service": "API Server",
                "port": self.ports['api_server'],
                "url": f"http://{self.runpod_ip}:{self.ports['api_server']}"
            })
        
        with open('/root/runpod_monitor_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print("💾 監視結果を保存: /root/runpod_monitor_results.json")

def main():
    """メイン実行"""
    monitor = RunPodConnectionMonitor()
    
    try:
        success = monitor.monitor()
        if success:
            print("\n✅ RunPod接続監視完了 - サービス準備完了！")
        else:
            print("\n⚠️ RunPod接続監視完了 - 一部サービス未準備")
    except KeyboardInterrupt:
        print("\n🛑 監視を停止しました")
    except Exception as e:
        print(f"\n❌ 監視エラー: {e}")

if __name__ == "__main__":
    main()
