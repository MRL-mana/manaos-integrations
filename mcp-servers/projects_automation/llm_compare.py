#!/usr/bin/env python3
"""
🔬 LLMモデル比較ツール
複数のモデルで同じ質問を試して性能を比較
"""

import requests
import time
import sys

class LLMCompare:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        
    def get_available_models(self):
        """利用可能なモデル一覧を取得"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except requests.RequestException:
            return []
    
    def ask_model(self, model_name, question):
        """特定のモデルに質問"""
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={'model': model_name, 'prompt': question, 'stream': False},
                timeout=120
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'response': data.get('response', ''),
                    'time': elapsed,
                    'tokens': data.get('eval_count', 0)
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'time': elapsed
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'time': 0
            }
    
    def compare_models(self, question, models=None):
        """複数のモデルで同じ質問を比較"""
        if models is None:
            models = self.get_available_models()
        
        if not models:
            print("❌ 利用可能なモデルがありません")
            return
        
        print(f"\n📝 質問: {question}\n")
        print("=" * 70)
        
        results = []
        
        for model in models:
            print(f"\n🤖 {model} に質問中...")
            result = self.ask_model(model, question)
            
            if result['success']:
                print(f"⏱️  応答時間: {result['time']:.2f}秒")
                print(f"📊 トークン数: {result['tokens']}")
                print(f"\n💬 応答:\n{result['response']}\n")
                print("-" * 70)
                
                results.append({
                    'model': model,
                    'time': result['time'],
                    'tokens': result['tokens'],
                    'response': result['response']
                })
            else:
                print(f"❌ エラー: {result['error']}\n")
                print("-" * 70)
        
        # サマリー表示
        if results:
            print("\n" + "=" * 70)
            print("📊 パフォーマンスサマリー")
            print("=" * 70)
            
            # 応答時間でソート
            sorted_by_time = sorted(results, key=lambda x: x['time'])
            
            print("\n⚡ 最速モデル:")
            fastest = sorted_by_time[0]
            print(f"  {fastest['model']}: {fastest['time']:.2f}秒")
            
            print("\n📊 全モデル比較:")
            for i, r in enumerate(sorted_by_time, 1):
                print(f"  {i}. {r['model']:<20} {r['time']:>6.2f}秒  {r['tokens']:>5}トークン")
            
            print("\n" + "=" * 70)
        
        return results
    
    def interactive_mode(self):
        """対話モード"""
        print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║         🔬 LLMモデル比較ツール v1.0 🔬                       ║
║                                                                ║
║           複数モデルで同じ質問を試して性能比較                 ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
        """)
        
        models = self.get_available_models()
        
        if not models:
            print("❌ 利用可能なモデルがありません")
            return
        
        print(f"\n📋 利用可能なモデル ({len(models)}個):")
        for i, model in enumerate(models, 1):
            print(f"  {i}. {model}")
        
        print("\n💡 使い方:")
        print("  • 質問を入力すると、全モデルで比較します")
        print("  • 'exit' で終了")
        print("")
        
        while True:
            try:
                question = input("\n🔬 質問を入力してください > ").strip()
                
                if not question:
                    continue
                
                if question.lower() in ['exit', 'quit', 'q']:
                    print("\n👋 終了します\n")
                    break
                
                self.compare_models(question, models)
                
            except KeyboardInterrupt:
                print("\n\n👋 終了します\n")
                break
            except Exception as e:
                print(f"\n❌ エラー: {e}\n")

def main():
    compare = LLMCompare()
    
    if len(sys.argv) > 1:
        # コマンドライン引数から質問
        question = ' '.join(sys.argv[1:])
        compare.compare_models(question)
    else:
        # 対話モード
        compare.interactive_mode()

if __name__ == '__main__':
    main()

