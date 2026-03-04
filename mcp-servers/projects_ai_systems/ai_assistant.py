#!/usr/bin/env python3
"""
🤖 Mana AI統合アシスタント
複数のAIシステムを統合して自然言語で操作
"""

import requests
import sys

class ManaAIAssistant:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.manaos_url = "http://localhost:9200"
        self.comfyui_url = "http://localhost:8188"
        
    def chat_with_llm(self, message, model="llama3.2:3b"):
        """LLMとチャット"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": message,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('response', '応答なし')
            else:
                return f"エラー: ステータスコード {response.status_code}"
        except Exception as e:
            return f"接続エラー: {e}"
    
    def manaos_execute(self, command, actor="remi"):
        """ManaOS v3.0で自律実行"""
        try:
            # MCPツールを使用する想定
            print(f"🎯 ManaOS実行: {command}")
            print(f"   アクター: {actor}")
            return {"status": "MCP経由で実行してください"}
        except Exception as e:
            return {"error": str(e)}
    
    def interactive_mode(self):
        """対話モード"""
        print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║            🤖 Mana AI統合アシスタント v1.0 🤖                ║
║                                                                ║
║               複数のAIシステムを自然言語で操作                 ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

利用可能なコマンド:
  💬 chat <メッセージ>     - LLMと対話
  🎯 manaos <指示>        - ManaOS自律実行
  📊 status               - システム状態確認
  🎨 models               - 利用可能なモデル一覧
  💡 help                 - ヘルプ表示
  👋 exit / quit          - 終了

        """)
        
        while True:
            try:
                user_input = input("🌟 Mana > ").strip()
                
                if not user_input:
                    continue
                
                # 終了コマンド
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("\n👋 終了します。ありがとうございました！\n")
                    break
                
                # ヘルプ
                elif user_input.lower() == 'help':
                    print("""
💡 コマンド一覧:
  chat <メッセージ>  - LLMと対話（例: chat こんにちは）
  manaos <指示>     - ManaOS実行（例: manaos 今日の予定教えて）
  status            - システム状態確認
  models            - 利用可能なAIモデル一覧
  help              - このヘルプを表示
  exit / quit       - アシスタント終了
                    """)
                
                # ステータス確認
                elif user_input.lower() == 'status':
                    print("\n📊 システム状態確認中...\n")
                    self.check_system_status()
                
                # モデル一覧
                elif user_input.lower() == 'models':
                    print("\n🤖 利用可能なモデル一覧:\n")
                    self.list_models()
                
                # チャット
                elif user_input.lower().startswith('chat '):
                    message = user_input[5:].strip()
                    if message:
                        print("\n💬 LLM応答中...\n")
                        response = self.chat_with_llm(message)
                        print(f"🤖 {response}\n")
                    else:
                        print("❌ メッセージを入力してください\n")
                
                # ManaOS実行
                elif user_input.lower().startswith('manaos '):
                    command = user_input[7:].strip()
                    if command:
                        result = self.manaos_execute(command)
                        print(f"✅ {result}\n")
                    else:
                        print("❌ 指示を入力してください\n")
                
                # デフォルト: LLMとチャット
                else:
                    print("\n💬 LLM応答中...\n")
                    response = self.chat_with_llm(user_input)
                    print(f"🤖 {response}\n")
                    
            except KeyboardInterrupt:
                print("\n\n👋 終了します。\n")
                break
            except Exception as e:
                print(f"❌ エラー: {e}\n")
    
    def check_system_status(self):
        """システム状態確認"""
        services = {
            'Ollama': f"{self.ollama_url}/api/tags",
            'ManaOS': f"{self.manaos_url}/health",
            'ComfyUI': f"{self.comfyui_url}/system_stats"
        }
        
        for name, url in services.items():
            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    print(f"  ✅ {name}: オンライン")
                else:
                    print(f"  ⚠️  {name}: 応答異常 (コード {response.status_code})")
            except requests.RequestException:
                print(f"  ❌ {name}: オフライン")
        print()
    
    def list_models(self):
        """モデル一覧取得"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                if models:
                    for model in models:
                        size_gb = model.get('size', 0) / 1e9
                        print(f"  • {model['name']:<20} {size_gb:>6.1f} GB")
                else:
                    print("  モデルがインストールされていません")
            else:
                print(f"  エラー: ステータスコード {response.status_code}")
        except Exception as e:
            print(f"  接続エラー: {e}")
        print()

def main():
    if len(sys.argv) > 1:
        # コマンドライン引数モード
        assistant = ManaAIAssistant()
        command = ' '.join(sys.argv[1:])
        
        if command.startswith('chat '):
            message = command[5:]
            print(assistant.chat_with_llm(message))
        elif command == 'status':
            assistant.check_system_status()
        elif command == 'models':
            assistant.list_models()
        else:
            print(assistant.chat_with_llm(command))
    else:
        # 対話モード
        assistant = ManaAIAssistant()
        assistant.interactive_mode()

if __name__ == '__main__':
    main()

