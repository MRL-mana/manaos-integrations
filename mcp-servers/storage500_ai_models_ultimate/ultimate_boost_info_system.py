#!/usr/bin/env python3
"""
🚀 究極ブーストモード情報収集システム
- YouTube + X + Instagram + Yahooニュース 同時収集
- 急上昇ワード・トレンド分析
- リアルタイム情報処理
- Obsidian自動連携
- Gemini AI分析統合
"""

import asyncio
import aiohttp
import json
import logging
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp

# カスタムモジュール
from enhanced_youtube_info_collector import EnhancedYouTubeCollector, YouTubeVideoInfo
from social_media_collector import SocialMediaCollector, TrendingTopic
import google.generativeai as genai

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_boost_info.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class UltimateInfoResult:
    """究極情報収集結果"""
    youtube_videos: List[YouTubeVideoInfo]
    social_trends: List[TrendingTopic]
    trending_keywords: List[str]
    ai_insights: str
    collection_time: float
    total_items: int
    success_rate: float

class UltimateBoostInfoSystem:
    """究極ブーストモード情報収集システム"""
    
    def __init__(self):
        """初期化"""
        self.setup_components()
        self.obsidian_vault = os.getenv('OBSIDIAN_VAULT_PATH', '/root/obsidian_vault')
        os.makedirs(self.obsidian_vault, exist_ok=True)
        
    def setup_components(self):
        """コンポーネント初期化"""
        # YouTube収集器
        self.youtube_collector = EnhancedYouTubeCollector()
        
        # ソーシャルメディア収集器
        self.social_collector = SocialMediaCollector()
        
        # Gemini AI
        gemini_key = os.getenv('GEMINI_API_KEY')
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel('gemini-pro')
            logger.info("✅ Gemini AI初期化完了")
        else:
            logger.warning("⚠️ Gemini APIキーが未設定")
            self.gemini_model = None
        
        logger.info("🚀 究極ブーストモードシステム初期化完了")
    
    async def ultimate_parallel_collection(self) -> UltimateInfoResult:
        """究極並列収集実行"""
        logger.info("🚀🚀🚀 究極ブーストモード開始 🚀🚀🚀")
        start_time = time.time()
        
        # 並列タスク定義
        tasks = []
        
        # YouTube収集タスク
        if hasattr(self.youtube_collector, 'youtube_api_key') and self.youtube_collector.youtube_api_key:
            tasks.append(self.collect_youtube_boost())
        
        # ソーシャルメディア収集タスク
        tasks.append(self.collect_social_boost())
        
        # 急上昇ワード分析タスク
        tasks.append(self.analyze_trending_keywords())
        
        logger.info(f"📊 {len(tasks)}個のタスクを並列実行開始")
        
        # 並列実行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果処理
        youtube_videos = []
        social_trends = []
        trending_keywords = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"タスク {i} エラー: {result}")
                continue
            
            if i == 0 and isinstance(result, list) and result and hasattr(result[0], 'video_id'):
                youtube_videos = result
            elif isinstance(result, list) and result and hasattr(result[0], 'platform'):
                social_trends = result
            elif isinstance(result, list) and result and isinstance(result[0], str):
                trending_keywords = result
        
        # AI統合分析
        ai_insights = await self.generate_ai_insights(youtube_videos, social_trends, trending_keywords)
        
        # 処理時間計算
        collection_time = time.time() - start_time
        total_items = len(youtube_videos) + len(social_trends) + len(trending_keywords)
        success_rate = (len([r for r in results if not isinstance(r, Exception)]) / len(tasks)) * 100
        
        result = UltimateInfoResult(
            youtube_videos=youtube_videos,
            social_trends=social_trends,
            trending_keywords=trending_keywords,
            ai_insights=ai_insights,
            collection_time=collection_time,
            total_items=total_items,
            success_rate=success_rate
        )
        
        logger.info(f"""
🎉 究極収集完了！
📊 統計:
  - YouTube動画: {len(youtube_videos)}本
  - ソーシャルトレンド: {len(social_trends)}件
  - 急上昇ワード: {len(trending_keywords)}個
  - 処理時間: {collection_time:.1f}秒
  - 成功率: {success_rate:.1f}%
""")
        
        return result
    
    async def collect_youtube_boost(self) -> List[YouTubeVideoInfo]:
        """YouTube ブースト収集"""
        try:
            logger.info("📺 YouTube ブースト収集開始")
            videos = await self.youtube_collector.search_revenue_videos(max_videos=20)
            logger.info(f"✅ YouTube収集完了: {len(videos)}本")
            return videos
        except Exception as e:
            logger.error(f"YouTube収集エラー: {e}")
            return []
    
    async def collect_social_boost(self) -> List[TrendingTopic]:
        """ソーシャルメディア ブースト収集"""
        try:
            logger.info("📱 ソーシャルメディア ブースト収集開始")
            trends = await self.social_collector.collect_all_trends()
            logger.info(f"✅ ソーシャル収集完了: {len(trends)}件")
            return trends
        except Exception as e:
            logger.error(f"ソーシャル収集エラー: {e}")
            return []
    
    async def analyze_trending_keywords(self) -> List[str]:
        """急上昇ワード分析"""
        try:
            logger.info("🔥 急上昇ワード分析開始")
            
            # 複数ソースから急上昇ワードを収集
            keywords = []
            
            # Google Trendsライクな分析（簡易版）
            trending_topics = [
                "AI副業", "ChatGPT活用", "自動化ツール", "プログラミング学習",
                "YouTube収益化", "ブログマネタイズ", "フリーランス", "リモートワーク",
                "投資戦略", "暗号通貨", "NFT", "メタバース", "Web3",
                "マーケティング自動化", "SEO対策", "SNS運用", "インフルエンサー"
            ]
            
            # 現在のトレンド強度を分析（実際のAPIでは検索ボリューム等を使用）
            for topic in trending_topics:
                # 簡易的なトレンド判定
                trend_score = await self.calculate_trend_score(topic)
                if trend_score > 3:  # 閾値以上のもののみ
                    keywords.append(topic)
            
            logger.info(f"✅ 急上昇ワード分析完了: {len(keywords)}個")
            return keywords[:10]  # 上位10個
            
        except Exception as e:
            logger.error(f"急上昇ワード分析エラー: {e}")
            return []
    
    async def calculate_trend_score(self, keyword: str) -> int:
        """トレンドスコア計算（1-5）"""
        try:
            if not self.gemini_model:
                return 3  # デフォルト値
            
            prompt = f"""
キーワード「{keyword}」の現在のトレンド強度を1-5で評価してください。

評価基準:
1: 全く注目されていない
2: 少し注目されている
3: 普通レベルの注目
4: 高い注目度
5: 非常に高いトレンド

数字のみで回答してください。
"""
            
            response = self.gemini_model.generate_content(prompt)
            score_text = response.text.strip()
            
            try:
                score = int(score_text)
                return max(1, min(5, score))  # 1-5の範囲に制限
            except ValueError:
                return 3
                
        except Exception as e:
            logger.warning(f"トレンドスコア計算エラー: {e}")
            return 3
    
    async def generate_ai_insights(self, youtube_videos: List[YouTubeVideoInfo], 
                                 social_trends: List[TrendingTopic], 
                                 trending_keywords: List[str]) -> str:
        """AI統合分析・洞察生成"""
        try:
            if not self.gemini_model:
                return "AI分析機能が利用できません"
            
            # データサマリー作成
            youtube_summary = f"YouTube動画 {len(youtube_videos)}本"
            if youtube_videos:
                top_video = max(youtube_videos, key=lambda x: x.revenue_potential)
                youtube_summary += f"（最高収益スコア: {top_video.revenue_potential}/5）"
            
            social_summary = f"ソーシャルトレンド {len(social_trends)}件"
            if social_trends:
                platforms = list(set(t.platform for t in social_trends))
                social_summary += f"（プラットフォーム: {', '.join(platforms)}）"
            
            keywords_summary = f"急上昇ワード {len(trending_keywords)}個"
            if trending_keywords:
                keywords_summary += f"（例: {', '.join(trending_keywords[:3])}）"
            
            prompt = f"""
以下の情報収集結果を分析して、ビジネス・収益化に関する洞察を提供してください：

【収集データ】
- {youtube_summary}
- {social_summary}  
- {keywords_summary}

【分析観点】
1. 現在の収益化トレンド
2. 注目すべきビジネス機会
3. 実践可能なアクションプラン
4. 今後の展望・予測

簡潔で実用的な日本語で回答してください。
"""
            
            response = self.gemini_model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"AI洞察生成エラー: {e}")
            return f"AI分析エラー: {e}"
    
    def generate_ultimate_report(self, result: UltimateInfoResult) -> str:
        """究極レポート生成"""
        today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        content = f"""# 🚀 究極ブーストモード情報収集レポート

## 📊 収集サマリー
- **生成日時**: {today}
- **処理時間**: {result.collection_time:.1f}秒
- **総アイテム数**: {result.total_items}
- **成功率**: {result.success_rate:.1f}%

---

## 🎯 AI統合分析・洞察

{result.ai_insights}

---

## 📺 YouTube収益分析 ({len(result.youtube_videos)}本)

"""
        
        if result.youtube_videos:
            # 高収益動画TOP5
            top_videos = sorted(result.youtube_videos, key=lambda x: x.revenue_potential, reverse=True)[:5]
            content += "### 🏆 高収益ポテンシャル TOP5\n\n"
            
            for i, video in enumerate(top_videos, 1):
                content += f"""**{i}. {video.title}**
- チャンネル: {video.channel_title}
- 再生回数: {video.view_count:,}回
- 収益スコア: {video.revenue_potential}/5
- [動画リンク]({video.url})

"""
        
        content += f"""
## 📱 ソーシャルメディア・トレンド ({len(result.social_trends)}件)

"""
        
        if result.social_trends:
            # プラットフォーム別統計
            platforms = {}
            for trend in result.social_trends:
                platforms[trend.platform] = platforms.get(trend.platform, 0) + 1
            
            content += "### 📊 プラットフォーム別統計\n\n"
            for platform, count in platforms.items():
                content += f"- **{platform}**: {count}件\n"
            
            content += "\n### 🔥 注目トレンド\n\n"
            content += "| キーワード | プラットフォーム | タイプ | 感情 |\n"
            content += "|------------|------------------|--------|------|\n"
            
            for trend in result.social_trends[:10]:
                content += f"| {trend.keyword} | {trend.platform} | {trend.trend_type} | {trend.sentiment} |\n"
        
        content += f"""

## 🚀 急上昇ワード分析 ({len(result.trending_keywords)}個)

"""
        
        if result.trending_keywords:
            for i, keyword in enumerate(result.trending_keywords, 1):
                content += f"{i}. **{keyword}**\n"
        
        content += f"""

## ⚡ パフォーマンス統計

- **YouTube動画収集**: {len(result.youtube_videos)}本
- **ソーシャルトレンド**: {len(result.social_trends)}件  
- **急上昇ワード**: {len(result.trending_keywords)}個
- **総処理時間**: {result.collection_time:.1f}秒
- **処理効率**: {result.total_items/result.collection_time:.1f} items/sec
- **システム成功率**: {result.success_rate:.1f}%

---

## 💡 次のアクション

1. **高収益動画の分析**: 上位動画の手法を研究
2. **トレンドキーワード活用**: コンテンツ作成に活用
3. **ソーシャル戦略**: プラットフォーム別アプローチ
4. **継続監視**: 定期的な情報更新

---
*Generated by 究極ブーストモード情報収集システム*
*Next Update: {(datetime.now() + timedelta(hours=6)).strftime('%Y-%m-%d %H:%M')}*
"""
        
        return content
    
    async def save_ultimate_report(self, result: UltimateInfoResult):
        """究極レポート保存"""
        try:
            # レポート生成
            report_content = self.generate_ultimate_report(result)
            
            # Obsidian保存
            today = datetime.now().strftime('%Y-%m-%d')
            filename = f"{self.obsidian_vault}/究極ブーストモード情報収集_{today}.md"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            logger.info(f"✅ 究極レポート保存完了: {filename}")
            
            # JSON形式でも保存（データ処理用）
            json_filename = f"{self.obsidian_vault}/data_ultimate_boost_{today}.json"
            json_data = {
                'youtube_videos': [asdict(v) for v in result.youtube_videos],
                'social_trends': [asdict(t) for t in result.social_trends],
                'trending_keywords': result.trending_keywords,
                'ai_insights': result.ai_insights,
                'stats': {
                    'collection_time': result.collection_time,
                    'total_items': result.total_items,
                    'success_rate': result.success_rate
                },
                'generated_at': datetime.now().isoformat()
            }
            
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ JSONデータ保存完了: {json_filename}")
            
        except Exception as e:
            logger.error(f"レポート保存エラー: {e}")
    
    async def run_ultimate_boost(self):
        """究極ブーストモード実行"""
        print("\n" + "🚀"*20)
        print("究極ブーストモード情報収集システム")
        print("🚀"*20 + "\n")
        
        try:
            # 究極収集実行
            result = await self.ultimate_parallel_collection()
            
            # レポート保存
            await self.save_ultimate_report(result)
            
            # 結果表示
            print("🎉 究極ブーストモード完了！")
            print(f"📊 収集統計:")
            print(f"  📺 YouTube: {len(result.youtube_videos)}本")
            print(f"  📱 ソーシャル: {len(result.social_trends)}件")
            print(f"  🔥 急上昇ワード: {len(result.trending_keywords)}個")
            print(f"⚡ 処理時間: {result.collection_time:.1f}秒")
            print(f"✅ 成功率: {result.success_rate:.1f}%")
            
            if result.trending_keywords:
                print(f"\n🚀 注目急上昇ワード:")
                for i, keyword in enumerate(result.trending_keywords[:5], 1):
                    print(f"  {i}. {keyword}")
            
            print(f"\n💾 保存先: {self.obsidian_vault}")
            
        except Exception as e:
            logger.error(f"究極ブーストモード実行エラー: {e}")
            raise

async def main():
    """メイン関数"""
    system = UltimateBoostInfoSystem()
    await system.run_ultimate_boost()

if __name__ == "__main__":
    asyncio.run(main())

