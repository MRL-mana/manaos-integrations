"""
学習システム
使用パターンから学習し、自動改善
"""

import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_service_logger("learning-system")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("LearningSystem")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("LearningSystem")

# 依存モジュール（オプション）
try:
    from mem0_integration import Mem0Integration
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    logger.warning("Mem0Integrationが利用できません")

try:
    from workflow_automation import WorkflowAutomation
    WORKFLOW_AVAILABLE = True
except ImportError:
    WORKFLOW_AVAILABLE = False
    logger.warning("WorkflowAutomationが利用できません")


class LearningSystem:
    """学習システム"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """初期化"""
        if MEM0_AVAILABLE:
            try:
                self.mem0 = Mem0Integration()
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"module": "Mem0Integration"},
                    user_message="Mem0統合の初期化に失敗しました"
                )
                logger.warning(f"Mem0統合初期化エラー: {error.message}")
                self.mem0 = None
        else:
            self.mem0 = None
        
        if WORKFLOW_AVAILABLE:
            try:
                self.workflow = WorkflowAutomation()
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"module": "WorkflowAutomation"},
                    user_message="ワークフロー自動化の初期化に失敗しました"
                )
                logger.warning(f"ワークフロー自動化初期化エラー: {error.message}")
                self.workflow = None
        else:
            self.workflow = None
        
        self.usage_patterns = defaultdict(list)
        self.preferences = {}
        self.optimizations = []
        self._feedback_history = []
        self.storage_path = storage_path or Path(__file__).parent / "learning_system_state.json"
        self._load_state()
        
        logger.info("✅ Learning System初期化完了")
    
    def _load_state(self):
        """状態を読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.usage_patterns = defaultdict(list, state.get("usage_patterns", {}))
                    self.preferences = state.get("preferences", {})
                    self.optimizations = state.get("optimizations", [])
                    self._feedback_history = state.get("feedback_history", [])
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"storage_path": str(self.storage_path)},
                    user_message="学習システムの状態読み込みに失敗しました"
                )
                logger.warning(f"状態読み込みエラー: {error.message}")
                self.usage_patterns = defaultdict(list)
                self.preferences = {}
                self.optimizations = []
                self._feedback_history = []
        else:
            self.usage_patterns = defaultdict(list)
            self.preferences = {}
            self.optimizations = []
            self._feedback_history = []
    
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
                        "feedback_history": self._feedback_history,
                        "last_updated": datetime.now().isoformat()
                    }, f, ensure_ascii=False, indent=2)
                
                # アトミックにリネーム
                temp_path.replace(self.storage_path)
                return
            except Exception as e:
                if attempt == max_retries - 1:
                    error = error_handler.handle_exception(
                        e,
                        context={"storage_path": str(self.storage_path), "attempt": attempt + 1},
                        user_message="学習システムの状態保存に失敗しました"
                    )
                    logger.warning(f"状態保存エラー（{max_retries}回リトライ後）: {error.message}")
                else:
                    import time
                    time.sleep(0.1 * (attempt + 1))  # 指数バックオフ
    
    def record_usage(
        self,
        action: str,
        context: Dict[str, Any],
        result: Dict[str, Any]
    ):
        """
        使用パターンを記録
        
        Args:
            action: 実行したアクション
            context: コンテキスト情報
            result: 実行結果
        """
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
        
        # Mem0に保存
        if self.mem0 and hasattr(self.mem0, 'is_available') and self.mem0.is_available():
            try:
                self.mem0.add_memory(
                    memory_text=f"アクション実行: {action}",
                    user_id="mana",
                    metadata={
                        "type": "usage_pattern",
                        "action": action,
                        "success": usage_record["success"],
                        "context": context
                    }
                )
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"action": action, "service": "Mem0"},
                    user_message="Mem0への記憶保存に失敗しました"
                )
                logger.warning(f"Mem0保存エラー: {error.message}")
    
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
        hour_counts = defaultdict(int)
        for records in self.usage_patterns.values():
            for record in records:
                try:
                    hour = datetime.fromisoformat(record["timestamp"]).hour
                    hour_counts[hour] += 1
                except (ValueError, KeyError, TypeError):
                    continue
        
        if hour_counts:
            peak_hour = max(hour_counts.items(), key=lambda x: x[1])
            analysis["time_patterns"] = {
                "peak_hour": peak_hour[0],
                "peak_count": peak_hour[1],
                "hour_distribution": dict(hour_counts)
            }
        
        # 推奨事項
        recommendations = []
        
        # 成功率が低いアクション
        for action, stats in analysis["success_rates"].items():
            if stats["rate"] < 50 and stats["total"] > 5:
                recommendations.append({
                    "type": "low_success_rate",
                    "action": action,
                    "rate": stats["rate"],
                    "suggestion": f"{action}の成功率が低いです。パラメータの調整を検討してください。"
                })
        
        # よく使われるアクションの最適化
        for item in analysis["most_used_actions"][:5]:
            if item["count"] > 10:
                recommendations.append({
                    "type": "frequent_action",
                    "action": item["action"],
                    "count": item["count"],
                    "suggestion": f"{item['action']}が頻繁に使用されています。自動化を検討してください。"
                })
        
        analysis["recommendations"] = recommendations
        
        return analysis
    
    def learn_preferences(self) -> Dict[str, Any]:
        """
        好みを学習
        
        Returns:
            学習された好み
        """
        preferences = {}
        
        # 画像生成の好みを学習
        image_gen_records = self.usage_patterns.get("image_generation", [])
        if image_gen_records:
            successful_records = [r for r in image_gen_records if r["success"]]
            if successful_records:
                # よく使われるパラメータを抽出
                widths = [r["context"].get("width", 512) for r in successful_records]
                heights = [r["context"].get("height", 512) for r in successful_records]
                steps = [r["context"].get("steps", 20) for r in successful_records]
                
                preferences["image_generation"] = {
                    "preferred_width": max(set(widths), key=widths.count) if widths else 512,
                    "preferred_height": max(set(heights), key=heights.count) if heights else 512,
                    "preferred_steps": max(set(steps), key=steps.count) if steps else 20
                }
        
        # モデル検索の好みを学習
        search_records = self.usage_patterns.get("model_search", [])
        if search_records:
            successful_records = [r for r in search_records if r["success"]]
            if successful_records:
                queries = [r["context"].get("query", "") for r in successful_records]
                if queries:
                    # よく使われるクエリを抽出
                    common_queries = Counter(queries).most_common(5)
                    preferences["model_search"] = {
                        "common_queries": [q[0] for q in common_queries]
                    }
        
        self.preferences = preferences
        self._save_state()
        
        return preferences
    
    def suggest_optimizations(self) -> List[Dict[str, Any]]:
        """
        最適化を提案
        
        Returns:
            最適化提案のリスト
        """
        analysis = self.analyze_patterns()
        preferences = self.learn_preferences()
        
        optimizations = []
        
        # 成功率が低いアクションの最適化
        for action, stats in analysis["success_rates"].items():
            if stats["rate"] < 60 and stats["total"] > 5:
                optimizations.append({
                    "type": "improve_success_rate",
                    "action": action,
                    "current_rate": stats["rate"],
                    "suggestion": f"{action}の成功率を向上させるため、パラメータの調整やエラーハンドリングの改善を検討してください。"
                })
        
        # よく使われるアクションの自動化
        for item in analysis["most_used_actions"][:3]:
            if item["count"] > 20:
                optimizations.append({
                    "type": "automate_frequent_action",
                    "action": item["action"],
                    "count": item["count"],
                    "suggestion": f"{item['action']}を自動化することで、効率を向上させることができます。"
                })
        
        # 時間パターンに基づく最適化
        if analysis.get("time_patterns"):
            peak_hour = analysis["time_patterns"].get("peak_hour")
            if peak_hour:
                optimizations.append({
                    "type": "schedule_optimization",
                    "peak_hour": peak_hour,
                    "suggestion": f"使用のピーク時間は{peak_hour}時です。この時間帯のリソース確保を検討してください。"
                })
        
        self.optimizations = optimizations
        self._save_state()
        
        return optimizations
    
    def apply_learned_preferences(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        学習された好みを適用
        
        Args:
            action: アクション名
            params: パラメータ
            
        Returns:
            最適化されたパラメータ
        """
        optimized_params = params.copy()
        
        if action == "image_generation" and "image_generation" in self.preferences:
            prefs = self.preferences["image_generation"]
            if "width" not in optimized_params:
                optimized_params["width"] = prefs.get("preferred_width", 512)
            if "height" not in optimized_params:
                optimized_params["height"] = prefs.get("preferred_height", 512)
            if "steps" not in optimized_params:
                optimized_params["steps"] = prefs.get("preferred_steps", 20)
        
        return optimized_params

    # =========================================================================
    # 自動フィードバックループ（v2追加）
    # =========================================================================

    def auto_apply_optimizations(self) -> Dict[str, Any]:
        """
        学習結果を実際のシステム設定に自動適用する。
        
        以下の自動調整を行う:
        1. 成功率が低いアクションのリトライ回数を増加
        2. 頻繁に使われるアクションのタイムアウトを延長
        3. 時間パターンに基づくレート制限の動的調整
        
        Returns:
            適用された変更のサマリー
        """
        analysis = self.analyze_patterns()
        changes_applied = []

        # --- 1. 成功率ベースのリトライ調整 ---
        retry_adjustments = self._adjust_retry_config(analysis)
        if retry_adjustments:
            changes_applied.extend(retry_adjustments)

        # --- 2. 頻出アクションのタイムアウト延長 ---
        timeout_adjustments = self._adjust_timeouts(analysis)
        if timeout_adjustments:
            changes_applied.extend(timeout_adjustments)

        # --- 3. LLMルーティング成功率の改善 ---
        routing_adjustments = self._adjust_llm_routing(analysis)
        if routing_adjustments:
            changes_applied.extend(routing_adjustments)

        # 適用履歴を記録
        if changes_applied:
            self._feedback_history.append({
                "timestamp": datetime.now().isoformat(),
                "changes": changes_applied,
                "trigger": "auto_apply"
            })
            # 直近20件の適用履歴のみ保持
            self._feedback_history = self._feedback_history[-20:]
            self._save_state()
            logger.info(f"✅ フィードバックループ: {len(changes_applied)}件の最適化を適用")
        else:
            logger.info("フィードバックループ: 調整不要（現在の設定で十分）")

        return {
            "changes_applied": changes_applied,
            "analysis_summary": {
                "actions_analyzed": len(analysis.get("success_rates", {})),
                "recommendations": len(analysis.get("recommendations", []))
            },
            "timestamp": datetime.now().isoformat()
        }

    def _adjust_retry_config(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """成功率が低いアクションのリトライ設定を調整"""
        changes = []
        retry_config_path = self.storage_path.parent / "manaos_timeout_config.json"

        if not retry_config_path.exists():
            return changes

        try:
            with open(retry_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            return changes

        modified = False
        for action, stats in analysis.get("success_rates", {}).items():
            if stats["rate"] < 50 and stats["total"] >= 5:
                # 成功率50%未満 → リトライ回数を+1（上限5）
                current_retries = config.get("retries", {}).get(action, 2)
                new_retries = min(current_retries + 1, 5)
                if new_retries != current_retries:
                    config.setdefault("retries", {})[action] = new_retries
                    modified = True
                    changes.append({
                        "type": "retry_increase",
                        "action": action,
                        "old_value": current_retries,
                        "new_value": new_retries,
                        "reason": f"成功率 {stats['rate']:.0f}% (< 50%)"
                    })

        if modified:
            try:
                with open(retry_config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"リトライ設定の保存に失敗: {e}")
                return []

        return changes

    def _adjust_timeouts(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """頻出アクションのタイムアウトを調整"""
        changes = []
        timeout_config_path = self.storage_path.parent / "manaos_timeout_config.json"

        if not timeout_config_path.exists():
            return changes

        try:
            with open(timeout_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            return changes

        modified = False
        for item in analysis.get("most_used_actions", [])[:5]:
            action = item["action"]
            action_stats = analysis.get("success_rates", {}).get(action, {})
            # 高頻度かつ成功率が中途半端（50-80%）→ タイムアウト延長
            if item["count"] > 15 and 50 <= action_stats.get("rate", 100) < 80:
                current_timeout = config.get("timeouts", {}).get(action, 10)
                new_timeout = min(current_timeout + 5, 60)
                if new_timeout != current_timeout:
                    config.setdefault("timeouts", {})[action] = new_timeout
                    modified = True
                    changes.append({
                        "type": "timeout_increase",
                        "action": action,
                        "old_value": current_timeout,
                        "new_value": new_timeout,
                        "reason": f"高頻度({item['count']}回) + 成功率{action_stats.get('rate', 0):.0f}%"
                    })

        if modified:
            try:
                with open(timeout_config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"タイムアウト設定の保存に失敗: {e}")
                return []

        return changes

    def _adjust_llm_routing(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """LLMルーティングの成功率に基づいて優先モデルを調整"""
        changes = []
        routing_config_path = self.storage_path.parent / "llm_routing_config.yaml"

        # LLM関連アクションの成功率を確認
        llm_actions = {
            action: stats
            for action, stats in analysis.get("success_rates", {}).items()
            if "llm" in action.lower() or "chat" in action.lower() or "generate" in action.lower()
        }

        if not llm_actions:
            return changes

        # 成功率が高いモデル/アクションを記録（設定ファイルへの直接書き込みはしない）
        # 代わりに preferences に学習結果を保存
        for action, stats in llm_actions.items():
            if stats["total"] >= 3:
                self.preferences.setdefault("llm_routing", {})[action] = {
                    "success_rate": stats["rate"],
                    "sample_size": stats["total"],
                    "last_updated": datetime.now().isoformat()
                }
                changes.append({
                    "type": "llm_preference_update",
                    "action": action,
                    "success_rate": stats["rate"],
                    "reason": f"LLM成功率学習 ({stats['total']}回中{stats['success']}回成功)"
                })

        return changes

    def get_feedback_history(self) -> List[Dict[str, Any]]:
        """フィードバックループの適用履歴を取得"""
        return list(self._feedback_history)
    
    def get_status(self) -> Dict[str, Any]:
        """状態を取得"""
        analysis = self.analyze_patterns()
        preferences = self.learn_preferences()
        optimizations = self.suggest_optimizations()
        
        return {
            "total_actions_recorded": sum(len(records) for records in self.usage_patterns.values()),
            "unique_actions": len(self.usage_patterns),
            "analysis": analysis,
            "preferences": preferences,
            "optimizations": optimizations,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("学習システムテスト")
    print("=" * 60)
    
    learning = LearningSystem()
    
    # 使用パターンを記録（サンプル）
    print("\n使用パターンを記録中...")
    learning.record_usage(
        "image_generation",
        {"prompt": "landscape", "width": 512, "height": 512, "steps": 20},
        {"status": "success", "prompt_id": "test123"}
    )
    
    learning.record_usage(
        "image_generation",
        {"prompt": "portrait", "width": 768, "height": 768, "steps": 30},
        {"status": "success", "prompt_id": "test456"}
    )
    
    learning.record_usage(
        "model_search",
        {"query": "realistic"},
        {"status": "success", "count": 10}
    )
    
    # パターンを分析
    print("\nパターンを分析中...")
    analysis = learning.analyze_patterns()
    print(f"最も使用されるアクション: {analysis['most_used_actions']}")
    print(f"成功率: {analysis['success_rates']}")
    
    # 好みを学習
    print("\n好みを学習中...")
    preferences = learning.learn_preferences()
    print(f"学習された好み: {preferences}")
    
    # 最適化を提案
    print("\n最適化を提案中...")
    optimizations = learning.suggest_optimizations()
    print(f"最適化提案: {len(optimizations)}件")
    for opt in optimizations:
        print(f"  - {opt['suggestion']}")
    
    # 状態を表示
    status = learning.get_status()
    print(f"\n状態:")
    print(f"  記録されたアクション数: {status['total_actions_recorded']}")
    print(f"  ユニークアクション数: {status['unique_actions']}")


if __name__ == "__main__":
    main()




















