#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
スマートプロンプト生成ツール
Brave Search APIとBase AI APIを活用して高品質なプロンプトを生成
"""

import sys
import io
from pathlib import Path
from dotenv import load_dotenv

# Windowsでのエンコーディング問題を回避
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

# 環境変数を読み込む
load_dotenv(Path(__file__).parent / '.env')

# ManaOS Core APIをインポート
try:
    from manaos_core_api import ManaOSCoreAPI
    MANAOS_AVAILABLE = True
except ImportError:
    MANAOS_AVAILABLE = False
    print("[ERROR] ManaOS Core APIが利用できません")
    sys.exit(1)

def search_prompt_references(query: str, count: int = 5):
    """Brave Search APIでプロンプトの参考資料を検索"""
    print(f"\n[検索] '{query}' を検索中...")
    
    try:
        manaos = ManaOSCoreAPI()
        result = manaos.act("brave_search", {
            "query": query,
            "count": count,
            "search_lang": "jp"
        })
        
        if result.get("status") == "success" and result.get("results"):
            print(f"[検索] {len(result['results'])}件の結果を取得")
            references = []
            for i, item in enumerate(result["results"], 1):
                title = item.get("title", "")
                url = item.get("url", "")
                description = item.get("description", "")[:100]
                references.append({
                    "title": title,
                    "url": url,
                    "description": description
                })
                print(f"  {i}. {title}")
                if description:
                    print(f"     {description}...")
            return references
        else:
            print("[検索] 結果が見つかりませんでした")
            return []
    except Exception as e:
        print(f"[ERROR] Brave Searchエラー: {e}")
        return []

def generate_prompt_with_ai(theme: str, style: str = "", references: list = None):  # type: ignore
    """Base AI APIでプロンプトを生成"""
    print(f"\n[AI] プロンプト生成中...")
    
    # 参考資料をプロンプトに含める
    reference_text = ""
    if references:
        reference_text = "\n参考資料:\n"
        for ref in references[:3]:
            reference_text += f"- {ref['title']}\n"
    
    prompt = f"""以下のテーマで画像生成プロンプトを作成してください。

テーマ: {theme}
スタイル: {style if style else "指定なし"}
{reference_text}

要件:
- 詳細で具体的なプロンプト
- 高品質な画像が生成されるように最適化
- 英語で記述
- プロンプトのみを返してください（説明不要）

プロンプト:"""
    
    try:
        manaos = ManaOSCoreAPI()
        result = manaos.act("base_ai_chat", {
            "prompt": prompt,
            "use_free": True
        })
        
        if result.get("result") and result["result"].get("response"):
            generated = result["result"]["response"].strip()
            # プロンプトのみを抽出
            if "プロンプト:" in generated:
                generated = generated.split("プロンプト:", 1)[1].strip()
            if generated.startswith('"') and generated.endswith('"'):
                generated = generated[1:-1]
            
            print("[AI] プロンプト生成完了")
            return generated
    except Exception as e:
        print(f"[ERROR] Base AIエラー: {e}")
    
    return None

def improve_prompt_with_ai(prompt: str):
    """Base AI APIでプロンプトを改善"""
    print(f"\n[AI] プロンプト改善中...")
    
    improvement_prompt = f"""以下の画像生成プロンプトを改善してください。
より詳細で、高品質な画像が生成されるようにプロンプトを最適化してください。

元のプロンプト:
{prompt}

改善されたプロンプトのみを返してください（説明不要）:"""
    
    try:
        manaos = ManaOSCoreAPI()
        result = manaos.act("base_ai_chat", {
            "prompt": improvement_prompt,
            "use_free": True
        })
        
        if result.get("result") and result["result"].get("response"):
            improved = result["result"]["response"].strip()
            # プロンプトのみを抽出
            if "改善されたプロンプト:" in improved:
                improved = improved.split("改善されたプロンプト:", 1)[1].strip()
            if improved.startswith('"') and improved.endswith('"'):
                improved = improved[1:-1]
            
            print("[AI] プロンプト改善完了")
            return improved
    except Exception as e:
        print(f"[ERROR] Base AIエラー: {e}")
    
    return prompt

def main():
    """メイン処理"""
    print("=" * 70)
    print("スマートプロンプト生成ツール")
    print("Brave Search APIとBase AI APIを活用")
    print("=" * 70)
    print()
    
    # モード選択
    print("モードを選択してください:")
    print("  1. 新規プロンプト生成（検索 + AI生成）")
    print("  2. 既存プロンプト改善（AI改善）")
    print("  3. 参考資料検索のみ")
    
    mode = input("\nモード (1-3): ").strip()
    
    if mode == "1":
        # 新規プロンプト生成
        theme = input("\nテーマを入力してください: ").strip()
        if not theme:
            print("[ERROR] テーマが入力されていません")
            return
        
        style = input("スタイル（オプション）: ").strip()
        
        # 参考資料を検索
        search_query = f"{theme} {style} stable diffusion prompt" if style else f"{theme} stable diffusion prompt"
        references = search_prompt_references(search_query)
        
        # AIでプロンプト生成
        prompt = generate_prompt_with_ai(theme, style, references)
        
        if prompt:
            print("\n" + "=" * 70)
            print("生成されたプロンプト:")
            print("=" * 70)
            print(prompt)
            print("=" * 70)
            
            # 改善するか確認
            improve = input("\nこのプロンプトを改善しますか？ (y/n): ").lower() == 'y'
            if improve:
                improved = improve_prompt_with_ai(prompt)
                if improved != prompt:
                    print("\n" + "=" * 70)
                    print("改善されたプロンプト:")
                    print("=" * 70)
                    print(improved)
                    print("=" * 70)
    
    elif mode == "2":
        # 既存プロンプト改善
        prompt = input("\n改善するプロンプトを入力してください: ").strip()
        if not prompt:
            print("[ERROR] プロンプトが入力されていません")
            return
        
        improved = improve_prompt_with_ai(prompt)
        
        if improved != prompt:
            print("\n" + "=" * 70)
            print("改善されたプロンプト:")
            print("=" * 70)
            print(improved)
            print("=" * 70)
        else:
            print("\n[INFO] プロンプトは変更されませんでした")
    
    elif mode == "3":
        # 参考資料検索のみ
        query = input("\n検索クエリを入力してください: ").strip()
        if not query:
            print("[ERROR] 検索クエリが入力されていません")
            return
        
        references = search_prompt_references(query)
        
        if references:
            print("\n" + "=" * 70)
            print("検索結果:")
            print("=" * 70)
            for i, ref in enumerate(references, 1):
                print(f"\n{i}. {ref['title']}")
                print(f"   URL: {ref['url']}")
                if ref['description']:
                    print(f"   {ref['description']}")
    
    else:
        print("[ERROR] 無効なモードです")

if __name__ == "__main__":
    main()

