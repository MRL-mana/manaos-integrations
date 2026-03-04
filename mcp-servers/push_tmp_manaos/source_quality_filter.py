#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ソース品質フィルタ（嘘の温床を切る）
公式/論文/規格を優先し、まとめサイト・匿名掲示板を補助扱い
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from manaos_logger import get_logger, get_service_logger
from .schemas import Citation, SearchResult

logger = get_service_logger("source-quality-filter")


class SourceQuality(str, Enum):
    """ソース品質"""
    PRIMARY = "primary"  # 一次情報（公式/論文/規格）
    SECONDARY = "secondary"  # 二次情報（信頼できるメディア）
    TERTIARY = "tertiary"  # 三次情報（まとめサイト等）
    LOW = "low"  # 低品質（匿名掲示板等）


@dataclass
class SourceQualityFilter:
    """ソース品質フィルタ"""
    
    # 優先ドメイン（一次情報）
    primary_domains = [
        "microsoft.com", "github.com", "python.org", "npmjs.com",
        "w3.org", "ietf.org", "rfc-editor.org",
        "arxiv.org", "ieee.org", "acm.org"
    ]
    
    # 信頼できるメディア（二次情報）
    secondary_domains = [
        "techcrunch.com", "theverge.com", "zdnet.com",
        "stackoverflow.com", "reddit.com/r/",  # 特定のサブレディットのみ
    ]
    
    # 低品質ドメイン（三次情報以下）
    low_quality_domains = [
        "2ch.net", "5ch.net", "anonymous", "pastebin.com"
    ]
    
    # まとめサイトパターン
    summary_site_patterns = [
        r"まとめ", r"まとめサイト", r"wiki", r"wikipedia"
    ]
    
    def filter_and_rank_sources(self, search_results: List[SearchResult]) -> List[SearchResult]:
        """
        ソースをフィルタリングしてランク付け
        
        Args:
            search_results: 検索結果リスト
        
        Returns:
            フィルタリング・ランク付け済みリスト
        """
        ranked_results = []
        
        for result in search_results:
            quality = self.assess_source_quality(result)
            result.quality = quality.value  # 動的属性として追加
            
            # 低品質は除外（または最後に）
            if quality != SourceQuality.LOW:
                ranked_results.append((quality, result))
        
        # 品質順にソート
        ranked_results.sort(key=lambda x: self._quality_priority(x[0]))
        
        return [result for _, result in ranked_results]
    
    def assess_source_quality(self, result: SearchResult) -> SourceQuality:
        """
        ソース品質を評価
        
        Args:
            result: 検索結果
        
        Returns:
            ソース品質
        """
        url = result.url.lower()
        title = result.title.lower()
        
        # 一次情報チェック
        for domain in self.primary_domains:
            if domain in url:
                return SourceQuality.PRIMARY
        
        # 低品質チェック
        for domain in self.low_quality_domains:
            if domain in url:
                return SourceQuality.LOW
        
        # まとめサイトチェック
        for pattern in self.summary_site_patterns:
            if pattern in title or pattern in url:
                return SourceQuality.TERTIARY
        
        # 二次情報チェック
        for domain in self.secondary_domains:
            if domain in url:
                return SourceQuality.SECONDARY
        
        # デフォルトは三次情報
        return SourceQuality.TERTIARY
    
    def filter_citations_by_quality(
        self,
        citations: List[Citation],
        min_quality: SourceQuality = SourceQuality.TERTIARY
    ) -> List[Citation]:
        """
        引用を品質でフィルタリング
        
        Args:
            citations: 引用リスト
            min_quality: 最低品質
        
        Returns:
            フィルタリング済み引用リスト
        """
        filtered = []
        
        for citation in citations:
            quality = self.assess_citation_quality(citation)
            if self._quality_priority(quality) >= self._quality_priority(min_quality):
                filtered.append(citation)
        
        return filtered
    
    def assess_citation_quality(self, citation: Citation) -> SourceQuality:
        """
        引用の品質を評価
        
        Args:
            citation: 引用
        
        Returns:
            ソース品質
        """
        source = citation.source.lower()
        
        # 一次情報チェック
        for domain in self.primary_domains:
            if domain in source:
                return SourceQuality.PRIMARY
        
        # 低品質チェック
        for domain in self.low_quality_domains:
            if domain in source:
                return SourceQuality.LOW
        
        # まとめサイトチェック
        for pattern in self.summary_site_patterns:
            if pattern in source:
                return SourceQuality.TERTIARY
        
        # 二次情報チェック
        for domain in self.secondary_domains:
            if domain in source:
                return SourceQuality.SECONDARY
        
        return SourceQuality.TERTIARY
    
    def add_quality_warnings(self, citations: List[Citation]) -> List[Citation]:
        """
        品質警告を追加
        
        Args:
            citations: 引用リスト
        
        Returns:
            警告追加済み引用リスト
        """
        for citation in citations:
            quality = self.assess_citation_quality(citation)
            
            if quality == SourceQuality.TERTIARY:
                citation.warning = "まとめサイトの情報です。一次情報を確認することを推奨します。"
            elif quality == SourceQuality.LOW:
                citation.warning = "低品質な情報源です。結論の根拠として使用しないでください。"
            
            # 日付抽出とチェック
            extracted_date = self._extract_date_from_citation(citation)
            if extracted_date:
                # 動的属性として日付を追加
                setattr(citation, 'date', extracted_date)
                # 古い情報（5年以上前）の警告
                if self._is_old_date(extracted_date, years=5):
                    if not citation.warning:
                        citation.warning = ""
                    citation.warning += f" 注意: この情報は{extracted_date.year}年のもので、古い可能性があります。"
        
        return citations
    
    def _quality_priority(self, quality: SourceQuality) -> int:
        """品質の優先度（数値が大きいほど高品質）"""
        priority_map = {
            SourceQuality.PRIMARY: 4,
            SourceQuality.SECONDARY: 3,
            SourceQuality.TERTIARY: 2,
            SourceQuality.LOW: 1
        }
        return priority_map.get(quality, 1)
    
    def _extract_date_from_citation(self, citation: Citation) -> Optional[datetime]:
        """
        引用から日付を抽出
        
        Args:
            citation: 引用
        
        Returns:
            抽出された日付（Noneの場合は抽出失敗）
        """
        # 引用のソース、要約、タイトルから日付を探す
        text_to_search = f"{citation.source} {citation.summary}"
        if hasattr(citation, 'title'):
            text_to_search += f" {citation.title}"
        
        # 日付パターンを検索
        date_patterns = [
            # YYYY-MM-DD形式
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            # YYYY/MM/DD形式
            r'(\d{4})/(\d{1,2})/(\d{1,2})',
            # YYYY年MM月DD日形式
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            # YYYY年MM月形式
            r'(\d{4})年(\d{1,2})月',
            # YYYY年形式
            r'(\d{4})年',
            # MM/DD/YYYY形式（英語圏）
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            # 月名形式（January 2024, Jan 2024等）
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text_to_search, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    
                    # YYYY-MM-DD形式
                    if len(groups) == 3 and '-' in match.group(0):
                        year, month, day = map(int, groups)
                        return datetime(year, month, day)
                    
                    # YYYY/MM/DD形式
                    if len(groups) == 3 and '/' in match.group(0):
                        # 最初のグループが4桁ならYYYY/MM/DD
                        if len(groups[0]) == 4:
                            year, month, day = map(int, groups)
                            return datetime(year, month, day)
                        # そうでなければMM/DD/YYYY
                        else:
                            month, day, year = map(int, groups)
                            return datetime(year, month, day)
                    
                    # YYYY年MM月DD日形式
                    if '年' in match.group(0) and '月' in match.group(0) and '日' in match.group(0):
                        year, month, day = map(int, groups)
                        return datetime(year, month, day)
                    
                    # YYYY年MM月形式
                    if '年' in match.group(0) and '月' in match.group(0) and len(groups) == 2:
                        year, month = map(int, groups)
                        return datetime(year, month, 1)
                    
                    # YYYY年形式
                    if '年' in match.group(0) and len(groups) == 1:
                        year = int(groups[0])
                        return datetime(year, 1, 1)
                    
                    # 月名形式
                    month_names = {
                        'january': 1, 'february': 2, 'march': 3, 'april': 4,
                        'may': 5, 'june': 6, 'july': 7, 'august': 8,
                        'september': 9, 'october': 10, 'november': 11, 'december': 12,
                        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                        'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                        'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                    }
                    if len(groups) == 2:
                        month_name = groups[0].lower()
                        if month_name in month_names:
                            year = int(groups[1])
                            month = month_names[month_name]
                            return datetime(year, month, 1)
                
                except (ValueError, IndexError) as e:
                    logger.debug(f"日付抽出エラー: {e}")
                    continue
        
        return None
    
    def _is_old_date(self, date: datetime, years: int = 5) -> bool:
        """
        日付が古いかチェック
        
        Args:
            date: チェックする日付
            years: 何年以上前を古いとみなすか
        
        Returns:
            古い場合True
        """
        if date is None:
            return False
        
        threshold = datetime.now().replace(year=datetime.now().year - years)
        return date < threshold


