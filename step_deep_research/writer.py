#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
報告書作成エージェント（Writer）
"""

import os
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

try:
    from manaos_integrations._paths import OLLAMA_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import OLLAMA_PORT  # type: ignore
    except Exception:  # pragma: no cover
        OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))


DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")

from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from .schemas import Plan, ResearchResults, Citation, Summary, CounterArgument
from .utils import load_prompt_template, format_prompt
from .citation_formatter import CitationFormatter
from .template_router import TemplateRouter

logger = get_service_logger("writer")
error_handler = ManaOSErrorHandler("StepDeepResearchWriter")


class Writer:
    """報告書作成エージェント"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: Writer設定
        """
        self.config = config
        self.ollama_url = config.get("ollama_url", DEFAULT_OLLAMA_URL)
        self.model = config.get("model", "qwen2.5:7b")
        self.citation_format = config.get("citation_format", "markdown")
        
        # レポートテンプレート読み込み（デフォルト）
        template_path = config.get("report_template", "step_deep_research/templates/report_template.md")
        self.default_report_template = load_prompt_template(template_path)
        
        # テンプレートルーター初期化
        self.template_router = TemplateRouter()
        
        # 引用フォーマッター初期化
        self.citation_formatter = CitationFormatter(citation_format=self.citation_format)
    
    def create_report(
        self,
        research_results: ResearchResults,
        plan: Plan,
        job_id: str = "",
        user_query: str = ""
    ) -> str:
        """
        レポート作成
        
        Args:
            research_results: 調査結果
            plan: 調査計画
            job_id: ジョブID
        
        Returns:
            レポート（Markdown形式）
        """
        try:
            # テンプレートタイプを検出
            template_type = self.template_router.detect_template_type(user_query or plan.goal)
            report_template = self.template_router.get_template(template_type=template_type)
            
            logger.info(f"Using template: {template_type}")
            
            # レポート内容を構築
            report_content = self._build_report_content(research_results, plan, job_id, template_type)
            
            # テンプレートに埋め込む
            report = format_prompt(
                report_template,
                title=plan.goal,
                date=datetime.now().strftime("%Y-%m-%d"),
                job_id=job_id,
                **report_content
            )
            
            # 引用フォーマットを強制適用
            report = self.citation_formatter.enforce_format(report, research_results.citations)
            
            logger.info("Report created")
            return report
            
        except Exception as e:
            error_handler.handle_error(
                e,
                "Report creation failed",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.HIGH
            )
            raise
    
    def revise_report(
        self,
        original_report: str,
        fix_requests: List[str]
    ) -> str:
        """
        レポートを修正
        
        Args:
            original_report: 元のレポート
            fix_requests: 修正要求リスト
        
        Returns:
            修正後のレポート
        """
        try:
            # 修正プロンプト読み込み
            revision_template = load_prompt_template("step_deep_research/prompts/revision_prompt.txt")
            
            # プロンプト生成
            prompt = format_prompt(
                revision_template,
                original_report=original_report,
                fix_requests="\n".join(f"- {req}" for req in fix_requests),
                fail_flags="",  # 必要に応じて追加
                score="",  # 必要に応じて追加
                pass_status="",  # 必要に応じて追加
                rubric_details=""  # 必要に応じて追加
            )
            
            # LLM呼び出し
            response = self._call_llm(prompt)
            
            # Markdownブロックを抽出
            if "```markdown" in response:
                start = response.find("```markdown") + 11
                end = response.find("```", start)
                report = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                report = response[start:end].strip()
            else:
                report = response.strip()
            
            logger.info("Report revised")
            return report
            
        except Exception as e:
            error_handler.handle_error(
                e,
                "Report revision failed",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.MEDIUM
            )
            return original_report  # 失敗時は元のレポートを返す
    
    def _build_report_content(
        self,
        research_results: ResearchResults,
        plan: Plan,
        job_id: str,
        template_type: str = "default"
    ) -> Dict[str, str]:
        """
        レポート内容を構築
        
        Args:
            research_results: 調査結果
            plan: 調査計画
            job_id: ジョブID
        
        Returns:
            レポート内容の辞書
        """
        # 主要な発見
        main_findings = self._format_main_findings(research_results.summaries)
        
        # 詳細な分析
        detailed_analysis = self._format_detailed_analysis(research_results.citations)
        
        # 反証候補
        counter_arguments = self._format_counter_arguments(research_results.counter_arguments)
        
        # 結論（簡易版）
        conclusion = self._format_conclusion(research_results, plan)
        
        # 結論の根拠
        conclusion_support = self._format_conclusion_support(research_results.citations)
        
        # 不確実性
        uncertainty = self._format_uncertainty(research_results)
        
        # 次のアクション
        next_actions = self._format_next_actions(research_results, plan)
        
        # コスト・時間・リスク
        cost_time_risk = self._format_cost_time_risk(plan)
        
        # 実装手順
        implementation_steps = self._format_implementation_steps(plan)
        
        # 参考文献
        citations = self._format_citations(research_results.citations)
        
        # ベースコンテンツ
        base_content = {
            "goal": plan.goal,
            "scope": self._format_scope(plan),
            "main_findings": main_findings,
            "detailed_analysis": detailed_analysis,
            "counter_arguments": counter_arguments,
            "conclusion": conclusion,
            "conclusion_support": conclusion_support,
            "uncertainty": uncertainty,
            "next_actions": self._format_next_actions(research_results, plan),
            "cost_time_risk": cost_time_risk,
            "implementation_steps": implementation_steps,
            "citations": citations,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "score": "",  # 後で埋める
            "pass_status": ""  # 後で埋める
        }
        
        # テンプレートタイプ別の追加コンテンツ
        if template_type == "technical_selection":
            base_content.update({
                "comparison_targets": plan.goal,
                "feature_comparison": detailed_analysis,
                "performance_comparison": self._format_performance_comparison(research_results),
                "security_comparison": self._format_security_comparison(research_results),
                "cost_comparison": cost_time_risk,
                "recommended_choice": conclusion,
                "recommendation_reason": conclusion_support,
                "risks_and_considerations": counter_arguments + "\n\n" + uncertainty,
                "pre_implementation_checklist": self._format_next_actions(research_results, plan),
                "cost_time_estimate": cost_time_risk
            })
        elif template_type == "troubleshooting":
            base_content.update({
                "symptoms": plan.goal,
                "environment": "環境情報は調査結果から抽出されました。",
                "reproduction_conditions": "再現条件は調査結果から抽出されました。",
                "cause_candidates": main_findings,
                "evidence_for_causes": detailed_analysis,
                "diagnosis_steps": implementation_steps,
                "verification_items": self._format_next_actions(research_results, plan),
                "recommended_solution": conclusion,
                "alternative_solutions": counter_arguments,
                "prevention_measures": uncertainty,
                "immediate_actions": self._format_next_actions(research_results, plan),
                "verification_actions": self._format_next_actions(research_results, plan),
                "long_term_measures": self._format_next_actions(research_results, plan)
            })
        elif template_type == "latest_trends":
            base_content.update({
                "changes_and_updates": main_findings,
                "new_features": self._extract_new_features(research_results),
                "deprecations": self._extract_deprecations(research_results),
                "impact_on_existing_systems": detailed_analysis,
                "migration_requirements": implementation_steps,
                "compatibility_issues": counter_arguments,
                "immediate_checks": self._format_next_actions(research_results, plan),
                "preparation_items": self._format_next_actions(research_results, plan),
                "migration_plan": implementation_steps,
                "uncertainties": uncertainty,
                "items_to_verify": self._format_next_actions(research_results, plan),
                "information_limitations": uncertainty
            })
        
        return base_content
    
    def _format_main_findings(self, summaries: List[Summary]) -> str:
        """主要な発見をフォーマット"""
        if not summaries:
            return "調査結果がありません。"
        
        formatted = []
        for summary in summaries[:5]:  # 上位5件
            formatted.append(f"- **{summary.source}**: {summary.summary}")
            if summary.key_points:
                for point in summary.key_points[:3]:
                    formatted.append(f"  - {point}")
        
        return "\n".join(formatted) if formatted else "主要な発見はありません。"
    
    def _format_detailed_analysis(self, citations: List[Citation]) -> str:
        """詳細な分析をフォーマット"""
        if not citations:
            return "詳細な分析データがありません。"
        
        formatted = []
        for citation in citations[:10]:  # 上位10件
            formatted.append(f"""
### {citation.id}
**出典**: {citation.source}
**引用**: {citation.quote}
**要約**: {citation.summary}
**タグ**: {citation.tag.value}
""")
        
        return "\n".join(formatted) if formatted else "詳細な分析はありません。"
    
    def _format_counter_arguments(self, counter_args: List[CounterArgument]) -> str:
        """反証候補をフォーマット"""
        if not counter_args:
            return "反証候補は見つかりませんでした。"
        
        formatted = []
        for counter in counter_args:
            formatted.append(f"""
- **主張**: {counter.claim}
- **反証**: {counter.counter_evidence}
- **出典**: {counter.source}
""")
        
        return "\n".join(formatted)
    
    def _format_conclusion(self, research_results: ResearchResults, plan: Plan) -> str:
        """
        結論をフォーマット
        LLMを使用して結論を生成
        
        Args:
            research_results: 調査結果
            plan: 調査計画
        
        Returns:
            フォーマットされた結論
        """
        try:
            # LLMルーターを使用して結論を生成
            try:
                from llm_routing import LLMRouter
                
                router = LLMRouter()
                
                # 結論生成プロンプトを作成
                citations_summary = "\n".join([
                    f"- {citation.summary} ({citation.source})" 
                    for citation in research_results.citations[:10]
                ])
                
                summaries_text = "\n".join([
                    f"- {summary.content}" 
                    for summary in research_results.summaries[:10]
                ])
                
                conclusion_prompt = f"""以下の調査結果に基づいて、簡潔で明確な結論を生成してください。

## 調査目標
{plan.goal}

## 引用（{len(research_results.citations)}件）
{citations_summary if citations_summary else "引用なし"}

## 要約（{len(research_results.summaries)}件）
{summaries_text if summaries_text else "要約なし"}

## 注意事項
- 簡潔で明確な結論を1-2段落で生成してください
- 調査目標に対する回答を提供してください
- 根拠となる引用や要約を考慮してください
- 不確実性がある場合は、その旨を明記してください

## 結論
"""
                
                # reasoningタスクタイプで結論生成を実行（推論が必要なため）
                result = router.route(
                    task_type="reasoning",
                    prompt=conclusion_prompt
                )
                
                conclusion = result.get("response", "").strip()
                
                # 余分な説明文を削除
                if "## 結論" in conclusion:
                    conclusion = conclusion.split("## 結論")[-1].strip()
                if "結論:" in conclusion:
                    conclusion = conclusion.split("結論:")[-1].strip()
                if "結論" in conclusion and len(conclusion.split("結論")) > 1:
                    conclusion = conclusion.split("結論")[-1].strip()
                
                if conclusion:
                    logger.info("LLMで結論を生成しました")
                    return conclusion
                else:
                    logger.warning("LLM結論生成の結果が空です。フォールバックを使用します。")
            
            except ImportError:
                logger.warning("LLMRouterが利用できません。フォールバックを使用します。")
            except Exception as e:
                logger.warning(f"LLM結論生成エラー: {e}。フォールバックを使用します。")
        
        except Exception as e:
            logger.warning(f"結論生成エラー: {e}。フォールバックを使用します。")
        
        # フォールバック: 簡易版の結論を生成
        conclusion_parts = [
            f"調査目標「{plan.goal}」について、"
        ]
        
        if research_results.citations:
            conclusion_parts.append(f"{len(research_results.citations)}件の引用")
        
        if research_results.summaries:
            if research_results.citations:
                conclusion_parts.append("と")
            conclusion_parts.append(f"{len(research_results.summaries)}件の要約")
        
        conclusion_parts.append("を基に分析を行いました。")
        
        if research_results.contradictions:
            conclusion_parts.append(f"\nなお、{len(research_results.contradictions)}件の矛盾が検出されました。")
        
        return "".join(conclusion_parts)
    
    def _format_conclusion_support(self, citations: List[Citation]) -> str:
        """結論の根拠をフォーマット"""
        if not citations:
            return "根拠となる引用がありません。"
        
        formatted = []
        for citation in citations[:5]:
            formatted.append(f"- {citation.summary} ({citation.source})")
        
        return "\n".join(formatted)
    
    def _format_uncertainty(self, research_results: ResearchResults) -> str:
        """不確実性をフォーマット"""
        uncertainties = []
        if research_results.contradictions:
            uncertainties.append(f"- {len(research_results.contradictions)}件の矛盾が検出されました")
        if not research_results.counter_arguments:
            uncertainties.append("- 反証候補が見つかりませんでした")
        
        return "\n".join(uncertainties) if uncertainties else "不確実性は特に見つかりませんでした。"
    
    def _format_next_actions(self, research_results: Optional[ResearchResults] = None, plan: Optional[Plan] = None) -> str:
        """次のアクションをフォーマット"""
        if plan and plan.todo:
            formatted = []
            for todo in plan.todo[:5]:
                formatted.append(f"{todo.step}. {todo.description}")
            return "\n".join(formatted)
        elif research_results and research_results.counter_arguments:
            # 反証候補から次アクションを推測
            formatted = []
            formatted.append("1. 反証候補を検証する")
            formatted.append("2. 追加の調査を実施する")
            return "\n".join(formatted)
        return "次のアクションは計画されていません。"
    
    def _format_cost_time_risk(self, plan: Plan) -> str:
        """コスト・時間・リスクをフォーマット"""
        formatted = []
        formatted.append(f"- **推定時間**: {plan.estimated_time_minutes}分")
        formatted.append(f"- **推定コスト**: {plan.estimated_cost_tokens}トークン")
        
        if plan.risks:
            formatted.append("- **リスク**:")
            for risk in plan.risks[:3]:
                formatted.append(f"  - {risk.risk} (対策: {risk.mitigation})")
        
        return "\n".join(formatted)
    
    def _format_implementation_steps(self, plan: Plan) -> str:
        """実装手順をフォーマット"""
        if not plan.todo:
            return "実装手順は計画されていません。"
        
        formatted = []
        for todo in plan.todo:
            formatted.append(f"""
### ステップ {todo.step}: {todo.description}
- **ツール**: {todo.tool.value}
- **期待される出力**: {todo.expected_output}
- **優先度**: {todo.priority.value}
""")
        
        return "\n".join(formatted)
    
    def _format_scope(self, plan: Plan) -> str:
        """調査範囲をフォーマット"""
        return f"本調査は「{plan.goal}」を目標とし、{len(plan.todo)}個のタスクを実行します。"
    
    def _format_citations(self, citations: List[Citation]) -> str:
        """参考文献をフォーマット"""
        if not citations:
            return "参考文献がありません。"
        
        formatted = []
        for i, citation in enumerate(citations, 1):
            formatted.append(f"{i}. [{citation.id}] {citation.source}")
            formatted.append(f"   - {citation.quote[:100]}...")
            if citation.warning:
                formatted.append(f"   ⚠️  {citation.warning}")
        
        return "\n".join(formatted)
    
    def _format_comparison_targets(self, research_results: ResearchResults, plan: Plan) -> str:
        """比較対象をフォーマット"""
        # 計画のgoalから比較対象を抽出（簡易版）
        return plan.goal
    
    def _format_performance_comparison(self, research_results: ResearchResults) -> str:
        """パフォーマンス比較をフォーマット"""
        return self._format_detailed_analysis(research_results.citations)
    
    def _format_security_comparison(self, research_results: ResearchResults) -> str:
        """セキュリティ比較をフォーマット"""
        # セキュリティ関連の引用を抽出
        security_citations = [c for c in research_results.citations if "セキュリティ" in c.summary.lower() or "security" in c.summary.lower()]
        if security_citations:
            return self._format_detailed_analysis(security_citations)
        return "セキュリティ比較データが不足しています。"
    
    def _extract_symptoms(self, goal: str) -> str:
        """症状を抽出"""
        return goal
    
    def _format_environment(self, research_results: ResearchResults) -> str:
        """環境情報をフォーマット"""
        return "環境情報は調査結果から抽出されました。"
    
    def _format_reproduction_conditions(self, research_results: ResearchResults) -> str:
        """再現条件をフォーマット"""
        return "再現条件は調査結果から抽出されました。"
    
    def _format_prevention_measures(self, research_results: ResearchResults) -> str:
        """予防策をフォーマット"""
        return self._format_uncertainty(research_results)
    
    def _format_long_term_measures(self, research_results: ResearchResults) -> str:
        """長期的対策をフォーマット"""
        return self._format_next_actions(research_results, None)
    
    def _extract_new_features(self, research_results: ResearchResults) -> str:
        """新機能を抽出"""
        new_feature_citations = [c for c in research_results.citations if "新機能" in c.summary.lower() or "new feature" in c.summary.lower()]
        if new_feature_citations:
            return self._format_main_findings([s for s in research_results.summaries if "新機能" in s.summary.lower()])
        return "新機能情報は調査結果から抽出されました。"
    
    def _extract_deprecations(self, research_results: ResearchResults) -> str:
        """非推奨・廃止予定を抽出"""
        deprecation_citations = [c for c in research_results.citations if "非推奨" in c.summary.lower() or "deprecated" in c.summary.lower()]
        if deprecation_citations:
            return self._format_main_findings([s for s in research_results.summaries if "非推奨" in s.summary.lower()])
        return "非推奨・廃止予定の情報は見つかりませんでした。"
    
    def _call_llm(self, prompt: str) -> str:
        """LLMを呼び出す"""
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 4000
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
        except httpx.HTTPError as e:
            error_handler.handle_error(
                e,
                "LLM API call failed",
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH
            )
            raise

