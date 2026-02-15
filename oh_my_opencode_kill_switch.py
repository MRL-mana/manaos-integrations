#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛑 OH MY OPENCODE Kill Switch
緊急停止・実行時間制限・無限ループ検知システム
"""

import asyncio
import time
import hashlib
import os
import sys
import subprocess
import json
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque
from pathlib import Path

from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler

logger = get_service_logger("oh-my-opencode-kill-switch")
error_handler = ManaOSErrorHandler("OHMyOpenCodeKillSwitch")


class KillSwitchReason(str, Enum):
    """Kill Switch理由"""
    MANUAL = "manual"  # 手動停止
    TIME_LIMIT = "time_limit"  # 実行時間制限
    ITERATION_LIMIT = "iteration_limit"  # 反復回数制限
    INFINITE_LOOP = "infinite_loop"  # 無限ループ検知
    COST_LIMIT = "cost_limit"  # コスト上限
    ERROR_THRESHOLD = "error_threshold"  # エラー閾値


@dataclass
class KillSwitchStatus:
    """Kill Switch状態"""
    active: bool
    task_id: Optional[str] = None
    reason: Optional[str] = None
    triggered_at: Optional[str] = None
    execution_time: float = 0.0
    iterations: int = 0
    errors: int = 0
    # 停止時情報（運用の詰め）
    last_prompt: Optional[str] = None  # 直前のプロンプト（要点）
    last_error: Optional[str] = None  # 最後のエラー（スタックトレース先頭）
    resume_context_id: Optional[str] = None  # 再開用コンテキストID
    cost_at_kill: float = 0.0  # 停止時のコスト
    final_state: Optional[Dict[str, Any]] = None  # 最終状態（差分用）


@dataclass
class TaskMonitor:
    """タスク監視情報"""
    task_id: str
    start_time: datetime
    last_check_time: datetime
    iterations: int
    errors: List[str]
    error_patterns: deque  # エラーパターンの履歴
    cost: float
    status: str  # "running", "completed", "killed", "failed"
    # 停止時情報用
    last_prompt: Optional[str] = None  # 直前のプロンプト
    last_error: Optional[str] = None  # 最後のエラー
    resume_context_id: Optional[str] = None  # 再開用コンテキストID
    task_description: Optional[str] = None  # タスク説明（再開用）
    execution_context: Optional[Dict[str, Any]] = None  # 実行コンテキスト
    environment_fingerprint: Optional[str] = None  # 環境フィンガープリント（再開安全性用）
    downgrade_count: int = 0  # 降格回数（弱体化の連鎖防止用）


class OHMyOpenCodeKillSwitch:
    """OH MY OPENCODE Kill Switch"""
    
    def __init__(
        self,
        max_execution_time: int = 3600,  # 最大実行時間（秒）
        max_iterations: int = 20,  # 最大反復回数
        detect_infinite_loop: bool = True,  # 無限ループ検知
        error_threshold: int = 5,  # エラー閾値
        auto_kill_on_error: bool = False  # エラー時の自動停止
    ):
        """
        初期化
        
        Args:
            max_execution_time: 最大実行時間（秒）
            max_iterations: 最大反復回数
            detect_infinite_loop: 無限ループ検知を有効にするか
            error_threshold: エラー閾値
            auto_kill_on_error: エラー時の自動停止
        """
        self.max_execution_time = max_execution_time
        self.max_iterations = max_iterations
        self.detect_infinite_loop = detect_infinite_loop
        self.error_threshold = error_threshold
        self.auto_kill_on_error = auto_kill_on_error
        
        # アクティブなタスクの監視
        self.active_tasks: Dict[str, TaskMonitor] = {}
        
        # Kill Switch状態
        self.kill_switch_status: Dict[str, KillSwitchStatus] = {}
        
        # 無限ループ検知用のエラーパターン履歴
        self.error_pattern_history: Dict[str, deque] = {}
        
        logger.info("✅ Kill Switch initialized")
    
    def _generate_environment_fingerprint(self) -> str:
        """
        環境フィンガープリントを生成
        
        Returns:
            環境フィンガープリント（hash）
        """
        fingerprint_data = {
            "python_version": sys.version,
            "cwd": str(Path.cwd()),
            "env_keys": sorted([k for k in os.environ.keys() if k.startswith(("OH_MY_OPENCODE", "OPENAI", "ANTHROPIC"))]),
            "platform": sys.platform
        }
        
        # Gitブランチ情報（あれば）
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2.0
            )
            if result.returncode == 0:
                fingerprint_data["git_branch"] = result.stdout.strip()
        except Exception:
            pass
        
        # Hash生成
        fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
        fingerprint_hash = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]
        
        return fingerprint_hash
    
    def register_task(
        self,
        task_id: str,
        max_execution_time: Optional[int] = None,
        max_iterations: Optional[int] = None,
        task_description: Optional[str] = None,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> TaskMonitor:
        """
        タスクを登録
        
        Args:
            task_id: タスクID
            max_execution_time: 最大実行時間（Noneの場合はデフォルト値）
            max_iterations: 最大反復回数（Noneの場合はデフォルト値）
            task_description: タスク説明（再開用）
            execution_context: 実行コンテキスト（再開用）
        
        Returns:
            タスク監視情報
        """
        # 再開用コンテキストID生成
        resume_context_id = f"resume_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 環境フィンガープリント生成（再開安全性用）
        environment_fingerprint = self._generate_environment_fingerprint()
        
        monitor = TaskMonitor(
            task_id=task_id,
            start_time=datetime.now(),
            last_check_time=datetime.now(),
            iterations=0,
            errors=[],
            error_patterns=deque(maxlen=10),  # 直近10回のエラーパターン
            cost=0.0,
            status="running",
            task_description=task_description,
            execution_context=execution_context,
            resume_context_id=resume_context_id,
            environment_fingerprint=environment_fingerprint,
            downgrade_count=0
        )
        
        self.active_tasks[task_id] = monitor
        self.error_pattern_history[task_id] = deque(maxlen=10)
        
        logger.info(f"✅ タスクを登録しました: {task_id} (再開ID: {resume_context_id}, 環境FP: {environment_fingerprint})")
        
        return monitor
    
    def update_task(
        self,
        task_id: str,
        iteration: Optional[int] = None,
        error: Optional[str] = None,
        cost: Optional[float] = None,
        last_prompt: Optional[str] = None,
        execution_state: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        タスクの状態を更新
        
        Args:
            task_id: タスクID
            iteration: 反復回数（インクリメント）
            error: エラーメッセージ
            cost: コスト
            last_prompt: 直前のプロンプト（要点）
            execution_state: 実行状態（差分用）
        
        Returns:
            続行可能かどうか（Falseの場合は停止が必要）
        """
        if task_id not in self.active_tasks:
            logger.warning(f"タスクが見つかりません: {task_id}")
            return True
        
        monitor = self.active_tasks[task_id]
        monitor.last_check_time = datetime.now()
        
        # 反復回数の更新
        if iteration is not None:
            monitor.iterations = iteration
        
        # エラーの記録
        if error:
            monitor.errors.append(error)
            monitor.error_patterns.append(error[:100])  # エラーメッセージの最初の100文字
            self.error_pattern_history[task_id].append(error[:100])
            monitor.last_error = error[:500]  # 最後のエラー（スタックトレース先頭500文字）
        
        # コストの更新
        if cost is not None:
            monitor.cost = cost
        
        # 直前のプロンプトの更新（要点のみ、最大500文字）
        if last_prompt:
            monitor.last_prompt = last_prompt[:500] if len(last_prompt) > 500 else last_prompt
        
        # 実行状態の更新
        if execution_state:
            monitor.execution_context = execution_state
        
        # チェック: 実行時間制限
        execution_time = (datetime.now() - monitor.start_time).total_seconds()
        if execution_time > self.max_execution_time:
            self._kill_task(task_id, KillSwitchReason.TIME_LIMIT)
            return False
        
        # チェック: 反復回数制限
        if monitor.iterations >= self.max_iterations:
            self._kill_task(task_id, KillSwitchReason.ITERATION_LIMIT)
            return False
        
        # チェック: エラー閾値
        if len(monitor.errors) >= self.error_threshold:
            if self.auto_kill_on_error:
                self._kill_task(task_id, KillSwitchReason.ERROR_THRESHOLD)
                return False
        
        # チェック: 無限ループ検知
        if self.detect_infinite_loop:
            if self._detect_infinite_loop(task_id):
                self._kill_task(task_id, KillSwitchReason.INFINITE_LOOP)
                return False
        
        return True
    
    def kill_task(
        self,
        task_id: str,
        reason: KillSwitchReason = KillSwitchReason.MANUAL
    ) -> bool:
        """
        タスクを強制停止
        
        Args:
            task_id: タスクID
            reason: 停止理由
        
        Returns:
            停止成功かどうか
        """
        if task_id not in self.active_tasks:
            logger.warning(f"タスクが見つかりません: {task_id}")
            return False
        
        return self._kill_task(task_id, reason)
    
    def _kill_task(
        self,
        task_id: str,
        reason: KillSwitchReason
    ) -> bool:
        """
        タスクを停止（内部メソッド）
        
        Args:
            task_id: タスクID
            reason: 停止理由
        
        Returns:
            停止成功かどうか
        """
        monitor = self.active_tasks[task_id]
        execution_time = (datetime.now() - monitor.start_time).total_seconds()
        
        monitor.status = "killed"
        
        # 停止時情報を完全に記録
        kill_status = KillSwitchStatus(
            active=True,
            task_id=task_id,
            reason=reason.value,
            triggered_at=datetime.now().isoformat(),
            execution_time=execution_time,
            iterations=monitor.iterations,
            errors=len(monitor.errors),
            # 停止時情報（運用の詰め）
            last_prompt=monitor.last_prompt,
            last_error=monitor.last_error,
            resume_context_id=monitor.resume_context_id,
            cost_at_kill=monitor.cost,
            final_state={
                "task_description": monitor.task_description,
                "execution_context": monitor.execution_context,
                "error_history": list(monitor.error_patterns)[-5:] if monitor.error_patterns else []  # 直近5件
            }
        )
        
        self.kill_switch_status[task_id] = kill_status
        
        # 詳細なログ出力（運用の詰め）
        logger.warning(
            f"🛑 タスクを強制停止しました: {task_id}\n"
            f"  理由: {reason.value}\n"
            f"  実行時間: {execution_time:.2f}秒\n"
            f"  反復回数: {monitor.iterations}\n"
            f"  エラー数: {len(monitor.errors)}\n"
            f"  コスト: ${monitor.cost:.2f}\n"
            f"  再開ID: {monitor.resume_context_id}\n"
            f"  直前プロンプト: {monitor.last_prompt[:100] if monitor.last_prompt else 'N/A'}...\n"
            f"  最後のエラー: {monitor.last_error[:200] if monitor.last_error else 'N/A'}..."
        )
        
        return True
    
    def _detect_infinite_loop(self, task_id: str) -> bool:
        """
        無限ループを検知
        
        Args:
            task_id: タスクID
        
        Returns:
            無限ループが検知されたかどうか
        """
        if task_id not in self.error_pattern_history:
            return False
        
        error_history = self.error_pattern_history[task_id]
        
        # エラーパターンが3回以上繰り返されている場合
        if len(error_history) >= 3:
            # 直近3回のエラーが同じかチェック
            recent_errors = list(error_history)[-3:]
            if len(set(recent_errors)) == 1:  # すべて同じエラー
                logger.warning(f"無限ループを検知しました: {task_id} (エラー: {recent_errors[0]})")
                return True
        
        # エラーパターンが5回以上繰り返されている場合（より厳格）
        if len(error_history) >= 5:
            recent_errors = list(error_history)[-5:]
            if len(set(recent_errors)) <= 2:  # 2種類以下のエラーが繰り返されている
                logger.warning(f"無限ループを検知しました: {task_id} (エラーパターンが繰り返されています)")
                return True
        
        return False
    
    def get_task_status(self, task_id: str) -> Optional[KillSwitchStatus]:
        """
        タスクのKill Switch状態を取得
        
        Args:
            task_id: タスクID
        
        Returns:
            Kill Switch状態（Noneの場合はタスクが見つからない）
        """
        if task_id in self.kill_switch_status:
            return self.kill_switch_status[task_id]
        
        if task_id in self.active_tasks:
            monitor = self.active_tasks[task_id]
            execution_time = (datetime.now() - monitor.start_time).total_seconds()
            
            return KillSwitchStatus(
                active=False,
                task_id=task_id,
                execution_time=execution_time,
                iterations=monitor.iterations,
                errors=len(monitor.errors),
                last_prompt=monitor.last_prompt,
                last_error=monitor.last_error,
                resume_context_id=monitor.resume_context_id,
                cost_at_kill=monitor.cost
            )
        
        return None
    
    def get_resume_context(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        再開用コンテキストを取得
        
        Args:
            task_id: タスクID
        
        Returns:
            再開用コンテキスト（Noneの場合はタスクが見つからない）
        """
        if task_id not in self.active_tasks:
            return None
        
        monitor = self.active_tasks[task_id]
        kill_status = self.kill_switch_status.get(task_id)
        
        # 現在の環境フィンガープリントを取得
        current_fingerprint = self._generate_environment_fingerprint()
        fingerprint_match = monitor.environment_fingerprint == current_fingerprint
        
        return {
            "task_id": task_id,
            "resume_context_id": monitor.resume_context_id,
            "task_description": monitor.task_description,
            "execution_context": monitor.execution_context,
            "kill_reason": kill_status.reason if kill_status else None,
            "last_prompt": monitor.last_prompt,
            "last_error": monitor.last_error,
            "iterations": monitor.iterations,
            "cost": monitor.cost,
            "execution_time": (datetime.now() - monitor.start_time).total_seconds(),
            # 再開安全性チェック
            "environment_fingerprint": monitor.environment_fingerprint,
            "current_fingerprint": current_fingerprint,
            "fingerprint_match": fingerprint_match,
            "safe_to_resume": fingerprint_match,  # 環境が一致する場合のみ安全に再開可能
            "resume_safety_check": {
                "environment_changed": not fingerprint_match,
                "recommendation": "安全に再開可能" if fingerprint_match else "環境が変更されています。再開前に環境を確認してください。"
            }
        }
    
    def can_resume_safely(self, task_id: str) -> tuple[bool, str]:
        """
        安全に再開できるかチェック
        
        Args:
            task_id: タスクID
        
        Returns:
            (安全に再開可能かどうか, 理由)
        """
        resume_context = self.get_resume_context(task_id)
        if not resume_context:
            return False, "タスクが見つかりません"
        
        if resume_context.get("safe_to_resume", False):
            return True, "環境が一致しています。安全に再開可能です。"
        else:
            return False, resume_context.get("resume_safety_check", {}).get("recommendation", "環境が変更されています。")
    
    def is_task_killed(self, task_id: str) -> bool:
        """
        タスクが停止されているかチェック
        
        Args:
            task_id: タスクID
        
        Returns:
            停止されているかどうか
        """
        if task_id in self.kill_switch_status:
            return self.kill_switch_status[task_id].active
        
        return False
    
    def complete_task(self, task_id: str):
        """
        タスクを完了としてマーク
        
        Args:
            task_id: タスクID
        """
        if task_id in self.active_tasks:
            monitor = self.active_tasks[task_id]
            monitor.status = "completed"
            logger.info(f"✅ タスクを完了しました: {task_id}")
    
    def cleanup_task(self, task_id: str):
        """
        タスクのクリーンアップ
        
        Args:
            task_id: タスクID
        """
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
        
        if task_id in self.error_pattern_history:
            del self.error_pattern_history[task_id]
        
        logger.debug(f"タスクをクリーンアップしました: {task_id}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        統計情報を取得
        
        Returns:
            統計情報
        """
        active_count = sum(1 for m in self.active_tasks.values() if m.status == "running")
        killed_count = len(self.kill_switch_status)
        completed_count = sum(1 for m in self.active_tasks.values() if m.status == "completed")
        
        kill_reasons = {}
        for status in self.kill_switch_status.values():
            reason = status.reason or "unknown"
            kill_reasons[reason] = kill_reasons.get(reason, 0) + 1
        
        return {
            "active_tasks": active_count,
            "killed_tasks": killed_count,
            "completed_tasks": completed_count,
            "kill_reasons": kill_reasons,
            "max_execution_time": self.max_execution_time,
            "max_iterations": self.max_iterations,
            "detect_infinite_loop": self.detect_infinite_loop,
            "error_threshold": self.error_threshold
        }


# 使用例
if __name__ == "__main__":
    kill_switch = OHMyOpenCodeKillSwitch(
        max_execution_time=3600,
        max_iterations=20,
        detect_infinite_loop=True
    )
    
    # タスク登録
    task_id = "test_task_1"
    monitor = kill_switch.register_task(task_id)
    
    # タスク更新
    for i in range(5):
        can_continue = kill_switch.update_task(task_id, iteration=i + 1)
        if not can_continue:
            print(f"タスクが停止されました: {task_id}")
            break
    
    # 統計情報取得
    stats = kill_switch.get_statistics()
    print(f"統計情報: {stats}")
