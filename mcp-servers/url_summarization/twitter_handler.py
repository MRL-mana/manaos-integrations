#!/usr/bin/env python3
"""
Twitter/X処理モジュール
ツイート取得、スレッド取得
"""

import snscrape.modules.twitter as sntwitter
from typing import Dict
import re


class TwitterHandler:
    """Twitter/X処理"""
    
    def get_tweet(self, url: str) -> Dict:
        """ツイート取得"""
        try:
            # URLからツイートID抽出
            tweet_id = self._extract_tweet_id(url)
            if not tweet_id:
                return {"success": False, "error": "無効なツイートURL"}
            
            # ツイート検索
            query = f"from:{tweet_id.split('/')[0]} since_id:{tweet_id.split('/')[-1]}"
            
            tweets = []
            for i, tweet in enumerate(sntwitter.TwitterTweetScraper(tweetId=tweet_id).get_items()):
                tweets.append({
                    "id": str(tweet.id),
                    "content": tweet.content,
                    "date": tweet.date.isoformat() if tweet.date else None,
                    "user": tweet.user.username if tweet.user else None,
                    "likes": tweet.likeCount or 0,
                    "retweets": tweet.retweetCount or 0,
                    "replies": tweet.replyCount or 0,
                    "urls": tweet.urls or [],
                    "media": [m.fullUrl for m in (tweet.media or [])]
                })
                break  # 1件のみ取得
            
            if not tweets:
                return {"success": False, "error": "ツイートが見つかりません"}
            
            return {
                "success": True,
                "tweet": tweets[0]
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_thread(self, url: str) -> Dict:
        """スレッド全体取得"""
        try:
            # 親ツイート取得
            parent_result = self.get_tweet(url)
            if not parent_result["success"]:
                return parent_result
            
            parent_tweet = parent_result["tweet"]
            
            # リプライ取得（簡易版）
            # 実際の実装では、Twitter API v2を使用することを推奨
            
            return {
                "success": True,
                "parent": parent_tweet,
                "replies": [],  # 実装は後で追加
                "thread_count": 1
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _extract_tweet_id(self, url: str) -> str:
        """URLからツイートID抽出"""
        # 例: https://x.com/username/status/1234567890
        match = re.search(r'/status/(\d+)', url)
        if match:
            return match.group(1)
        return None


