#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Critic合格条件固定システム（ふわっと防止）
機械的な合格判定を実装
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from manaos_logger import get_logger
from .schemas import CritiqueResult, Citation

logger = get_logger(__name__)


@dataclass
class CriticGuard:
    """Critic合格条件ガード"""
    
    # 最低条件
    min_citations_per_claim: int = 1  # 主張1つにつき最低1つの引用
    require_claim_support: bool = True  # 結論に根拠が必要
    require_counter_argument: bool = True  # 反証候補が最低1つ必要
    require_fact_inference_distinction: bool = True  # 事実と推測の区別が必要
    
    def validate_pass_conditions(
        self,
        report: str,
        citations: List[Citation],
        critique_result: CritiqueResult
    ) -> tuple[bool, List[str]]:
        """
        合格条件を機械的に検証
        
        Args:
            report: レポート内容
            citations: 引用リスト
            critique_result: Criticの採点結果
        
        Returns:
            (合格かどうか, 失敗理由リスト)
        """
        fail_reasons = []
        
        # 1. 引用数のチェック
        if self.require_claim_support:
            claims = self._extract_claims(report)
            if len(claims) > 0:
                citations_per_claim = len(citations) / len(claims) if len(claims) > 0 else 0
                if citations_per_claim < self.min_citations_per_claim:
                    fail_reasons.append(f"引用不足: 主張{len(claims)}個に対して引用{len(citations)}個 (最低{self.min_citations_per_claim}個/主張必要)")
        
        # 2. 結論→根拠の対応チェック
        if self.require_claim_support:
            if not self._has_claim_support(report, citations):
                fail_reasons.append("結論に対する根拠の対応が不明確")
        
        # 3. 反証候補のチェック
        if self.require_counter_argument:
            if not self._has_counter_argument(report):
                fail_reasons.append("反証候補または注意点が不足（最低1つ必要）")
        
        # 4. 事実と推測の区別チェック
        if self.require_fact_inference_distinction:
            if not self._has_fact_inference_distinction(report, citations):
                fail_reasons.append("事実（fact）と推測（inference）の区別が不明確")
        
        # Criticのfail_flagsもチェック
        if critique_result.fail_flags:
            fail_reasons.extend([f"Critic指摘: {flag}" for flag in critique_result.fail_flags])
        
        # スコアチェック（Criticの判定を尊重）
        is_pass = len(fail_reasons) == 0 and critique_result.is_passed
        
        return is_pass, fail_reasons
    
    def _extract_claims(self, report: str) -> List[str]:
        """
        レポートから主張を抽出
        
        Args:
            report: レポート内容
        
        Returns:
            主張のリスト
        """
        # 「結論」「まとめ」「主張」などのセクションから抽出
        claims = []
        
        # 結論セクションを探す
        conclusion_patterns = [
            r"##\s*結論[^\n]*\n(.*?)(?=##|\Z)",
            r"##\s*まとめ[^\n]*\n(.*?)(?=##|\Z)",
            r"結論[：:]\s*(.+?)(?=\n\n|\Z)",
        ]
        
        for pattern in conclusion_patterns:
            matches = re.findall(pattern, report, re.DOTALL | re.IGNORECASE)
            for match in matches:
                # 箇条書きや段落から主張を抽出
                lines = match.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 10:  # 短すぎるものは除外
                        # 箇条書き記号を除去
                        line = re.sub(r'^[-*•]\s*', '', line)
                        if line:
                            claims.append(line)
        
        return claims[:5]  # 最大5つまで
    
    def _has_claim_support(self, report: str, citations: List[Citation]) -> bool:
        """
        結論に根拠が対応しているかチェック
        
        Args:
            report: レポート内容
            citations: 引用リスト
        
        Returns:
            対応があるかどうか
        """
        if len(citations) == 0:
            return False
        
        # 引用がレポート内で参照されているかチェック
        citation_ids = [cite.id for cite in citations]
        citation_sources = [cite.source for cite in citations]
        
        # レポート内に引用IDやソースが含まれているか
        for cite_id in citation_ids:
            if cite_id in report:
                return True
        
        for source in citation_sources[:3]:  # 最初の3つをチェック
            if source in report:
                return True
        
        return False
    
    def _has_counter_argument(self, report: str) -> bool:
        """
        反証候補があるかチェック
        
        Args:
            report: レポート内容
        
        Returns:
            反証候補があるかどうか
        """
        counter_keywords = [
            "反証", "反対", "注意点", "リスク", "課題", "問題点",
            "デメリット", "欠点", "限界", "不確実", "懸念"
        ]
        
        report_lower = report.lower()
        for keyword in counter_keywords:
            if keyword in report_lower:
                return True
        
        return False
    
    def _has_fact_inference_distinction(self, report: str, citations: List[Citation]) -> bool:
        """
        事実と推測が区別されているかチェック
        
        Args:
            report: レポート内容
            citations: 引用リスト
        
        Returns:
            区別されているかどうか
        """
        # 引用にタグがあるかチェック
        has_fact = any(cite.tag.value == "fact" for cite in citations)
        has_inference = any(cite.tag.value == "inference" for cite in citations)
        
        # レポート内に「事実」「推測」などのキーワードがあるか
        distinction_keywords = ["事実", "推測", "fact", "inference", "推論", "推定"]
        report_lower = report.lower()
        has_keywords = any(keyword in report_lower for keyword in distinction_keywords)
        
        return has_fact or has_inference or has_keywords or len(citations) > 0



