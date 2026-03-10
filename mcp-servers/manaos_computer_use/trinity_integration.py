#!/usr/bin/env python3
"""
ManaOS Computer Use × Trinity 統合モジュール

Trinity Orchestrator v3から自然言語でComputer Useを呼び出せるようにする
"""

import sys
from pathlib import Path
from typing import Dict, Any

# パス追加
sys.path.insert(0, str(Path("/root")))

from manaos_computer_use import ComputerUseOrchestrator  # type: ignore[attr-defined]


class TrinityComputerUseIntegration:
    """
    Trinity × Computer Use 統合クラス
    
    使い方:
        integration = TrinityComputerUseIntegration()
        result = integration.process_natural_language_command(
            "X280でメモ帳を開いてHello Worldと入力して"
        )
    """
    
    # GUI操作関連のキーワード
    GUI_KEYWORDS = [
        "x280", "メモ帳", "notepad", "ブラウザ", "browser",
        "開いて", "クリック", "入力", "操作",
        "excel", "word", "アプリ", "ウィンドウ",
        "マウス", "キーボード", "画面"
    ]
    
    def __init__(self, vision_provider: str = "claude"):
        """
        Args:
            vision_provider: "claude" または "openai"
        """
        self.vision_provider = vision_provider
        self.orchestrator = None
    
    def is_gui_task(self, text: str) -> bool:
        """
        テキストがGUI操作タスクかどうか判定
        
        Args:
            text: 入力テキスト
        
        Returns:
            bool: GUI操作タスクならTrue
        """
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.GUI_KEYWORDS)
    
    def process_natural_language_command(
        self,
        command: str,
        max_steps: int = 20,
        step_delay: float = 2.0
    ) -> Dict[str, Any]:
        """
        自然言語コマンドを処理
        
        GUI操作タスクの場合はComputer Useで実行し、
        それ以外の場合は通常処理を促す
        
        Args:
            command: 自然言語のコマンド
            max_steps: 最大ステップ数
            step_delay: ステップ間隔（秒）
        
        Returns:
            Dict: 実行結果
        """
        # GUI操作タスクか判定
        if not self.is_gui_task(command):
            return {
                "handled": False,
                "reason": "GUI操作タスクではありません",
                "command": command
            }
        
        # Computer Use Orchestrator初期化（遅延）
        if self.orchestrator is None:
            try:
                self.orchestrator = ComputerUseOrchestrator(
                    vision_provider=self.vision_provider
                )
            except Exception as e:
                return {
                    "handled": False,
                    "success": False,
                    "error": f"Orchestrator初期化失敗: {e}"
                }
        
        # タスク実行
        try:
            result = self.orchestrator.execute_task(
                task=command,
                max_steps=max_steps,
                step_delay=step_delay
            )
            
            return {
                "handled": True,
                "success": result.status.value == "success",
                "status": result.status.value,
                "total_steps": result.total_steps,
                "success_rate": result.success_rate,
                "duration_seconds": (result.end_time - result.start_time).total_seconds() if result.end_time else 0,
                "error": result.error_message
            }
        
        except Exception as e:
            return {
                "handled": True,
                "success": False,
                "error": str(e)
            }


# ===== グローバルインスタンス（シングルトン） =====
_global_integration = None


def get_trinity_computer_use() -> TrinityComputerUseIntegration:
    """グローバルインスタンスを取得（シングルトン）"""
    global _global_integration
    if _global_integration is None:
        _global_integration = TrinityComputerUseIntegration()
    return _global_integration


def handle_trinity_command(command: str, **kwargs) -> Dict[str, Any]:
    """
    Trinityコマンドをハンドル（シンプルAPI）
    
    Args:
        command: 自然言語コマンド
        **kwargs: その他のパラメータ
    
    Returns:
        Dict: 実行結果
    """
    integration = get_trinity_computer_use()
    return integration.process_natural_language_command(command, **kwargs)


# ===== デモ =====

if __name__ == "__main__":
    print("🔗 Trinity × Computer Use 統合デモ")
    print("=" * 60)
    
    integration = TrinityComputerUseIntegration()
    
    # テストコマンド
    test_commands = [
        "今日の天気を教えて",  # GUI操作ではない
        "X280でメモ帳を開いて",  # GUI操作
        "ブラウザでGoogleを開く",  # GUI操作
        "Pythonのバージョンを確認",  # GUI操作ではない
    ]
    
    for command in test_commands:
        print(f"\n📝 コマンド: {command}")
        is_gui = integration.is_gui_task(command)
        print(f"   GUI操作タスク: {'✅ Yes' if is_gui else '❌ No'}")
    
    print("\n" + "=" * 60)
    print("統合準備完了！")
    print("=" * 60)


