#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💰 OH MY OPENCODE コスト管理モジュール
コスト上限・監視・警告システム
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler

logger = get_service_logger("oh-my-opencode-cost-manager")
error_handler = ManaOSErrorHandler("OHMyOpenCodeCostManager")


@dataclass
class CostRecord:
    """コスト記録"""
    task_id: str
    cost: float
    timestamp: str
    task_type: str
    mode: str


class OHMyOpenCodeCostManager:
    """OH MY OPENCODE コスト管理クラス"""
    
    def __init__(
        self,
        daily_limit: float = 100.0,
        monthly_limit: float = 2000.0,
        warning_threshold: float = 0.8,
        auto_stop: bool = True,
        storage_path: Optional[Path] = None
    ):
        """
        初期化
        
        Args:
            daily_limit: 日次コスト上限
            monthly_limit: 月次コスト上限
            warning_threshold: 警告閾値（0.0-1.0）
            auto_stop: 上限到達時に自動停止
            storage_path: ストレージパス
        """
        self.daily_limit = daily_limit
        self.monthly_limit = monthly_limit
        self.warning_threshold = warning_threshold
        self.auto_stop = auto_stop
        
        self.storage_path = storage_path or Path(__file__).parent / "oh_my_opencode_cost_history.json"
        self.cost_history: list[CostRecord] = []
        
        self._load_history()
    
    def _load_history(self):
        """コスト履歴を読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cost_history = [
                        CostRecord(**record) for record in data.get("records", [])
                    ]
                logger.info(f"コスト履歴を読み込みました: {len(self.cost_history)}件")
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"storage_path": str(self.storage_path)},
                    user_message="コスト履歴の読み込みに失敗しました"
                )
                logger.warning(f"コスト履歴読み込みエラー: {error.message}")
                self.cost_history = []
    
    def _save_history(self):
        """コスト履歴を保存"""
        try:
            data = {
                "records": [asdict(record) for record in self.cost_history],
                "last_updated": datetime.now().isoformat()
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"storage_path": str(self.storage_path)},
                user_message="コスト履歴の保存に失敗しました"
            )
            logger.error(f"コスト履歴保存エラー: {error.message}")
    
    def record_cost(
        self,
        task_id: str,
        cost: float,
        task_type: str = "general",
        mode: str = "normal"
    ):
        """
        コストを記録
        
        Args:
            task_id: タスクID
            cost: コスト
            task_type: タスクタイプ
            mode: 実行モード
        """
        record = CostRecord(
            task_id=task_id,
            cost=cost,
            timestamp=datetime.now().isoformat(),
            task_type=task_type,
            mode=mode
        )
        
        self.cost_history.append(record)
        self._save_history()
        
        logger.info(f"コストを記録しました: ${cost:.2f} (タスク: {task_id})")
    
    def get_daily_cost(self, date: Optional[datetime] = None) -> float:
        """
        日次コストを取得
        
        Args:
            date: 日付（Noneの場合は今日）
        
        Returns:
            日次コスト
        """
        if date is None:
            date = datetime.now()
        
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        daily_cost = sum(
            record.cost
            for record in self.cost_history
            if date_start <= datetime.fromisoformat(record.timestamp) < date_end
        )
        
        return daily_cost
    
    def get_monthly_cost(self, date: Optional[datetime] = None) -> float:
        """
        月次コストを取得
        
        Args:
            date: 日付（Noneの場合は今月）
        
        Returns:
            月次コスト
        """
        if date is None:
            date = datetime.now()
        
        month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if date.month == 12:
            month_end = date.replace(year=date.year + 1, month=1, day=1)
        else:
            month_end = date.replace(month=date.month + 1, day=1)
        
        monthly_cost = sum(
            record.cost
            for record in self.cost_history
            if month_start <= datetime.fromisoformat(record.timestamp) < month_end
        )
        
        return monthly_cost
    
    def check_limit(self, estimated_cost: float = 0.0) -> tuple[bool, Optional[str]]:
        """
        コスト上限をチェック
        
        Args:
            estimated_cost: 推定コスト
        
        Returns:
            (実行可能かどうか, 警告メッセージ)
        """
        daily_cost = self.get_daily_cost()
        monthly_cost = self.get_monthly_cost()
        
        # 日次上限チェック
        if daily_cost + estimated_cost > self.daily_limit:
            if self.auto_stop:
                return False, f"日次コスト上限に達しました（現在: ${daily_cost:.2f}, 上限: ${self.daily_limit:.2f}）"
            else:
                return True, f"警告: 日次コスト上限に近づいています（現在: ${daily_cost:.2f}, 上限: ${self.daily_limit:.2f}）"
        
        # 月次上限チェック
        if monthly_cost + estimated_cost > self.monthly_limit:
            if self.auto_stop:
                return False, f"月次コスト上限に達しました（現在: ${monthly_cost:.2f}, 上限: ${self.monthly_limit:.2f}）"
            else:
                return True, f"警告: 月次コスト上限に近づいています（現在: ${monthly_cost:.2f}, 上限: ${self.monthly_limit:.2f}）"
        
        # 警告閾値チェック
        daily_warning_threshold = self.daily_limit * self.warning_threshold
        monthly_warning_threshold = self.monthly_limit * self.warning_threshold
        
        warnings = []
        
        if daily_cost >= daily_warning_threshold:
            warnings.append(f"日次コスト警告: ${daily_cost:.2f} / ${self.daily_limit:.2f} ({daily_cost/self.daily_limit*100:.1f}%)")
        
        if monthly_cost >= monthly_warning_threshold:
            warnings.append(f"月次コスト警告: ${monthly_cost:.2f} / ${self.monthly_limit:.2f} ({monthly_cost/self.monthly_limit*100:.1f}%)")
        
        warning_message = " | ".join(warnings) if warnings else None
        
        return True, warning_message
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        統計情報を取得
        
        Returns:
            統計情報
        """
        daily_cost = self.get_daily_cost()
        monthly_cost = self.get_monthly_cost()
        
        # タスクタイプ別コスト
        task_type_costs: Dict[str, float] = {}
        for record in self.cost_history:
            task_type_costs[record.task_type] = task_type_costs.get(record.task_type, 0.0) + record.cost
        
        # モード別コスト
        mode_costs: Dict[str, float] = {}
        for record in self.cost_history:
            mode_costs[record.mode] = mode_costs.get(record.mode, 0.0) + record.cost
        
        return {
            "daily_cost": daily_cost,
            "daily_limit": self.daily_limit,
            "daily_usage_percent": (daily_cost / self.daily_limit * 100) if self.daily_limit > 0 else 0,
            "monthly_cost": monthly_cost,
            "monthly_limit": self.monthly_limit,
            "monthly_usage_percent": (monthly_cost / self.monthly_limit * 100) if self.monthly_limit > 0 else 0,
            "total_tasks": len(self.cost_history),
            "task_type_costs": task_type_costs,
            "mode_costs": mode_costs,
            "last_updated": datetime.now().isoformat()
        }
