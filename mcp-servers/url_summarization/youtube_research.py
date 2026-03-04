#!/usr/bin/env python3
"""
YouTube研究システム
YouTube検索、複数動画処理、文字起こし、比較分析
"""

import yt_dlp
import anthropic
import os
from typing import Dict, List
from datetime import datetime
from youtube_handler import YouTubeHandler


class YouTubeResearch:
    """YouTube研究システム"""
    
    def __init__(self):
        self.youtube_handler = YouTubeHandler()
        
        # Claude API
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.claude_client = anthropic.Anthropic(api_key=api_key) if api_key else None
    
    def search_youtube(self, query: str, max_results: int = 5) -> Dict:
        """YouTube検索"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            search_url = f"ytsearch{max_results}:{query}"
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_url, download=False)
                
                videos = []
                if 'entries' in info:
                    for entry in info['entries']:
                        videos.append({
                            "title": entry.get('title', ''),
                            "url": f"https://youtube.com/watch?v={entry.get('id', '')}",
                            "duration": entry.get('duration', 0),
                            "uploader": entry.get('uploader', ''),
                            "view_count": entry.get('view_count', 0)
                        })
                
                return {
                    "success": True,
                    "query": query,
                    "videos": videos,
                    "total": len(videos)
                }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def process_multiple_videos(self, video_urls: List[str]) -> Dict:
        """複数動画処理"""
        try:
            results = []
            
            for i, url in enumerate(video_urls, 1):
                print(f"🎥 [{i}/{len(video_urls)}] 処理中: {url}")
                
                result = self.youtube_handler.process(url)
                
                if result["success"]:
                    results.append({
                        "url": url,
                        "title": result["video_info"]["title"],
                        "description": result["video_info"]["description"],
                        "transcript": result["transcript"]["text"],
                        "duration": result["video_info"]["duration"]
                    })
            
            return {
                "success": True,
                "videos": results,
                "total": len(results)
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def research_and_summarize(self, query: str, max_results: int = 3) -> Dict:
        """YouTube研究→要約"""
        try:
            # 1. YouTube検索
            print(f"🔍 YouTube検索中: {query}")
            search_result = self.search_youtube(query, max_results)
            
            if not search_result["success"]:
                return {"success": False, "error": "検索失敗"}
            
            videos = search_result["videos"]
            print(f"📊 検索結果: {len(videos)}件")
            
            # 2. 動画処理
            print("🎥 動画処理中...")
            video_urls = [v["url"] for v in videos]
            process_result = self.process_multiple_videos(video_urls)
            
            if not process_result["success"]:
                return {"success": False, "error": "動画処理失敗"}
            
            processed_videos = process_result["videos"]
            
            # 3. AI要約
            if processed_videos and self.claude_client:
                print("🤖 AI要約中...")
                summary = self._generate_summary(query, processed_videos)
            else:
                summary = "AI要約は利用できません"
            
            return {
                "success": True,
                "query": query,
                "videos": processed_videos,
                "summary": summary,
                "total_videos": len(processed_videos),
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_summary(self, query: str, videos: List[Dict]) -> str:
        """AI要約生成"""
        try:
            # コンテキスト作成
            context = f"検索クエリ: {query}\n\n"
            context += f"以下の{len(videos)}件のYouTube動画を要約してください:\n\n"
            
            for i, video in enumerate(videos, 1):
                context += f"【動画{i}】{video['title']}\n"
                context += f"説明: {video['description'][:500]}\n"
                context += f"文字起こし: {video['transcript'][:1000]}\n\n"
            
            prompt = f"""{context}

上記の動画を基に、検索クエリ「{query}」について以下の形式で要約してください:

## 総合要約
（全体の要点を3-5つのポイントで）

## 主要な内容
（各動画の重要な内容）

## 共通点・相違点
（動画間の比較）

## おすすめポイント
（特に参考になる内容）"""

            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            return response.content[0].text
        
        except Exception as e:
            return f"要約生成エラー: {str(e)}"
    
    def compare_videos(self, video_urls: List[str]) -> Dict:
        """動画比較分析"""
        try:
            # 動画処理
            process_result = self.process_multiple_videos(video_urls)
            
            if not process_result["success"]:
                return {"success": False, "error": "動画処理失敗"}
            
            videos = process_result["videos"]
            
            # 比較分析
            if self.claude_client:
                comparison = self._generate_comparison(videos)
            else:
                comparison = "AI比較分析は利用できません"
            
            return {
                "success": True,
                "videos": videos,
                "comparison": comparison,
                "total": len(videos)
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_comparison(self, videos: List[Dict]) -> str:
        """比較分析生成"""
        try:
            context = "以下の動画を比較分析してください:\n\n"
            
            for i, video in enumerate(videos, 1):
                context += f"【動画{i}】{video['title']}\n"
                context += f"内容: {video['transcript'][:1000]}\n\n"
            
            prompt = f"""{context}

上記の動画を比較分析してください:

## 共通点
（すべての動画で共通する内容）

## 相違点
（各動画の特徴的な内容）

## おすすめ
（それぞれの動画の特徴とおすすめポイント）

## 総合評価
（全体の評価と推奨）"""

            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            return response.content[0].text
        
        except Exception as e:
            return f"比較分析エラー: {str(e)}"

