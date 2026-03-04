#!/usr/bin/env python3
"""
ManaSearch Nexus Helper
トリニティやCursorから簡単に呼び出せるヘルパー関数
"""
import httpx
import asyncio
from typing import Optional, Dict, Any, List


MANASEARCH_URL = "http://localhost:9111"


async def manasearch(
    query: str,
    use_web: bool = True,
    models: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    ManaSearch Nexus で検索
    
    使用例:
        result = await manasearch("AI技術トレンド")
        print(result["summary"])
    
    Args:
        query: 検索クエリ
        use_web: Web検索を含めるか
        models: 使用するAIモデル（デフォルト: 全て）
    
    Returns:
        検索結果の辞書
    """
    if models is None:
        models = ["remi", "luna", "mina"]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{MANASEARCH_URL}/search",
            json={
                "query": query,
                "options": {
                    "web_search": use_web,
                    "ai_models": models,
                    "confidence_threshold": 0.7
                }
            }
        )
        response.raise_for_status()
        return response.json()


def manasearch_sync(
    query: str,
    use_web: bool = True,
    models: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    ManaSearch Nexus で検索（同期版）
    
    使用例:
        result = manasearch_sync("AI技術トレンド")
        print(result["summary"])
    """
    return asyncio.run(manasearch(query, use_web, models))


async def manasearch_quick(query: str) -> str:
    """
    ManaSearch Nexus クイック検索
    
    統合回答のみを返す簡易版
    
    使用例:
        answer = await manasearch_quick("Pythonの非同期プログラミング")
        print(answer)
    """
    result = await manasearch(query)
    return result.get("summary", "")


def manasearch_quick_sync(query: str) -> str:
    """ManaSearch Nexus クイック検索（同期版）"""
    return asyncio.run(manasearch_quick(query))


# トリニティ専用インターフェース
class ManaSearchForTrinity:
    """トリニティ専用のManaSearchインターフェース"""
    
    @staticmethod
    async def search_by_remi(query: str) -> str:
        """Remiから呼び出し"""
        result = await manasearch(query, use_web=True, models=["remi", "luna", "mina"])
        return format_for_trinity(result, "remi")
    
    @staticmethod
    async def search_by_luna(query: str) -> str:
        """Lunaから呼び出し"""
        result = await manasearch(query, use_web=True, models=["remi", "luna", "mina"])
        return format_for_trinity(result, "luna")
    
    @staticmethod
    async def search_by_mina(query: str) -> str:
        """Minaから呼び出し"""
        result = await manasearch(query, use_web=True, models=["remi", "luna", "mina"])
        return format_for_trinity(result, "mina")


def format_for_trinity(result: Dict[str, Any], caller: str) -> str:
    """トリニティ向けフォーマット"""
    query = result.get("query", "")
    summary = result.get("summary", "")
    confidence = result.get("confidence_score", 0.0)
    
    output = f"""
【{caller.upper()}からManaSearch Nexus検索】

質問: {query}
信頼スコア: {confidence:.0%}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 統合回答:
{summary}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 各AIの見解:
"""
    
    for model, resp in result.get("ai_responses", {}).items():
        answer = resp.get("answer", "")
        output += f"\n{model.upper()}: {answer[:150]}...\n"
    
    web_results = result.get("web_results", [])
    if web_results:
        output += "\n🌐 Web検索結果:\n"
        for i, wr in enumerate(web_results[:3], 1):
            output += f"{i}. {wr.get('title', '')}\n"
    
    return output


# 簡易使用例
if __name__ == "__main__":
    print("🔍 ManaSearch Nexus Helper - 使用例\n")
    
    # 同期版
    print("【同期版】")
    result = manasearch_sync("Pythonとは")
    print(f"信頼スコア: {result['confidence_score']:.0%}")
    print(f"回答: {result['summary'][:100]}...\n")
    
    # クイック版
    print("【クイック版】")
    answer = manasearch_quick_sync("JavaScriptとは")
    print(answer[:200] + "...")



