#!/usr/bin/env python3
"""
ManaOS Computer Use System - Action Executor
アクション実行エンジン
"""

import time
from typing import Dict, Any
import sys
from pathlib import Path

# X280 GUI Controllerをインポート
sys.path.append(str(Path("/root/x280_gui_automation")))
from x280_gui_client import X280GUIController

from .manaos_computer_use_types import Action, ActionType


class ActionExecutor:
    """アクション実行エンジン"""
    
    def __init__(self, x280_host: str = "100.127.121.20", x280_port: int = 5009):
        """
        Args:
            x280_host: X280のIPアドレス
            x280_port: X280 GUI APIのポート
        """
        self.x280 = X280GUIController(host=x280_host, port=x280_port)
        
        # 接続確認
        health = self.x280.health_check()
        if not health:
            raise ConnectionError("X280 GUI APIに接続できません")
        
        print(f"✅ X280接続成功: {health.get('screen_size')}")
    
    def execute(self, action: Action) -> Dict[str, Any]:
        """
        アクションを実行
        
        Args:
            action: 実行するアクション
        
        Returns:
            Dict: 実行結果
        """
        action_type = action.action_type
        params = action.parameters
        
        try:
            if action_type == ActionType.CLICK:
                return self._execute_click(params)
            
            elif action_type == ActionType.DOUBLE_CLICK:
                return self._execute_double_click(params)
            
            elif action_type == ActionType.RIGHT_CLICK:
                return self._execute_right_click(params)
            
            elif action_type == ActionType.TYPE_TEXT:
                return self._execute_type(params)
            
            elif action_type == ActionType.PRESS_KEY:
                return self._execute_press_key(params)
            
            elif action_type == ActionType.HOTKEY:
                return self._execute_hotkey(params)
            
            elif action_type == ActionType.SCROLL:
                return self._execute_scroll(params)
            
            elif action_type == ActionType.DRAG:
                return self._execute_drag(params)
            
            elif action_type == ActionType.WAIT:
                return self._execute_wait(params)
            
            elif action_type == ActionType.SCREENSHOT:
                return self._execute_screenshot(params)
            
            elif action_type == ActionType.COMPLETE:
                return {"success": True, "message": "タスク完了"}
            
            else:
                return {
                    "success": False,
                    "error": f"未対応のアクション: {action_type}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"実行エラー: {str(e)}"
            }
    
    def _execute_click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """クリック実行"""
        x = params.get("x")
        y = params.get("y")
        
        if x is None or y is None:
            return {"success": False, "error": "座標が指定されていません"}
        
        result = self.x280.mouse_click(x=int(x), y=int(y))
        time.sleep(0.5)  # クリック後の待機
        return result
    
    def _execute_double_click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """ダブルクリック実行"""
        x = params.get("x")
        y = params.get("y")
        
        if x is None or y is None:
            return {"success": False, "error": "座標が指定されていません"}
        
        result = self.x280.double_click(x=int(x), y=int(y))
        time.sleep(0.5)
        return result
    
    def _execute_right_click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """右クリック実行"""
        x = params.get("x")
        y = params.get("y")
        
        if x is None or y is None:
            return {"success": False, "error": "座標が指定されていません"}
        
        result = self.x280.right_click(x=int(x), y=int(y))
        time.sleep(0.5)
        return result
    
    def _execute_type(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """テキスト入力実行"""
        text = params.get("text")
        interval = params.get("interval", 0.05)
        
        if not text:
            return {"success": False, "error": "テキストが指定されていません"}
        
        result = self.x280.type_text(text=text, interval=interval)
        time.sleep(0.3)
        return result
    
    def _execute_press_key(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """キー押下実行"""
        key = params.get("key")
        
        if not key:
            return {"success": False, "error": "キーが指定されていません"}
        
        result = self.x280.press_key(key=key)
        time.sleep(0.3)
        return result
    
    def _execute_hotkey(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """ホットキー実行"""
        keys = params.get("keys", [])
        
        if not keys:
            return {"success": False, "error": "キーが指定されていません"}
        
        result = self.x280.hotkey(*keys)
        time.sleep(0.5)
        return result
    
    def _execute_scroll(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """スクロール実行（PyAutoGUIのscroll相当）"""
        clicks = params.get("clicks", 3)
        x = params.get("x")
        y = params.get("y")
        
        # PyAutoGUIのscrollはクリック数（正=上、負=下）
        # 今回は簡易実装: PageUp/PageDownキーで代替
        direction = "up" if clicks > 0 else "down"
        key = "pageup" if direction == "up" else "pagedown"
        
        result = self.x280.press_key(key=key)
        time.sleep(0.5)
        return result
    
    def _execute_drag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """ドラッグ&ドロップ実行"""
        to_x = params.get("to_x")
        to_y = params.get("to_y")
        from_x = params.get("from_x")
        from_y = params.get("from_y")
        duration = params.get("duration", 0.5)
        
        if to_x is None or to_y is None:
            return {"success": False, "error": "終点座標が指定されていません"}
        
        result = self.x280.drag_to(
            to_x=int(to_x),
            to_y=int(to_y),
            from_x=int(from_x) if from_x is not None else None,
            from_y=int(from_y) if from_y is not None else None,
            duration=float(duration)
        )
        time.sleep(0.5)
        return result
    
    def _execute_wait(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """待機実行"""
        duration = params.get("duration", 2.0)
        time.sleep(float(duration))
        return {"success": True, "message": f"{duration}秒待機しました"}
    
    def _execute_screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """スクリーンショット取得"""
        region = params.get("region")
        result = self.x280.screenshot(region=region)
        
        if result.get("success"):
            # ダウンロード
            filename = result.get("filename")
            local_path = self.x280.download_screenshot(filename)
            result["local_path"] = local_path
        
        return result
    
    def take_screenshot_and_download(self) -> str:
        """
        スクリーンショットを撮影してダウンロード
        
        Returns:
            str: ダウンロードしたファイルのパス
        """
        result = self.x280.screenshot()
        if not result.get("success"):
            raise Exception(f"スクリーンショット失敗: {result}")
        
        filename = result.get("filename")
        local_path = self.x280.download_screenshot(filename)
        
        if not local_path:
            raise Exception("スクリーンショットのダウンロード失敗")
        
        return local_path


# ===== テスト用 =====

if __name__ == "__main__":
    print("🎮 Action Executor テスト")
    print("=" * 60)
    
    executor = ActionExecutor()
    
    # テスト1: スクリーンショット
    print("\n📸 Test 1: スクリーンショット")
    screenshot_path = executor.take_screenshot_and_download()
    print(f"✅ スクリーンショット保存: {screenshot_path}")
    
    # テスト2: マウス移動してクリック
    print("\n🖱️ Test 2: マウスクリック（画面中央）")
    screen_info = executor.x280.screen_info()
    if screen_info.get("success"):
        center_x = screen_info["screen_width"] // 2
        center_y = screen_info["screen_height"] // 2
        
        action = Action(
            action_type=ActionType.CLICK,
            parameters={"x": center_x, "y": center_y}
        )
        result = executor.execute(action)
        print(f"結果: {result}")
    
    # テスト3: 待機
    print("\n⏳ Test 3: 2秒待機")
    action = Action(
        action_type=ActionType.WAIT,
        parameters={"duration": 2}
    )
    result = executor.execute(action)
    print(f"結果: {result}")
    
    print("\n✅ テスト完了")

