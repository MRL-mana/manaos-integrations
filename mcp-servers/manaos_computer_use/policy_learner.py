#!/usr/bin/env python3
"""
ManaOS Computer Use System - Policy Learner
成功パターンから最適なWait時間・Retry回数を学習
"""

import json
import statistics
from typing import Dict, List, Any, Optional
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PolicyLearner:
    """
    ポリシー学習エンジン
    
    成功した実行ログから最適なパラメータを学習：
    - Wait時間
    - Retry回数
    - スクリーンショット頻度
    """
    
    def __init__(
        self,
        logs_dir: Optional[Path] = None,
        min_samples: int = 3
    ):
        """
        Args:
            logs_dir: ログディレクトリ
            min_samples: 学習に必要な最小サンプル数
        """
        self.logs_dir = logs_dir or Path("/root/manaos_computer_use/logs")
        self.min_samples = min_samples
        
        # 学習済みポリシー
        self.policies = self._load_or_init_policies()
    
    def _load_or_init_policies(self) -> Dict[str, Any]:
        """ポリシーを読み込むか初期化"""
        policy_file = self.logs_dir / "learned_policies.json"
        
        if policy_file.exists():
            try:
                with open(policy_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load policies: {e}")
        
        # 初期ポリシー
        return {
            "wait_times": {},      # {action_type: recommended_wait}
            "retry_counts": {},    # {action_type: recommended_retry}
            "screenshot_interval": 3,  # ステップ
            "updated_at": None
        }
    
    def learn_from_logs(self, lookback_days: int = 7) -> Dict[str, Any]:
        """
        ログから学習
        
        Args:
            lookback_days: 過去N日分のログを対象
        
        Returns:
            Dict: 学習結果
        """
        # 成功した実行のログを収集
        successful_logs = self._collect_successful_logs(lookback_days)
        
        if len(successful_logs) < self.min_samples:
            logger.warning(f"Not enough samples for learning: {len(successful_logs)} < {self.min_samples}")
            return self.policies
        
        logger.info(f"Learning from {len(successful_logs)} successful executions...")
        
        # Wait時間の学習
        self._learn_wait_times(successful_logs)
        
        # Retry回数の学習
        self._learn_retry_counts(successful_logs)
        
        # スクリーンショット頻度の学習
        self._learn_screenshot_interval(successful_logs)
        
        # 更新時刻を記録
        self.policies["updated_at"] = datetime.now().isoformat()
        
        # 保存
        self._save_policies()
        
        logger.info("Policy learning completed")
        return self.policies
    
    def _collect_successful_logs(self, lookback_days: int) -> List[Dict]:
        """成功した実行ログを収集"""
        logs = []
        cutoff_date = datetime.now().timestamp() - (lookback_days * 86400)
        
        for log_file in sorted(self.logs_dir.glob("execution_*.json"), reverse=True):
            # 日付チェック
            if log_file.stat().st_mtime < cutoff_date:
                break
            
            try:
                with open(log_file, 'r') as f:
                    data = json.load(f)
                
                # 成功したもののみ
                if data.get("status") == "success":
                    logs.append(data)
            
            except Exception as e:
                logger.debug(f"Failed to load {log_file}: {e}")
        
        return logs
    
    def _learn_wait_times(self, logs: List[Dict]) -> None:
        """Wait時間の最適値を学習"""
        wait_data = defaultdict(list)
        
        for log in logs:
            steps = log.get("steps", [])
            
            for i, step in enumerate(steps):
                if not step.get("success"):
                    continue
                
                action = step.get("action_taken", {})
                action_type = action.get("action_type")
                
                if not action_type or i == 0:
                    continue
                
                # 前のステップからの経過時間を計算
                try:
                    curr_time = datetime.fromisoformat(step.get("timestamp"))
                    prev_time = datetime.fromisoformat(steps[i-1].get("timestamp"))
                    actual_wait = (curr_time - prev_time).total_seconds()
                    
                    # 妥当な範囲（0.1s - 10s）のみ記録
                    if 0.1 <= actual_wait <= 10.0:
                        wait_data[action_type].append(actual_wait)
                except Exception as e:
                    logger.debug(f"Failed to calculate wait time: {e}")
        
        # 中央値を推奨値とする
        for action_type, waits in wait_data.items():
            if len(waits) >= self.min_samples:
                recommended = statistics.median(waits)
                self.policies["wait_times"][action_type] = round(recommended, 1)
    
    def _learn_retry_counts(self, logs: List[Dict]) -> None:
        """Retry回数の最適値を学習"""
        # 失敗→成功パターンを分析
        retry_success = defaultdict(list)
        
        for log in logs:
            steps = log.get("steps", [])
            
            for i, step in enumerate(steps):
                action_type = step.get("action_taken", {}).get("action_type")
                
                if not action_type:
                    continue
                
                # 連続する同じアクションのリトライパターンを検出
                # （簡易実装: 成功したアクションは retry=1 で十分）
                if step.get("success"):
                    retry_success[action_type].append(1)
        
        # 推奨リトライ回数
        for action_type, retries in retry_success.items():
            if len(retries) >= self.min_samples:
                # 95パーセンタイル
                recommended = int(statistics.quantiles(retries, n=20)[-1]) if len(retries) > 1 else 1
                self.policies["retry_counts"][action_type] = min(recommended, 3)  # 最大3回
    
    def _learn_screenshot_interval(self, logs: List[Dict]) -> None:
        """スクリーンショット頻度を学習"""
        intervals = []
        
        for log in logs:
            steps = log.get("steps", [])
            
            # SCREENSHOTアクション間のステップ数を計算
            screenshot_indices = [
                i for i, step in enumerate(steps)
                if step.get("action_taken", {}).get("action_type") == "screenshot"
            ]
            
            for i in range(len(screenshot_indices) - 1):
                interval = screenshot_indices[i + 1] - screenshot_indices[i]
                intervals.append(interval)
        
        if len(intervals) >= self.min_samples:
            # 中央値を推奨値とする
            recommended = int(statistics.median(intervals))
            self.policies["screenshot_interval"] = max(2, min(recommended, 5))  # 2-5の範囲
    
    def get_recommendation(
        self,
        action_type: str,
        metric: str = "wait"
    ) -> Optional[float]:
        """
        推奨値を取得
        
        Args:
            action_type: アクションタイプ
            metric: "wait" または "retry"
        
        Returns:
            float or None: 推奨値
        """
        if metric == "wait":
            return self.policies["wait_times"].get(action_type)
        elif metric == "retry":
            return self.policies["retry_counts"].get(action_type)
        else:
            return None
    
    def apply_to_scenario(
        self,
        scenario_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        学習済みポリシーをシナリオに適用
        
        Args:
            scenario_data: シナリオYAMLデータ
        
        Returns:
            Dict: ポリシー適用後のシナリオ
        """
        optimized = scenario_data.copy()
        
        for step in optimized.get("steps", []):
            action = step.get("action")
            
            # Wait時間の最適化
            recommended_wait = self.get_recommendation(action, "wait")
            if recommended_wait and "wait" not in step:
                step["wait"] = recommended_wait
            
            # Retry回数の最適化
            recommended_retry = self.get_recommendation(action, "retry")
            if recommended_retry and "retry" not in step:
                step["retry"] = recommended_retry
        
        return optimized
    
    def _save_policies(self) -> None:
        """ポリシーを保存"""
        policy_file = self.logs_dir / "learned_policies.json"
        
        with open(policy_file, 'w', encoding='utf-8') as f:
            json.dump(self.policies, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Policies saved: {policy_file}")
    
    def get_summary(self) -> Dict[str, Any]:
        """学習結果サマリー"""
        return {
            "total_policies": len(self.policies["wait_times"]) + len(self.policies["retry_counts"]),
            "wait_times": len(self.policies["wait_times"]),
            "retry_counts": len(self.policies["retry_counts"]),
            "screenshot_interval": self.policies["screenshot_interval"],
            "updated_at": self.policies["updated_at"],
            "policies": self.policies
        }


# ===== テスト用 =====

if __name__ == "__main__":
    print("🧠 Policy Learner - テスト")
    print("=" * 60)
    
    learner = PolicyLearner()
    
    # 現在のポリシー
    print("\n📋 Current policies:")
    summary = learner.get_summary()
    print(f"  Total policies: {summary['total_policies']}")
    print(f"  Wait times: {summary['wait_times']}")
    print(f"  Retry counts: {summary['retry_counts']}")
    print(f"  Screenshot interval: {summary['screenshot_interval']}")
    print(f"  Updated: {summary['updated_at']}")
    
    # 学習実行
    print("\n🧠 Learning from logs...")
    policies = learner.learn_from_logs(lookback_days=7)
    
    print("\n✅ Learned policies:")
    print(json.dumps(policies, indent=2, ensure_ascii=False))
    
    print("\n✅ Test completed")

