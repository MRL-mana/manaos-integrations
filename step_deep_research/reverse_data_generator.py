#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
逆算データ生成
良いレポートから学習データ（依頼文＋計画＋途中ログ）を生成
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from .schemas import Plan, ResearchResults, CritiqueResult

logger = get_service_logger("reverse-data-generator")
error_handler = ManaOSErrorHandler("ReverseDataGenerator")


class ReverseDataGenerator:
    """逆算データ生成器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: 設定データ
        """
        self.config = config
        self.learning_data_path = Path(
            config.get("memory_integration", {}).get("learning_data_path", "logs/step_deep_research/learning_data/")
        )
        self.learning_data_path.mkdir(parents=True, exist_ok=True)
        
        # 良いレポートの判定基準
        self.min_score_threshold = 21  # 30項目中70%以上
        self.min_citations = 5
        self.min_summaries = 3
    
    def generate_from_report(
        self,
        report_path: Path,
        job_id: str,
        critique_result: CritiqueResult,
        plan: Optional[Plan] = None,
        research_results: Optional[ResearchResults] = None
    ) -> Optional[Dict[str, Any]]:
        """
        レポートから逆算データを生成
        
        Args:
            report_path: レポートファイルのパス
            job_id: ジョブID
            critique_result: 採点結果
            plan: 調査計画（オプション）
            research_results: 調査結果（オプション）
        
        Returns:
            学習データ（Noneの場合は生成しない）
        """
        # 良いレポートかチェック
        if not self._is_good_report(critique_result, research_results):
            logger.info(f"Report {job_id} does not meet quality threshold, skipping")
            return None
        
        try:
            # レポート読み込み
            with open(report_path, "r", encoding="utf-8") as f:
                report_content = f.read()
            
            # 逆算データ生成
            learning_data = {
                "generated_at": datetime.now().isoformat(),
                "source_job_id": job_id,
                "source_report_path": str(report_path),
                "score": critique_result.score,
                "pass": critique_result.is_passed,
                
                # 逆算された依頼文
                "inferred_query": self._infer_query_from_report(report_content),
                
                # 逆算された計画
                "inferred_plan": self._infer_plan_from_report(report_content, plan),
                
                # 逆算された調査ログ
                "inferred_research_log": self._infer_research_log_from_report(
                    report_content,
                    research_results
                ),
                
                # 元のレポート（参考用）
                "original_report": report_content[:1000],  # 最初の1000文字のみ
                
                # メタデータ
                "metadata": {
                    "citations_count": len(research_results.citations) if research_results else 0,
                    "summaries_count": len(research_results.summaries) if research_results else 0,
                    "contradictions_count": len(research_results.contradictions) if research_results else 0,
                }
            }
            
            # 保存
            self._save_learning_data(learning_data, job_id)
            
            logger.info(f"Learning data generated from report {job_id}")
            return learning_data
            
        except Exception as e:
            error_handler.handle_error(
                e,
                f"Failed to generate learning data from {report_path}",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.MEDIUM
            )
            return None
    
    def _is_good_report(
        self,
        critique_result: CritiqueResult,
        research_results: Optional[ResearchResults]
    ) -> bool:
        """
        良いレポートか判定
        
        Args:
            critique_result: 採点結果
            research_results: 調査結果
        
        Returns:
            良いレポートかどうか
        """
        # スコアチェック
        if critique_result.score < self.min_score_threshold:
            return False
        
        # 合格チェック
        if not critique_result.is_passed:
            return False
        
        # 情報量チェック
        if research_results:
            if len(research_results.citations) < self.min_citations:
                return False
            if len(research_results.summaries) < self.min_summaries:
                return False
        
        return True
    
    def _infer_query_from_report(self, report_content: str) -> str:
        """
        レポートから依頼文を逆算
        
        Args:
            report_content: レポート内容
        
        Returns:
            推測された依頼文
        """
        # レポートのタイトルや目標から推測
        lines = report_content.split("\n")
        
        # "# 調査目標" セクションを探す
        for i, line in enumerate(lines):
            if "調査目標" in line or "goal" in line.lower():
                # 次の数行から目標を抽出
                for j in range(i + 1, min(i + 5, len(lines))):
                    if lines[j].strip() and not lines[j].startswith("#"):
                        return lines[j].strip()
        
        # タイトルから推測
        if lines and lines[0].startswith("#"):
            title = lines[0].replace("#", "").strip()
            return f"{title}について調べて"
        
        return "調査依頼（自動生成）"
    
    def _infer_plan_from_report(self, report_content: str, plan: Optional[Plan] = None) -> Dict[str, Any]:
        """
        レポートから計画を逆算
        
        Args:
            report_content: レポート内容
            plan: 元の計画（あれば使用）
        
        Returns:
            推測された計画
        """
        if plan:
            # 元の計画がある場合はそれを使用
            return {
                "goal": plan.goal,
                "todo_count": len(plan.todo),
                "estimated_time_minutes": plan.estimated_time_minutes,
                "estimated_cost_tokens": plan.estimated_cost_tokens
            }
        
        # レポートから推測
        inferred = {
            "goal": "",
            "todo_count": 0,
            "estimated_time_minutes": 60,
            "estimated_cost_tokens": 30000
        }
        
        # 実装手順セクションからタスク数を推測
        if "実装手順" in report_content or "implementation" in report_content.lower():
            # ステップ番号を数える
            step_count = report_content.count("ステップ") + report_content.count("Step")
            inferred["todo_count"] = max(step_count, 5)
        
        return inferred
    
    def _infer_research_log_from_report(
        self,
        report_content: str,
        research_results: Optional[ResearchResults] = None
    ) -> Dict[str, Any]:
        """
        レポートから調査ログを逆算
        
        Args:
            report_content: レポート内容
            research_results: 調査結果（あれば使用）
        
        Returns:
            推測された調査ログ
        """
        if research_results:
            return {
                "citations_count": len(research_results.citations),
                "summaries_count": len(research_results.summaries),
                "contradictions_count": len(research_results.contradictions),
                "counter_arguments_count": len(research_results.counter_arguments),
                "iterations_count": len(research_results.iterations)
            }
        
        # レポートから推測
        inferred = {
            "citations_count": report_content.count("出典") + report_content.count("引用"),
            "summaries_count": report_content.count("要約"),
            "contradictions_count": 0,
            "counter_arguments_count": report_content.count("反証"),
            "iterations_count": 5  # デフォルト
        }
        
        return inferred
    
    def _save_learning_data(self, learning_data: Dict[str, Any], job_id: str):
        """
        学習データを保存
        
        Args:
            learning_data: 学習データ
            job_id: ジョブID
        """
        # JSON形式で保存
        json_file = self.learning_data_path / f"{job_id}_learning.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(learning_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Learning data saved: {json_file}")
    
    def auto_pipeline(self, report_dir: Path, min_score: int = 21) -> Dict[str, Any]:
        """
        自動逆算データ化パイプライン
        
        Args:
            report_dir: レポートディレクトリ
            min_score: 最低スコア（このスコア以上のレポートのみ処理）
        
        Returns:
            パイプライン実行結果
        """
        logger.info(f"Starting auto reverse data pipeline (min_score: {min_score})")
        
        # レポートファイルを検索
        report_files = list(report_dir.glob("*.md"))
        
        processed = 0
        generated = 0
        skipped = 0
        
        for report_file in report_files:
            job_id = report_file.stem
            
            # 対応するログファイルを探す
            log_file = Path("logs/step_deep_research/jobs") / f"{job_id}.jsonl"
            
            try:
                # ログファイルからcritique_result、plan、research_resultsを復元
                critique_result = None
                plan = None
                research_results = None
                
                if log_file.exists():
                    try:
                        # JSONLファイルからログを読み込む
                        with open(log_file, "r", encoding="utf-8") as f:
                            log_lines = f.readlines()
                        
                        # ログからデータを抽出
                        for line in log_lines:
                            try:
                                log_entry = json.loads(line.strip())
                                log_type = log_entry.get("type", "")
                                
                                # Criticの結果を探す
                                if log_type == "critic_result" or "critic" in log_type.lower():
                                    if "critique_result" in log_entry or "result" in log_entry:
                                        critique_data = log_entry.get("critique_result") or log_entry.get("result", {})
                                        critique_result = CritiqueResult(
                                            score=critique_data.get("score", 25),
                                            is_passed=critique_data.get("is_passed", True),
                                            feedback=critique_data.get("feedback", "")
                                        )
                                
                                # Planを探す
                                if log_type == "plan" or "planner" in log_type.lower():
                                    if "plan" in log_entry:
                                        plan_data = log_entry.get("plan", {})
                                        # Planオブジェクトに変換（簡易版）
                                        try:
                                            plan = Plan(**plan_data)
                                        except Exception:
                                            # フォールバック: 基本的なPlanを作成
                                            from .schemas import TodoItem, TaskTool, TaskPriority
                                            todo_items = []
                                            for todo_data in plan_data.get("todo", []):
                                                try:
                                                    todo_items.append(TodoItem(**todo_data))
                                                except Exception:
                                                    pass
                                            plan = Plan(
                                                goal=plan_data.get("goal", ""),
                                                todo=todo_items,
                                                success_criteria=plan_data.get("success_criteria", [])
                                            )
                                
                                # ResearchResultsを探す
                                if log_type == "research_results" or "research" in log_type.lower():
                                    if "research_results" in log_entry or "results" in log_entry:
                                        results_data = log_entry.get("research_results") or log_entry.get("results", {})
                                        # ResearchResultsオブジェクトに変換（簡易版）
                                        try:
                                            research_results = ResearchResults(**results_data)
                                        except Exception:
                                            # フォールバック: 基本的なResearchResultsを作成
                                            research_results = ResearchResults()
                                            if "citations" in results_data:
                                                research_results.citations = results_data.get("citations", [])
                                            if "summaries" in results_data:
                                                research_results.summaries = results_data.get("summaries", [])
                            
                            except json.JSONDecodeError:
                                continue
                            except Exception as e:
                                logger.warning(f"ログエントリの処理エラー: {e}")
                                continue
                    
                    except Exception as e:
                        logger.warning(f"ログファイル読み込みエラー ({log_file}): {e}")
                
                # デフォルト値の設定
                if critique_result is None:
                    critique_result = CritiqueResult(
                        score=25,  # デフォルト
                        is_passed=True
                    )
                
                # ログから復元したデータを使用して学習データを生成
                learning_data = self.generate_from_report(
                    report_path=report_file,
                    job_id=job_id,
                    critique_result=critique_result,
                    plan=plan,
                    research_results=research_results
                )
                
                if learning_data:
                    if learning_data.get("score", 0) >= min_score:
                        generated += 1
                    else:
                        skipped += 1
                else:
                    skipped += 1
                
                processed += 1
                
            except Exception as e:
                logger.warning(f"Failed to process {report_file}: {e}")
                skipped += 1
                continue
        
        logger.info(f"Pipeline completed: processed={processed}, generated={generated}, skipped={skipped}")
        
        return {
            "processed": processed,
            "generated": generated,
            "skipped": skipped,
            "generation_rate": generated / processed if processed > 0 else 0
        }
    
    def batch_generate_from_reports(self, report_dir: Path, max_reports: int = 10) -> List[Dict[str, Any]]:
        """
        複数のレポートから一括で学習データを生成
        
        Args:
            report_dir: レポートディレクトリ
            max_reports: 最大処理数
        
        Returns:
            生成された学習データのリスト
        """
        learning_data_list = []
        
        # レポートファイルを検索
        report_files = list(report_dir.glob("*.md"))[:max_reports]
        
        logger.info(f"Processing {len(report_files)} reports for learning data generation")
        
        for report_file in report_files:
            # ジョブIDをファイル名から取得
            job_id = report_file.stem
            
            # 対応するログファイルを探す
            log_file = Path("logs/step_deep_research/jobs") / f"{job_id}.jsonl"
            
            # ログファイルからplanとresearch_resultsを復元
            plan = None
            research_results = None
            
            if log_file.exists():
                try:
                    # JSONLファイルからログを読み込む
                    with open(log_file, "r", encoding="utf-8") as f:
                        log_lines = f.readlines()
                    
                    # ログからデータを抽出
                    for line in log_lines:
                        try:
                            log_entry = json.loads(line.strip())
                            log_type = log_entry.get("type", "")
                            
                            # Planを探す
                            if log_type == "plan" or "planner" in log_type.lower():
                                if "plan" in log_entry:
                                    plan_data = log_entry.get("plan", {})
                                    try:
                                        plan = Plan(**plan_data)
                                    except Exception:
                                        # フォールバック: 基本的なPlanを作成
                                        from .schemas import TodoItem, TaskTool, TaskPriority
                                        todo_items = []
                                        for todo_data in plan_data.get("todo", []):
                                            try:
                                                todo_items.append(TodoItem(**todo_data))
                                            except Exception:
                                                pass
                                        plan = Plan(
                                            goal=plan_data.get("goal", ""),
                                            todo=todo_items,
                                            success_criteria=plan_data.get("success_criteria", [])
                                        )
                            
                            # ResearchResultsを探す
                            if log_type == "research_results" or "research" in log_type.lower():
                                if "research_results" in log_entry or "results" in log_entry:
                                    results_data = log_entry.get("research_results") or log_entry.get("results", {})
                                    try:
                                        research_results = ResearchResults(**results_data)
                                    except Exception:
                                        # フォールバック: 基本的なResearchResultsを作成
                                        research_results = ResearchResults()
                                        if "citations" in results_data:
                                            research_results.citations = results_data.get("citations", [])
                                        if "summaries" in results_data:
                                            research_results.summaries = results_data.get("summaries", [])
                        
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            logger.warning(f"ログエントリの処理エラー: {e}")
                            continue
                
                except Exception as e:
                    logger.warning(f"ログファイル読み込みエラー ({log_file}): {e}")
            
            try:
                # デフォルトのcritique_resultを作成
                critique_result = CritiqueResult(
                    score=25,  # デフォルト
                    is_passed=True
                )
                
                learning_data = self.generate_from_report(
                    report_path=report_file,
                    job_id=job_id,
                    critique_result=CritiqueResult(
                        score=25,  # デフォルトスコア
                        is_passed=True
                    )
                )
                
                if learning_data:
                    learning_data_list.append(learning_data)
                    
            except Exception as e:
                logger.warning(f"Failed to generate learning data from {report_file}: {e}")
                continue
        
        logger.info(f"Generated {len(learning_data_list)} learning data entries")
        return learning_data_list


