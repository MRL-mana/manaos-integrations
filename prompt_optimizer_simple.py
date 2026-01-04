"""
シンプルなプロンプト最適化エンジン
RAGタスク向けにプロンプトを最適化
"""

import os
import logging
from typing import Dict, Optional, Any
import re

logger = logging.getLogger(__name__)


class SimplePromptOptimizer:
    """シンプルなプロンプト最適化クラス"""
    
    def __init__(self, enable_optimization: bool = True):
        """
        初期化
        
        Args:
            enable_optimization: プロンプト最適化を有効にするか
        """
        self.enable_optimization = enable_optimization
        self.optimization_rules = self._load_optimization_rules()
    
    def _load_optimization_rules(self) -> Dict[str, Any]:
        """最適化ルールを読み込み"""
        return {
            "rag_enhancements": [
                "明確な質問形式に変換",
                "コンテキスト理解を促進する指示を追加",
                "回答の形式を指定",
            ],
            "japanese_optimizations": [
                "日本語の自然な表現に調整",
                "敬語・丁寧語の統一",
                "専門用語の明確化",
            ],
            "query_expansions": {
                "短いクエリ": "関連する用語や同義語を追加",
                "曖昧な表現": "具体的な説明を追加",
            }
        }
    
    def optimize(self, prompt: str, task_type: str = "rag", context: Optional[str] = None) -> Dict[str, Any]:
        """
        プロンプトを最適化
        
        Args:
            prompt: 元のプロンプト
            task_type: タスクタイプ（rag, chat, code, etc.）
            context: 追加コンテキスト
            
        Returns:
            最適化結果の辞書
        """
        if not self.enable_optimization:
            return {
                "optimized": False,
                "original_prompt": prompt,
                "optimized_prompt": prompt,
                "changes": []
            }
        
        original_prompt = prompt
        optimized_prompt = prompt
        changes = []
        
        # RAGタスク向けの最適化
        if task_type == "rag":
            optimized_prompt, rag_changes = self._optimize_for_rag(optimized_prompt, context)
            changes.extend(rag_changes)
        
        # 日本語の最適化
        optimized_prompt, jp_changes = self._optimize_japanese(optimized_prompt)
        changes.extend(jp_changes)
        
        # クエリ拡張
        optimized_prompt, expansion_changes = self._expand_query(optimized_prompt)
        changes.extend(expansion_changes)
        
        # プロンプトの明確化
        optimized_prompt, clarity_changes = self._improve_clarity(optimized_prompt)
        changes.extend(clarity_changes)
        
        return {
            "optimized": len(changes) > 0,
            "original_prompt": original_prompt,
            "optimized_prompt": optimized_prompt,
            "changes": changes,
            "task_type": task_type
        }
    
    def _optimize_for_rag(self, prompt: str, context: Optional[str] = None) -> tuple[str, list]:
        """RAGタスク向けの最適化"""
        changes = []
        optimized = prompt
        
        # 短いプロンプトの拡張
        if len(prompt) < 20:
            optimized = f"以下の質問について、提供されたコンテキスト情報を基に、正確で詳細な回答を提供してください。\n\n質問: {prompt}"
            changes.append("短いプロンプトをRAG向けに拡張")
        
        # コンテキスト指示の追加
        if "コンテキスト" not in optimized and "情報" not in optimized:
            optimized = f"{optimized}\n\n注意: 提供されたコンテキスト情報を優先的に使用し、コンテキストにない情報は推測せずに「情報がありません」と回答してください。"
            changes.append("コンテキスト優先指示を追加")
        
        # 回答形式の指定
        if "形式" not in optimized and "回答" not in optimized.lower():
            optimized = f"{optimized}\n\n回答は明確で簡潔に、必要に応じて箇条書きで構造化してください。"
            changes.append("回答形式の指示を追加")
        
        return optimized, changes
    
    def _optimize_japanese(self, prompt: str) -> tuple[str, list]:
        """日本語の最適化"""
        changes = []
        optimized = prompt
        
        # カタカナの統一（必要に応じて）
        # ここでは基本的な処理のみ
        
        return optimized, changes
    
    def _expand_query(self, prompt: str) -> tuple[str, list]:
        """クエリの拡張"""
        changes = []
        optimized = prompt
        
        # 短いクエリの拡張
        words = prompt.split()
        if len(words) < 3:
            # 単語が少ない場合は拡張を試みる
            # 実際の実装では、同義語辞書や関連語検索を使用
            pass
        
        return optimized, changes
    
    def _improve_clarity(self, prompt: str) -> tuple[str, list]:
        """明確性の向上"""
        changes = []
        optimized = prompt
        
        # 曖昧な表現の検出と改善
        ambiguous_patterns = {
            r"これ": "具体的な対象を明確にする",
            r"それ": "具体的な対象を明確にする",
            r"あれ": "具体的な対象を明確にする",
        }
        
        for pattern, suggestion in ambiguous_patterns.items():
            if re.search(pattern, optimized):
                # 実際の実装では、より高度な処理を行う
                pass
        
        return optimized, changes


def optimize_prompt(prompt: str, task_type: str = "rag", enable: bool = True) -> str:
    """
    プロンプトを最適化する簡易関数
    
    Args:
        prompt: 元のプロンプト
        task_type: タスクタイプ
        enable: 最適化を有効にするか
        
    Returns:
        最適化されたプロンプト
    """
    optimizer = SimplePromptOptimizer(enable_optimization=enable)
    result = optimizer.optimize(prompt, task_type=task_type)
    return result["optimized_prompt"]



