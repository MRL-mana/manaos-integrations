"""
マルチモデル対応
複数のモデルを同時に使用・比較
"""

from manaos_logger import get_logger
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import os

try:
    from _paths import OLLAMA_PORT
except Exception:
    OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))

logger = get_logger(__name__)


class MultiModelManager:
    """マルチモデル管理クラス"""
    
    def __init__(self, models: List[str], base_url: Optional[str] = None):
        """
        初期化
        
        Args:
            models: モデルリスト
            base_url: OllamaのベースURL
        """
        self.models = models
        self.base_url = base_url or os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")
        self.model_stats = {model: {"calls": 0, "successes": 0, "errors": 0} for model in models}
    
    def query_all(
        self,
        prompt: str,
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """
        全モデルでクエリを実行
        
        Args:
            prompt: プロンプト
            timeout: タイムアウト（秒）
            
        Returns:
            各モデルの結果
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=len(self.models)) as executor:
            futures = {
                executor.submit(self._query_model, model, prompt): model
                for model in self.models
            }
            
            for future in as_completed(futures, timeout=timeout):
                model = futures[future]
                try:
                    result = future.result()
                    results[model] = result
                    self.model_stats[model]["successes"] += 1
                except Exception as e:
                    results[model] = {"error": str(e)}
                    self.model_stats[model]["errors"] += 1
                    logger.error(f"モデル {model} のクエリエラー: {e}")
                
                self.model_stats[model]["calls"] += 1
        
        return results
    
    def query_best(
        self,
        prompt: str,
        selection_criteria: Callable = None
    ) -> Dict[str, Any]:
        """
        最適なモデルでクエリを実行
        
        Args:
            prompt: プロンプト
            selection_criteria: モデル選択基準関数
            
        Returns:
            最適なモデルの結果
        """
        if selection_criteria is None:
            # デフォルト: 成功率が最も高いモデル
            best_model = max(
                self.models,
                key=lambda m: self.model_stats[m]["successes"] / max(self.model_stats[m]["calls"], 1)
            )
        else:
            best_model = selection_criteria(self.models, self.model_stats)
        
        logger.info(f"最適モデル選択: {best_model}")
        return self._query_model(best_model, prompt)
    
    def compare_models(
        self,
        prompt: str,
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """
        モデルを比較
        
        Args:
            prompt: プロンプト
            timeout: タイムアウト（秒）
            
        Returns:
            比較結果
        """
        results = self.query_all(prompt, timeout)
        
        comparison = {
            "prompt": prompt[:200],
            "models": {},
            "best_model": None,
            "fastest_model": None,
            "comparison": []
        }
        
        fastest_time = float('inf')
        best_score = -1
        
        for model, result in results.items():
            if "error" in result:
                comparison["models"][model] = {
                    "success": False,
                    "error": result["error"]
                }
                continue
            
            response_time = result.get("response_time", 0)
            response_length = len(result.get("response", ""))
            
            # スコア計算（応答時間と長さのバランス）
            score = response_length / max(response_time, 0.1)
            
            comparison["models"][model] = {
                "success": True,
                "response_time": response_time,
                "response_length": response_length,
                "score": score,
                "response": result.get("response", "")[:500]  # 最初の500文字
            }
            
            if response_time < fastest_time:
                fastest_time = response_time
                comparison["fastest_model"] = model
            
            if score > best_score:
                best_score = score
                comparison["best_model"] = model
        
        # 比較リストを作成
        comparison["comparison"] = sorted(
            [
                {
                    "model": model,
                    "response_time": data.get("response_time", 0),
                    "score": data.get("score", 0)
                }
                for model, data in comparison["models"].items()
                if data.get("success", False)
            ],
            key=lambda x: x["score"],
            reverse=True
        )
        
        return comparison
    
    def _query_model(self, model: str, prompt: str) -> Dict[str, Any]:
        """モデルでクエリを実行"""
        import requests
        
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "response": result.get("response", ""),
                "response_time": time.time() - start_time,
                "model": model
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time,
                "model": model
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        stats = {}
        
        for model in self.models:
            calls = self.model_stats[model]["calls"]
            successes = self.model_stats[model]["successes"]
            errors = self.model_stats[model]["errors"]
            
            stats[model] = {
                "calls": calls,
                "successes": successes,
                "errors": errors,
                "success_rate": successes / max(calls, 1),
                "error_rate": errors / max(calls, 1)
            }
        
        return stats


class ModelSelector:
    """モデル選択クラス"""
    
    def __init__(self, models: List[str]):
        """
        初期化
        
        Args:
            models: モデルリスト
        """
        self.models = models
        self.usage_history = []
    
    def select_model(
        self,
        task_type: str = "general",
        priority: str = "quality"  # "quality", "speed", "balanced"
    ) -> str:
        """
        タスクに最適なモデルを選択
        
        Args:
            task_type: タスクタイプ
            priority: 優先度
            
        Returns:
            選択されたモデル名
        """
        # タスクタイプに基づくモデルマッピング
        task_model_map = {
            "rag": "qwen3:4b",
            "chat": "qwen3:4b",
            "code": "qwen3:4b",
            "general": "qwen3:4b"
        }
        
        # 優先度に基づくモデルマッピング
        priority_model_map = {
            "quality": "qwen3:4b",
            "speed": "qwen2.5:7b",
            "balanced": "qwen3:4b"
        }
        
        # タスクタイプを優先
        if task_type in task_model_map:
            selected = task_model_map[task_type]
            if selected in self.models:
                return selected
        
        # 優先度に基づいて選択
        if priority in priority_model_map:
            selected = priority_model_map[priority]
            if selected in self.models:
                return selected
        
        # デフォルト: 最初のモデル
        return self.models[0] if self.models else "qwen3:4b"
    
    def record_usage(self, model: str, success: bool, response_time: float):
        """使用履歴を記録"""
        self.usage_history.append({
            "model": model,
            "success": success,
            "response_time": response_time,
            "timestamp": time.time()
        })
        
        # 履歴を100件に制限
        if len(self.usage_history) > 100:
            self.usage_history = self.usage_history[-100:]

