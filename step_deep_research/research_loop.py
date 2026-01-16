#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
調査ループ（Research Loop）
"""

from typing import Dict, Any, Optional
from datetime import datetime

from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from .schemas import Plan, ResearchResults, ResearchIteration, JobBudget
from .searcher import Searcher
from .reader import Reader
from .verifier import Verifier
from .writer import Writer
from .budget_guard import BudgetGuard, StopReason
from .fail_safe import FailSafeGuard

logger = get_logger(__name__)
error_handler = ManaOSErrorHandler("StepDeepResearchLoop")


class ResearchLoop:
    """調査ループ（ReAct形式）"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: Research Loop設定
        """
        self.config = config
        self.max_iterations = config.get("max_iterations", 10)
        self.iteration_timeout_seconds = config.get("iteration_timeout_seconds", 300)
        
        # コンポーネント初期化
        self.searcher = Searcher(config.get("searcher", {}))
        self.reader = Reader(config.get("reader", {}))
        self.verifier = Verifier(config.get("verifier", {}))
        self.writer = Writer(config.get("writer", {}))
    
    def execute(
        self,
        plan: Plan,
        budget: JobBudget,
        budget_guard: Optional[BudgetGuard] = None,
        fail_safe_guard: Optional[FailSafeGuard] = None
    ) -> ResearchResults:
        """
        調査ループ実行
        
        Args:
            plan: 調査計画
            budget: 予算管理
        
        Returns:
            調査結果
        """
        results = ResearchResults()
        
        try:
            for iteration in range(1, self.max_iterations + 1):
                logger.info(f"Research iteration {iteration}/{self.max_iterations}")
                
                # 予算ガードチェック
                if budget_guard:
                    budget_guard.record_iteration()
                    can_continue, stop_reason, stop_message = budget_guard.check_budget(budget)
                    if not can_continue:
                        logger.warning(f"Budget guard triggered: {stop_message}")
                        results.stop_reason = stop_reason
                        break
                elif not self._check_budget(budget):
                    logger.warning("Budget exceeded, stopping research loop")
                    results.stop_reason = StopReason.BUDGET_EXCEEDED
                    break
                
                # 現在のタスクを取得
                current_todo = None
                if iteration <= len(plan.todo):
                    current_todo = plan.todo[iteration - 1]
                else:
                    # タスクが終わったら収束判定
                    if self._is_converged(results, iteration):
                        logger.info("Research converged")
                        break
                    continue
                
                # 1. Search
                search_results = []
                if current_todo and current_todo.tool.value != "none":
                    if budget_guard:
                        budget_guard.record_search(1)
                    
                    try:
                        search_results = self.searcher.search(
                            query=current_todo.description,
                            tool=current_todo.tool,
                            max_results=10
                        )
                        budget.used_searches += 1
                        
                        # フェイルセーフチェック
                        if fail_safe_guard and len(search_results) == 0:
                            can_continue, fail_safe_mode, fail_message = fail_safe_guard.check_failure("search_error")
                            if not can_continue:
                                logger.warning(f"Fail-safe triggered: {fail_message}")
                                results.stop_reason = StopReason.BUDGET_EXCEEDED  # 暫定
                                break
                    except Exception as e:
                        logger.warning(f"Search error: {e}")
                        if fail_safe_guard:
                            can_continue, fail_safe_mode, fail_message = fail_safe_guard.check_failure("search_error")
                            if not can_continue:
                                logger.warning(f"Fail-safe triggered: {fail_message}")
                                results.stop_reason = StopReason.BUDGET_EXCEEDED  # 暫定
                                break
                        continue
                    
                    # ソース数記録
                    if budget_guard:
                        budget_guard.record_sources(len(search_results))
                
                # 2. Read & Extract
                citations = self.reader.extract_citations(search_results)
                summaries = self.reader.create_summaries(search_results)
                
                results.citations.extend(citations)
                results.summaries.extend(summaries)
                
                # 3. Verify
                contradictions = self.verifier.check_contradictions(
                    citations=citations,
                    summaries=summaries
                )
                results.contradictions.extend(contradictions)
                
                # 反証候補と信頼性評価
                if iteration == self.max_iterations or self._is_converged(results, iteration):
                    counter_arguments = self.verifier.find_counter_arguments(
                        citations=results.citations,
                        summaries=results.summaries
                    )
                    results.counter_arguments.extend(counter_arguments)
                    
                    reliability_assessments = self.verifier.assess_reliability(
                        citations=results.citations
                    )
                    results.reliability_assessments.extend(reliability_assessments)
                
                # イテレーション記録
                iteration_result = ResearchIteration(
                    iteration=iteration,
                    timestamp=datetime.now(),
                    search_results=search_results,
                    citations=citations,
                    summaries=summaries,
                    contradictions=contradictions
                )
                results.iterations.append(iteration_result)
                
                # 収束判定
                if self._is_converged(results, iteration):
                    logger.info("Research converged")
                    if not hasattr(results, 'stop_reason'):
                        results.stop_reason = StopReason.QUALITY_PASSED
                    break
            
            # 最終的な停止理由が設定されていない場合
            if not hasattr(results, 'stop_reason'):
                results.stop_reason = StopReason.MAX_ITERATIONS
            
            logger.info(f"Research loop completed: {len(results.citations)} citations, {len(results.summaries)} summaries (stop_reason: {results.stop_reason.value})")
            return results
            
        except Exception as e:
            error_handler.handle_error(
                e,
                "Research loop execution failed",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.HIGH
            )
            return results  # 部分的な結果を返す
    
    def _check_budget(self, budget: JobBudget) -> bool:
        """
        予算チェック
        
        Args:
            budget: 予算管理
        
        Returns:
            予算内かどうか
        """
        return (
            budget.used_tokens < budget.max_tokens and
            budget.used_searches < budget.max_searches and
            budget.elapsed_seconds < budget.max_time_minutes * 60
        )
    
    def _is_converged(self, results: ResearchResults, iteration: int) -> bool:
        """
        収束判定
        
        Args:
            results: 調査結果
            iteration: 現在のイテレーション
        
        Returns:
            収束したかどうか
        """
        # 最低限の情報が集まったか
        min_citations = 5
        min_summaries = 3
        
        if len(results.citations) >= min_citations and len(results.summaries) >= min_summaries:
            # 十分な情報が集まった
            return True
        
        # イテレーションが最大に達した
        if iteration >= self.max_iterations:
            return True
        
        return False

