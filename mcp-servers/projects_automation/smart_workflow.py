#!/usr/bin/env python3
"""
🧠 スマートワークフローシステム
AIを活用した賢い作業自動化
"""

import requests
from datetime import datetime
import sys

class SmartWorkflow:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.best_model = "llama3.2:3b"  # デフォルトは最速モデル
        
    def ask_ai(self, prompt, model=None):
        """AIに質問"""
        if model is None:
            model = self.best_model
            
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={'model': model, 'prompt': prompt, 'stream': False},
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json().get('response', '')
            return None
        except requests.RequestException:
            return None
    
    def code_generator(self, description):
        """AIコード生成"""
        print("🤖 AIがコードを生成中...\n")
        
        prompt = f"""以下の機能を実装するPythonコードを書いてください:
{description}

要件:
- シンプルで読みやすいコード
- コメント付き
- エラーハンドリング込み

コードのみを出力してください。"""
        
        code = self.ask_ai(prompt, "llama3.1:8b")  # 大型モデル使用
        
        if code:
            print("=" * 70)
            print("生成されたコード:")
            print("=" * 70)
            print(code)
            print("=" * 70)
            
            # ファイルに保存
            filename = f"/root/generated_code_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(code)
            
            print(f"\n💾 コード保存: {filename}")
            return code
        else:
            print("❌ コード生成失敗")
            return None
    
    def document_generator(self, topic):
        """AIドキュメント生成"""
        print("📝 AIがドキュメントを生成中...\n")
        
        prompt = f"""以下のトピックについて、詳細なドキュメントを書いてください:
{topic}

要件:
- わかりやすい説明
- 具体例を含む
- 実用的な内容

マークダウン形式で出力してください。"""
        
        doc = self.ask_ai(prompt, "gemma2:9b")  # 最詳細モデル使用
        
        if doc:
            print("=" * 70)
            print("生成されたドキュメント:")
            print("=" * 70)
            print(doc)
            print("=" * 70)
            
            # ファイルに保存
            filename = f"/root/generated_doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# {topic}\n\n")
                f.write(doc)
            
            print(f"\n💾 ドキュメント保存: {filename}")
            return doc
        else:
            print("❌ ドキュメント生成失敗")
            return None
    
    def command_explainer(self, command):
        """コマンドを日本語で説明"""
        print(f"💡 コマンド '{command}' を説明中...\n")
        
        prompt = f"""以下のコマンドを初心者にもわかるように日本語で説明してください:
{command}

要件:
- 何をするコマンドか
- 各オプションの意味
- 使用例
- 注意点

わかりやすく説明してください。"""
        
        explanation = self.ask_ai(prompt, "qwen2.5:3b")
        
        if explanation:
            print("=" * 70)
            print(explanation)
            print("=" * 70)
            return explanation
        else:
            print("❌ 説明生成失敗")
            return None
    
    def error_analyzer(self, error_message):
        """エラーメッセージを解析して解決策を提案"""
        print("🔍 エラーを分析中...\n")
        
        prompt = f"""以下のエラーメッセージを解析して、原因と解決策を提案してください:
{error_message}

要件:
- エラーの原因
- 解決方法（具体的なコマンド含む）
- 予防方法

実用的なアドバイスをお願いします。"""
        
        analysis = self.ask_ai(prompt, "llama3.1:8b")
        
        if analysis:
            print("=" * 70)
            print("エラー分析結果:")
            print("=" * 70)
            print(analysis)
            print("=" * 70)
            return analysis
        else:
            print("❌ 分析失敗")
            return None
    
    def meeting_note_summarizer(self, notes):
        """会議メモを要約"""
        print("📋 会議メモを要約中...\n")
        
        prompt = f"""以下の会議メモを要約してください:
{notes}

要件:
- 主要なポイント
- 決定事項
- アクションアイテム
- 次のステップ

構造化された要約をお願いします。"""
        
        summary = self.ask_ai(prompt, "gemma2:9b")
        
        if summary:
            print("=" * 70)
            print("会議メモ要約:")
            print("=" * 70)
            print(summary)
            print("=" * 70)
            
            # ファイルに保存
            filename = f"/root/meeting_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("# 会議メモ要約\n")
                f.write(f"日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(summary)
            
            print(f"\n💾 要約保存: {filename}")
            return summary
        else:
            print("❌ 要約失敗")
            return None
    
    def ai_tutor(self, topic):
        """AIが先生になって教える"""
        print(f"👨‍🏫 AIチューターモード: {topic}\n")
        
        prompt = f"""あなたは優しい先生です。以下のトピックについて、初心者にもわかるように教えてください:
{topic}

要件:
- 基礎から丁寧に説明
- 具体例を使う
- 理解しやすい比喩を使う
- ステップバイステップで説明

わかりやすく教えてください。"""
        
        lesson = self.ask_ai(prompt, "gemma2:9b")
        
        if lesson:
            print("=" * 70)
            print("📚 レッスン:")
            print("=" * 70)
            print(lesson)
            print("=" * 70)
            return lesson
        else:
            print("❌ レッスン生成失敗")
            return None
    
    def brainstorm(self, theme):
        """アイデアをブレインストーミング"""
        print(f"💡 ブレインストーミング中: {theme}\n")
        
        prompt = f"""以下のテーマについて、創造的なアイデアを10個提案してください:
{theme}

要件:
- ユニークなアイデア
- 実現可能性も考慮
- 具体的な説明
- 番号付きリスト

革新的なアイデアをお願いします。"""
        
        ideas = self.ask_ai(prompt, "llama3.1:8b")
        
        if ideas:
            print("=" * 70)
            print("💡 ブレインストーミング結果:")
            print("=" * 70)
            print(ideas)
            print("=" * 70)
            
            # ファイルに保存
            filename = f"/root/brainstorm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# ブレインストーミング: {theme}\n\n")
                f.write(ideas)
            
            print(f"\n💾 アイデア保存: {filename}")
            return ideas
        else:
            print("❌ ブレインストーミング失敗")
            return None

def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║         🧠 スマートワークフローシステム v1.0 🧠             ║
║                                                                ║
║              AIを活用した賢い作業自動化                        ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    workflow = SmartWorkflow()
    
    if len(sys.argv) < 2:
        print("使い方:")
        print("  code <説明>      - コード生成")
        print("  doc <トピック>   - ドキュメント生成")
        print("  explain <コマンド> - コマンド説明")
        print("  error <エラー>   - エラー分析")
        print("  summarize <メモ> - 会議メモ要約")
        print("  teach <トピック> - AIチューター")
        print("  brainstorm <テーマ> - ブレインストーミング")
        print("")
        print("例:")
        print("  python3 smart_workflow.py code 'CSVファイルを読み込んで平均を計算'")
        print("  python3 smart_workflow.py teach 'Pythonの基礎'")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'code' and len(sys.argv) > 2:
        description = ' '.join(sys.argv[2:])
        workflow.code_generator(description)
        
    elif command == 'doc' and len(sys.argv) > 2:
        topic = ' '.join(sys.argv[2:])
        workflow.document_generator(topic)
        
    elif command == 'explain' and len(sys.argv) > 2:
        cmd = ' '.join(sys.argv[2:])
        workflow.command_explainer(cmd)
        
    elif command == 'error' and len(sys.argv) > 2:
        error = ' '.join(sys.argv[2:])
        workflow.error_analyzer(error)
        
    elif command == 'summarize' and len(sys.argv) > 2:
        notes = ' '.join(sys.argv[2:])
        workflow.meeting_note_summarizer(notes)
        
    elif command == 'teach' and len(sys.argv) > 2:
        topic = ' '.join(sys.argv[2:])
        workflow.ai_tutor(topic)
        
    elif command == 'brainstorm' and len(sys.argv) > 2:
        theme = ' '.join(sys.argv[2:])
        workflow.brainstorm(theme)
        
    else:
        print(f"❌ 不明なコマンド: {command}")
        print("使い方を確認してください")

if __name__ == '__main__':
    main()

