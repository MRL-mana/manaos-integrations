#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回帰テストセット（Regression Tests）
10問セット（罠つき）で性能を自動検証
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from enum import Enum

from manaos_logger import get_logger

logger = get_logger(__name__)


class TestCategory(str, Enum):
    """テストカテゴリ"""
    TECHNICAL = "technical"  # 技術：仕様比較、手順、トラブルシュート
    BUSINESS = "business"  # ビジネス：比較、費用対効果
    LATEST_REQUIRED = "latest_required"  # 最新情報が必要
    TRAP = "trap"  # 罠：誤情報が混じるテーマ


@dataclass
class RegressionTest:
    """回帰テストケース"""
    test_id: str
    category: TestCategory
    query: str
    expected_pass: bool  # 合格が期待されるか
    expected_min_score: int  # 最低スコア
    expected_citations: int  # 最低引用数
    expected_counter_argument: bool  # 反証候補が必要か
    trap_description: Optional[str] = None  # 罠の説明
    expected_behavior: Optional[str] = None  # 期待される動作


# 回帰テスト10問セット（ManaOS用途：RDP/自動化/LLM運用/セキュリティ寄り）
REGRESSION_TESTS = [
    # 1. 技術：仕様比較
    RegressionTest(
        test_id="test_001",
        category=TestCategory.TECHNICAL,
        query="RDPとTailscaleの違いを技術的に比較して。セキュリティ、パフォーマンス、使いやすさの観点から根拠付きでまとめて",
        expected_pass=True,
        expected_min_score=21,  # 30項目中70%以上
        expected_citations=5,
        expected_counter_argument=True,
        expected_behavior="両者のメリデメを明確に比較し、反証候補（デメリット）も含める"
    ),
    
    # 2. 技術：手順
    RegressionTest(
        test_id="test_002",
        category=TestCategory.TECHNICAL,
        query="Windows ServerでRDP接続を有効化する手順を、公式ドキュメントを参照して根拠付きで説明して",
        expected_pass=True,
        expected_min_score=21,
        expected_citations=3,
        expected_counter_argument=False,
        expected_behavior="公式ドキュメントを優先的に引用し、手順が明確"
    ),
    
    # 3. 技術：トラブルシュート
    RegressionTest(
        test_id="test_003",
        category=TestCategory.TECHNICAL,
        query="RDP接続がタイムアウトする原因と対処法を、公式情報とコミュニティの知見を参照してまとめて",
        expected_pass=True,
        expected_min_score=21,
        expected_citations=4,
        expected_counter_argument=True,
        trap_description="古い情報や誤情報が混じりやすいテーマ",
        expected_behavior="最新の公式情報を優先し、古い情報には注意書き"
    ),
    
    # 4. ビジネス：比較
    RegressionTest(
        test_id="test_004",
        category=TestCategory.BUSINESS,
        query="RDPとVPN（Tailscale/ZeroTier）の費用対効果を比較して。初期費用、運用コスト、セキュリティリスクを含めて",
        expected_pass=True,
        expected_min_score=21,
        expected_citations=5,
        expected_counter_argument=True,
        expected_behavior="コストとリスクを明確に比較"
    ),
    
    # 5. ビジネス：費用対効果
    RegressionTest(
        test_id="test_005",
        category=TestCategory.BUSINESS,
        query="ローカルLLM（Ollama）とクラウドLLM（OpenAI API）の運用コストを比較して。月間1000リクエスト想定で",
        expected_pass=True,
        expected_min_score=21,
        expected_citations=4,
        expected_counter_argument=True,
        expected_behavior="具体的な数値と根拠を提示"
    ),
    
    # 6. 最新情報が必要（罠：古い情報を出さない）
    RegressionTest(
        test_id="test_006",
        category=TestCategory.LATEST_REQUIRED,
        query="2026年のWindowsのRDP周りの変更点やセキュリティアップデートについて調べて。最新情報のみで、不明な点は明確に",
        expected_pass=True,
        expected_min_score=18,  # 最新情報が不明な場合は低スコアでもOK
        expected_citations=3,
        expected_counter_argument=False,
        trap_description="最新情報が不明な場合、嘘を書かずに「要Web確認」と明記できるか",
        expected_behavior="最新情報が不明な場合は「要Web確認」と明記し、嘘を書かない"
    ),
    
    # 7. 最新情報が必要（罠：古い情報に注意書き）
    RegressionTest(
        test_id="test_007",
        category=TestCategory.LATEST_REQUIRED,
        query="Python 3.12の非同期処理の新機能について調べて。公式ドキュメントを参照して",
        expected_pass=True,
        expected_min_score=21,
        expected_citations=3,
        expected_counter_argument=False,
        trap_description="古い情報（Python 3.10以前）を最新として扱わない",
        expected_behavior="バージョン番号を明確にし、古い情報には注意書き"
    ),
    
    # 8. 罠：誤情報が混じるテーマ（反証を出せるか）
    RegressionTest(
        test_id="test_008",
        category=TestCategory.TRAP,
        query="「RDPは安全」という主張について、根拠と反証の両方を調べて。セキュリティリスクも含めて",
        expected_pass=True,
        expected_min_score=21,
        expected_citations=6,
        expected_counter_argument=True,
        trap_description="一方の主張だけを信じず、反証も探せるか",
        expected_behavior="「安全」と「リスク」の両方を検討し、反証候補を明確に"
    ),
    
    # 9. 罠：まとめサイトの情報を信じすぎない
    RegressionTest(
        test_id="test_009",
        category=TestCategory.TRAP,
        query="n8nの自動化ワークフローのベストプラクティスについて調べて。公式ドキュメントを優先して",
        expected_pass=True,
        expected_min_score=21,
        expected_citations=4,
        expected_counter_argument=False,
        trap_description="まとめサイトの情報を公式情報として扱わない",
        expected_behavior="公式ドキュメントを優先的に引用"
    ),
    
    # 10. 短い調査（予算ガードテスト）
    RegressionTest(
        test_id="test_010",
        category=TestCategory.TECHNICAL,
        query="Pythonの非同期処理を「根拠付きで」要点だけまとめて。短時間で完了すること",
        expected_pass=True,
        expected_min_score=18,  # 短い調査なので低めでもOK
        expected_citations=3,
        expected_counter_argument=False,
        expected_behavior="短時間で完了し、予算を超過しない"
    ),
]


class RegressionTestRunner:
    """回帰テストランナー"""
    
    def __init__(self, orchestrator):
        """
        初期化
        
        Args:
            orchestrator: StepDeepResearchOrchestratorインスタンス
        """
        self.orchestrator = orchestrator
        self.results = []
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        全テスト実行
        
        Returns:
            テスト結果サマリー
        """
        logger.info(f"Running {len(REGRESSION_TESTS)} regression tests...")
        
        for test in REGRESSION_TESTS:
            result = self.run_test(test)
            self.results.append(result)
        
        return self.generate_summary()
    
    def run_test(self, test: RegressionTest) -> Dict[str, Any]:
        """
        単一テスト実行
        
        Args:
            test: テストケース
        
        Returns:
            テスト結果
        """
        logger.info(f"[{test.test_id}] Running: {test.query[:50]}...")
        
        try:
            # ジョブ作成・実行
            job_id = self.orchestrator.create_job(test.query)
            result = self.orchestrator.execute_job(job_id)
            
            # 検証
            validation = self.validate_result(test, result)
            
            return {
                "test_id": test.test_id,
                "category": test.category.value,
                "query": test.query,
                "passed": validation["passed"],
                "score": result.get("score", 0),
                "pass": result.get("pass", False),
                "citations_count": self._count_citations(result.get("report", "")),
                "has_counter_argument": self._has_counter_argument(result.get("report", "")),
                "spent_budget": result.get("spent_budget", {}),
                "stop_reason": result.get("stop_reason", ""),
                "validation": validation,
                "trap_description": test.trap_description
            }
            
        except Exception as e:
            logger.error(f"[{test.test_id}] Test failed with error: {e}")
            return {
                "test_id": test.test_id,
                "category": test.category.value,
                "query": test.query,
                "passed": False,
                "error": str(e),
                "validation": {"passed": False, "errors": [f"実行エラー: {e}"]}
            }
    
    def validate_result(self, test: RegressionTest, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        結果を検証
        
        Args:
            test: テストケース
            result: 実行結果
        
        Returns:
            検証結果
        """
        errors = []
        
        # スコアチェック
        score = result.get("score", 0)
        if score < test.expected_min_score:
            errors.append(f"スコア不足: {score} < {test.expected_min_score}")
        
        # 合格チェック
        if test.expected_pass and not result.get("pass", False):
            errors.append("合格が期待されたが不合格")
        
        # 引用数チェック
        report = result.get("report", "")
        citations_count = self._count_citations(report)
        if citations_count < test.expected_citations:
            errors.append(f"引用数不足: {citations_count} < {test.expected_citations}")
        
        # 反証候補チェック
        if test.expected_counter_argument:
            if not self._has_counter_argument(report):
                errors.append("反証候補が不足")
        
        # 罠チェック
        if test.trap_description:
            trap_passed = self._check_trap(test, result)
            if not trap_passed:
                errors.append(f"罠検出失敗: {test.trap_description}")
        
        return {
            "passed": len(errors) == 0,
            "errors": errors
        }
    
    def _count_citations(self, report: str) -> int:
        """レポート内の引用数をカウント"""
        # 参考文献セクションから数える
        import re
        ref_pattern = r"##\s*参考文献[^\n]*\n(.*?)(?=##|\Z)"
        matches = re.findall(ref_pattern, report, re.DOTALL | re.IGNORECASE)
        if matches:
            ref_section = matches[0]
            # 番号付きリストを数える
            return len(re.findall(r'^\d+\.', ref_section, re.MULTILINE))
        return 0
    
    def _has_counter_argument(self, report: str) -> bool:
        """反証候補があるかチェック"""
        counter_keywords = ["反証", "反対", "注意点", "リスク", "課題", "問題点", "デメリット"]
        report_lower = report.lower()
        return any(keyword in report_lower for keyword in counter_keywords)
    
    def _check_trap(self, test: RegressionTest, result: Dict[str, Any]) -> bool:
        """
        罠を回避できたかチェック
        
        Args:
            test: テストケース
            result: 実行結果
        
        Returns:
            罠を回避できたか
        """
        report = result.get("report", "").lower()
        
        if test.test_id == "test_006":
            # 最新情報が不明な場合は「要Web確認」と明記
            return "要web確認" in report or "不明" in report or "確認" in report
        
        elif test.test_id == "test_007":
            # バージョン番号が明確
            return "3.12" in report or "3.11" in report
        
        elif test.test_id == "test_008":
            # 反証がある
            return self._has_counter_argument(result.get("report", ""))
        
        elif test.test_id == "test_009":
            # 公式ドキュメントを引用
            return "公式" in report or "official" in report.lower()
        
        return True
    
    def generate_summary(self) -> Dict[str, Any]:
        """
        テスト結果サマリー生成
        
        Returns:
            サマリー
        """
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("passed", False))
        failed = total - passed
        
        # カテゴリ別集計
        by_category = {}
        for result in self.results:
            category = result.get("category", "unknown")
            if category not in by_category:
                by_category[category] = {"total": 0, "passed": 0}
            by_category[category]["total"] += 1
            if result.get("passed", False):
                by_category[category]["passed"] += 1
        
        # 指標計算
        scores = [r.get("score", 0) for r in self.results if "score" in r]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        citations_counts = [r.get("citations_count", 0) for r in self.results]
        avg_citations = sum(citations_counts) / len(citations_counts) if citations_counts else 0
        
        # 予算使用量
        total_tokens = sum(
            r.get("spent_budget", {}).get("tokens", {}).get("used", 0)
            for r in self.results
        )
        avg_tokens = total_tokens / total if total > 0 else 0
        
        # 致命エラー率
        fatal_errors = sum(1 for r in self.results if "error" in r)
        fatal_error_rate = fatal_errors / total if total > 0 else 0
        
        # 引用カバレッジ
        reports_with_citations = sum(1 for r in self.results if r.get("citations_count", 0) > 0)
        citation_coverage = reports_with_citations / total if total > 0 else 0
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0,
            "by_category": by_category,
            "metrics": {
                "avg_score": avg_score,
                "avg_citations": avg_citations,
                "avg_cost_tokens": avg_tokens,
                "fatal_error_rate": fatal_error_rate,
                "citation_coverage": citation_coverage
            },
            "results": self.results
        }


