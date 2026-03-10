#!/usr/bin/env python3
"""
ManaOS Agents - 基本的な使い方のサンプル
Trinity達が参考にできる実用例
"""

import sys
sys.path.insert(0, '/root/manaos_agents')

from trinity_interface import TrinityAgentInterface, quick_ask, quick_research, quick_code

def example1_simple_question():
    """例1: シンプルな質問"""
    print("\n" + "="*60)
    print("例1: シンプルな質問")
    print("="*60)
    
    interface = TrinityAgentInterface()
    
    # Researcherに質問
    answer = interface.ask("researcher", "Pythonの最新バージョンと新機能について教えてください")
    print(f"\n📝 回答:\n{answer}")


def example2_code_generation():
    """例2: コード生成"""
    print("\n" + "="*60)
    print("例2: コード生成")
    print("="*60)
    
    interface = TrinityAgentInterface()
    
    # Coderにコード生成を依頼
    code = interface.generate_code(
        "CSVファイルを読み込んで、各列の統計情報（平均、最大、最小）を表示する関数",
        language="Python"
    )
    print(f"\n💻 生成されたコード:\n{code}")


def example3_team_collaboration():
    """例3: チームで協力"""
    print("\n" + "="*60)
    print("例3: チームで協力")
    print("="*60)
    
    interface = TrinityAgentInterface()
    
    # 複数のエージェントで協力
    result = interface.team_work(
        "Webスクレイピングツールを作成するプロジェクトを計画してください。要件定義、技術選定、実装計画を含めてください。",
        agents=["researcher", "coder", "writer"]
    )
    
    print(f"\n🤝 統合結果:\n{result.get('integrated_result', 'N/A')}")


def example4_custom_agent():
    """例4: カスタムエージェント作成"""
    print("\n" + "="*60)
    print("例4: カスタムエージェント作成")
    print("="*60)
    
    interface = TrinityAgentInterface()
    
    # カスタムエージェントを作成
    interface.create_custom_agent(
        name="japanese_teacher",
        role="日本語教師",
        instructions="""
        あなたは経験豊富な日本語教師です。
        日本語学習者に分かりやすく、丁寧に日本語を教えてください。
        文法、語彙、表現を具体例を交えて説明してください。
        """
    )
    
    # 使用
    lesson = interface.ask("japanese_teacher", "「は」と「が」の違いを教えてください")
    print(f"\n📚 レッスン:\n{lesson}")


def example5_quick_functions():
    """例5: クイック関数（一行で実行）"""
    print("\n" + "="*60)
    print("例5: クイック関数（一行で実行）")
    print("="*60)
    
    # 一行で質問
    answer = quick_ask("researcher", "機械学習とディープラーニングの違いは？")
    print(f"\n💡 quick_ask:\n{answer[:200]}...")
    
    # 一行でリサーチ
    research = quick_research("量子コンピューター")
    print(f"\n🔍 quick_research:\n{research[:200]}...")
    
    # 一行でコード生成
    code = quick_code("FizzBuzzを実装して")
    print(f"\n⚡ quick_code:\n{code[:200]}...")


def example6_save_and_load():
    """例6: 状態の保存と読み込み"""
    print("\n" + "="*60)
    print("例6: 状態の保存と読み込み")
    print("="*60)
    
    interface = TrinityAgentInterface()
    
    # カスタムエージェントを作成
    interface.create_custom_agent(
        name="mana_assistant",
        role="Mana専用アシスタント",
        instructions="ManaOSの運用とTrinityのサポートを行います"
    )
    
    # 状態を保存
    print("\n💾 状態を保存中...")
    interface.save()
    
    # 新しいインターフェースで読み込み
    print("\n📂 新しいインターフェースで読み込み中...")
    interface2 = TrinityAgentInterface()
    interface2.load()
    
    # 保存したエージェントを使用
    if interface2.get_agent("mana_assistant"):  # type: ignore
        print("\n✅ カスタムエージェントが正しく復元されました!")
    else:
        print("\n❌ カスタムエージェントの復元に失敗")


def main():
    """メイン関数 - 全ての例を実行"""
    print("\n🌟 ManaOS Agents - 基本的な使い方のサンプル")
    print("="*60)
    print("注意: OpenAI APIキーが設定されている必要があります")
    print("     export OPENAI_API_KEY='your-key-here'")
    print("="*60)
    
    try:
        # 実行する例を選択（APIコスト削減のため）
        print("\n実行する例を選んでください:")
        print("  1. シンプルな質問")
        print("  2. コード生成")
        print("  3. チームで協力")
        print("  4. カスタムエージェント作成")
        print("  5. クイック関数")
        print("  6. 状態の保存と読み込み")
        print("  all. 全て実行（APIコストがかかります）")
        print("  demo. デモモード（API呼び出しなし）")
        
        choice = input("\n選択 (1-6/all/demo): ").strip()
        
        if choice == "1":
            example1_simple_question()
        elif choice == "2":
            example2_code_generation()
        elif choice == "3":
            example3_team_collaboration()
        elif choice == "4":
            example4_custom_agent()
        elif choice == "5":
            example5_quick_functions()
        elif choice == "6":
            example6_save_and_load()
        elif choice == "all":
            print("\n⚠️  全ての例を実行します（APIコストがかかります）")
            confirm = input("続行しますか？ (yes/no): ").strip().lower()
            if confirm == "yes":
                example1_simple_question()
                example2_code_generation()
                example3_team_collaboration()
                example4_custom_agent()
                example5_quick_functions()
                example6_save_and_load()
        elif choice == "demo":
            print("\n🎬 デモモード:")
            print("  - Trinity Interface初期化")
            interface = TrinityAgentInterface()
            print("\n  - エージェント一覧:")
            for agent in interface.list_agents():
                print(f"    ✓ {agent['name']}: {agent['role']}")
            print("\n✅ デモ完了!")
        else:
            print("❌ 無効な選択です")
            
        print("\n✨ サンプル実行完了!")
        
    except KeyboardInterrupt:
        print("\n\n👋 中断されました")
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

