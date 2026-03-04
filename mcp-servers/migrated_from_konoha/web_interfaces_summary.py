#!/usr/bin/env python3
"""
Web Interfaces Summary
Trinity AI システムの全Webインターフェース一覧
"""

import os
import subprocess
from datetime import datetime

class WebInterfacesSummary:
    def __init__(self):
        self.interfaces = {
            "trinity_webui": {
                "name": "🎨 Trinity WebUI",
                "port": 5093,
                "description": "統合Webインターフェース - 画像生成・ギャラリー・モデル管理",
                "features": [
                    "画像生成フォーム",
                    "リアルタイム生成状況",
                    "画像ギャラリー",
                    "モデル管理",
                    "タブ式インターフェース"
                ],
                "urls": [
                    "http://127.0.0.1:5093",
                    "http://163.44.120.49:5093",
                    "http://100.93.120.33:5093"
                ]
            },
            "image_gallery": {
                "name": "🖼️ Image Gallery",
                "port": 5092,
                "description": "画像ギャラリー - 生成された画像の閲覧・管理",
                "features": [
                    "画像一覧表示",
                    "画像詳細情報",
                    "モーダル表示",
                    "レスポンシブデザイン"
                ],
                "urls": [
                    "http://127.0.0.1:5092",
                    "http://163.44.120.49:5092",
                    "http://100.93.120.33:5092"
                ]
            },
            "image_generator": {
                "name": "🎨 Image Generator",
                "port": 5091,
                "description": "画像生成Webインターフェース - 基本的な画像生成機能",
                "features": [
                    "プロンプト入力",
                    "モデル選択",
                    "サイズ設定",
                    "生成実行"
                ],
                "urls": [
                    "http://127.0.0.1:5091",
                    "http://163.44.120.49:5091",
                    "http://100.93.120.33:5091"
                ]
            }
        }
    
    def check_service_status(self, port):
        """サービス状況確認"""
        try:
            result = subprocess.run(['lsof', '-i', f':{port}'], capture_output=True, text=True)
            return len(result.stdout.strip()) > 0
        except:
            return False
    
    def get_interface_status(self):
        """全インターフェース状況取得"""
        status = {}
        for interface_id, interface_info in self.interfaces.items():
            port = interface_info['port']
            is_running = self.check_service_status(port)
            status[interface_id] = {
                "running": is_running,
                "port": port,
                "name": interface_info['name'],
                "description": interface_info['description']
            }
        return status
    
    def display_summary(self):
        """サマリー表示"""
        print("🌐 Trinity AI Web Interfaces Summary")
        print("=" * 80)
        print(f"📅 更新日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        status = self.get_interface_status()
        
        print("📊 インターフェース状況")
        print("-" * 80)
        
        for interface_id, interface_info in self.interfaces.items():
            interface_status = status[interface_id]
            status_icon = "🟢" if interface_status['running'] else "🔴"
            
            print(f"\n{status_icon} {interface_info['name']}")
            print(f"   ポート: {interface_info['port']}")
            print(f"   状況: {'稼働中' if interface_status['running'] else '停止中'}")
            print(f"   説明: {interface_info['description']}")
            
            print("   機能:")
            for feature in interface_info['features']:
                print(f"     • {feature}")
            
            print("   アクセスURL:")
            for url in interface_info['urls']:
                print(f"     {url}")
        
        print(f"\n🎯 推奨アクセス順序")
        print("-" * 80)
        print("1. Trinity WebUI (ポート5093) - 統合インターフェース")
        print("2. Image Gallery (ポート5092) - 画像閲覧専用")
        print("3. Image Generator (ポート5091) - 基本生成機能")
        
        print(f"\n💡 使用方法")
        print("-" * 80)
        print("• Trinity WebUI: 全機能を一箇所で管理")
        print("• Image Gallery: 生成された画像を閲覧")
        print("• Image Generator: シンプルな画像生成")
        
        print(f"\n🔧 管理コマンド")
        print("-" * 80)
        print("# 全サービス状況確認")
        print("ps aux | grep -E '(webui|gallery)' | grep -v grep")
        print()
        print("# 特定ポート確認")
        print("lsof -i :5093  # Trinity WebUI")
        print("lsof -i :5092  # Image Gallery")
        print("lsof -i :5091  # Image Generator")
        print()
        print("# サービス再起動")
        print("pkill -f simple_webui && python3 /root/trinity_workspace/tools/simple_webui.py &")
        print("pkill -f web_image_gallery && python3 /root/trinity_workspace/tools/web_image_gallery.py &")
    
    def get_quick_access_info(self):
        """クイックアクセス情報"""
        print("\n🚀 クイックアクセス")
        print("=" * 80)
        
        status = self.get_interface_status()
        
        for interface_id, interface_info in self.interfaces.items():
            interface_status = status[interface_id]
            if interface_status['running']:
                print(f"✅ {interface_info['name']}: {interface_info['urls'][0]}")
            else:
                print(f"❌ {interface_info['name']}: 停止中")
        
        print(f"\n💬 チャットでの使用方法")
        print("-" * 80)
        print("「画像生成して」→ Trinity WebUIで実行")
        print("「画像見たい」→ Image Galleryで確認")
        print("「モデル管理」→ Trinity WebUIで管理")
        print("「WebUI起動して」→ 全サービス自動起動")


def main():
    """メイン関数"""
    summary = WebInterfacesSummary()
    summary.display_summary()
    summary.get_quick_access_info()


if __name__ == "__main__":
    main()


