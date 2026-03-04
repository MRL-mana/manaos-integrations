#!/usr/bin/env python3
"""
Trinity Interface for ManaOS Agents
Trinity達が簡単にエージェントを使えるインターフェース
"""

import sys
from typing import Optional, Dict, Any
from agent_manager import AgentManager, setup_default_agents


class TrinityAgentInterface:
    """Trinity用のシンプルなエージェントインターフェース"""
    
    def __init__(self):
        self.manager = AgentManager()
        setup_default_agents(self.manager)
        print("🌟 Trinity Agent Interface 起動完了!")
        
    def ask(self, agent_name: str, question: str, context: Optional[Dict] = None) -> str:
        """
        エージェントに質問する（最もシンプルな使い方）
        
        Args:
            agent_name: エージェント名 ("researcher", "coder", "analyzer", "writer")
            question: 質問内容
            context: 追加のコンテキスト
            
        Returns:
            エージェントの回答
            
        Example:
            interface.ask("researcher", "Pythonの最新バージョンは？")
        """
        result = self.manager.run_agent(agent_name, question, context)
        
        if result.get("success"):
            return result.get("result", "")
        else:
            return f"❌ エラー: {result.get('error', '不明なエラー')}"
    
    def research(self, topic: str) -> str:
        """リサーチャーに調査を依頼"""
        return self.ask("researcher", f"以下のトピックについて調査してください: {topic}")
    
    def generate_code(self, description: str, language: str = "Python") -> str:
        """コーダーにコード生成を依頼"""
        return self.ask("coder", f"{language}で以下の機能を実装してください: {description}")
    
    def analyze_data(self, data_description: str) -> str:
        """アナライザーにデータ分析を依頼"""
        return self.ask("analyzer", f"以下のデータを分析してください: {data_description}")
    
    def write_document(self, topic: str, style: str = "formal") -> str:
        """ライターに文書作成を依頼"""
        return self.ask("writer", f"{style}なスタイルで以下について文書を作成してください: {topic}")
    
    def team_work(self, task: str, agents: Optional[list] = None) -> Dict[str, Any]:
        """
        複数のエージェントに協力してもらう
        
        Args:
            task: タスク内容
            agents: 協力するエージェントのリスト（省略時は全員）
            
        Returns:
            協力作業の結果
        """
        if agents is None:
            agents = ["researcher", "coder", "analyzer", "writer"]
            
        return self.manager.collaborate(
            agent_names=agents,
            task=task,
            orchestrator_instructions="各エージェントの結果を統合して、最終的な回答を作成してください。"
        )
    
    def create_custom_agent(
        self,
        name: str,
        role: str,
        instructions: str,
        model: str = "gpt-4"
    ) -> bool:
        """
        カスタムエージェントを作成
        
        Args:
            name: エージェント名
            role: 役割
            instructions: 詳細な指示
            model: 使用するモデル
            
        Returns:
            成功したかどうか
        """
        try:
            self.manager.create_agent(name, role, instructions, model)
            print(f"✅ カスタムエージェント '{name}' を作成しました!")
            return True
        except Exception as e:
            print(f"❌ エージェント作成失敗: {e}")
            return False
    
    def list_agents(self) -> list:
        """利用可能なエージェントのリストを取得"""
        return self.manager.list_agents()
    
    def save(self, filepath: str = "/root/manaos_agents/trinity_agents.json"):
        """エージェントの状態を保存"""
        self.manager.save_state(filepath)
        print(f"💾 状態を保存しました: {filepath}")
        
    def load(self, filepath: str = "/root/manaos_agents/trinity_agents.json"):
        """エージェントの状態を読み込み"""
        if self.manager.load_state(filepath):
            print(f"📂 状態を読み込みました: {filepath}")
            return True
        else:
            print(f"⚠️  状態ファイルが見つかりません: {filepath}")
            return False


# === 便利な関数（Trinityがimportして使える） ===

def quick_ask(agent: str, question: str) -> str:
    """最速で質問できる関数"""
    interface = TrinityAgentInterface()
    return interface.ask(agent, question)


def quick_research(topic: str) -> str:
    """すぐにリサーチ"""
    interface = TrinityAgentInterface()
    return interface.research(topic)


def quick_code(description: str, language: str = "Python") -> str:
    """すぐにコード生成"""
    interface = TrinityAgentInterface()
    return interface.generate_code(description, language)


def quick_analyze(data: str) -> str:
    """すぐにデータ分析"""
    interface = TrinityAgentInterface()
    return interface.analyze_data(data)


def quick_write(topic: str) -> str:
    """すぐに文書作成"""
    interface = TrinityAgentInterface()
    return interface.write_document(topic)


# === インタラクティブモード ===

def interactive_mode():
    """対話モードで使う"""
    print("\n" + "="*60)
    print("🌟 Trinity Agent Interface - インタラクティブモード")
    print("="*60)
    
    interface = TrinityAgentInterface()
    
    print("\n利用可能なエージェント:")
    for agent in interface.list_agents():
        print(f"  📋 {agent['name']}: {agent['role']}")
    
    print("\nコマンド:")
    print("  ask <エージェント名> <質問>  - エージェントに質問")
    print("  research <トピック>          - リサーチを依頼")
    print("  code <説明>                  - コード生成を依頼")
    print("  analyze <データ>             - データ分析を依頼")
    print("  write <トピック>             - 文書作成を依頼")
    print("  team <タスク>                - チームで協力")
    print("  list                         - エージェント一覧")
    print("  save                         - 状態保存")
    print("  load                         - 状態読み込み")
    print("  exit                         - 終了")
    
    while True:
        try:
            print("\n" + "-"*60)
            command = input("🌟 Trinity> ").strip()
            
            if not command:
                continue
                
            if command == "exit":
                print("👋 またね!")
                break
                
            elif command == "list":
                print("\n利用可能なエージェント:")
                for agent in interface.list_agents():
                    print(f"  📋 {agent['name']}: {agent['role']}")
                    
            elif command == "save":
                interface.save()
                
            elif command == "load":
                interface.load()
                
            elif command.startswith("ask "):
                parts = command[4:].split(" ", 1)
                if len(parts) == 2:
                    agent_name, question = parts
                    print(f"\n💭 {agent_name}に質問中...")
                    answer = interface.ask(agent_name, question)
                    print(f"\n✨ 回答:\n{answer}")
                else:
                    print("❌ 使い方: ask <エージェント名> <質問>")
                    
            elif command.startswith("research "):
                topic = command[9:]
                print(f"\n🔍 {topic}について調査中...")
                result = interface.research(topic)
                print(f"\n✨ 調査結果:\n{result}")
                
            elif command.startswith("code "):
                description = command[5:]
                print("\n💻 コード生成中...")
                code = interface.generate_code(description)
                print(f"\n✨ 生成されたコード:\n{code}")
                
            elif command.startswith("analyze "):
                data = command[8:]
                print("\n📊 データ分析中...")
                analysis = interface.analyze_data(data)
                print(f"\n✨ 分析結果:\n{analysis}")
                
            elif command.startswith("write "):
                topic = command[6:]
                print("\n📝 文書作成中...")
                document = interface.write_document(topic)
                print(f"\n✨ 作成された文書:\n{document}")
                
            elif command.startswith("team "):
                task = command[5:]
                print("\n👥 チームで協力して作業中...")
                result = interface.team_work(task)
                if result.get("integrated_result"):
                    print(f"\n✨ 統合結果:\n{result['integrated_result']}")
                else:
                    print("\n✨ 各エージェントの結果:")
                    for r in result.get("results", []):
                        if r.get("success"):
                            print(f"\n【{r['agent']}】\n{r['result']}")
            else:
                print("❌ 不明なコマンドです。'exit'で終了、'list'でエージェント一覧を表示します。")
                
        except KeyboardInterrupt:
            print("\n\n👋 中断されました。またね!")
            break
        except Exception as e:
            print(f"\n❌ エラー: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        interactive_mode()
    else:
        # デモ実行
        print("\n🌟 Trinity Agent Interface - デモモード\n")
        print("インタラクティブモードで起動するには:")
        print("  python3 trinity_interface.py interactive")
        print("\nPythonから使う例:")
        print("""
from trinity_interface import TrinityAgentInterface

interface = TrinityAgentInterface()

# 簡単に質問
answer = interface.ask("researcher", "量子コンピューターとは？")
print(answer)

# リサーチを依頼
result = interface.research("AI技術の最新トレンド")
print(result)

# コード生成
code = interface.generate_code("ファイルを読み込んでJSON形式で保存する")
print(code)
        """)

