#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
オーケストレーター（Orchestrator）
"""

import json
import uuid
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from .schemas import (
    JobState, JobBudget, JobStatus, Checkpoint, Plan, ResearchResults, CritiqueResult, Citation
)
from .planner import PlannerAgent
from .research_loop import ResearchLoop
from .critic import CriticAgent
from .writer import Writer
from .utils import save_jsonl
from .trinity_integration import TrinityIntegration, TrinityAgent
from .reverse_data_generator import ReverseDataGenerator
from .budget_guard import BudgetGuard, StopReason
from .fail_safe import FailSafeGuard, FailSafeMode
from .cache_system import CacheSystem

logger = get_service_logger("orchestrator")
error_handler = ManaOSErrorHandler("StepDeepResearchOrchestrator")


class StepDeepResearchOrchestrator:
    """Step-Deep-Research オーケストレーター"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: 設定データ
        """
        self.config = config
        self.orchestrator_config = config.get("orchestrator", {})
        
        # ログディレクトリ
        self.log_dir = Path("logs/step_deep_research/jobs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.report_dir = Path("logs/step_deep_research/reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # コンポーネント初期化
        self.planner = PlannerAgent(config.get("planner", {}))
        self.research_loop = ResearchLoop(config.get("research_loop", {}))
        self.critic = CriticAgent(config.get("critic", {}))
        self.writer = Writer(config.get("research_loop", {}).get("writer", {}))
        
        # Trinity統合
        self.trinity = TrinityIntegration(config)
        
        # 逆算データ生成器
        self.reverse_generator = ReverseDataGenerator(config)
        
        # キャッシュシステム初期化
        cache_dir = config.get("memory_integration", {}).get("cache_dir", "logs/step_deep_research/cache")
        self.cache_system = CacheSystem(cache_dir=cache_dir)
        
        # フェイルセーフガード初期化
        self.fail_safe_guard = FailSafeGuard()
        
        # 予算ガード初期化
        budget_config = self.orchestrator_config
        self.budget_guard_template = BudgetGuard(
            max_iterations=config.get("research_loop", {}).get("max_iterations", 10),
            max_search_calls=budget_config.get("max_search_queries", 20),
            max_sources=50,  # デフォルト値
            time_budget_sec=budget_config.get("max_time_minutes", 60) * 60,
            token_budget=budget_config.get("max_budget_tokens", 50000)
        )
        
        # ジョブ状態管理
        self.jobs: Dict[str, JobState] = {}
    
    def create_job(self, user_query: str) -> str:
        """
        ジョブ作成
        
        Args:
            user_query: ユーザーの調査依頼
        
        Returns:
            ジョブID
        """
        job_id = str(uuid.uuid4())
        
        # 予算設定
        budget = JobBudget(
            max_tokens=self.orchestrator_config.get("max_budget_tokens", 50000),
            max_searches=self.orchestrator_config.get("max_search_queries", 20),
            max_time_minutes=self.orchestrator_config.get("max_time_minutes", 60)
        )
        
        # 予算ガード作成
        budget_guard = BudgetGuard(
            max_iterations=self.budget_guard_template.max_iterations,
            max_search_calls=self.budget_guard_template.max_search_calls,
            max_sources=self.budget_guard_template.max_sources,
            time_budget_sec=self.budget_guard_template.time_budget_sec,
            token_budget=self.budget_guard_template.token_budget
        )
        
        # ジョブ状態作成
        job_state = JobState(
            job_id=job_id,
            user_query=user_query,
            status=JobStatus.PENDING,
            budget=budget,
            created_at=datetime.now()
        )
        
        # 予算ガードをジョブ状態に追加（動的属性として）
        job_state.budget_guard = budget_guard
        
        self.jobs[job_id] = job_state
        
        # ログファイル作成
        log_file = self.log_dir / f"{job_id}.jsonl"
        self._save_checkpoint(job_state, log_file)
        
        logger.info(f"Job created: {job_id}")
        return job_id
    
    def execute_job(self, job_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        ジョブ実行
        
        Args:
            job_id: ジョブID
        
        Returns:
            実行結果
        """
        job_state = self.jobs.get(job_id)
        if not job_state:
            raise ValueError(f"Job not found: {job_id}")
        
        log_file = self.log_dir / f"{job_id}.jsonl"
        start_time = time.time()
        
        # キャッシュチェック
        if use_cache:
            cache_key = self.cache_system.generate_cache_key(job_state.user_query)
            cache_data = self.cache_system.get_cache(cache_key)
            
            if cache_data and self.cache_system.should_use_cache(cache_data):
                logger.info(f"[{job_id}] Cache hit, using cached result")
                # Criticで軽く再チェック
                report = cache_data["report"]
                citations = [Citation(**c) for c in cache_data.get("citations", [])]
                critique_result = self.critic.evaluate(report, iteration=1, citations=citations)
                
                return {
                    "job_id": job_id,
                    "status": "completed",
                    "report": report,
                    "score": critique_result.score,
                    "pass": critique_result.is_passed,
                    "report_path": cache_data.get("metadata", {}).get("report_path", ""),
                    "spent_budget": {"iterations": {"used": 0, "max": 0, "remaining": 0}},
                    "stop_reason": "cache_hit",
                    "cached": True
                }
        
        try:
            # 1. Planning (Remi担当)
            job_state.status = JobStatus.PLANNING
            self._save_checkpoint(job_state, log_file)
            logger.info(f"[{job_id}] Planning started (Remi)")
            
            agent = self.trinity.get_agent_for_planning()
            self.trinity.log_agent_activity(agent, "Planning started", {"job_id": job_id})
            
            plan = self.planner.create_plan(job_state.user_query)
            job_state.planner_output = plan
            
            self.trinity.log_agent_activity(agent, "Planning completed", {"tasks": len(plan.todo)})
            
            # 予算ガードチェック
            budget_guard = job_state.budget_guard
            can_continue, stop_reason, stop_message = budget_guard.check_budget(job_state.budget)
            if not can_continue:
                raise Exception(f"Budget guard triggered: {stop_message} (reason: {stop_reason.value})")
            
            # 2. Research Loop (Luna担当)
            job_state.status = JobStatus.RESEARCHING
            self._save_checkpoint(job_state, log_file)
            logger.info(f"[{job_id}] Research started (Luna)")
            
            agent = self.trinity.get_agent_for_search()
            self.trinity.log_agent_activity(agent, "Research started", {"job_id": job_id})
            
            # 予算ガードをResearch Loopに渡す
            research_results = self.research_loop.execute(
                plan=plan,
                budget=job_state.budget,
                budget_guard=budget_guard
            )
            job_state.research_output = research_results
            
            # 予算ガードの最終状態を記録
            if hasattr(research_results, 'stop_reason'):
                job_state.stop_reason = research_results.stop_reason
            
            self.trinity.log_agent_activity(
                agent,
                "Research completed",
                {
                    "citations": len(research_results.citations),
                    "summaries": len(research_results.summaries)
                }
            )
            
            # 3. Writing (Remi担当)
            job_state.status = JobStatus.WRITING
            self._save_checkpoint(job_state, log_file)
            logger.info(f"[{job_id}] Writing started (Remi)")
            
            agent = self.trinity.get_agent_for_writing()
            self.trinity.log_agent_activity(agent, "Writing started", {"job_id": job_id})
            
            report = self.writer.create_report(
                research_results=research_results,
                plan=plan,
                job_id=job_id,
                user_query=job_state.user_query
            )
            job_state.writer_output = report
            
            self.trinity.log_agent_activity(agent, "Writing completed", {"report_length": len(report)})
            
            # 4. Critiquing (Mina担当)
            job_state.status = JobStatus.CRITIQUING
            self._save_checkpoint(job_state, log_file)
            logger.info(f"[{job_id}] Critiquing started (Mina)")
            
            agent = self.trinity.get_agent_for_critique()
            self.trinity.log_agent_activity(agent, "Critiquing started", {"job_id": job_id})
            
            critique_results = []
            for iteration in range(1, self.critic.max_iterations + 1):
                # 引用リストをCriticに渡す（Critic Guard用）
                citations = research_results.citations if research_results else []
                critique_result = self.critic.evaluate(report, iteration=iteration, citations=citations)
                critique_results.append(critique_result)
                
                if critique_result.is_passed:
                    logger.info(f"[{job_id}] Critique passed: {critique_result.score}")
                    self.trinity.log_agent_activity(
                        agent,
                        "Critique passed",
                        {"score": critique_result.score, "iteration": iteration}
                    )
                    break
                else:
                    logger.info(f"[{job_id}] Critique failed: {critique_result.score}, revising...")
                    self.trinity.log_agent_activity(
                        agent,
                        "Critique failed, revising",
                        {"score": critique_result.score, "iteration": iteration}
                    )
                    # 修正 (Remi担当)
                    revise_agent = self.trinity.get_agent_for_writing()
                    self.trinity.log_agent_activity(revise_agent, "Revising report", {"iteration": iteration})
                    report = self.writer.revise_report(
                        original_report=report,
                        fix_requests=critique_result.fix_requests
                    )
                    job_state.writer_output = report
            
            job_state.critic_output = critique_results
            final_critique = critique_results[-1]
            
            self.trinity.log_agent_activity(
                agent,
                "Critiquing completed",
                {"final_score": final_critique.score, "pass": final_critique.is_passed}
            )
            
            # 5. 完了処理
            if final_critique.is_passed:
                job_state.status = JobStatus.COMPLETED
                report_path = self._save_final_report(job_id, report)
                job_state.final_report_path = str(report_path)
                
                # キャッシュ保存（合格レポートのみ）
                if use_cache:
                    cache_key = self.cache_system.generate_cache_key(job_state.user_query)
                    citations_data = [
                        {
                            "id": cite.id,
                            "source": cite.source,
                            "quote": cite.quote,
                            "summary": cite.summary,
                            "tag": cite.tag.value
                        }
                        for cite in research_results.citations
                    ]
                    self.cache_system.set_cache(
                        cache_key=cache_key,
                        report=report,
                        score=final_critique.score,
                        citations=citations_data,
                        metadata={"report_path": str(report_path), "job_id": job_id}
                    )
            else:
                job_state.status = JobStatus.COMPLETED  # 不合格でも完了とする
                report_path = self._save_final_report(job_id, report)
                job_state.final_report_path = str(report_path)
                logger.warning(f"[{job_id}] Report did not pass critique: {final_critique.score}")
            
            # 予算更新
            job_state.budget.elapsed_seconds = time.time() - start_time
            
            # 予算ガードの最終状態を取得
            spent_budget = budget_guard.get_spent_budget()
            stop_reason = getattr(job_state, 'stop_reason', StopReason.QUALITY_PASSED if final_critique.is_passed else StopReason.BUDGET_EXCEEDED)
            
            # 6. 逆算データ生成（良いレポートの場合）
            if final_critique.is_passed and self.config.get("memory_integration", {}).get("auto_save_reports", True):
                try:
                    learning_data = self.reverse_generator.generate_from_report(
                        report_path=report_path,
                        job_id=job_id,
                        critique_result=final_critique,
                        plan=plan,
                        research_results=research_results
                    )
                    if learning_data:
                        logger.info(f"[{job_id}] Learning data generated")
                except Exception as e:
                    logger.warning(f"[{job_id}] Failed to generate learning data: {e}")
            
            self._save_checkpoint(job_state, log_file)
            
            return {
                "job_id": job_id,
                "status": job_state.status.value,
                "report": report,
                "score": final_critique.score,
                "pass": final_critique.is_passed,
                "report_path": str(report_path),
                "spent_budget": spent_budget,
                "stop_reason": stop_reason.value,
                "budget_used": {
                    "tokens": job_state.budget.used_tokens,
                    "searches": job_state.budget.used_searches,
                    "elapsed_seconds": job_state.budget.elapsed_seconds
                }
            }
            
        except Exception as e:
            job_state.status = JobStatus.FAILED
            error_handler.handle_error(
                e,
                f"Job execution failed: {job_id}",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.HIGH
            )
            self._save_checkpoint(job_state, log_file)
            raise
    
    def _check_budget(self, budget: JobBudget) -> bool:
        """予算チェック"""
        return (
            budget.used_tokens < budget.max_tokens and
            budget.used_searches < budget.max_searches and
            budget.elapsed_seconds < budget.max_time_minutes * 60
        )
    
    def _save_checkpoint(self, job_state: JobState, log_file: Path):
        """チェックポイント保存"""
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "status": job_state.status.value,
            "budget": {
                "used_tokens": job_state.budget.used_tokens,
                "used_searches": job_state.budget.used_searches,
                "elapsed_seconds": job_state.budget.elapsed_seconds
            }
        }
        save_jsonl(checkpoint, log_file)
    
    def _save_final_report(self, job_id: str, report: str) -> Path:
        """最終レポート保存"""
        report_file = self.report_dir / f"{job_id}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"Report saved: {report_file}")
        return report_file
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        ジョブステータス取得
        
        Args:
            job_id: ジョブID
        
        Returns:
            ジョブステータス
        """
        job_state = self.jobs.get(job_id)
        if not job_state:
            return None
        
        return {
            "job_id": job_id,
            "status": job_state.status.value,
            "created_at": job_state.created_at.isoformat(),
            "budget": {
                "used_tokens": job_state.budget.used_tokens,
                "used_searches": job_state.budget.used_searches,
                "elapsed_seconds": job_state.budget.elapsed_seconds
            }
        }

