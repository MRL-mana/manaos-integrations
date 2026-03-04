#!/usr/bin/env python3
"""
🌟 Manaシステム統合マネージャー
全システムの起動・監視・管理を一元化
"""

import requests
import json
from datetime import datetime

class ManaSystemManager:
    def __init__(self):
        self.services = {
            'screen_sharing': {'port': 5008, 'name': '画面共有', 'icon': '🖥️'},
            'dashboard': {'port': 8000, 'name': '統合ダッシュボード', 'icon': '🌟'},
            'comfyui': {'port': 8188, 'name': 'ComfyUI', 'icon': '🎨'},
            'ollama': {'port': 11434, 'name': 'Ollama LLM', 'icon': '🤖'},
            'manaos': {'port': 9200, 'name': 'ManaOS Orchestrator', 'icon': '🎯'},
            'command_center': {'port': 10000, 'name': 'Command Center', 'icon': '🏠'},
            'google_services': {'port': 8097, 'name': 'Google Services', 'icon': '📧'},
            'trinity_secretary': {'port': 8087, 'name': 'Trinity秘書', 'icon': '🤖'}
        }
    
    def check_service(self, service_name):
        """サービスの稼働状況をチェック"""
        service = self.services.get(service_name)
        if not service:
            return {'status': 'unknown', 'message': 'サービス未登録'}
        
        try:
            response = requests.get(f"http://localhost:{service['port']}", timeout=2)
            return {
                'status': 'online',
                'port': service['port'],
                'response_code': response.status_code
            }
        except requests.exceptions.RequestException:
            return {'status': 'offline', 'port': service['port']}
    
    def check_all_services(self):
        """全サービスの状況をチェック"""
        results = {}
        print(f"\n🔍 システムチェック開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        print("=" * 70)
        
        for name, info in self.services.items():
            status = self.check_service(name)
            results[name] = status
            
            status_icon = '✅' if status['status'] == 'online' else '❌'
            print(f"{status_icon} {info['icon']} {info['name']:<20} | Port: {info['port']:<5} | {status['status'].upper()}")
        
        print("=" * 70)
        
        online_count = sum(1 for s in results.values() if s['status'] == 'online')
        total_count = len(results)
        print(f"\n📊 稼働率: {online_count}/{total_count} ({online_count/total_count*100:.1f}%)\n")
        
        return results
    
    def get_ollama_models(self):
        """Ollamaのモデル一覧を取得"""
        try:
            response = requests.get('http://localhost:11434/api/tags', timeout=2)
            data = response.json()
            print("\n🤖 Ollamaモデル一覧:")
            print("-" * 50)
            for model in data.get('models', []):
                size_gb = model.get('size', 0) / 1e9
                modified = model.get('modified_at', 'Unknown')
                print(f"  • {model['name']:<20} {size_gb:>6.1f} GB")
            print("-" * 50)
            return data
        except Exception as e:
            print(f"❌ Ollama接続エラー: {e}")
            return None
    
    def get_comfyui_stats(self):
        """ComfyUIの統計情報を取得"""
        try:
            response = requests.get('http://localhost:8188/system_stats', timeout=2)
            data = response.json()
            system = data.get('system', {})
            
            print("\n🎨 ComfyUI システム情報:")
            print("-" * 50)
            print(f"  Version: {system.get('comfyui_version', 'Unknown')}")
            print(f"  Python: {system.get('python_version', 'Unknown')}")
            print(f"  PyTorch: {system.get('pytorch_version', 'Unknown')}")
            
            ram_total_gb = system.get('ram_total', 0) / 1e9
            ram_free_gb = system.get('ram_free', 0) / 1e9
            ram_used_percent = (1 - ram_free_gb/ram_total_gb) * 100
            print(f"  RAM: {ram_used_percent:.1f}% 使用 ({ram_free_gb:.1f}/{ram_total_gb:.1f} GB 空き)")
            print("-" * 50)
            return data
        except Exception as e:
            print(f"❌ ComfyUI接続エラー: {e}")
            return None
    
    def get_manaos_health(self):
        """ManaOS v3.0のヘルスチェック"""
        try:
            response = requests.get('http://localhost:9200/health', timeout=2)
            data = response.json()
            
            print("\n🎯 ManaOS v3.0 ヘルスチェック:")
            print("-" * 50)
            print(f"  Orchestrator: {data.get('orchestrator', 'unknown').upper()}")
            
            services = data.get('services', {})
            for service_name, status in services.items():
                status_icon = '✅' if status == 'online' else '❌'
                print(f"  {status_icon} {service_name.capitalize()}: {status.upper()}")
            
            overall = data.get('overall', 'unknown')
            overall_icon = '✅' if overall == 'healthy' else '⚠️'
            print(f"\n  {overall_icon} 総合状態: {overall.upper()}")
            print("-" * 50)
            return data
        except Exception as e:
            print(f"❌ ManaOS接続エラー: {e}")
            return None
    
    def quick_test(self):
        """クイックテスト: 主要機能の動作確認"""
        print("\n🧪 クイックテスト開始\n")
        
        # LLMテスト
        try:
            print("💬 LLMテスト (llama3.2:3b)...")
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={'model': 'llama3.2:3b', 'prompt': 'こんにちは', 'stream': False},
                timeout=30
            )
            if response.status_code == 200:
                print("  ✅ LLM応答成功")
            else:
                print(f"  ❌ LLM応答失敗 (ステータス: {response.status_code})")
        except Exception as e:
            print(f"  ❌ LLM接続エラー: {e}")
        
        # ManaOS自律実行テスト
        try:
            print("\n🎯 ManaOS自律実行テスト...")
            response = requests.post(
                'http://localhost:9200/orchestrate',
                json={'text': 'システムの状態を確認して', 'actor': 'remi'},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ 自律実行成功 (意図: {data.get('intention', 'unknown')})")
            else:
                print(f"  ⚠️ 応答コード: {response.status_code}")
        except Exception as e:
            print(f"  ❌ ManaOS接続エラー: {e}")
        
        print("\n✨ テスト完了\n")
    
    def generate_report(self):
        """システムレポート生成"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'services': self.check_all_services(),
            'ollama': self.get_ollama_models(),
            'comfyui': self.get_comfyui_stats(),
            'manaos': self.get_manaos_health()
        }
        
        # JSONレポート保存
        report_file = f"/root/logs/system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 レポート保存: {report_file}")
        return report

def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║         🌟 Manaシステム統合マネージャー v1.0 🌟              ║
║                                                                ║
║            全システムの監視・管理・テストを一元化              ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    manager = ManaSystemManager()
    
    # 全サービスチェック
    manager.check_all_services()
    
    # 詳細情報取得
    manager.get_ollama_models()
    manager.get_comfyui_stats()
    manager.get_manaos_health()
    
    # クイックテスト
    manager.quick_test()
    
    # レポート生成
    manager.generate_report()
    
    print("""
╔════════════════════════════════════════════════════════════════╗
║  🎯 アクセスURL一覧                                           ║
╠════════════════════════════════════════════════════════════════╣
║  🌟 統合ダッシュボード: http://localhost:8000/mana_unified_dashboard.html
║  🖥️  画面共有: http://localhost:5008                          ║
║  🎨 ComfyUI: http://localhost:8188                            ║
║  🎯 ManaOS: http://localhost:9200                             ║
║  🏠 Command Center: http://localhost:10000                    ║
║  📧 Google Services: http://localhost:8097                    ║
╚════════════════════════════════════════════════════════════════╝
    """)

if __name__ == '__main__':
    main()

