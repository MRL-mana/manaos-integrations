#!/usr/bin/env python3
"""
ManaOS Computer Use System - Main Orchestrator
メインの制御システム
"""

import time
import json
from datetime import datetime
from typing import Optional
from pathlib import Path

from .manaos_computer_use_types import (
    ExecutionStep, TaskResult, TaskStatus, ActionType,
    DEFAULT_MAX_STEPS, DEFAULT_STEP_DELAY,
    DEFAULT_SCREENSHOT_DIR, DEFAULT_LOGS_DIR
)
from .manaos_computer_use_vision import VisionEngine
from .manaos_computer_use_executor import ActionExecutor
from .action_budget import BudgetTracker
from .dynamic_budget import DynamicBudgetAdjuster
from .recovery_playbook import RecoveryPlaybook, ErrorType
from .replay_system import ReplaySystem


class ComputerUseOrchestrator:
    """Computer Use メインオーケストレーター"""
    
    def __init__(
        self,
        vision_provider: str = "claude",
        x280_host: str = "100.127.121.20",
        x280_port: int = 5009,
        screenshots_dir: Optional[Path] = None,
        logs_dir: Optional[Path] = None
    ):
        """
        Args:
            vision_provider: "claude" または "openai"
            x280_host: X280のIPアドレス
            x280_port: X280 GUI APIのポート
            screenshots_dir: スクリーンショット保存ディレクトリ
            logs_dir: ログ保存ディレクトリ
        """
        self.vision = VisionEngine(provider=vision_provider, use_hybrid=True)
        self.executor = ActionExecutor(x280_host=x280_host, x280_port=x280_port)
        
        # ディレクトリ設定
        self.screenshots_dir = screenshots_dir or DEFAULT_SCREENSHOT_DIR
        self.logs_dir = logs_dir or DEFAULT_LOGS_DIR
        
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        print("✅ ManaOS Computer Use Orchestrator 初期化完了")
        print(f"   Vision Engine: {vision_provider} (Hybrid Vision enabled)")
        print(f"   X280: {x280_host}:{x280_port}")
    
    def execute_task(
        self,
        task: str,
        max_steps: int = None,  # type: ignore
        step_delay: float = DEFAULT_STEP_DELAY,
        max_cost: float = None,  # type: ignore
        max_time: float = None,  # type: ignore
        auto_adjust_budget: bool = True,
        enable_recovery: bool = True,
        enable_replay: bool = True,
        seed: Optional[int] = None
    ) -> TaskResult:
        """
        タスクを自律的に実行
        
        Args:
            task: 実行するタスク（自然言語）
            max_steps: 最大ステップ数（Noneの場合は自動調整）
            step_delay: ステップ間の待機時間（秒）
            max_cost: 最大コスト（ドル、Noneの場合は自動調整）
            max_time: 最大時間（秒、Noneの場合は自動調整）
            auto_adjust_budget: 動的予算調整を有効化
            enable_recovery: エラー自動回復を有効化
            enable_replay: リプレイ記録を有効化
            seed: ランダムシード（再現性用）
        
        Returns:
            TaskResult: 実行結果
        """
        print("\n" + "=" * 60)
        print(f"🚀 タスク実行開始: {task}")
        print("=" * 60)
        
        # シード設定（再現性確保）
        if seed is not None and enable_replay:
            replay_system = ReplaySystem()
            replay_system.set_seed(seed)
            print(f"🎲 Seed set: {seed}")
        else:
            replay_system = ReplaySystem() if enable_replay else None
        
        # 動的予算調整
        if auto_adjust_budget and (max_steps is None or max_cost is None or max_time is None):
            adjuster = DynamicBudgetAdjuster()
            auto_budget = adjuster.adjust_budget(task)
            
            max_steps = max_steps or auto_budget.get("max_steps", DEFAULT_MAX_STEPS)
            max_cost = max_cost or auto_budget.get("max_cost", 1.0)
            max_time = max_time or auto_budget.get("max_time", 300.0)
            
            print(f"💰 Auto-adjusted budget: {max_steps} steps, ${max_cost:.2f}, {max_time:.0f}s")
        else:
            max_steps = max_steps or DEFAULT_MAX_STEPS
            max_cost = max_cost or 1.0
            max_time = max_time or 300.0
        
        # 行動予算トラッカー
        budget_tracker = BudgetTracker(
            max_steps=max_steps,
            max_cost=max_cost,
            max_time=max_time
        )
        
        # リカバリプレイブック
        recovery_playbook = RecoveryPlaybook() if enable_recovery else None
        
        # タスク結果オブジェクト初期化
        result = TaskResult(
            task=task,
            status=TaskStatus.RUNNING,
            steps=[],
            start_time=datetime.now()
        )
        
        try:
            for step_number in range(1, max_steps + 1):
                print(f"\n📍 Step {step_number}/{max_steps}")
                print("-" * 60)
                
                # ステップ実行
                step = self._execute_step(
                    step_number=step_number,
                    task=task,
                    history=result.steps
                )
                
                result.steps.append(step)
                
                # 予算消費
                if step.action_taken:
                    if not budget_tracker.consume(step.action_taken.action_type):
                        print("\n⚠️ 予算を使い切りました")
                        budget_status = budget_tracker.get_status()
                        print(f"   Steps: {budget_status['current']['steps']}/{max_steps}")
                        print(f"   Cost: ${budget_status['current']['cost']:.4f}/${max_cost}")
                        print(f"   Time: {budget_status['current']['time']:.1f}s/{max_time}s")
                        result.status = TaskStatus.TIMEOUT
                        result.error_message = "予算切れ"
                        break
                    
                    # 予算警告
                    budget_tracker.warn_if_low(threshold=0.8)
                
                # 完了判定
                if step.ai_analysis and step.ai_analysis.is_complete:
                    print(f"\n✅ タスク完了！（Step {step_number}）")
                    result.status = TaskStatus.SUCCESS
                    break
                
                # completeアクション判定
                if step.action_taken and step.action_taken.action_type == ActionType.COMPLETE:
                    print(f"\n✅ タスク完了！（Step {step_number}）")
                    result.status = TaskStatus.SUCCESS
                    break
                
                # エラー判定 & 自動リカバリ
                if not step.success:
                    print(f"\n⚠️ Step {step_number}で失敗")
                    
                    # エラー自動回復を試行
                    if recovery_playbook and step.error:
                        print("🔧 エラー自動回復を試行中...")
                        error_type = self._classify_error(step.error)
                        
                        if recovery_playbook.execute_recovery(error_type, self.executor, max_attempts=3):
                            print("✅ リカバリ成功！ステップを再試行します")
                            
                            # ステップを再実行
                            step = self._execute_step(
                                step_number=step_number,
                                task=task,
                                history=result.steps
                            )
                            result.steps[-1] = step  # 最後のステップを更新
                        else:
                            print("❌ リカバリ失敗。続行します...")
                
                # 待機
                print(f"⏳ {step_delay}秒待機...")
                time.sleep(step_delay)
            
            # タイムアウト判定
            if result.status == TaskStatus.RUNNING:
                print(f"\n⏱️ タイムアウト（{max_steps}ステップ達成）")
                result.status = TaskStatus.TIMEOUT
        
        except KeyboardInterrupt:
            print("\n\n⚠️ ユーザーによる中断")
            result.status = TaskStatus.FAILED
            result.error_message = "ユーザーによる中断"
        
        except Exception as e:
            print(f"\n\n❌ エラー発生: {e}")
            result.status = TaskStatus.FAILED
            result.error_message = str(e)
        
        finally:
            # 完了処理
            result.end_time = datetime.now()
            result.total_steps = len(result.steps)
            
            # 成功率計算
            success_count = sum(1 for step in result.steps if step.success)
            result.success_rate = success_count / len(result.steps) if result.steps else 0.0
            
            # 予算情報を結果に追加
            if 'budget_tracker' in locals():
                result.budget_status = budget_tracker.get_status()  # type: ignore
            
            # リプレイ記録
            if replay_system and enable_replay:
                replay = replay_system.record_execution(result, seed=seed)
                print(f"💾 Replay saved: {replay.execution_id}")
            
            # ログ保存
            self._save_execution_log(result)
            
            # サマリー表示
            self._print_summary(result)
        
        return result
    
    def _execute_step(
        self,
        step_number: int,
        task: str,
        history: list
    ) -> ExecutionStep:
        """
        1ステップ実行
        
        Args:
            step_number: ステップ番号
            task: タスク
            history: 実行履歴
        
        Returns:
            ExecutionStep: ステップ実行結果
        """
        step = ExecutionStep(
            step_number=step_number,
            timestamp=datetime.now(),
            screenshot_path=None,
            ai_analysis=None,
            action_taken=None,
            success=False
        )
        
        try:
            # 1. スクリーンショット取得
            print("📸 スクリーンショット取得中...")
            screenshot_path = self.executor.take_screenshot_and_download()
            step.screenshot_path = screenshot_path
            print(f"   保存: {screenshot_path}")
            
            # 2. AI分析
            print("🤖 AI分析中...")
            analysis = self.vision.analyze_screenshot(
                screenshot_path=screenshot_path,
                task=task,
                history=history
            )
            step.ai_analysis = analysis
            
            print(f"   状態: {analysis.current_state}")
            print(f"   アクション: {analysis.next_action.action_type.value}")
            print(f"   パラメータ: {analysis.next_action.parameters}")
            print(f"   理由: {analysis.reasoning}")
            print(f"   完了: {analysis.is_complete}")
            print(f"   確信度: {analysis.confidence:.2f}")
            
            # 3. アクション実行
            if not analysis.is_complete:
                print(f"⚡ アクション実行: {analysis.next_action.action_type.value}")
                action_result = self.executor.execute(analysis.next_action)
                step.action_taken = analysis.next_action
                step.action_result = action_result
                
                if action_result.get("success"):
                    print(f"   ✅ 成功: {action_result.get('message', '')}")
                    step.success = True
                else:
                    print(f"   ❌ 失敗: {action_result.get('error', '')}")
                    step.error = action_result.get("error")
            else:
                print("✅ タスク完了と判定")
                step.success = True
        
        except Exception as e:
            print(f"❌ ステップ実行エラー: {e}")
            step.error = str(e)
            step.success = False
        
        return step
    
    def _save_execution_log(self, result: TaskResult):
        """実行ログを保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"execution_{timestamp}.json"
        log_path = self.logs_dir / log_filename
        
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 実行ログ保存: {log_path}")
        except Exception as e:
            print(f"⚠️ ログ保存失敗: {e}")
    
    def _print_summary(self, result: TaskResult):
        """実行サマリーを表示"""
        print("\n" + "=" * 60)
        print("📊 実行サマリー")
        print("=" * 60)
        print(f"タスク: {result.task}")
        print(f"ステータス: {result.status.value}")
        print(f"総ステップ数: {result.total_steps}")
        print(f"成功率: {result.success_rate * 100:.1f}%")
        
        if result.end_time and result.start_time:
            duration = (result.end_time - result.start_time).total_seconds()
            print(f"実行時間: {duration:.1f}秒")
        
        if result.error_message:
            print(f"エラー: {result.error_message}")
        
        # 予算情報
        if hasattr(result, 'budget_status'):
            budget = result.budget_status  # type: ignore
            print("\n💰 予算消費:")
            print(f"   Steps: {budget['current']['steps']} ({budget['percentage_used']['steps']:.1f}%)")
            print(f"   Cost: ${budget['current']['cost']:.4f} ({budget['percentage_used']['cost']:.1f}%)")
            print(f"   Time: {budget['current']['time']:.1f}s ({budget['percentage_used']['time']:.1f}%)")
        
        print("=" * 60)
    
    def _classify_error(self, error_message: str) -> ErrorType:
        """
        エラーメッセージからエラータイプを分類
        
        Args:
            error_message: エラーメッセージ
        
        Returns:
            ErrorType: エラータイプ
        """
        import re
        
        error_lower = str(error_message).lower()
        
        # パターンマッチング
        if re.search(r"click.*fail|coordinate.*invalid", error_lower):
            return ErrorType.CLICK_FAILED
        elif re.search(r"element.*not found|no.*element", error_lower):
            return ErrorType.ELEMENT_NOT_FOUND
        elif re.search(r"window.*not.*active|focus", error_lower):
            return ErrorType.WINDOW_NOT_ACTIVE
        elif re.search(r"screenshot.*fail|capture.*fail", error_lower):
            return ErrorType.SCREENSHOT_FAILED
        elif re.search(r"timeout|timed out", error_lower):
            return ErrorType.TIMEOUT
        elif re.search(r"dialog|popup|unexpected", error_lower):
            return ErrorType.UNEXPECTED_DIALOG
        else:
            return ErrorType.UNKNOWN


# ===== メイン実行 =====

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python manaos_computer_use_orchestrator.py <task>")
        print("\n例:")
        print('  python manaos_computer_use_orchestrator.py "メモ帳を開いて Hello World と入力"')
        print('  python manaos_computer_use_orchestrator.py "ブラウザでGoogleを開く"')
        sys.exit(1)
    
    task = " ".join(sys.argv[1:])
    
    print("🚀 ManaOS Computer Use System")
    print("=" * 60)
    
    # オーケストレーター初期化
    orchestrator = ComputerUseOrchestrator(vision_provider="claude")
    
    # タスク実行
    result = orchestrator.execute_task(task=task, max_steps=20)
    
    # 終了
    if result.status == TaskStatus.SUCCESS:
        print("\n🎉 タスク成功！")
        sys.exit(0)
    else:
        print(f"\n😢 タスク失敗: {result.status.value}")
        sys.exit(1)

