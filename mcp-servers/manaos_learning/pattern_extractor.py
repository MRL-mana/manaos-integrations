#!/usr/bin/env python3
"""
ManaOS 自動パターン抽出システム
修正履歴から共通パターンを自動抽出してルール化
"""

import re
from typing import Dict, Any, List, Optional
from collections import Counter
import logging

from .learning_log import get_learning_log
from .rule_engine import get_rule_engine
from .ollama_brain import get_ollama_brain

logger = logging.getLogger(__name__)


class PatternExtractor:
    """パターン抽出クラス"""

    def __init__(self):
        self.log = get_learning_log()
        self.rule_engine = get_rule_engine()
        self.brain = get_ollama_brain()

    def extract_patterns_from_corrections(
        self,
        tool: str,
        min_occurrences: int = 3,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        修正履歴からパターンを抽出

        Args:
            tool: ツール名
            min_occurrences: 最小出現回数（これ以上出現したパターンのみ抽出）
            limit: 分析する修正履歴の最大数

        Returns:
            抽出されたパターンのリスト
        """
        # 修正履歴を取得
        corrections = self.log.get_failure_patterns(tool, limit=limit)

        if len(corrections) < min_occurrences:
            logger.info(f"修正履歴が少ないため、パターン抽出をスキップ (tool={tool}, count={len(corrections)})")
            return []

        # パターン抽出
        patterns = []

        # 1. 文字列置換パターン
        replacement_patterns = self._extract_replacement_patterns(corrections, min_occurrences)
        patterns.extend(replacement_patterns)

        # 2. 正規表現パターン
        regex_patterns = self._extract_regex_patterns(corrections, min_occurrences)
        patterns.extend(regex_patterns)

        # 3. Ollamaで高度なパターン抽出（利用可能な場合）
        if self.brain.available:
            llm_patterns = self._extract_with_llm(corrections)
            patterns.extend(llm_patterns)

        # 重複を除去
        patterns = self._deduplicate_patterns(patterns)

        logger.info(f"パターンを抽出しました: {len(patterns)}個 (tool={tool})")
        return patterns

    def _extract_replacement_patterns(
        self,
        corrections: List[Dict[str, Any]],
        min_occurrences: int
    ) -> List[Dict[str, Any]]:
        """文字列置換パターンを抽出"""
        replacements = []

        for correction in corrections:
            raw = correction.get("raw_output", "")
            corrected = correction.get("corrected_output", "")

            if not raw or not corrected:
                continue

            # 完全一致の置換を検出
            if raw != corrected and len(raw) < 50 and len(corrected) < 50:
                replacements.append({
                    "from": raw,
                    "to": corrected,
                    "context": correction.get("input", "")[:100]
                })

        # 出現頻度をカウント
        from_counter = Counter([r["from"] for r in replacements])
        to_counter = Counter([r["to"] for r in replacements])

        patterns = []
        for replacement in replacements:
            from_text = replacement["from"]
            to_text = replacement["to"]

            # 最小出現回数を満たすもののみ
            if from_counter[from_text] >= min_occurrences:
                patterns.append({
                    "type": "replacement",
                    "from": from_text,
                    "to": to_text,
                    "occurrences": from_counter[from_text],
                    "pattern": f"'{from_text}' → '{to_text}'"
                })

        return patterns

    def _extract_regex_patterns(
        self,
        corrections: List[Dict[str, Any]],
        min_occurrences: int
    ) -> List[Dict[str, Any]]:
        """正規表現パターンを抽出"""
        patterns = []

        # よくあるパターンを検出
        common_patterns = [
            {
                "name": "semicolon_to_comma",
                "regex": r"(?<=\d);\s*(?=\d)",
                "replace": ",",
                "description": "数字の間のセミコロンをカンマに"
            },
            {
                "name": "mixed_comma_semicolon",
                "regex": r";\s*,\s*|,\s*;\s*",
                "replace": ",",
                "description": "混在するカンマとセミコロンをカンマに"
            },
            {
                "name": "continuous_commas",
                "regex": r",\s*,\s*",
                "replace": ",",
                "description": "連続するカンマを1つに"
            },
            {
                "name": "fullwidth_space",
                "regex": r"　",
                "replace": " ",
                "description": "全角スペースを半角に"
            }
        ]

        for pattern_def in common_patterns:
            matches = 0
            for correction in corrections:
                raw = correction.get("raw_output", "")
                corrected = correction.get("corrected_output", "")

                if not raw or not corrected:
                    continue

                # パターンが適用されているかチェック
                test_result = re.sub(pattern_def["regex"], pattern_def["replace"], raw)
                if test_result == corrected or test_result in corrected:
                    matches += 1

            if matches >= min_occurrences:
                patterns.append({
                    "type": "regex",
                    "name": pattern_def["name"],
                    "regex": pattern_def["regex"],
                    "replace": pattern_def["replace"],
                    "description": pattern_def["description"],
                    "occurrences": matches
                })

        return patterns

    def _extract_with_llm(
        self,
        corrections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Ollamaを使って高度なパターン抽出"""
        if not corrections:
            return []

        try:
            pattern = self.brain.extract_pattern("pdf_excel", corrections)
            if pattern:
                return [{
                    "type": "llm_extracted",
                    "pattern": pattern.get("pattern", ""),
                    "rule": pattern.get("rule", ""),
                    "regex": pattern.get("regex"),
                    "occurrences": len(corrections)
                }]
        except Exception as e:
            logger.warning(f"LLMパターン抽出エラー: {e}")

        return []

    def _deduplicate_patterns(
        self,
        patterns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """重複パターンを除去"""
        seen = set()
        unique = []

        for pattern in patterns:
            # パターンの一意性を判定
            if pattern["type"] == "replacement":
                key = (pattern["from"], pattern["to"])
            elif pattern["type"] == "regex":
                key = (pattern["regex"], pattern["replace"])
            else:
                key = str(pattern.get("pattern", ""))

            if key not in seen:
                seen.add(key)
                unique.append(pattern)

        return unique

    def auto_add_rules(
        self,
        tool: str,
        min_occurrences: int = 3,
        dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """
        抽出したパターンを自動でペンディング（候補箱）に追加
        → 承認後にアクティブになる

        Args:
            tool: ツール名
            min_occurrences: 最小出現回数
            dry_run: Trueの場合は追加せずに結果のみ返す

        Returns:
            追加された（または追加予定の）ルールのリスト
        """
        patterns = self.extract_patterns_from_corrections(tool, min_occurrences)

        added_rules = []

        for pattern in patterns:
            occurrences = pattern.get("occurrences", min_occurrences)

            if pattern["type"] == "replacement":
                # 文字列置換ルール
                rule_id = f"auto_{tool}_{pattern['from'][:20].replace(' ', '_').replace('/', '_')}"
                if not dry_run:
                    self.rule_engine.add_rule_to_pending(
                        rule_id=rule_id,
                        target=[tool],
                        pattern=f"自動抽出: {pattern['from']} → {pattern['to']}",
                        action=f"'{pattern['from']}' を '{pattern['to']}' に置換",
                        occurrences=occurrences,
                        regex=None,
                        replace=None,
                        source="auto_extracted"
                    )
                added_rules.append({
                    "rule_id": rule_id,
                    "type": "replacement",
                    "pattern": pattern,
                    "status": "pending" if not dry_run else "dry_run"
                })

            elif pattern["type"] == "regex":
                # 正規表現ルール
                rule_id = f"auto_{tool}_{pattern['name']}"
                if not dry_run:
                    self.rule_engine.add_rule_to_pending(
                        rule_id=rule_id,
                        target=[tool],
                        pattern=pattern["description"],
                        action=pattern["description"],
                        occurrences=occurrences,
                        regex=pattern["regex"],
                        replace=pattern["replace"],
                        source="auto_extracted"
                    )
                added_rules.append({
                    "rule_id": rule_id,
                    "type": "regex",
                    "pattern": pattern,
                    "status": "pending" if not dry_run else "dry_run"
                })

        if not dry_run:
            logger.info(f"ペンディングルール追加完了: {len(added_rules)}個 (tool={tool})")
            logger.info(f"  → 承認待ち: /root/manaos_learning/rules/rules_pending.yaml を確認してください")
        else:
            logger.info(f"自動ルール追加予定: {len(added_rules)}個 (tool={tool}, dry_run=True)")

        return added_rules


# === グローバルインスタンス ===
_global_extractor = None

def get_pattern_extractor() -> PatternExtractor:
    """グローバルなPatternExtractorインスタンスを取得"""
    global _global_extractor
    if _global_extractor is None:
        _global_extractor = PatternExtractor()
    return _global_extractor

