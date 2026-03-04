#!/usr/bin/env python3
"""
🎨 ManaOS Supercharge Menu
トリニティ・スーパーチャージの統合メニュー
"""

import sys

# Trinity統合モジュールをインポート
sys.path.insert(0, '/root/mana_ai_ecosystem')
from trinity_supercharge_integration import get_trinity_integration

def print_banner():
    """バナー表示"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║              🚀 MANA OS - TRINITY SUPERCHARGE MENU 🚀                ║
║                                                                      ║
║                    トリニティ達の全機能を統合管理                       ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")

def print_menu():
    """メインメニュー表示"""
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📋 メインメニュー")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("\n【カテゴリ別機能】")
    print("  1. 🤖 AI & コミュニケーション")
    print("  2. 🎨 インターフェース & 可視化")
    print("  3. 💾 データ管理 & バックアップ")
    print("  4. ⚙️  自動化 & 監視")
    print("  5. 🔒 セキュリティ & API")
    print()
    print("【クイックアクション】")
    print("  Q. ⚡ クイックアクション一覧")
    print("  W. 🌐 Webサービス一覧")
    print("  S. 📊 全サービスステータス")
    print()
    print("  0. 🚪 終了")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

def show_category_menu(category: str, services: list):
    """カテゴリ別メニュー表示"""
    integration = get_trinity_integration()
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"📦 {category}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    for idx, service_id in enumerate(services, 1):
        status = integration.get_service_status(service_id)
        status_icon = "🟢" if status.get('status') == 'running' else "⚪"
        print(f"  {idx}. {status_icon} {status['name']}")
        print(f"     {status['description']}")
        if 'url' in status:
            print(f"     🌐 {status['url']}")
        print()
    
    print("  B. ⬅️  戻る")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

def show_service_actions(service_id: str):
    """サービスアクションメニュー"""
    integration = get_trinity_integration()
    status = integration.get_service_status(service_id)
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"⚙️  {status['name']}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    is_running = status.get('status') == 'running'
    status_text = "🟢 起動中" if is_running else "⚪ 停止中"
    print(f"状態: {status_text}")
    print(f"説明: {status['description']}\n")
    
    print("【アクション】")
    if not is_running:
        print("  1. ▶️  起動")
    else:
        print("  2. ⏹️  停止")
    
    # サービス固有のアクション
    if service_id == "auto_notes":
        print("  3. 📝 ノート作成")
    elif service_id == "smart_backup":
        print("  3. 💾 バックアップ実行")
    elif service_id == "smart_scheduler":
        print("  3. 📅 タスク一覧")
    elif service_id == "notification_system":
        print("  3. 🔔 テスト通知送信")
    
    if 'url' in status:
        print("  4. 🌐 ブラウザで開く")
    
    print("\n  B. ⬅️  戻る")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

def show_quick_actions():
    """クイックアクション一覧"""
    integration = get_trinity_integration()
    actions = integration.get_quick_actions()
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("⚡ クイックアクション")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    for idx, action in enumerate(actions, 1):
        print(f"  {idx}. {action['name']}")
        print(f"     {action['description']}\n")
    
    print("  B. ⬅️  戻る")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

def show_web_services():
    """Webサービス一覧"""
    integration = get_trinity_integration()
    web_services = integration.get_web_services()
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🌐 Webサービス")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    for service in web_services:
        print(f"  {service['name']}")
        print(f"  ├─ ローカル:     {service['url']}")
        print(f"  ├─ 外部アクセス: {service['external_url']}")
        print(f"  └─ Tailscale:    {service['tailscale_url']}\n")
    
    print("  B. ⬅️  戻る")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

def show_all_status():
    """全サービスステータス"""
    integration = get_trinity_integration()
    services = integration.get_all_services_status()
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📊 全サービスステータス")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    running_count = sum(1 for s in services if s.get('status') == 'running')
    
    print(f"起動中: {running_count}/{len(services)} サービス\n")
    
    for service in services:
        status_icon = "🟢" if service.get('status') == 'running' else "⚪"
        print(f"{status_icon} {service['name']:<35} {service.get('status', 'unknown')}")
    
    print("\n  B. ⬅️  戻る")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

def execute_action(service_id: str, action: str):
    """アクションを実行"""
    integration = get_trinity_integration()
    
    if action == "create_note":
        print("\n📝 ノート作成")
        title = input("タイトル: ")
        content = input("内容: ")
        result = integration.execute_service_action(service_id, 'create', title=title, content=content)
    
    elif action == "create_backup":
        print("\n💾 バックアップ実行")
        name = input("バックアップ名（空白でデフォルト）: ") or "manual"
        print("バックアップ中...")
        result = integration.execute_service_action(service_id, 'create', name=name)
    
    elif action == "list_tasks":
        print("\n📅 スケジュールタスク")
        result = integration.execute_service_action(service_id, 'list')
    
    elif action == "send_notification":
        print("\n🔔 通知送信")
        message = input("メッセージ: ")
        level = input("レベル (info/warning/error): ") or "info"
        result = integration.execute_service_action(service_id, 'send', message=message, level=level)
    
    elif action == "start":
        result = integration.execute_service_action(service_id, 'start')
    
    elif action == "stop":
        result = integration.execute_service_action(service_id, 'stop')
    
    else:
        result = {"success": False, "error": "Unknown action"}
    
    if result.get('success'):
        print(f"\n✅ {result.get('message', '成功')}")
        if 'output' in result:
            print(result['output'])
    else:
        print(f"\n❌ エラー: {result.get('error', 'Unknown error')}")
    
    input("\nEnterキーで続行...")

def main():
    """メインループ"""
    integration = get_trinity_integration()
    
    while True:
        print_banner()
        print_menu()
        
        choice = input("選択 > ").strip().upper()
        
        if choice == '0':
            print("\n👋 ManaOS Supercharge Menu を終了します")
            break
        
        elif choice == '1':
            # AI & コミュニケーション
            categories = integration.get_categories()
            ai_services = categories.get('ai', []) + categories.get('interaction', [])
            show_category_menu("AI & コミュニケーション", ai_services)
            # TODO: サブメニュー処理
        
        elif choice == '2':
            # インターフェース & 可視化
            categories = integration.get_categories()
            ui_services = categories.get('interface', []) + categories.get('monitoring', [])
            show_category_menu("インターフェース & 可視化", ui_services)
        
        elif choice == '3':
            # データ管理
            categories = integration.get_categories()
            data_services = categories.get('data', []) + categories.get('productivity', [])
            show_category_menu("データ管理 & バックアップ", data_services)
        
        elif choice == '4':
            # 自動化 & 監視
            categories = integration.get_categories()
            auto_services = categories.get('automation', [])
            show_category_menu("自動化 & 監視", auto_services)
        
        elif choice == '5':
            # セキュリティ & API
            categories = integration.get_categories()
            security_services = categories.get('security', []) + categories.get('communication', [])
            show_category_menu("セキュリティ & API", security_services)
        
        elif choice == 'Q':
            show_quick_actions()
            input("\nEnterキーで続行...")
        
        elif choice == 'W':
            show_web_services()
            input("\nEnterキーで続行...")
        
        elif choice == 'S':
            show_all_status()
            input("\nEnterキーで続行...")
        
        else:
            print("\n❌ 無効な選択です")
            input("\nEnterキーで続行...")

if __name__ == "__main__":
    main()


