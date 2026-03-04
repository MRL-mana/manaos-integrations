#!/usr/bin/env python3
"""
ManaOS 共通学習API
全ツールから使える統一インターフェース
"""

from typing import Dict, Any, List, Optional
import logging

from .learning_log import get_learning_log, LearningLog
from .rule_engine import get_rule_engine, RuleEngine
from .ollama_brain import get_ollama_brain, OllamaBrain

logger = logging.getLogger(__name__)


class LearningAPI:
    """共通学習APIクラス"""

    def __init__(self):
        self.log = get_learning_log()
        self.rule_engine = get_rule_engine()
        self.brain = get_ollama_brain()

    def register_correction(
        self,
        tool: str,
        input_data: str,
        raw_output: str,
        corrected_output: str,
        feedback: str = "needs_review",
        tags: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        修正履歴を登録

        Args:
            tool: ツール名
            input_data: 入力データ
            raw_output: 生出力
            corrected_output: 修正後出力
            feedback: フィードバック（"good", "bad", "needs_review"）
            tags: タグリスト
            meta: メタデータ

        Returns:
            登録されたログID
        """
        return self.log.register_correction(
            tool=tool,
            input_data=input_data,
            raw_output=raw_output,
            corrected_output=corrected_output,
            feedback=feedback,
            tags=tags,
            meta=meta
        )

    def suggest_improvement(
        self,
        tool: str,
        input_text: str,
        raw_output: str,
        task: Optional[str] = None
    ) -> Optional[str]:
        """
        改善案を提案

        Args:
            tool: ツール名
            input_text: 入力テキスト
            raw_output: 現在の出力
            task: タスク名（過去事例の検索に使用）

        Returns:
            改善案（Noneの場合は提案不可）
        """
        # 過去の成功事例を取得
        similar_cases = self.log.get_best_examples(
            tool=tool,
            task=task,
            limit=3,
            feedback="good"
        )

        # 適用可能なルールを取得
        rules = self.rule_engine.get_rules_for_tool(tool)

        # Ollamaで改善案を生成
        improvement = self.brain.suggest_improvement(
            tool=tool,
            input_text=input_text,
            raw_output=raw_output,
            similar_cases=similar_cases if similar_cases else None,
            rules=rules if rules else None
        )

        return improvement

    def get_best_examples(
        self,
        tool: str,
        task: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        過去の成功事例を取得

        Args:
            tool: ツール名
            task: タスク名
            limit: 最大取得数

        Returns:
            成功事例のリスト
        """
        return self.log.get_best_examples(tool=tool, task=task, limit=limit)

    def apply_rules(
        self,
        text: str,
        tool: str
    ) -> str:
        """
        共通ルールを適用

        Args:
            text: 修正対象テキスト
            tool: ツール名

        Returns:
            修正後のテキスト
        """
        return self.rule_engine.apply_rules(text, tool)

    def search_similar_cases(
        self,
        tool: str,
        query_text: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        類似ケースを検索

        Args:
            tool: ツール名
            query_text: 検索クエリ
            limit: 最大取得数

        Returns:
            類似ケースのリスト
        """
        return self.log.search_similar_cases(tool=tool, query_text=query_text, limit=limit)

    def get_statistics(
        self,
        tool: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        統計情報を取得

        Args:
            tool: ツール名（Noneの場合は全体）

        Returns:
            統計情報
        """
        return self.log.get_statistics(tool=tool)

    def add_rule(
        self,
        rule_id: str,
        target: List[str],
        pattern: str,
        action: str,
        regex: Optional[str] = None,
        replace: Optional[str] = None,
        replace_func: Optional[str] = None
    ):
        """
        新しいルールを追加

        Args:
            rule_id: ルールID
            target: 適用対象ツールのリスト
            pattern: パターン説明
            action: アクション説明
            regex: 正規表現パターン
            replace: 置換文字列
            replace_func: 置換関数名
        """
        self.rule_engine.add_rule(
            rule_id=rule_id,
            target=target,
            pattern=pattern,
            action=action,
            regex=regex,
            replace=replace,
            replace_func=replace_func
        )


# === グローバルインスタンス ===
_global_api = None

def get_learning_api() -> LearningAPI:
    """グローバルなLearningAPIインスタンスを取得"""
    global _global_api
    if _global_api is None:
        _global_api = LearningAPI()
    return _global_api


# === 便利関数（直接呼び出し用） ===

def register_correction(
    tool: str,
    input_data: str,
    raw_output: str,
    corrected_output: str,
    feedback: str = "needs_review",
    tags: Optional[List[str]] = None,
    meta: Optional[Dict[str, Any]] = None
) -> str:
    """修正履歴を登録（便利関数）"""
    api = get_learning_api()
    return api.register_correction(
        tool, input_data, raw_output, corrected_output,
        feedback, tags, meta
    )


def suggest_improvement(
    tool: str,
    input_text: str,
    raw_output: str,
    task: Optional[str] = None
) -> Optional[str]:
    """改善案を提案（便利関数）"""
    api = get_learning_api()
    return api.suggest_improvement(tool, input_text, raw_output, task)


def apply_rules(text: str, tool: str) -> str:
    """共通ルールを適用（便利関数）"""
    api = get_learning_api()
    return api.apply_rules(text, tool)









