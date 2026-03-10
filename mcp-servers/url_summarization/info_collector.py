#!/usr/bin/env python3
"""
自動情報収集システム
検索結果から自動で情報収集・要約
"""

import anthropic
import os
from typing import Dict, List
from datetime import datetime
from search_integration import SearchIntegration
from web_scraper import WebScraper


class InfoCollector:
    """自動情報収集システム"""
    
    def __init__(self):
        self.search = SearchIntegration()
        self.web_scraper = WebScraper()
        
        # Claude API
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.claude_client = anthropic.Anthropic(api_key=api_key) if api_key else None
    
    def collect_and_summarize(self, query: str, max_results: int = 5) -> Dict:
        """検索→収集→要約"""
        try:
            # 1. 検索実行
            print(f"🔍 検索中: {query}")
            search_result = self.search.search_multiple(query, count=max_results * 2)
            
            if not search_result["success"]:
                return {"success": False, "error": "検索失敗"}
            
            # 2. 各URLから情報取得
            print(f"📥 情報収集中... ({len(search_result['results']['combined'])}件)")
            articles = []
            
            for i, item in enumerate(search_result["results"]["combined"][:max_results]):
                print(f"  [{i+1}/{max_results}] {item['title']}")
                
                try:
                    # Webスクレイピング
                    scraped = self.web_scraper.scrape(item["url"])
                    
                    if scraped["success"]:
                        articles.append({
                            "title": scraped["title"],
                            "url": item["url"],
                            "content": scraped["content"][:2000],  # 最初の2000文字
                            "word_count": scraped["word_count"]
                        })
                except Exception as e:
                    print(f"    ❌ エラー: {e}")
                    continue
            
            # 3. AI要約
            if articles and self.claude_client:
                print("🤖 AI要約中...")
                summary = self._generate_summary(query, articles)
            else:
                summary = "AI要約は利用できません"
            
            return {
                "success": True,
                "query": query,
                "articles": articles,
                "summary": summary,
                "total_articles": len(articles),
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_summary(self, query: str, articles: List[Dict]) -> str:
        """AI要約生成"""
        try:
            # コンテキスト作成
            context = f"検索クエリ: {query}\n\n"
            context += f"以下の{len(articles)}件の記事を要約してください:\n\n"
            
            for i, article in enumerate(articles, 1):
                context += f"【記事{i}】{article['title']}\n"
                context += f"{article['content']}\n\n"
            
            prompt = f"""{context}

上記の記事を基に、検索クエリ「{query}」について以下の形式で要約してください:

## 総合要約
（全体の要点を3-5つのポイントで）

## 主要な発見
（重要な情報・データ）

## トレンド・傾向
（見られる傾向や変化）

## 参考情報
（参考になる情報源）"""

            response = self.claude_client.messages.create(  # type: ignore[union-attr]
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            return response.content[0].text  # type: ignore
        
        except Exception as e:
            return f"要約生成エラー: {str(e)}"
    
    def competitive_analysis(self, companies: List[str]) -> Dict:
        """競合分析"""
        try:
            results = {}
            
            for company in companies:
                query = f"{company} 戦略 価格"
                print(f"🔍 {company}の情報収集中...")
                
                result = self.collect_and_summarize(query, max_results=5)
                results[company] = result
            
            return {
                "success": True,
                "companies": results,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def news_monitoring(self, keywords: List[str], max_results: int = 5) -> Dict:
        """ニュース監視"""
        try:
            results = {}
            
            for keyword in keywords:
                query = f"{keyword} 最新 ニュース"
                print(f"📰 {keyword}のニュース収集中...")
                
                result = self.collect_and_summarize(query, max_results=max_results)
                results[keyword] = result
            
            return {
                "success": True,
                "keywords": results,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}

