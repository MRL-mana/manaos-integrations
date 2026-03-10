#!/usr/bin/env python3
"""
ManaOS 共通ブレーン（Ollama統合）
全ツールが共有するローカルLLM
"""

import os
import json
import requests
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class OllamaBrain:
    """Ollama統合クラス（共通ブレーン）"""

    def __init__(self, base_url: str = None, model: str = "llama3.2"):  # type: ignore
        self.base_url = base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.available = self._check_availability()

    def _check_availability(self) -> bool:
        """Ollamaが利用可能かチェック"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama接続不可: {e}")
            return False

    def suggest_improvement(
        self,
        tool: str,
        input_text: str,
        raw_output: str,
        similar_cases: Optional[List[Dict[str, Any]]] = None,
        rules: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[str]:
        """
        改善案を提案

        Args:
            tool: ツール名
            input_text: 入力テキスト
            raw_output: 現在の出力
            similar_cases: 類似ケース（過去の成功事例）
            rules: 適用可能なルール

        Returns:
            改善案（Noneの場合は利用不可）
        """
        if not self.available:
            return None

        # プロンプト構築
        prompt = self._build_improvement_prompt(
            tool, input_text, raw_output, similar_cases, rules
        )

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                logger.error(f"Ollama API エラー: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Ollama リクエストエラー: {e}")
            return None

    def _build_improvement_prompt(
        self,
        tool: str,
        input_text: str,
        raw_output: str,
        similar_cases: Optional[List[Dict[str, Any]]],
        rules: Optional[List[Dict[str, Any]]]
    ) -> str:
        """改善提案用のプロンプトを構築"""

        prompt_parts = [
            f"【タスク】{tool}ツールの出力を改善してください。",
            "",
            "【入力】",
            input_text[:500],  # 長すぎる場合は切り詰め
            "",
            "【現在の出力】",
            raw_output[:500],
            ""
        ]

        if similar_cases:
            prompt_parts.append("【過去の成功事例】")
            for i, case in enumerate(similar_cases[:3], 1):
                prompt_parts.append(f"事例{i}:")
                prompt_parts.append(f"  入力: {case.get('input', '')[:200]}")
                prompt_parts.append(f"  修正前: {case.get('raw_output', '')[:200]}")
                prompt_parts.append(f"  修正後: {case.get('corrected_output', '')[:200]}")
                prompt_parts.append("")

        if rules:
            prompt_parts.append("【適用可能なルール】")
            for rule in rules[:5]:
                prompt_parts.append(f"- {rule.get('pattern', '')}: {rule.get('action', '')}")
            prompt_parts.append("")

        prompt_parts.extend([
            "【指示】",
            "上記の情報を参考に、現在の出力を改善してください。",
            "改善後の出力のみを返してください（説明不要）。",
            "",
            "【改善後の出力】"
        ])

        return "\n".join(prompt_parts)

    def extract_pattern(
        self,
        tool: str,
        corrections: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        修正履歴からパターンを抽出

        Args:
            tool: ツール名
            corrections: 修正履歴のリスト

        Returns:
            抽出されたパターン
        """
        if not self.available or not corrections:
            return None

        prompt = self._build_pattern_extraction_prompt(tool, corrections)

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "").strip()

                # JSON形式で返すことを期待（簡易実装）
                try:
                    return json.loads(response_text)
                except:
                    # JSONでない場合はテキストとして返す
                    return {"pattern": response_text}
            else:
                return None

        except Exception as e:
            logger.error(f"パターン抽出エラー: {e}")
            return None

    def _build_pattern_extraction_prompt(
        self,
        tool: str,
        corrections: List[Dict[str, Any]]
    ) -> str:
        """パターン抽出用のプロンプトを構築"""

        prompt_parts = [
            f"【タスク】{tool}ツールの修正履歴から共通パターンを抽出してください。",
            "",
            "【修正履歴】"
        ]

        for i, correction in enumerate(corrections[:5], 1):
            prompt_parts.append(f"修正{i}:")
            prompt_parts.append(f"  修正前: {correction.get('raw_output', '')[:200]}")
            prompt_parts.append(f"  修正後: {correction.get('corrected_output', '')[:200]}")
            prompt_parts.append("")

        prompt_parts.extend([
            "【指示】",
            "上記の修正履歴から、繰り返し発生するパターンやルールを抽出してください。",
            "JSON形式で返してください:",
            '{"pattern": "パターン説明", "rule": "ルール内容", "regex": "正規表現（あれば）"}',
            "",
            "【抽出結果】"
        ])

        return "\n".join(prompt_parts)


# === グローバルインスタンス ===
_global_brain = None

def get_ollama_brain() -> OllamaBrain:
    """グローバルなOllamaBrainインスタンスを取得"""
    global _global_brain
    if _global_brain is None:
        _global_brain = OllamaBrain()
    return _global_brain









