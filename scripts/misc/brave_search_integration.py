#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brave Search API統合モジュール
"""

import os
import requests
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class BraveSearchResult:
    """Brave Search結果"""
    title: str
    url: str
    description: str
    age: Optional[str] = None
    meta_url: Optional[Dict[str, str]] = None

class BraveSearchIntegration:
    """Brave Search API統合"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初期化
        
        Args:
            api_key: Brave Search APIキー（Noneの場合は環境変数から取得）
        """
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        self.base_url = "https://api.search.brave.com/res/v1"
        
        if not self.api_key:
            logger.warning("BRAVE_API_KEYが設定されていません")
    
    def is_available(self) -> bool:
        """APIが利用可能か確認"""
        return self.api_key is not None and len(self.api_key) > 0
    
    def search(
        self,
        query: str,
        count: int = 10,
        search_lang: str = "jp",  # Brave Search APIは'jp'を使用（'ja'ではない）
        country: str = "JP",
        safesearch: str = "moderate",
        freshness: Optional[str] = None,
        text_decorations: bool = True,
        spellcheck: bool = True
    ) -> List[BraveSearchResult]:
        """
        Web検索を実行
        
        Args:
            query: 検索クエリ
            count: 取得件数（デフォルト: 10、最大: 20）
            search_lang: 検索言語（デフォルト: ja）
            country: 国コード（デフォルト: JP）
            safesearch: セーフサーチ設定（off/moderate/strict、デフォルト: moderate）
            freshness: 時間範囲フィルタ（pd: 過去1日、pw: 過去1週間、pm: 過去1ヶ月、py: 過去1年）
            text_decorations: テキスト装飾を含めるか（デフォルト: True）
            spellcheck: スペルチェックを有効にするか（デフォルト: True）
        
        Returns:
            検索結果のリスト
        """
        if not self.is_available():
            logger.error("Brave Search APIキーが設定されていません")
            return []
        
        try:
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key
            }
            
            params = {
                "q": query,
                "count": min(count, 20),  # 最大20件
                "search_lang": search_lang,
                "country": country,
                "safesearch": safesearch,
                "text_decorations": "true" if text_decorations else "false",
                "spellcheck": "true" if spellcheck else "false"
            }
            
            if freshness:
                params["freshness"] = freshness
            
            response = requests.get(
                f"{self.base_url}/web/search",
                headers=headers,
                params=params,
                timeout=10
            )
            
            response.raise_for_status()
            data = response.json()
            
            results = []
            if "web" in data and "results" in data["web"]:
                for item in data["web"]["results"]:
                    results.append(BraveSearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        description=item.get("description", ""),
                        age=item.get("age"),
                        meta_url=item.get("meta_url")
                    ))
            
            logger.info(f"Brave Search: {len(results)}件の結果を取得しました（クエリ: {query}）")
            return results
            
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                error_detail = f" - {error_data}"
            except Exception:
                error_detail = f" - {e.response.text[:200]}"
            logger.error(f"Brave Search API HTTPエラー ({e.response.status_code}): {e}{error_detail}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Brave Search APIリクエストエラー: {e}")
            return []
        except Exception as e:
            logger.error(f"Brave Search APIエラー: {e}", exc_info=True)
            return []
    
    def search_simple(self, query: str, count: int = 5) -> List[Dict[str, str]]:
        """
        シンプルな検索（結果のみ返す）
        
        Args:
            query: 検索クエリ
            count: 取得件数（デフォルト: 5）
        
        Returns:
            検索結果の辞書リスト
        """
        results = self.search(query, count=count)
        return [
            {
                "title": r.title,
                "url": r.url,
                "description": r.description
            }
            for r in results
        ]
    
    def search_with_summary(self, query: str, count: int = 10) -> Dict[str, Any]:
        """
        検索結果とサマリーを返す
        
        Args:
            query: 検索クエリ
            count: 取得件数（デフォルト: 10）
        
        Returns:
            検索結果とサマリーを含む辞書
        """
        results = self.search(query, count=count)
        
        summary = {
            "query": query,
            "total_results": len(results),
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "description": r.description,
                    "age": r.age
                }
                for r in results
            ]
        }
        
        return summary

