"""
LLMメトリクス収集システム
プロンプト最適化の効果やパフォーマンスを測定
"""

import json
import os
from manaos_logger import get_logger
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from collections import defaultdict

logger = get_service_logger("llm-metrics")


class LLMMetrics:
    """LLMメトリクス収集クラス"""
    
    def __init__(self, metrics_dir: Optional[str] = None):
        """
        初期化
        
        Args:
            metrics_dir: メトリクス保存ディレクトリ（Noneの場合は自動決定）
        """
        if metrics_dir:
            self.metrics_dir = Path(metrics_dir)
        else:
            if Path("/root").exists() and os.access("/root", os.W_OK):
                self.metrics_dir = Path("/root/llm_metrics")
            else:
                self.metrics_dir = Path.home() / "llm_metrics"
        
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.metrics_dir / "metrics.json"
        self.metrics_data = self._load_metrics()
    
    def _load_metrics(self) -> Dict[str, Any]:
        """メトリクスデータを読み込み"""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ メトリクス読み込みエラー: {e}")
        
        return {
            "queries": [],
            "stats": {
                "total_queries": 0,
                "optimized_queries": 0,
                "cache_hits": 0,
                "average_response_time": 0.0,
                "average_prompt_length": 0.0,
                "average_answer_length": 0.0
            }
        }
    
    def _save_metrics(self):
        """メトリクスデータを保存"""
        try:
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(self.metrics_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ メトリクス保存エラー: {e}")
    
    def record_query(
        self,
        prompt: str,
        model: str,
        answer: str,
        response_time: float,
        optimized: bool = False,
        cache_hit: bool = False,
        prompt_length: Optional[int] = None,
        answer_length: Optional[int] = None,
        task_type: str = "rag"
    ):
        """
        クエリを記録
        
        Args:
            prompt: プロンプト
            model: モデル名
            answer: 回答
            response_time: 応答時間（秒）
            optimized: プロンプト最適化が適用されたか
            cache_hit: キャッシュヒットしたか
            prompt_length: プロンプトの長さ
            answer_length: 回答の長さ
            task_type: タスクタイプ
        """
        query_data = {
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt[:200],  # 最初の200文字のみ保存
            "model": model,
            "task_type": task_type,
            "response_time": response_time,
            "optimized": optimized,
            "cache_hit": cache_hit,
            "prompt_length": prompt_length or len(prompt),
            "answer_length": answer_length or len(answer)
        }
        
        self.metrics_data["queries"].append(query_data)
        
        # 統計を更新
        stats = self.metrics_data["stats"]
        stats["total_queries"] += 1
        if optimized:
            stats["optimized_queries"] += 1
        if cache_hit:
            stats["cache_hits"] += 1
        
        # 平均値を更新（簡易版：直近100件の平均）
        recent_queries = self.metrics_data["queries"][-100:]
        if recent_queries:
            stats["average_response_time"] = sum(q["response_time"] for q in recent_queries) / len(recent_queries)
            stats["average_prompt_length"] = sum(q["prompt_length"] for q in recent_queries) / len(recent_queries)
            stats["average_answer_length"] = sum(q["answer_length"] for q in recent_queries) / len(recent_queries)
        
        # 定期的に保存（100件ごと）
        if len(self.metrics_data["queries"]) % 100 == 0:
            self._save_metrics()
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        stats = self.metrics_data["stats"].copy()
        
        # 追加統計
        total = stats["total_queries"]
        if total > 0:
            stats["optimization_rate"] = stats["optimized_queries"] / total
            stats["cache_hit_rate"] = stats["cache_hits"] / total
        else:
            stats["optimization_rate"] = 0.0
            stats["cache_hit_rate"] = 0.0
        
        return stats
    
    def get_recent_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """最近のクエリを取得"""
        return self.metrics_data["queries"][-limit:]
    
    def clear_old_queries(self, keep_days: int = 30):
        """古いクエリを削除"""
        cutoff_date = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
        
        original_count = len(self.metrics_data["queries"])
        self.metrics_data["queries"] = [
            q for q in self.metrics_data["queries"]
            if datetime.fromisoformat(q["timestamp"]).timestamp() > cutoff_date
        ]
        
        deleted = original_count - len(self.metrics_data["queries"])
        self._save_metrics()
        logger.info(f"🗑️ 古いメトリクス削除: {deleted}件")
        return deleted


# グローバルメトリクスインスタンス
_global_metrics: Optional[LLMMetrics] = None


def get_metrics(enable: bool = True, **kwargs) -> Optional[LLMMetrics]:
    """
    グローバルメトリクスインスタンスを取得
    
    Args:
        enable: メトリクス収集を有効にするか
        **kwargs: LLMMetricsの初期化パラメータ
        
    Returns:
        LLMMetricsインスタンス、またはNone
    """
    global _global_metrics
    
    if not enable:
        return None
    
    if _global_metrics is None:
        _global_metrics = LLMMetrics(**kwargs)
    
    return _global_metrics

