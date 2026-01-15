#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 学習システム強化版
予測的学習・自動最適化・パラメータ自動調整
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from collections import defaultdict, Counter
import statistics

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# 最適化モジュールのインポート
from unified_cache_system import get_unified_cache

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("LearningSystemEnhanced")

# キャッシュシステムの取得
cache_system = get_unified_cache()


class LearningSystemEnhanced:
    """学習システム強化版"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """初期化"""
        self.usage_patterns = defaultdict(list)
        self.preferences = {}
        self.optimizations = []
        self.prediction_models = {}
        self.auto_optimization_enabled = True
        
        self.storage_path = storage_path or Path(__file__).parent / "learning_system_enhanced_state.json"
        self._load_state()
        
        logger.info("✅ Learning System Enhanced初期化完了")
    
    def _load_state(self):
        """状態を読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.usage_patterns = defaultdict(list, state.get("usage_patterns", {}))
                    self.preferences = state.get("preferences", {})
                    self.optimizations = state.get("optimizations", [])
                    self.prediction_models = state.get("prediction_models", {})
            except Exception as e:
                logger.warning(f"状態読み込みエラー: {e}")
    
    def _save_state(self, max_retries: int = 3):
        """状態を保存（リトライ機能付き）"""
        for attempt in range(max_retries):
            try:
                # ディレクトリが存在しない場合は作成
                self.storage_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 一時ファイルに書き込んでからリネーム（アトミック操作）
                temp_path = self.storage_path.with_suffix('.tmp')
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "usage_patterns": dict(self.usage_patterns),
                        "preferences": self.preferences,
                        "optimizations": self.optimizations,
                        "prediction_models": self.prediction_models,
                        "last_updated": datetime.now().isoformat()
                    }, f, ensure_ascii=False, indent=2)
                
                # アトミックにリネーム
                temp_path.replace(self.storage_path)
                return
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.warning(f"状態保存エラー（{max_retries}回リトライ後）: {e}")
                else:
                    import time
                    time.sleep(0.1 * (attempt + 1))  # 指数バックオフ
    
    def record_usage(
        self,
        action: str,
        context: Dict[str, Any],
        result: Dict[str, Any]
    ):
        """使用パターンを記録"""
        usage_record = {
            "action": action,
            "context": context,
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "success": result.get("status") == "success" or result.get("success", False)
        }
        
        self.usage_patterns[action].append(usage_record)
        
        # 最新100件のみ保持
        if len(self.usage_patterns[action]) > 100:
            self.usage_patterns[action] = self.usage_patterns[action][-100:]
        
        self._save_state()
        
        # 自動最適化が有効な場合、最適化を実行
        if self.auto_optimization_enabled:
            self._auto_optimize(action, usage_record)
    
    def predict_next_action(self, current_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        次のアクションを予測（予測的学習）
        
        Args:
            current_context: 現在のコンテキスト
        
        Returns:
            予測されたアクションのリスト
        """
        predictions = []
        
        # 時間パターンから予測
        current_hour = datetime.now().hour
        hour_patterns = self._analyze_hour_patterns()
        
        if current_hour in hour_patterns:
            for action, probability in hour_patterns[current_hour].items():
                predictions.append({
                    "action": action,
                    "probability": probability,
                    "reason": f"時間パターン（{current_hour}時）"
                })
        
        # コンテキストパターンから予測
        context_patterns = self._analyze_context_patterns()
        for pattern, actions in context_patterns.items():
            if self._matches_pattern(current_context, pattern):
                for action, probability in actions.items():
                    predictions.append({
                        "action": action,
                        "probability": probability,
                        "reason": f"コンテキストパターン: {pattern}"
                    })
        
        # 確率でソート
        predictions.sort(key=lambda x: x["probability"], reverse=True)
        
        return predictions[:5]  # 上位5件
    
    def _analyze_hour_patterns(self) -> Dict[int, Dict[str, float]]:
        """時間パターンを分析"""
        hour_patterns = defaultdict(lambda: defaultdict(int))
        
        for action, records in self.usage_patterns.items():
            for record in records:
                try:
                    hour = datetime.fromisoformat(record["timestamp"]).hour
                    hour_patterns[hour][action] += 1
                except:
                    pass
        
        # 確率に変換
        result = {}
        for hour, actions in hour_patterns.items():
            total = sum(actions.values())
            result[hour] = {
                action: count / total
                for action, count in actions.items()
            }
        
        return result
    
    def _analyze_context_patterns(self) -> Dict[str, Dict[str, float]]:
        """コンテキストパターンを分析"""
        context_patterns = defaultdict(lambda: defaultdict(int))
        
        for action, records in self.usage_patterns.items():
            for record in records:
                context = record.get("context", {})
                # 主要なコンテキストキーを抽出
                pattern_key = self._extract_pattern_key(context)
                if pattern_key:
                    context_patterns[pattern_key][action] += 1
        
        # 確率に変換
        result = {}
        for pattern, actions in context_patterns.items():
            total = sum(actions.values())
            result[pattern] = {
                action: count / total
                for action, count in actions.items()
            }
        
        return result
    
    def _extract_pattern_key(self, context: Dict[str, Any]) -> Optional[str]:
        """コンテキストからパターンキーを抽出"""
        keys = []
        for key in ["type", "category", "source"]:
            if key in context:
                keys.append(f"{key}:{context[key]}")
        
        return "|".join(keys) if keys else None
    
    def _matches_pattern(self, context: Dict[str, Any], pattern: str) -> bool:
        """コンテキストがパターンに一致するかチェック"""
        pattern_parts = pattern.split("|")
        for part in pattern_parts:
            key, value = part.split(":", 1)
            if context.get(key) != value:
                return False
        return True
    
    def _auto_optimize(self, action: str, usage_record: Dict[str, Any]):
        """自動最適化を実行"""
        # 成功率が低い場合、パラメータを調整
        action_records = self.usage_patterns[action]
        if len(action_records) >= 5:
            success_rate = sum(1 for r in action_records if r["success"]) / len(action_records)
            
            if success_rate < 0.5:
                # 成功したレコードのパラメータを分析
                successful_records = [r for r in action_records if r["success"]]
                if successful_records:
                    optimal_params = self._find_optimal_params(successful_records)
                    self.preferences[action] = optimal_params
                    logger.info(f"自動最適化: {action}のパラメータを調整しました")
                    self._save_state()
    
    def _find_optimal_params(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """最適なパラメータを見つける"""
        optimal = {}
        
        # 各パラメータの最頻値を取得
        param_values = defaultdict(list)
        for record in records:
            context = record.get("context", {})
            for key, value in context.items():
                if isinstance(value, (int, float, str)):
                    param_values[key].append(value)
        
        for key, values in param_values.items():
            if values:
                if isinstance(values[0], (int, float)):
                    # 数値の場合は平均値
                    optimal[key] = statistics.mean(values)
                else:
                    # 文字列の場合は最頻値
                    optimal[key] = Counter(values).most_common(1)[0][0]
        
        return optimal
    
    def apply_auto_optimization(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        自動最適化を適用
        
        Args:
            action: アクション名
            params: パラメータ
        
        Returns:
            最適化されたパラメータ
        """
        optimized_params = params.copy()
        
        # 学習された好みを適用
        if action in self.preferences:
            prefs = self.preferences[action]
            for key, value in prefs.items():
                if key not in optimized_params:
                    optimized_params[key] = value
        
        # 予測に基づく事前最適化
        predictions = self.predict_next_action(params)
        if predictions:
            predicted_action = predictions[0]["action"]
            if predicted_action == action and predicted_action in self.preferences:
                # 予測されたアクションの最適パラメータを適用
                prefs = self.preferences[predicted_action]
                for key, value in prefs.items():
                    if key not in optimized_params:
                        optimized_params[key] = value
        
        return optimized_params
    
    def analyze_patterns(self) -> Dict[str, Any]:
        """
        パターンを分析
        
        Returns:
            分析結果
        """
        analysis = {
            "most_used_actions": [],
            "success_rates": {},
            "time_patterns": {},
            "recommendations": []
        }
        
        # 最も使用されるアクション
        action_counts = Counter()
        for action, records in self.usage_patterns.items():
            action_counts[action] = len(records)
        
        analysis["most_used_actions"] = [
            {"action": action, "count": count}
            for action, count in action_counts.most_common(10)
        ]
        
        # 成功率
        for action, records in self.usage_patterns.items():
            if records:
                success_count = sum(1 for r in records if r["success"])
                success_rate = success_count / len(records) * 100
                analysis["success_rates"][action] = {
                    "rate": success_rate,
                    "total": len(records),
                    "success": success_count,
                    "failed": len(records) - success_count
                }
        
        # 時間パターン
        from collections import defaultdict
        hour_counts = defaultdict(int)
        for records in self.usage_patterns.values():
            for record in records:
                try:
                    hour = datetime.fromisoformat(record["timestamp"]).hour
                    hour_counts[hour] += 1
                except:
                    pass
        
        if hour_counts:
            peak_hour = max(hour_counts.items(), key=lambda x: x[1])
            analysis["time_patterns"] = {
                "peak_hour": peak_hour[0],
                "peak_count": peak_hour[1],
                "hour_distribution": dict(hour_counts)
            }
        
        return analysis
    
    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """最適化提案を取得"""
        suggestions = []
        
        # 成功率が低いアクション
        for action, records in self.usage_patterns.items():
            if len(records) >= 5:
                success_rate = sum(1 for r in records if r["success"]) / len(records)
                if success_rate < 0.5:
                    suggestions.append({
                        "type": "improve_success_rate",
                        "action": action,
                        "current_rate": success_rate,
                        "suggestion": f"{action}の成功率が低いです。パラメータの調整を検討してください。"
                    })
        
        # よく使われるアクションの自動化
        action_counts = Counter()
        for action, records in self.usage_patterns.items():
            action_counts[action] = len(records)
        
        for action, count in action_counts.most_common(3):
            if count > 20:
                suggestions.append({
                    "type": "automate_frequent_action",
                    "action": action,
                    "count": count,
                    "suggestion": f"{action}を自動化することで、効率を向上させることができます。"
                })
        
        return suggestions


def main():
    """テスト用メイン関数"""
    print("学習システム強化版テスト")
    print("=" * 60)
    
    learning = LearningSystemEnhanced()
    
    # 使用パターンを記録
    learning.record_usage(
        action="test_action",
        context={"param": "value"},
        result={"status": "success"}
    )
    
    # 予測
    predictions = learning.predict_next_action({"type": "test"})
    print(f"予測結果: {len(predictions)}件")


if __name__ == "__main__":
    main()















