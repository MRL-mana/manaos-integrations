#!/usr/bin/env python3
"""
RunPod動的IPアドレス検出システム
RunPodインスタンスの新しいIPアドレスを自動検出する
"""

import subprocess
import requests
import json
from datetime import datetime
import concurrent.futures

class RunPodIPDetector:
    def __init__(self):
        self.known_ips = [
            "213.181.111.2",  # 前回のIP
            # 他の可能性のあるIP範囲
        ]
        self.common_ports = [19123, 8888, 7860, 22, 3000, 8000, 5000]
        self.found_instances = []
        
    def scan_ip_range(self, base_ip="213.181.111"):
        """IPレンジをスキャン"""
        print(f"🔍 IPレンジスキャン開始: {base_ip}.x")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            
            for i in range(1, 255):
                ip = f"{base_ip}.{i}"
                future = executor.submit(self.check_ip, ip)
                futures.append((ip, future))
            
            for ip, future in futures:
                try:
                    result = future.result(timeout=2)
                    if result:
                        self.found_instances.append(result)
                        print(f"✅ 発見: {ip} - {result['service']}")
                except Exception:
                    pass
    
    def check_ip(self, ip):
        """単一IPのチェック"""
        try:
            # Web Terminal (19123)
            if self.check_port(ip, 19123):
                return {"ip": ip, "port": 19123, "service": "Web Terminal", "url": f"http://{ip}:19123"}
            
            # Jupyter (8888)
            if self.check_port(ip, 8888):
                return {"ip": ip, "port": 8888, "service": "Jupyter", "url": f"http://{ip}:8888"}
            
            # API Server (7860)
            if self.check_port(ip, 7860):
                return {"ip": ip, "port": 7860, "service": "API Server", "url": f"http://{ip}:7860"}
            
            # その他のポート
            for port in [3000, 8000, 5000]:
                if self.check_port(ip, port):
                    return {"ip": ip, "port": port, "service": f"Service on {port}", "url": f"http://{ip}:{port}"}
            
        except Exception:
            pass
        return None
    
    def check_port(self, ip, port, timeout=2):
        """ポート接続確認"""
        try:
            response = requests.get(f"http://{ip}:{port}", timeout=timeout)
            return response.status_code in [200, 401, 403]  # 応答があればOK
        except requests.RequestException:
            try:
                # HTTP以外のプロトコルも試す
                result = subprocess.run([
                    'nc', '-z', '-w', '2', ip, str(port)
                ], capture_output=True, text=True)
                return result.returncode == 0
            except requests.RequestException:
                return False
    
    def scan_known_ips(self):
        """既知のIPアドレスをスキャン"""
        print("🔍 既知のIPアドレスをスキャン中...")
        
        for ip in self.known_ips:
            print(f"📡 スキャン中: {ip}")
            
            for port in self.common_ports:
                if self.check_port(ip, port):
                    service_name = {
                        19123: "Web Terminal",
                        8888: "Jupyter Notebook", 
                        7860: "API Server",
                        22: "SSH",
                        3000: "Web Service",
                        8000: "API Service",
                        5000: "Flask Service"
                    }.get(port, f"Service on {port}")
                    
                    instance = {
                        "ip": ip,
                        "port": port,
                        "service": service_name,
                        "url": f"http://{ip}:{port}",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    self.found_instances.append(instance)
                    print(f"✅ 発見: {ip}:{port} - {service_name}")
    
    def test_runpod_services(self):
        """RunPodサービスをテスト"""
        print("🧪 RunPodサービステスト開始")
        
        for instance in self.found_instances:
            print(f"\n🔧 テスト中: {instance['service']} ({instance['url']})")
            
            try:
                if instance['service'] == "Web Terminal":
                    # Web Terminalテスト
                    response = requests.get(instance['url'], timeout=5)
                    if response.status_code == 200:
                        print("✅ Web Terminal: アクセス可能")
                        instance['status'] = 'accessible'
                    else:
                        print(f"⚠️ Web Terminal: ステータス {response.status_code}")
                        instance['status'] = 'restricted'
                
                elif instance['service'] == "Jupyter Notebook":
                    # Jupyterテスト
                    response = requests.get(instance['url'], timeout=5)
                    if response.status_code == 200:
                        print("✅ Jupyter: アクセス可能")
                        instance['status'] = 'accessible'
                    else:
                        print(f"⚠️ Jupyter: ステータス {response.status_code}")
                        instance['status'] = 'restricted'
                
                elif instance['service'] == "API Server":
                    # API Serverテスト
                    response = requests.get(instance['url'], timeout=5)
                    if response.status_code == 200:
                        print("✅ API Server: アクセス可能")
                        instance['status'] = 'accessible'
                        
                        # GPU状態確認
                        try:
                            gpu_response = requests.get(f"{instance['url']}/gpu/status", timeout=5)
                            if gpu_response.status_code == 200:
                                gpu_data = gpu_response.json()
                                print(f"🎮 GPU状態: {gpu_data}")
                                instance['gpu_status'] = gpu_data
                        except requests.RequestException:
                            pass
                    else:
                        print(f"⚠️ API Server: ステータス {response.status_code}")
                        instance['status'] = 'restricted'
                        
            except Exception as e:
                print(f"❌ エラー: {e}")
                instance['status'] = 'error'
    
    def generate_report(self):
        """検出レポート生成"""
        print("\n" + "="*60)
        print("🎯 RunPodインスタンス検出レポート")
        print("="*60)
        
        if not self.found_instances:
            print("❌ RunPodインスタンスが見つかりませんでした")
            print("\n💡 確認事項:")
            print("1. RunPodインスタンスが起動しているか")
            print("2. ネットワーク接続が正常か")
            print("3. ファイアウォール設定")
            return
        
        print(f"✅ 発見したインスタンス数: {len(self.found_instances)}")
        print()
        
        for i, instance in enumerate(self.found_instances, 1):
            print(f"📋 インスタンス {i}:")
            print(f"   IPアドレス: {instance['ip']}")
            print(f"   ポート: {instance['port']}")
            print(f"   サービス: {instance['service']}")
            print(f"   URL: {instance['url']}")
            print(f"   ステータス: {instance.get('status', 'unknown')}")
            
            if 'gpu_status' in instance:
                gpu = instance['gpu_status']
                print(f"   🎮 GPU: {gpu.get('gpu_name', 'Unknown')}")
                print(f"   💾 メモリ: {gpu.get('gpu_memory', 'Unknown')}")
            
            print()
        
        # 推奨アクセス方法
        print("🚀 推奨アクセス方法:")
        
        web_terminal = next((i for i in self.found_instances if i['service'] == 'Web Terminal' and i.get('status') == 'accessible'), None)
        jupyter = next((i for i in self.found_instances if i['service'] == 'Jupyter Notebook' and i.get('status') == 'accessible'), None)
        api_server = next((i for i in self.found_instances if i['service'] == 'API Server' and i.get('status') == 'accessible'), None)
        
        if web_terminal:
            print(f"🥇 Web Terminal: {web_terminal['url']}")
        
        if jupyter:
            print(f"🥈 Jupyter Notebook: {jupyter['url']}")
        
        if api_server:
            print(f"🥉 API Server: {api_server['url']}")
    
    def save_results(self):
        """結果をファイルに保存"""
        results = {
            "scan_time": datetime.now().isoformat(),
            "found_instances": self.found_instances,
            "summary": {
                "total_found": len(self.found_instances),
                "accessible_services": len([i for i in self.found_instances if i.get('status') == 'accessible'])
            }
        }
        
        with open('/root/runpod_scan_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print("💾 結果を保存: /root/runpod_scan_results.json")

def main():
    """メイン実行"""
    print("🔍 RunPod動的IPアドレス検出システム")
    print("="*50)
    
    detector = RunPodIPDetector()
    
    # 既知のIPをスキャン
    detector.scan_known_ips()
    
    # サービステスト
    detector.test_runpod_services()
    
    # レポート生成
    detector.generate_report()
    
    # 結果保存
    detector.save_results()

if __name__ == "__main__":
    main()
