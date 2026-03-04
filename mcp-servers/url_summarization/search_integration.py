#!/usr/bin/env python3
"""
検索統合システム
Brave Search, Google検索統合
"""

import requests
import os
from typing import Dict
from datetime import datetime


class SearchIntegration:
    """検索統合システム"""
    
    def __init__(self):
        self.brave_api_key = os.getenv("BRAVE_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cx = os.getenv("GOOGLE_CX")
    
    def search_brave(self, query: str, count: int = 10) -> Dict:
        """Brave Search実行"""
        if not self.brave_api_key:
            return {"success": False, "error": "BRAVE_API_KEYが設定されていません"}
        
        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.brave_api_key
            }
            params = {
                "q": query,
                "count": count,
                "search_lang": "ja",
                "country": "JP",
                "safesearch": "moderate"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            if "web" in data.get("results", {}):
                for item in data["web"]["results"][:count]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "description": item.get("description", ""),
                        "age": item.get("age", "")
                    })
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "total": len(results)
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search_google(self, query: str, count: int = 10) -> Dict:
        """Google Custom Search実行"""
        if not self.google_api_key or not self.google_cx:
            return {"success": False, "error": "GOOGLE_API_KEYまたはGOOGLE_CXが設定されていません"}
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.google_api_key,
                "cx": self.google_cx,
                "q": query,
                "num": count,
                "lr": "lang_ja",
                "gl": "jp"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            if "items" in data:
                for item in data["items"]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "description": item.get("snippet", ""),
                        "displayUrl": item.get("displayLink", "")
                    })
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "total": len(results)
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search_multiple(self, query: str, count: int = 10) -> Dict:
        """複数検索エンジン統合"""
        results = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "brave": None,
            "google": None,
            "combined": []
        }
        
        # Brave Search
        brave_result = self.search_brave(query, count)
        if brave_result["success"]:
            results["brave"] = brave_result
            results["combined"].extend(brave_result["results"])
        
        # Google Search
        google_result = self.search_google(query, count)
        if google_result["success"]:
            results["google"] = google_result
            results["combined"].extend(google_result["results"])
        
        # 重複除去
        seen_urls = set()
        unique_results = []
        for item in results["combined"]:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                unique_results.append(item)
        
        results["combined"] = unique_results
        results["total_unique"] = len(unique_results)
        
        return {
            "success": True,
            "results": results
        }

