#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
退避ルート（フェイルセーフ）システム
検索失敗・ツールエラー時の安全な終了処理
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass

from manaos_logger import get_logger
from .schemas import ResearchResults
from .budget_guard import StopReason
from .budget_guard import StopReason as BudgetStopReason

logger = get_service_logger("fail-safe")


class FailSafeMode(str, Enum):
    """フェイルセーフモード"""
    NORMAL = "normal"  # 通常モード
    NO_WEB = "no_web"  # Web検索なし（RAGのみ）
    CACHE_ONLY = "cache_only"  # キャッシュのみ
    EARLY_EXIT = "early_exit"  # 早期終了


@dataclass
class FailSafeGuard:
    """フェイルセーフガード"""
    
    max_consecutive_failures: int = 3  # 連続失敗の上限
    failure_count: int = 0
    last_failure_type: Optional[str] = None
    
    def check_failure(self, error_type: str) -> tuple[bool, Optional[FailSafeMode], str]:
        """
        失敗をチェックして退避ルートを決定
        
        Args:
            error_type: エラータイプ（search_error, tool_error, timeout等）
        
        Returns:
            (継続可能か, フェイルセーフモード, メッセージ)
        """
        if error_type == self.last_failure_type:
            self.failure_count += 1
        else:
            self.failure_count = 1
            self.last_failure_type = error_type
        
        if self.failure_count >= self.max_consecutive_failures:
            # 連続失敗が上限に達した
            if error_type == "search_error":
                return False, FailSafeMode.NO_WEB, f"検索が{self.failure_count}回連続で失敗。RAGのみで継続"
            elif error_type == "tool_error":
                return False, FailSafeMode.EARLY_EXIT, f"ツールエラーが{self.failure_count}回連続。早期終了"
            else:
                return False, FailSafeMode.EARLY_EXIT, f"エラーが{self.failure_count}回連続。早期終了"
        
        return True, None, "継続可能"
    
    def generate_partial_report(
        self,
        research_results: ResearchResults,
        stop_reason: str,
        user_query: str
    ) -> str:
        """
        部分的なレポートを生成（事故らない）
        
        Args:
            research_results: 調査結果（部分的なもの）
            stop_reason: 停止理由
            user_query: ユーザークエリ
        
        Returns:
            部分レポート
        """
        report = f"""# 調査レポート（部分結果）

**調査クエリ**: {user_query}
**停止理由**: {stop_reason}

## 現時点で言えること

"""
        
        # 収集できた情報をまとめる
        if research_results.citations:
            report += f"### 収集できた情報（{len(research_results.citations)}件）\n\n"
            for i, citation in enumerate(research_results.citations[:5], 1):
                report += f"{i}. **{citation.source}**\n"
                report += f"   - {citation.summary}\n\n"
        
        if research_results.summaries:
            report += "### 要約\n\n"
            for summary in research_results.summaries[:3]:
                report += f"- **{summary.source}**: {summary.summary}\n\n"
        
        # 不明な点
        report += """## 不明な点

以下の点については、追加の調査が必要です：

"""
        
        if stop_reason == "search_error":
            report += "- Web検索が失敗したため、最新情報が取得できませんでした\n"
            report += "- RAG（既存知識ベース）からの情報のみで構成されています\n"
        elif stop_reason == "tool_error":
            report += "- ツールエラーが発生したため、一部の情報が取得できませんでした\n"
        
        report += f"\n## 次に調べるべきこと\n\n"
        report += f"- {user_query}について、より詳細な調査が必要です\n"
        report += "- 特に、最新情報や公式ドキュメントの確認が推奨されます\n"
        
        # 参考文献
        if research_results.citations:
            report += "\n## 参考文献（部分）\n\n"
            for i, citation in enumerate(research_results.citations[:5], 1):
                report += f"{i}. {citation.source}\n"
        
        return report
    
    def reset(self):
        """リセット"""
        self.failure_count = 0
        self.last_failure_type = None

