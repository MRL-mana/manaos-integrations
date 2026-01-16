"""
難易度ルーティング対応のLLMルーター
プロンプトの難易度を分析して、適切なモデルにルーティング
"""

import os
import logging
import requests
from typing import Dict, Any, Optional, List
from llm_difficulty_analyzer import DifficultyAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedLLMRouter:
    """難易度ルーティング対応のLLMルーター"""
    
    def __init__(self, lm_studio_url: str = "http://localhost:1234/v1", ollama_url: str = "http://localhost:11434"):
        """
        初期化
        
        Args:
            lm_studio_url: LM StudioのOpenAI互換API URL
            ollama_url: OllamaのAPI URL
        """
        self.analyzer = DifficultyAnalyzer()
        self.lm_studio_url = lm_studio_url
        self.ollama_url = ollama_url
        
        # モデル設定（LM Studio用）
        self.models = {
            "light": "Qwen2.5-Coder-7B-Instruct",
            "medium": "Qwen2.5-Coder-14B-Instruct",
            "heavy": "Qwen2.5-Coder-32B-Instruct"
        }
        
        # モデル設定（Ollama用）
        self.ollama_models = {
            "light": "qwen2.5-coder:7b",
            "medium": "qwen2.5-coder:14b",
            "heavy": "qwen2.5-coder:32b"
        }
        
        # 使用するLLMサーバー（"lm_studio" or "ollama"）
        self.llm_server = os.getenv("LLM_SERVER", "lm_studio")
    
    def route(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        リクエストをルーティング
        
        Args:
            prompt: ユーザーのプロンプト
            context: コンテキスト情報（code_context, file_path等）
            preferences: ユーザー設定（prefer_speed, prefer_quality等）
        
        Returns:
            {
                "model": "モデル名",
                "difficulty_score": スコア,
                "difficulty_level": "low/medium/high",
                "reasoning": "理由",
                "response": "応答",
                "response_time_ms": レスポンス時間（ミリ秒）
            }
        """
        if context is None:
            context = {}
        if preferences is None:
            preferences = {}
        
        # 難易度判定
        difficulty_score = self.analyzer.calculate_difficulty(prompt, context)
        difficulty_level = self.analyzer.get_difficulty_level(difficulty_score)
        
        # ユーザー設定を考慮
        prefer_speed = preferences.get("prefer_speed", False)
        prefer_quality = preferences.get("prefer_quality", False)
        force_model = preferences.get("force_model", None)
        
        # モデル選択
        if force_model:
            # ユーザーが明示的にモデルを指定
            model = force_model
            reasoning = f"ユーザー指定のモデルを使用: {model}"
        elif prefer_speed or difficulty_score < 10:
            # 速度優先 or 低難易度
            model_key = "light"
            model = self._get_model_name(model_key)
            reasoning = f"プロンプトが短く、単純なタスクのため軽量モデルを選択（難易度スコア: {difficulty_score:.2f}）"
        elif prefer_quality or difficulty_score > 30:
            # 品質優先 or 高難易度
            model_key = "heavy"
            model = self._get_model_name(model_key)
            reasoning = f"プロンプトが複雑で、高品質な応答が必要なため高精度モデルを選択（難易度スコア: {difficulty_score:.2f}）"
        else:
            # 中程度の難易度
            model_key = "medium"
            model = self._get_model_name(model_key)
            reasoning = f"中程度の複雑度のため中量モデルを選択（難易度スコア: {difficulty_score:.2f}）"
        
        # LLM呼び出し
        import time
        start_time = time.time()
        
        try:
            response = self._call_llm(model, prompt, context)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                "model": model,
                "difficulty_score": difficulty_score,
                "difficulty_level": difficulty_level,
                "reasoning": reasoning,
                "response": response,
                "response_time_ms": response_time_ms,
                "success": True
            }
        except Exception as e:
            logger.error(f"LLM呼び出しエラー: {e}")
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # フォールバック（軽量モデルに切り替え）
            if model_key != "light":
                logger.info("フォールバック: 軽量モデルに切り替え")
                try:
                    fallback_model = self._get_model_name("light")
                    response = self._call_llm(fallback_model, prompt, context)
                    return {
                        "model": fallback_model,
                        "difficulty_score": difficulty_score,
                        "difficulty_level": difficulty_level,
                        "reasoning": f"{reasoning}（フォールバック: {fallback_model}）",
                        "response": response,
                        "response_time_ms": response_time_ms,
                        "success": True,
                        "fallback_used": True
                    }
                except Exception as fallback_error:
                    logger.error(f"フォールバックも失敗: {fallback_error}")
            
            return {
                "model": model,
                "difficulty_score": difficulty_score,
                "difficulty_level": difficulty_level,
                "reasoning": reasoning,
                "response": None,
                "error": str(e),
                "response_time_ms": response_time_ms,
                "success": False
            }
    
    def _get_model_name(self, model_key: str) -> str:
        """
        モデルキーから実際のモデル名を取得
        
        Args:
            model_key: "light", "medium", "heavy"
        
        Returns:
            モデル名
        """
        if self.llm_server == "ollama":
            return self.ollama_models.get(model_key, self.ollama_models["light"])
        else:
            return self.models.get(model_key, self.models["light"])
    
    def _call_llm(self, model: str, prompt: str, context: Dict[str, Any]) -> str:
        """
        LLMを呼び出し
        
        Args:
            model: モデル名
            prompt: プロンプト
            context: コンテキスト情報
        
        Returns:
            LLMの応答
        """
        # システムプロンプトを構築
        system_prompt = "You are a helpful coding assistant. Provide clear, concise, and accurate code solutions."
        
        # コンテキストがあれば追加
        if context.get("code_context"):
            system_prompt += f"\n\nCode context:\n{context['code_context']}"
        
        # メッセージを構築
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        if self.llm_server == "ollama":
            # Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False
                },
                timeout=300.0
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama APIエラー: HTTP {response.status_code}")
            
            result = response.json()
            return result.get("message", {}).get("content", "")
        else:
            # LM Studio OpenAI互換API
            response = requests.post(
                f"{self.lm_studio_url}/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2048
                },
                timeout=300.0
            )
            
            if response.status_code != 200:
                raise Exception(f"LM Studio APIエラー: HTTP {response.status_code}")
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
    
    def get_available_models(self) -> List[str]:
        """
        利用可能なモデル一覧を取得
        
        Returns:
            モデル名のリスト
        """
        if self.llm_server == "ollama":
            return list(self.ollama_models.values())
        else:
            return list(self.models.values())


if __name__ == "__main__":
    # テスト
    router = EnhancedLLMRouter()
    
    # テストケース1：軽量タスク
    print("=== テスト1: 軽量タスク ===")
    result1 = router.route(
        prompt="この関数のタイポを修正して",
        context={"code_context": "def hello():\n    print('helo')"}
    )
    print(f"モデル: {result1['model']}")
    print(f"難易度スコア: {result1['difficulty_score']:.2f}")
    print(f"理由: {result1['reasoning']}")
    print(f"応答: {result1.get('response', 'エラー')[:100]}...")
    print()
    
    # テストケース2：中量タスク
    print("=== テスト2: 中量タスク ===")
    result2 = router.route(
        prompt="このコードをリファクタリングして、関数を分割して",
        context={
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
    )
    print(f"モデル: {result2['model']}")
    print(f"難易度スコア: {result2['difficulty_score']:.2f}")
    print(f"理由: {result2['reasoning']}")
    print()



















