#!/usr/bin/env python3
"""
ManaOS Computer Use System - Error Recovery Playbook
エラー発生時の自動リカバリプレイブック
"""

import logging
from typing import Dict, List, Any
from enum import Enum

try:
    from .manaos_computer_use_types import Action, ActionType
except ImportError:
    from manaos_computer_use_types import Action, ActionType

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """エラータイプ"""
    CLICK_FAILED = "click_failed"
    ELEMENT_NOT_FOUND = "element_not_found"
    WINDOW_NOT_ACTIVE = "window_not_active"
    SCREENSHOT_FAILED = "screenshot_failed"
    TIMEOUT = "timeout"
    UNEXPECTED_DIALOG = "unexpected_dialog"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    """リカバリアクション"""
    RETRY = "retry"
    ESC_AND_RETRY = "esc_and_retry"
    REFRESH = "refresh"
    RESTART_APP = "restart_app"
    WAIT_LONGER = "wait_longer"
    SKIP = "skip"
    ABORT = "abort"


class RecoveryPlaybook:
    """
    エラーリカバリプレイブック
    
    エラーパターンごとに最適なリカバリ手順を定義
    """
    
    # エラーパターン → リカバリ手順のマッピング
    PLAYBOOK = {
        ErrorType.CLICK_FAILED: [
            # 手順1: 少し待ってリトライ
            {
                "action": RecoveryAction.WAIT_LONGER,
                "params": {"duration": 1.0},
                "description": "UI要素のロード待ち"
            },
            # 手順2: ESC押下して状態リセット
            {
                "action": RecoveryAction.ESC_AND_RETRY,
                "params": {},
                "description": "ダイアログを閉じて再試行"
            },
            # 手順3: アプリ再起動
            {
                "action": RecoveryAction.RESTART_APP,
                "params": {},
                "description": "アプリケーション再起動"
            }
        ],
        
        ErrorType.ELEMENT_NOT_FOUND: [
            {
                "action": RecoveryAction.WAIT_LONGER,
                "params": {"duration": 2.0},
                "description": "要素の表示待ち"
            },
            {
                "action": RecoveryAction.REFRESH,
                "params": {},
                "description": "画面更新（F5）"
            },
            {
                "action": RecoveryAction.ESC_AND_RETRY,
                "params": {},
                "description": "ESCで状態リセット"
            }
        ],
        
        ErrorType.WINDOW_NOT_ACTIVE: [
            {
                "action": RecoveryAction.RETRY,
                "params": {"click_window": True},
                "description": "ウィンドウをクリックしてアクティブ化"
            }
        ],
        
        ErrorType.SCREENSHOT_FAILED: [
            {
                "action": RecoveryAction.WAIT_LONGER,
                "params": {"duration": 0.5},
                "description": "画面描画完了待ち"
            },
            {
                "action": RecoveryAction.RETRY,
                "params": {},
                "description": "スクリーンショット再試行"
            }
        ],
        
        ErrorType.TIMEOUT: [
            {
                "action": RecoveryAction.ESC_AND_RETRY,
                "params": {},
                "description": "ESCで処理中断→再試行"
            },
            {
                "action": RecoveryAction.RESTART_APP,
                "params": {},
                "description": "アプリ再起動"
            }
        ],
        
        ErrorType.UNEXPECTED_DIALOG: [
            {
                "action": RecoveryAction.ESC_AND_RETRY,
                "params": {},
                "description": "ダイアログを閉じる"
            },
            {
                "action": RecoveryAction.RETRY,
                "params": {"try_enter": True},
                "description": "Enterでダイアログ確定"
            }
        ]
    }
    
    def __init__(self):
        """初期化"""
        self.recovery_history = []
    
    def get_recovery_plan(
        self,
        error_type: ErrorType,
        max_attempts: int = 3
    ) -> List[Dict[str, Any]]:
        """
        エラータイプに対するリカバリプランを取得
        
        Args:
            error_type: エラータイプ
            max_attempts: 最大試行回数
        
        Returns:
            List[Dict]: リカバリ手順のリスト
        """
        playbook = self.PLAYBOOK.get(error_type, [])
        
        # max_attemptsまで切り詰め
        return playbook[:max_attempts]
    
    def execute_recovery(
        self,
        error_type: ErrorType,
        executor: Any,  # ActionExecutor
        max_attempts: int = 3
    ) -> bool:
        """
        リカバリを実行
        
        Args:
            error_type: エラータイプ
            executor: ActionExecutor インスタンス
            max_attempts: 最大試行回数
        
        Returns:
            bool: リカバリ成功
        """
        plan = self.get_recovery_plan(error_type, max_attempts)
        
        logger.info(f"🔧 Starting recovery for {error_type.value}")
        logger.info(f"   Recovery plan: {len(plan)} step(s)")
        
        for i, step in enumerate(plan, 1):
            logger.info(f"   Step {i}/{len(plan)}: {step['description']}")
            
            try:
                success = self._execute_recovery_step(step, executor)
                
                if success:
                    logger.info(f"   ✅ Recovery successful at step {i}")
                    self._record_recovery(error_type, i, True)
                    return True
                else:
                    logger.warning(f"   ⚠️ Recovery step {i} failed, trying next...")
            
            except Exception as e:
                logger.error(f"   ❌ Recovery step {i} error: {e}")
        
        logger.error(f"   ❌ Recovery failed after {len(plan)} attempts")
        self._record_recovery(error_type, len(plan), False)
        return False
    
    def _execute_recovery_step(
        self,
        step: Dict[str, Any],
        executor: Any
    ) -> bool:
        """リカバリステップを実行"""
        action_type = step["action"]
        params = step.get("params", {})
        
        if action_type == RecoveryAction.RETRY:
            # 単純リトライ（何もしない）
            return True
        
        elif action_type == RecoveryAction.ESC_AND_RETRY:
            # ESCキーを押す
            result = executor.execute(Action(
                action_type=ActionType.PRESS_KEY,
                parameters={"key": "esc"}
            ))
            return result.get("success", False)
        
        elif action_type == RecoveryAction.REFRESH:
            # F5キーを押す
            result = executor.execute(Action(
                action_type=ActionType.PRESS_KEY,
                parameters={"key": "f5"}
            ))
            return result.get("success", False)
        
        elif action_type == RecoveryAction.WAIT_LONGER:
            # 待機
            import time
            duration = params.get("duration", 1.0)
            time.sleep(duration)
            return True
        
        elif action_type == RecoveryAction.RESTART_APP:
            # アプリ再起動（Alt+F4 → 再起動）
            # 簡易実装: Alt+F4のみ
            result = executor.execute(Action(
                action_type=ActionType.HOTKEY,
                parameters={"keys": ["alt", "f4"]}
            ))
            return result.get("success", False)
        
        else:
            return False
    
    def _record_recovery(
        self,
        error_type: ErrorType,
        attempts: int,
        success: bool
    ) -> None:
        """リカバリ履歴を記録"""
        self.recovery_history.append({
            "error_type": error_type.value,
            "attempts": attempts,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """リカバリ統計を取得"""
        if not self.recovery_history:
            return {
                "total_recoveries": 0,
                "success_rate": 0.0,
                "avg_attempts": 0.0
            }
        
        total = len(self.recovery_history)
        successes = sum(1 for r in self.recovery_history if r["success"])
        
        return {
            "total_recoveries": total,
            "success_rate": successes / total,
            "avg_attempts": sum(r["attempts"] for r in self.recovery_history) / total,
            "by_error_type": self._group_by_error_type()
        }
    
    def _group_by_error_type(self) -> Dict[str, Dict]:
        """エラータイプ別の統計"""
        from collections import defaultdict
        
        stats = defaultdict(lambda: {"count": 0, "successes": 0})
        
        for record in self.recovery_history:
            error_type = record["error_type"]
            stats[error_type]["count"] += 1
            if record["success"]:
                stats[error_type]["successes"] += 1
        
        return {
            k: {
                "count": v["count"],
                "success_rate": v["successes"] / v["count"] if v["count"] > 0 else 0.0
            }
            for k, v in stats.items()
        }


# ===== テスト用 =====

if __name__ == "__main__":
    print("🔧 Recovery Playbook - テスト")
    print("=" * 60)
    
    playbook = RecoveryPlaybook()
    
    # 各エラータイプのプランを表示
    print("\n📋 Recovery plans by error type:")
    print("-" * 60)
    
    for error_type in ErrorType:
        if error_type == ErrorType.UNKNOWN:
            continue
        
        plan = playbook.get_recovery_plan(error_type)
        
        print(f"\n{error_type.value}:")
        for i, step in enumerate(plan, 1):
            print(f"  {i}. {step['action'].value}: {step['description']}")
    
    print("\n✅ Test completed")

