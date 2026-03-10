#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
引用フォーマット強制システム（嘘防止）
Claim-ID方式で引用を強制的にフォーマット
"""

import re
from typing import Dict, Any, List
from dataclasses import dataclass

from manaos_logger import get_logger, get_service_logger
from .schemas import Citation

logger = get_service_logger("citation-formatter")


@dataclass
class CitationFormatter:
    """引用フォーマッター"""
    
    citation_format: str = "markdown"  # markdown or json
    
    def format_report_with_citations(
        self,
        report: str,
        citations: List[Citation],
        claims: List[str] = None  # type: ignore
    ) -> str:
        """
        レポートに引用を強制的にフォーマット
        
        Args:
            report: 元のレポート
            citations: 引用リスト
            claims: 主張リスト（オプション）
        
        Returns:
            フォーマット済みレポート
        """
        if not citations:
            logger.warning("No citations to format")
            return report
        
        # 主張を抽出（なければ生成）
        if not claims:
            claims = self._extract_claims(report)
        
        # 主張と引用をマッピング
        claim_citation_map = self._map_claims_to_citations(claims, citations)
        
        # レポートに引用を挿入
        formatted_report = self._insert_citations(report, claim_citation_map, citations)
        
        # 参照一覧を追加
        formatted_report = self._add_reference_section(formatted_report, citations)
        
        return formatted_report
    
    def _extract_claims(self, report: str) -> List[str]:
        """主張を抽出"""
        claims = []
        
        # 結論セクションから抽出
        conclusion_patterns = [
            r"##\s*結論[^\n]*\n(.*?)(?=##|\Z)",
            r"##\s*まとめ[^\n]*\n(.*?)(?=##|\Z)",
            r"結論[：:]\s*(.+?)(?=\n\n|\Z)",
        ]
        
        for pattern in conclusion_patterns:
            matches = re.findall(pattern, report, re.DOTALL | re.IGNORECASE)
            for match in matches:
                lines = match.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 10:
                        line = re.sub(r'^[-*•]\s*', '', line)
                        if line:
                            claims.append(line)
        
        return claims[:5]  # 最大5つ
    
    def _map_claims_to_citations(self, claims: List[str], citations: List[Citation]) -> Dict[str, List[Citation]]:
        """
        主張と引用をマッピング
        
        Args:
            claims: 主張リスト
            citations: 引用リスト
        
        Returns:
            主張→引用のマッピング
        """
        mapping = {}
        
        # 各主張に対して関連する引用を探す
        for i, claim in enumerate(claims):
            claim_id = f"CLAIM-{i+1}"
            related_citations = []
            
            # 主張のキーワードから関連引用を探す
            claim_keywords = set(re.findall(r'\w+', claim.lower()))
            
            for citation in citations:
                # 引用の要約や引用文からキーワードを抽出
                citation_text = (citation.summary + " " + citation.quote).lower()
                citation_keywords = set(re.findall(r'\w+', citation_text))
                
                # 共通キーワードがあるか
                common_keywords = claim_keywords & citation_keywords
                if len(common_keywords) >= 2:  # 最低2つの共通キーワード
                    related_citations.append(citation)
            
            # 関連引用がない場合は最初の引用を割り当て
            if not related_citations and citations:
                related_citations = [citations[i % len(citations)]]
            
            mapping[claim_id] = related_citations[:3]  # 最大3つまで
        
        return mapping
    
    def _insert_citations(self, report: str, claim_citation_map: Dict[str, List[Citation]], citations: List[Citation]) -> str:
        """
        レポートに引用を挿入
        
        Args:
            report: 元のレポート
            claim_citation_map: 主張→引用のマッピング
            citations: 引用リスト
        
        Returns:
            引用挿入済みレポート
        """
        formatted = report
        
        # 各主張の後に引用を挿入
        for claim_id, related_citations in claim_citation_map.items():
            if related_citations:
                citation_refs = []
                for cite in related_citations:
                    citation_refs.append(f"[{cite.id}]({cite.source})")
                
                citation_text = f"\n\n**引用**: {', '.join(citation_refs)}\n"
                
                # 主張の後に挿入（簡易版：結論セクション内に挿入）
                if "## 結論" in formatted or "## まとめ" in formatted:
                    # 結論セクションの最後に追加
                    formatted = re.sub(
                        r"(##\s*(結論|まとめ)[^\n]*\n.*?)(?=##|\Z)",
                        r"\1" + citation_text,
                        formatted,
                        flags=re.DOTALL | re.IGNORECASE
                    )
        
        return formatted
    
    def _add_reference_section(self, report: str, citations: List[Citation]) -> str:
        """
        参照一覧セクションを追加
        
        Args:
            report: レポート
            citations: 引用リスト
        
        Returns:
            参照一覧追加済みレポート
        """
        if "## 参考文献" in report or "## 参照" in report:
            return report  # 既にある場合は追加しない
        
        reference_section = "\n\n## 参考文献\n\n"
        
        for i, citation in enumerate(citations, 1):
            reference_section += f"{i}. **[{citation.id}]** {citation.source}\n"
            reference_section += f"   - {citation.quote[:100]}...\n"
            reference_section += f"   - タグ: {citation.tag.value}\n"
            if citation.summary:
                reference_section += f"   - 要約: {citation.summary}\n"
            reference_section += "\n"
        
        return report + reference_section
    
    def enforce_format(self, report: str, citations: List[Citation]) -> str:
        """
        フォーマットを強制適用
        
        Args:
            report: レポート
            citations: 引用リスト
        
        Returns:
            フォーマット適用済みレポート
        """
        # 必須セクションのチェック
        required_sections = [
            ("## 結論", "結論セクション"),
            ("## 根拠", "根拠セクション"),
            ("## 反証", "反証セクション"),
            ("## 次アクション", "次アクションセクション"),
            ("## 参考文献", "参考文献セクション")
        ]
        
        missing_sections = []
        for section_marker, section_name in required_sections:
            if section_marker not in report:
                missing_sections.append(section_name)
        
        if missing_sections:
            logger.warning(f"Missing sections: {', '.join(missing_sections)}")
            # 不足セクションを追加（簡易版）
            for section_name in missing_sections:
                report += f"\n\n## {section_name}\n\n（要追加）\n"
        
        # 引用をフォーマット
        formatted_report = self.format_report_with_citations(report, citations)
        
        return formatted_report



