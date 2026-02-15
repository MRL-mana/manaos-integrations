#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📋 OH MY OPENCODE 本番運用ルールセット（Policy）
デフォルトで安全運転にする運用ルール
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler

logger = get_service_logger("oh-my-opencode-policy")
error_handler = ManaOSErrorHandler("OHMyOpenCodePolicy")


class TimeSlot(Enum):
    """時間帯"""
    WEEKDAY = "weekday"  # 平日
    WEEKEND = "weekend"  # 週末
    MONTH_END = "month_end"  # 月末
    MONTH_START = "month_start"  # 月初


@dataclass
class PolicyRule:
    """運用ルール"""
    name: str
    description: str
    time_slot: TimeSlot
    allowed_modes: List[str]  # 許可されるモード
    max_cost_per_task: float  # タスクあたりの最大コスト
    max_daily_cost: float  # 日次最大コスト
    require_approval: bool  # 承認が必要か
    auto_downgrade_enabled: bool  # 自動降格が有効か
    kill_switch_strict: bool  # Kill Switchを厳格に


@dataclass
class PolicyConfig:
    """Policy設定"""
    rules: List[PolicyRule]
    default_rule: PolicyRule
    enabled: bool = True


class OHMyOpenCodePolicy:
    """OH MY OPENCODE 本番運用ルールセット"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            config: 設定（Noneの場合はデフォルト設定）
        """
        self.config = config or {}
        self.policy_config = self._load_default_policy()
        
        logger.info("✅ Policy initialized")
    
    def _load_default_policy(self) -> PolicyConfig:
        """
        デフォルトPolicyを読み込み
        
        Returns:
            Policy設定
        """
        # 平日ルール（安全運転）
        weekday_rule = PolicyRule(
            name="平日ルール（安全運転）",
            description="平日はNORMAL固定、Ultra Workは承認必須",
            time_slot=TimeSlot.WEEKDAY,
            allowed_modes=["normal"],
            max_cost_per_task=20.0,
            max_daily_cost=100.0,
            require_approval=True,  # Ultra Work使用時は承認必須
            auto_downgrade_enabled=True,
            kill_switch_strict=True
        )
        
        # 週末ルール（やや緩和）
        weekend_rule = PolicyRule(
            name="週末ルール（やや緩和）",
            description="週末はUltra Workも許可（ただし上限あり）",
            time_slot=TimeSlot.WEEKEND,
            allowed_modes=["normal", "ultra_work"],
            max_cost_per_task=50.0,
            max_daily_cost=200.0,
            require_approval=False,  # 週末は承認不要
            auto_downgrade_enabled=True,
            kill_switch_strict=True
        )
        
        # 月末ルール（厳格化）
        month_end_rule = PolicyRule(
            name="月末ルール（厳格化）",
            description="月末はコスト厳格化、Ultra Work禁止",
            time_slot=TimeSlot.MONTH_END,
            allowed_modes=["normal"],
            max_cost_per_task=10.0,
            max_daily_cost=50.0,
            require_approval=True,
            auto_downgrade_enabled=True,
            kill_switch_strict=True
        )
        
        # 月初ルール（通常）
        month_start_rule = PolicyRule(
            name="月初ルール（通常）",
            description="月初は通常運用",
            time_slot=TimeSlot.MONTH_START,
            allowed_modes=["normal", "ultra_work"],
            max_cost_per_task=30.0,
            max_daily_cost=150.0,
            require_approval=False,
            auto_downgrade_enabled=True,
            kill_switch_strict=True
        )
        
        # デフォルトルール（平日と同じ）
        default_rule = weekday_rule
        
        return PolicyConfig(
            rules=[weekday_rule, weekend_rule, month_end_rule, month_start_rule],
            default_rule=default_rule,
            enabled=True
        )
    
    def get_current_rule(self) -> PolicyRule:
        """
        現在の時間帯に適用されるルールを取得
        
        Returns:
            適用されるルール
        """
        if not self.policy_config.enabled:
            return self.policy_config.default_rule
        
        now = datetime.now()
        time_slot = self._get_time_slot(now)
        
        # 該当するルールを検索
        for rule in self.policy_config.rules:
            if rule.time_slot == time_slot:
                return rule
        
        # 該当するルールがない場合はデフォルト
        return self.policy_config.default_rule
    
    def _get_time_slot(self, dt: datetime) -> TimeSlot:
        """
        時間帯を取得
        
        Args:
            dt: 日時
        
        Returns:
            時間帯
        """
        # 週末判定（土曜日=5、日曜日=6）
        if dt.weekday() >= 5:
            return TimeSlot.WEEKEND
        
        # 月末判定（月末3日間）
        if dt.day >= 28:  # 簡易判定
            return TimeSlot.MONTH_END
        
        # 月初判定（月初3日間）
        if dt.day <= 3:
            return TimeSlot.MONTH_START
        
        # 平日
        return TimeSlot.WEEKDAY
    
    def can_use_mode(self, mode: str) -> tuple[bool, str]:
        """
        モードを使用できるかチェック
        
        Args:
            mode: モード名
        
        Returns:
            (使用可能かどうか, 理由)
        """
        rule = self.get_current_rule()
        
        if mode not in rule.allowed_modes:
            return False, f"{rule.name}: {mode}モードは許可されていません（許可モード: {', '.join(rule.allowed_modes)}）"
        
        return True, f"{rule.name}: {mode}モードは使用可能です"
    
    def requires_approval(self, mode: str) -> bool:
        """
        承認が必要かチェック
        
        Args:
            mode: モード名
        
        Returns:
            承認が必要かどうか
        """
        rule = self.get_current_rule()
        
        # Ultra Workは常に承認が必要（週末を除く）
        if mode == "ultra_work" and rule.require_approval:
            return True
        
        return False
    
    def get_max_cost_per_task(self) -> float:
        """
        タスクあたりの最大コストを取得
        
        Returns:
            最大コスト
        """
        rule = self.get_current_rule()
        return rule.max_cost_per_task
    
    def get_max_daily_cost(self) -> float:
        """
        日次最大コストを取得
        
        Returns:
            最大コスト
        """
        rule = self.get_current_rule()
        return rule.max_daily_cost
    
    def is_auto_downgrade_enabled(self) -> bool:
        """
        自動降格が有効かチェック
        
        Returns:
            自動降格が有効かどうか
        """
        rule = self.get_current_rule()
        return rule.auto_downgrade_enabled
    
    def is_kill_switch_strict(self) -> bool:
        """
        Kill Switchが厳格かチェック
        
        Returns:
            Kill Switchが厳格かどうか
        """
        rule = self.get_current_rule()
        return rule.kill_switch_strict
    
    def get_policy_summary(self) -> Dict[str, Any]:
        """
        Policyサマリーを取得
        
        Returns:
            Policyサマリー
        """
        rule = self.get_current_rule()
        time_slot = self._get_time_slot(datetime.now())
        
        return {
            "enabled": self.policy_config.enabled,
            "current_time_slot": time_slot.value,
            "current_rule": {
                "name": rule.name,
                "description": rule.description,
                "allowed_modes": rule.allowed_modes,
                "max_cost_per_task": rule.max_cost_per_task,
                "max_daily_cost": rule.max_daily_cost,
                "require_approval": rule.require_approval,
                "auto_downgrade_enabled": rule.auto_downgrade_enabled,
                "kill_switch_strict": rule.kill_switch_strict
            },
            "all_rules": [asdict(r) for r in self.policy_config.rules],
            "timestamp": datetime.now().isoformat()
        }


# 使用例
if __name__ == "__main__":
    policy = OHMyOpenCodePolicy()
    
    # 現在のルールを取得
    rule = policy.get_current_rule()
    print(f"現在のルール: {rule.name}")
    print(f"許可モード: {rule.allowed_modes}")
    print(f"最大コスト/タスク: ${rule.max_cost_per_task}")
    
    # モード使用可否チェック
    can_use, reason = policy.can_use_mode("ultra_work")
    print(f"Ultra Work使用可否: {can_use} ({reason})")
    
    # Policyサマリー
    summary = policy.get_policy_summary()
    print(f"\nPolicyサマリー: {summary}")
