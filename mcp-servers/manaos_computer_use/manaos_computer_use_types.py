#!/usr/bin/env python3
"""
ManaOS Computer Use System - Type Definitions
データ型と定数の定義
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path


class ActionType(Enum):
    """実行可能なアクションタイプ"""
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE_TEXT = "type"
    PRESS_KEY = "press"
    HOTKEY = "hotkey"
    SCROLL = "scroll"
    DRAG = "drag"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    COMPLETE = "complete"


class TaskStatus(Enum):
    """タスクの状態"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class Action:
    """実行するアクション"""
    action_type: ActionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "parameters": self.parameters,
            "reasoning": self.reasoning
        }


@dataclass
class AIAnalysis:
    """AIによる画像分析結果"""
    current_state: str
    next_action: Action
    is_complete: bool
    confidence: float = 0.0
    reasoning: str = ""
    raw_response: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_state": self.current_state,
            "next_action": self.next_action.to_dict(),
            "is_complete": self.is_complete,
            "confidence": self.confidence,
            "reasoning": self.reasoning
        }


@dataclass
class ExecutionStep:
    """実行ステップの記録"""
    step_number: int
    timestamp: datetime
    screenshot_path: Optional[str]
    ai_analysis: Optional[AIAnalysis]
    action_taken: Optional[Action]
    action_result: Dict[str, Any] = field(default_factory=dict)
    success: bool = False
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "timestamp": self.timestamp.isoformat(),
            "screenshot_path": self.screenshot_path,
            "ai_analysis": self.ai_analysis.to_dict() if self.ai_analysis else None,
            "action_taken": self.action_taken.to_dict() if self.action_taken else None,
            "action_result": self.action_result,
            "success": self.success,
            "error": self.error
        }


@dataclass
class TaskResult:
    """タスク実行結果"""
    task: str
    status: TaskStatus
    steps: List[ExecutionStep]
    start_time: datetime
    end_time: Optional[datetime] = None
    total_steps: int = 0
    success_rate: float = 0.0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "status": self.status.value,
            "total_steps": self.total_steps,
            "success_rate": self.success_rate,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time else None,
            "error_message": self.error_message,
            "steps": [step.to_dict() for step in self.steps]
        }


# 定数
DEFAULT_MAX_STEPS = 50
DEFAULT_STEP_DELAY = 2.0  # 秒
DEFAULT_SCREENSHOT_DIR = Path("/root/manaos_computer_use/screenshots")
DEFAULT_LOGS_DIR = Path("/root/manaos_computer_use/logs")
DEFAULT_CONTEXT_WINDOW = 5  # 直近N個のステップをコンテキストに含める

# 優先認識語彙（UI要素）
PRIORITY_UI_VOCABULARY = {
    "actions": [
        "保存", "Save", "開く", "Open", "閉じる", "Close",
        "検索", "Search", "次へ", "Next", "戻る", "Back",
        "OK", "キャンセル", "Cancel", "適用", "Apply",
        "削除", "Delete", "編集", "Edit", "追加", "Add",
        "コピー", "Copy", "貼り付け", "Paste", "切り取り", "Cut",
        "実行", "Run", "停止", "Stop", "更新", "Refresh"
    ],
    "dialogs": [
        "名前を付けて保存", "Save As", "ファイルを開く", "Open File",
        "確認", "Confirm", "警告", "Warning", "エラー", "Error",
        "ダイアログ", "Dialog", "ポップアップ", "Popup"
    ],
    "controls": [
        "ボタン", "Button", "テキストボックス", "Text Box",
        "チェックボックス", "Checkbox", "ラジオボタン", "Radio",
        "ドロップダウン", "Dropdown", "タブ", "Tab",
        "メニュー", "Menu", "ツールバー", "Toolbar"
    ]
}

# AI Vision プロンプトテンプレート（語彙拡張版）
VISION_PROMPT_TEMPLATE = """あなたはコンピューター操作AIです。
スクリーンショットを分析して、次のアクションを決定してください。

【現在のタスク】
{task}

【これまでの操作】
{history}

【優先認識語彙】
以下のUI要素を優先的に認識してください：
• アクション: 保存/Save、開く/Open、検索/Search、OK、キャンセル/Cancel、次へ/Next、戻る/Back
• ダイアログ: 名前を付けて保存、ファイルを開く、確認、警告、エラー
• コントロール: ボタン、テキストボックス、チェックボックス、ドロップダウン、メニュー

【判断してください】
1. 現在の画面状態（上記の語彙を使って説明）
2. 次に行うべき操作
3. 操作パラメータ（座標、テキストなど）
4. タスクが完了したか？

必ずJSON形式で回答してください：
{{
  "current_state": "画面の状態説明（優先語彙を使用）",
  "next_action": "click" | "double_click" | "right_click" | "type" | "press" | "hotkey" | "scroll" | "drag" | "wait" | "complete",
  "parameters": {{
    "x": 100,
    "y": 200,
    "to_x": 300,
    "to_y": 400,
    "text": "入力テキスト",
    "key": "enter",
    "keys": ["ctrl", "s"],
    "duration": 0.5
  }},
  "reasoning": "判断理由（優先語彙に基づく）",
  "is_complete": false,
  "confidence": 0.85
}}

注意事項：
- 座標は画面上の実際のピクセル位置を指定
- 「保存」ボタン等の優先語彙が見つかったら、それを中心に操作を組み立てる
- dragアクションはドラッグ&ドロップ用（from_x/from_y → to_x/to_y）
- is_completeはタスクが完全に終了した場合のみtrue
- confidenceは0.0-1.0で判断の確信度を示す
- 不明な場合はwaitアクションで様子を見る
- 優先語彙に該当するUI要素は高い確信度で判断すること
"""


