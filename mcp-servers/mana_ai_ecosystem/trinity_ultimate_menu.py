#!/usr/bin/env python3
"""
🌟 Trinity Ultimate Menu - 究極の統合メニュー
全てのTrinityシステムを一つのメニューで管理
"""

import sys

sys.path.insert(0, '/root/mana_ai_ecosystem')
from trinity_ultimate_integration import get_ultimate_integration

def print_banner():
    """バナー表示"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║            🌟 TRINITY ULTIMATE - 究極の統合メニュー 🌟              ║
║                                                                      ║
║              全21の機能・システムを統合管理                            ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")

def show_main_menu():
    """メインメニュー"""
    integration = get_ultimate_integration()
    dashboard = integration.get_dashboard_data()
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📊 システム概要")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"\n  合計システム数: {dashboard['summary']['total_systems']}")
    print(f"  🟢 起動中: {dashboard['summary']['running']}")
    print(f"  ⚪ 停止中: {dashboard['summary']['stopped']}")
    print(f"\n  • Trinity Supercharge: {dashboard['summary']['supercharge_features']}機能")
    print(f"  • 既存Trinityシステム: {dashboard['summary']['legacy_systems']}システム")
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📋 カテゴリメニュー")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    print("【Trinity Supercharge - 新機能】")
    print("  1. 🤖 AI & インタラクション")
    print("  2. 🎨 インターフェース & 可視化")
    print("  3. 💾 データ管理 & 生産性")
    print("  4. ⚙️  自動化 & 監視")
    print("  5. 🔒 セキュリティ")
    
    print("\n【既存Trinityシステム】")
    print("  6. 💬 会話 & コミュニケーション")
    print("  7. 📺 リモート & 画面共有")
    print("  8. 📁 ファイル & データ")
    print("  9. 🧠 AI & 学習")
    print("  10. 📚 知識管理")
    
    print("\n【クイックアクセス】")
    print("  W. 🌐 Webサービス一覧")
    print("  S. 📊 全システムステータス")
    print("  A. 🚀 自動起動システムを全て起動")
    
    print("\n  0. 🚪 終了")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

def show_category_systems(category_name: str, system_ids: list):
    """カテゴリ別システム表示"""
    integration = get_ultimate_integration()
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"📦 {category_name}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    for idx, system_id in enumerate(system_ids, 1):
        status = integration.get_system_status(system_id)
        if 'error' in status:
            continue
        
        status_icon = "🟢" if status.get('status') == 'running' else "⚪"
        print(f"  {idx}. {status_icon} {status['name']}")
        print(f"     {status['description']}")
        if 'url' in status:
            print(f"     🌐 {status['url']}")
        print()
    
    print("  S. 🚀 カテゴリ内システムを全て起動")
    print("  X. ⏹️  カテゴリ内システムを全て停止")
    print("  B. ⬅️  戻る")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

def show_web_services():
    """Webサービス一覧"""
    integration = get_ultimate_integration()
    web_services = integration.get_web_services()
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🌐 Webサービス一覧")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    for service in web_services:
        status_icon = "🟢" if service['status'] == 'running' else "⚪"
        print(f"{status_icon} {service['name']}")
        print(f"  ├─ ポート:       {service['port']}")
        print(f"  ├─ ローカル:     {service['url']}")
        print(f"  ├─ 外部アクセス: {service['external_url']}")
        print(f"  └─ Tailscale:    {service['tailscale_url']}\n")
    
    print("  B. ⬅️  戻る")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

def show_all_status():
    """全システムステータス"""
    integration = get_ultimate_integration()
    all_systems = integration.get_all_systems_status()
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📊 全システムステータス")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    # カテゴリ別に表示
    by_category = {}
    for system in all_systems:
        if 'error' in system:
            continue
        category = system['category']
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(system)
    
    for category, systems in sorted(by_category.items()):
        print(f"\n【{category}】")
        for system in systems:
            status_icon = "🟢" if system.get('status') == 'running' else "⚪"
            print(f"  {status_icon} {system['name']:<40} {system.get('status', 'unknown')}")
    
    running_count = sum(1 for s in all_systems if s.get('status') == 'running')
    print(f"\n合計: {running_count}/{len(all_systems)} システムが起動中")
    
    print("\n  B. ⬅️  戻る")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

def main():
    """メインループ"""
    integration = get_ultimate_integration()
    
    while True:
        print_banner()
        show_main_menu()
        
        choice = input("選択 > ").strip().upper()
        
        if choice == '0':
            print("\n👋 Trinity Ultimate Menu を終了します")
            break
        
        elif choice == 'W':
            show_web_services()
            input("\nEnterキーで続行...")
        
        elif choice == 'S':
            show_all_status()
            input("\nEnterキーで続行...")
        
        elif choice == 'A':
            print("\n🚀 自動起動システムを起動中...")
            result = integration.start_all_auto_systems()
            print(f"\n✅ {result['total']}個のシステムを起動しました")
            for r in result['results']:
                status = "✅" if r['result'].get('success') else "❌"
                print(f"  {status} {r['name']}")
            input("\nEnterキーで続行...")
        
        elif choice in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']:
            categories = integration.get_categories()
            category_list = list(categories.items())
            
            # カテゴリマッピング
            category_map = {
                '1': 'supercharge_interaction',
                '2': 'supercharge_interface',
                '3': 'supercharge_data',
                '4': 'supercharge_automation',
                '5': 'supercharge_security',
                '6': 'conversation',
                '7': 'remote',
                '8': 'files',
                '9': 'ai',
                '10': 'knowledge'
            }
            
            category_key = category_map.get(choice)
            if category_key and category_key in categories:
                systems = categories[category_key]
                show_category_systems(category_key, systems)
                input("\nEnterキーで続行...")
        
        else:
            print("\n❌ 無効な選択です")
            input("\nEnterキーで続行...")

if __name__ == "__main__":
    main()


