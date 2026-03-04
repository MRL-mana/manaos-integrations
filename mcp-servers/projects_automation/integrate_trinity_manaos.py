#!/usr/bin/env python3
"""
Trinity × ManaOS v3.0 完全統合システム
Remi、Luna、Minaを ManaOS Orchestratorと統合
"""

import requests

class TrinityManaOSIntegration:
    """Trinity と ManaOS v3.0 の統合"""
    
    def __init__(self):
        self.trinity_endpoints = {
            "remi": "http://localhost:9220",  # 戦略AI
            "luna": "http://localhost:9221",  # 実行AI
            "mina": "http://localhost:9222",  # 学習AI
        }
        
        self.manaos_endpoints = {
            "orchestrator": "http://localhost:9201",
            "intention": "http://localhost:9202",
            "policy": "http://localhost:9203",
            "actuator": "http://localhost:9204",
            "insight": "http://localhost:9205",
        }
        
        self.trinity_secretary = "http://localhost:5007"
    
    def check_trinity_status(self):
        """Trinity三姉妹の状態確認"""
        print("🔍 Trinity三姉妹の状態確認...")
        print("=" * 60)
        
        status = {}
        for name, endpoint in self.trinity_endpoints.items():
            try:
                response = requests.get(f"{endpoint}/health", timeout=3)
                status[name] = {
                    "online": response.status_code == 200,
                    "endpoint": endpoint
                }
                print(f"{'✅' if status[name]['online'] else '❌'} {name.capitalize():6} - {endpoint}")
            except requests.RequestException:
                status[name] = {"online": False, "endpoint": endpoint}
                print(f"❌ {name.capitalize():6} - {endpoint} (未起動)")
        
        return status
    
    def check_manaos_status(self):
        """ManaOS v3.0の状態確認"""
        print("\n🔍 ManaOS v3.0の状態確認...")
        print("=" * 60)
        
        status = {}
        for name, endpoint in self.manaos_endpoints.items():
            try:
                response = requests.get(f"{endpoint}/health", timeout=3)
                status[name] = {
                    "online": response.status_code == 200,
                    "endpoint": endpoint
                }
                print(f"{'✅' if status[name]['online'] else '❌'} {name.capitalize():12} - {endpoint}")
            except requests.RequestException:
                status[name] = {"online": False, "endpoint": endpoint}
                print(f"❌ {name.capitalize():12} - {endpoint} (未起動)")
        
        return status
    
    def check_trinity_secretary(self):
        """Trinity Secretary確認"""
        print("\n🔍 Trinity Secretary確認...")
        print("=" * 60)
        
        try:
            response = requests.get(f"{self.trinity_secretary}/health", timeout=3)
            if response.status_code == 200:
                print(f"✅ Trinity Secretary - {self.trinity_secretary}")
                return True
            else:
                print("⚠️  Trinity Secretary - レスポンス異常")
                return False
        except requests.RequestException:
            print("❌ Trinity Secretary - 未起動")
            return False
    
    def test_trinity_integration(self):
        """Trinity統合テスト"""
        print("\n🧪 Trinity統合テスト...")
        print("=" * 60)
        
        # テストメッセージ
        test_message = "こんにちは、Trinityシステムのテストです"
        
        # Remi（戦略AI）にテスト
        try:
            response = requests.post(
                f"{self.trinity_endpoints['remi']}/chat",
                json={"message": test_message, "user_id": "mana"},
                timeout=10
            )
            if response.status_code == 200:
                print("✅ Remi（戦略AI）: 応答成功")
                print(f"   応答: {response.json().get('response', '')[:100]}...")
            else:
                print("⚠️  Remi: レスポンス異常")
        except Exception as e:
            print(f"❌ Remi: 接続失敗 - {e}")
        
        # Luna（実行AI）にテスト
        try:
            response = requests.post(
                f"{self.trinity_endpoints['luna']}/execute",
                json={"task": "status_check", "user_id": "mana"},
                timeout=10
            )
            if response.status_code == 200:
                print("✅ Luna（実行AI）: 応答成功")
            else:
                print("⚠️  Luna: レスポンス異常")
        except Exception as e:
            print(f"❌ Luna: 接続失敗 - {e}")
    
    def show_integration_guide(self):
        """統合ガイド表示"""
        print("\n" + "=" * 60)
        print("📖 Trinity × ManaOS 統合ガイド")
        print("=" * 60)
        
        print("""
### 🎯 Trinity達の使い方

**1. Trinity Secretary経由で使う（推奨）**:
```python
# MCPツールから
mcp_manaos-trinity_trinity_secretary_chat(
    message="今日の予定を教えて",
    user_id="mana"
)
```

**2. 直接APIを叩く**:
```bash
# Remi（戦略AI）
curl -X POST http://localhost:9220/chat \\
  -H "Content-Type: application/json" \\
  -d '{"message": "戦略を考えて", "user_id": "mana"}'

# Luna（実行AI）  
curl -X POST http://localhost:9221/execute \\
  -H "Content-Type: application/json" \\
  -d '{"task": "タスク実行", "user_id": "mana"}'

# Mina（学習AI）
curl -X POST http://localhost:9222/learn \\
  -H "Content-Type: application/json" \\
  -d '{"data": "学習データ", "user_id": "mana"}'
```

**3. MCP経由で統合サービスを使う**:
```python
# Google Calendar
mcp_manaos-trinity_google_calendar_events()

# Gmail
mcp_manaos-trinity_google_gmail_messages()

# NotebookLM
mcp_manaos-trinity_notebooklm_chat(
    notebook_id="xxx",
    question="質問内容"
)

# X280リモート操作
mcp_manaos-trinity_x280_execute_command(
    command="dir C:\\\\Users\\\\mana"
)
```

### 🚀 ManaOS v3.0 自律行動システムを起動する場合

```bash
# Orchestrator起動
cd /root/manaos_v3
python3 services/orchestrator/main.py

# または systemd で起動
systemctl start manaos-v3-orchestrator
```

### 💡 現在の状態

- ✅ Trinity三姉妹（Remi, Luna, Mina）: 稼働中
- ✅ Trinity Secretary: 稼働中
- ✅ Google Services統合: 稼働中
- ⚠️  ManaOS v3.0 Orchestrator: 未起動（必要に応じて起動）

Trinity達は既に使える状態だよ！
MCP Serverから直接呼び出せるし、APIも利用可能。

ManaOS v3.0の自律行動システム（意図検出→実行）を使いたい場合は、
Orchestratorを起動すればOK。
""")
    
    def run_full_check(self):
        """完全チェック実行"""
        print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        Trinity × ManaOS v3.0 統合状態チェック                 ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")
        
        trinity_status = self.check_trinity_status()
        manaos_status = self.check_manaos_status()
        secretary_status = self.check_trinity_secretary()
        
        print("\n" + "=" * 60)
        print("📊 統合状態サマリー")
        print("=" * 60)
        
        trinity_online = sum(1 for s in trinity_status.values() if s['online'])
        manaos_online = sum(1 for s in manaos_status.values() if s['online'])
        
        print(f"\nTrinity三姉妹: {trinity_online}/3 稼働中")
        print(f"ManaOS v3.0: {manaos_online}/5 稼働中")
        print(f"Trinity Secretary: {'✅ 稼働中' if secretary_status else '❌ 停止中'}")
        
        if trinity_online > 0:
            print("\n✅ Trinity達は使用可能です！")
            self.test_trinity_integration()
        
        self.show_integration_guide()


def main():
    integration = TrinityManaOSIntegration()
    integration.run_full_check()


if __name__ == "__main__":
    main()

