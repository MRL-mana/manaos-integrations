"""
LLM難易度判定エンジン
プロンプトの難易度を分析して、適切なモデルを選択するためのスコアを計算
"""

import re
from manaos_logger import get_logger, get_service_logger
from typing import Dict, Any, List, Optional

logger = get_service_logger("llm-difficulty-analyzer")
class DifficultyAnalyzer:
    """プロンプトの難易度を分析"""
    
    def __init__(self):
        """初期化"""
        # 高難易度キーワード（設計・アーキテクチャ・複雑な処理）
        self.high_difficulty_keywords = [
            # 日本語
            "設計", "アーキテクチャ", "複雑", "最適化", "リファクタリング",
            "アーキテクチャ設計", "システム設計", "データベース設計",
            "パフォーマンス最適化", "スケーラビリティ", "セキュリティ設計",
            "マイクロサービス", "分散システム", "並列処理",
            # 英語
            "architecture", "design", "optimize", "refactor",
            "complex", "scalability", "performance", "security",
            "microservices", "distributed", "parallel", "concurrent",
            "algorithm", "data structure", "design pattern"
        ]
        
        # 低難易度キーワード（補完・修正・簡単な処理）
        self.low_difficulty_keywords = [
            # 日本語
            "補完", "修正", "リファクタ", "バグ", "エラー修正",
            "タイポ修正", "フォーマット", "リント修正",
            # 英語
            "complete", "fix", "bug", "error", "typo",
            "format", "lint", "simple", "quick"
        ]
        
        # コード複雑度の指標
        self.complexity_indicators = {
            "function": r"def\s+\w+\s*\(",
            "class": r"class\s+\w+",
            "import": r"import\s+\w+|from\s+\w+\s+import",
            "if_statement": r"if\s+.*:",
            "loop": r"for\s+.*:|while\s+.*:",
            "try_except": r"try\s*:|except\s+.*:",
            "decorator": r"@\w+",
            "async": r"async\s+def|await\s+"
        }
    
    def calculate_difficulty(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        難易度スコアを計算（0-100）
        
        Args:
            prompt: ユーザーのプロンプト
            context: コンテキスト情報（code_context, file_path等）
        
        Returns:
            難易度スコア（0-100）
        """
        if context is None:
            context = {}
        
        score = 0.0
        
        # 1. プロンプト長によるスコア（最大30点）
        prompt_length_score = min(len(prompt) / 100, 30)
        score += prompt_length_score
        logger.debug(f"プロンプト長スコア: {prompt_length_score:.2f}")
        
        # 2. コンテキスト長によるスコア（最大30点）
        code_context = context.get("code_context", "")
        if code_context:
            context_length_score = min(len(code_context) / 200, 30)
            score += context_length_score
            logger.debug(f"コンテキスト長スコア: {context_length_score:.2f}")
        
        # 3. キーワード検出によるスコア（最大20点）
        keywords_score = self._detect_keywords(prompt)
        score += keywords_score
        logger.debug(f"キーワードスコア: {keywords_score:.2f}")
        
        # 4. コード複雑度によるスコア（最大20点）
        complexity_score = self._calculate_complexity(context)
        score += complexity_score
        logger.debug(f"複雑度スコア: {complexity_score:.2f}")
        
        # スコアを0-100に正規化
        final_score = min(score, 100)
        logger.info(f"難易度スコア: {final_score:.2f}")
        
        return final_score
    
    def _detect_keywords(self, prompt: str) -> float:
        """
        キーワード検出によるスコア計算
        
        Returns:
            キーワードスコア（-20 〜 +20）
        """
        prompt_lower = prompt.lower()
        
        # 高難易度キーワードの検出
        high_count = sum(1 for kw in self.high_difficulty_keywords if kw.lower() in prompt_lower)
        high_score = high_count * 5  # 1キーワードあたり5点
        
        # 低難易度キーワードの検出
        low_count = sum(1 for kw in self.low_difficulty_keywords if kw.lower() in prompt_lower)
        low_score = low_count * -3  # 1キーワードあたり-3点
        
        # スコアを-20〜+20に制限
        keyword_score = max(-20, min(20, high_score + low_score))
        
        return keyword_score
    
    def _calculate_complexity(self, context: Dict[str, Any]) -> float:
        """
        コードの複雑度を計算
        
        Returns:
            複雑度スコア（0-20）
        """
        code_context = context.get("code_context", "")
        if not code_context:
            return 0.0
        
        complexity = 0.0
        
        # 各指標をカウント
        for indicator_name, pattern in self.complexity_indicators.items():
            count = len(re.findall(pattern, code_context))
            
            # 指標ごとの重み付け
            weights = {
                "function": 1.0,
                "class": 2.0,
                "import": 0.5,
                "if_statement": 0.5,
                "loop": 1.0,
                "try_except": 1.5,
                "decorator": 1.0,
                "async": 1.5
            }
            
            weight = weights.get(indicator_name, 1.0)
            complexity += count * weight
        
        # 複雑度を0-20に正規化（100行あたり1点）
        complexity_score = min(complexity / 5, 20)
        
        return complexity_score
    
    def get_difficulty_level(self, score: float) -> str:
        """
        難易度スコアから難易度レベルを取得
        
        Args:
            score: 難易度スコア（0-100）
        
        Returns:
            難易度レベル（"low", "medium", "high"）
        """
        if score < 10:
            return "low"
        elif score < 30:
            return "medium"
        else:
            return "high"
    
    def get_recommended_model(self, score: float) -> str:
        """
        難易度スコアから推奨モデルを取得
        
        Args:
            score: 難易度スコア（0-100）
        
        Returns:
            推奨モデル名
        """
        if score < 10:
            return "Qwen2.5-Coder-7B-Instruct"  # 軽量
        elif score < 30:
            return "Qwen2.5-Coder-14B-Instruct"  # 中量
        else:
            return "Qwen2.5-Coder-32B-Instruct"  # 高精度


if __name__ == "__main__":
    # テスト
    analyzer = DifficultyAnalyzer()
    
    # テストケース1：軽量タスク
    prompt1 = "この関数のタイポを修正して"
    context1 = {"code_context": "def hello():\n    print('helo')"}
    score1 = analyzer.calculate_difficulty(prompt1, context1)
    print(f"テスト1 - プロンプト: {prompt1}")
    print(f"  スコア: {score1:.2f}")
    print(f"  レベル: {analyzer.get_difficulty_level(score1)}")
    print(f"  推奨モデル: {analyzer.get_recommended_model(score1)}")
    print()
    
    # テストケース2：中量タスク
    prompt2 = "このコードをリファクタリングして、関数を分割して"
    context2 = {
        "code_context": """
def process_data(data):
    for item in data:
        if item['type'] == 'A':
            result = item['value'] * 2
        elif item['type'] == 'B':
            result = item['value'] * 3
        else:
            result = item['value']
        print(result)
"""
    }
    score2 = analyzer.calculate_difficulty(prompt2, context2)
    print(f"テスト2 - プロンプト: {prompt2}")
    print(f"  スコア: {score2:.2f}")
    print(f"  レベル: {analyzer.get_difficulty_level(score2)}")
    print(f"  推奨モデル: {analyzer.get_recommended_model(score2)}")
    print()
    
    # テストケース3：高難易度タスク
    prompt3 = "このシステムのアーキテクチャを設計して、マイクロサービス化して、パフォーマンスを最適化して"
    context3 = {
        "code_context": """
class System:
    def __init__(self):
        self.services = []
    
    def add_service(self, service):
        self.services.append(service)
    
    def process(self, data):
        results = []
        for service in self.services:
            result = service.process(data)
            results.append(result)
        return results
"""
    }
    score3 = analyzer.calculate_difficulty(prompt3, context3)
    print(f"テスト3 - プロンプト: {prompt3}")
    print(f"  スコア: {score3:.2f}")
    print(f"  レベル: {analyzer.get_difficulty_level(score3)}")
    print(f"  推奨モデル: {analyzer.get_recommended_model(score3)}")



















