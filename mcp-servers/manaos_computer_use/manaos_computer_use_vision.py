#!/usr/bin/env python3
"""
ManaOS Computer Use System - Vision & Decision Engine
画像認識と意思決定エンジン
"""

import json
import re
import base64
from typing import List, Optional
from anthropic import Anthropic
from openai import OpenAI

from .manaos_computer_use_types import (
    Action, ActionType, AIAnalysis, ExecutionStep,
    VISION_PROMPT_TEMPLATE, PRIORITY_UI_VOCABULARY
)
from .vision_hybrid import VisionHybrid


class VisionEngine:
    """画像認識と意思決定エンジン"""
    
    def __init__(self, provider: str = "claude", api_key: Optional[str] = None, use_hybrid: bool = True):
        """
        Args:
            provider: "claude" または "openai"
            api_key: APIキー（Noneの場合は環境変数から取得）
            use_hybrid: ハイブリッドビジョン（OCR+テンプレート）を使用
        """
        self.provider = provider
        self.use_hybrid = use_hybrid
        
        if provider == "claude":
            self.client = Anthropic(api_key=api_key)
            self.model = "claude-sonnet-4-20250514"
        elif provider == "openai":
            self.client = OpenAI(api_key=api_key)
            self.model = "gpt-4o"
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        # ハイブリッドビジョン
        if use_hybrid:
            try:
                self.vision_hybrid = VisionHybrid()
                print("✅ Hybrid vision enabled (OCR + Template Matching)")
            except Exception as e:
                print(f"⚠️ Hybrid vision disabled: {e}")
                self.vision_hybrid = None
        else:
            self.vision_hybrid = None
    
    def analyze_screenshot(
        self,
        screenshot_path: str,
        task: str,
        history: List[ExecutionStep]
    ) -> AIAnalysis:
        """
        スクリーンショットを分析して次のアクションを決定
        
        Args:
            screenshot_path: スクリーンショットのパス
            task: 実行するタスク
            history: 実行履歴
        
        Returns:
            AIAnalysis: 分析結果
        """
        # 履歴を文字列化
        history_str = self._format_history(history)
        
        # プロンプト生成
        prompt = VISION_PROMPT_TEMPLATE.format(
            task=task,
            history=history_str
        )
        
        # 画像をBase64エンコード
        image_data = self._encode_image(screenshot_path)
        
        # AI呼び出し
        if self.provider == "claude":
            response = self._call_claude(prompt, image_data)
        else:
            response = self._call_openai(prompt, image_data)
        
        # レスポンスをパース
        analysis = self._parse_response(response)
        
        # ハイブリッドビジョンで座標精度を改善
        if self.vision_hybrid and analysis.next_action.action_type in [
            ActionType.CLICK, ActionType.DOUBLE_CLICK, ActionType.RIGHT_CLICK
        ]:
            analysis = self._refine_coordinates(screenshot_path, analysis)
        
        return analysis
    
    def _refine_coordinates(
        self,
        screenshot_path: str,
        analysis: AIAnalysis
    ) -> AIAnalysis:
        """
        ハイブリッドビジョンで座標を精緻化
        
        Args:
            screenshot_path: スクリーンショット
            analysis: AI分析結果
        
        Returns:
            AIAnalysis: 座標精緻化後
        """
        try:
            params = analysis.next_action.parameters
            
            # 優先語彙が推論に含まれているか確認
            reasoning = analysis.reasoning.lower()
            
            for actions in PRIORITY_UI_VOCABULARY.values():
                for keyword in actions:
                    if keyword.lower() in reasoning:
                        # テンプレートマッチを試行
                        result = self.vision_hybrid.find_element(  # type: ignore[union-attr]
                            screenshot_path,
                            keyword,
                            confidence_threshold=0.7
                        )
                        
                        if result:
                            # 座標を更新
                            params['x'] = result['x']
                            params['y'] = result['y']
                            
                            # 確信度ブースト
                            boost = self.vision_hybrid.get_confidence_boost(  # type: ignore[union-attr]
                                result.get('method', 'template'),
                                template_matched=True,
                                ocr_matched=False
                            )
                            analysis.confidence = min(1.0, analysis.confidence * boost)
                            
                            print(f"🎯 Coordinates refined by template matching: "
                                  f"({result['x']}, {result['y']}) [confidence: {result['confidence']:.3f}]")
                            break
        
        except Exception as e:
            # エラーは無視（元の座標を使用）
            print(f"⚠️ Coordinate refinement failed: {e}")
        
        return analysis
    
    def _encode_image(self, image_path: str) -> str:
        """画像をBase64エンコード"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _format_history(self, history: List[ExecutionStep]) -> str:
        """実行履歴を文字列化"""
        if not history:
            return "（まだ操作なし）"
        
        lines = []
        for step in history[-5:]:  # 直近5ステップのみ
            action_desc = "不明"
            if step.action_taken:
                action_type = step.action_taken.action_type.value
                params = step.action_taken.parameters
                action_desc = f"{action_type}: {params}"
            
            lines.append(f"Step {step.step_number}: {action_desc} → {'成功' if step.success else '失敗'}")
        
        return "\n".join(lines)
    
    def _call_claude(self, prompt: str, image_data: str) -> str:
        """Claude APIを呼び出し"""
        try:
            message = self.client.messages.create(  # type: ignore
                model=self.model,
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            return message.content[0].text  # type: ignore
        
        except Exception as e:
            print(f"❌ Claude API呼び出し失敗: {e}")
            # フォールバック: デフォルトのwaitアクション
            return json.dumps({
                "current_state": "AI分析失敗",
                "next_action": "wait",
                "parameters": {"duration": 2},
                "reasoning": f"API呼び出しエラー: {e}",
                "is_complete": False,
                "confidence": 0.0
            })
    
    def _call_openai(self, prompt: str, image_data: str) -> str:
        """OpenAI APIを呼び出し"""
        try:
            response = self.client.chat.completions.create(  # type: ignore
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2048
            )
            
            return response.choices[0].message.content  # type: ignore
        
        except Exception as e:
            print(f"❌ OpenAI API呼び出し失敗: {e}")
            # フォールバック
            return json.dumps({
                "current_state": "AI分析失敗",
                "next_action": "wait",
                "parameters": {"duration": 2},
                "reasoning": f"API呼び出しエラー: {e}",
                "is_complete": False,
                "confidence": 0.0
            })
    
    def _parse_response(self, response: str) -> AIAnalysis:
        """AIレスポンスをパースしてAIAnalysisに変換"""
        try:
            # JSONブロックを抽出（```json ... ``` または { ... }）
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 直接JSONを探す
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("JSONが見つかりません")
            
            data = json.loads(json_str)
            
            # ActionTypeの変換
            action_type_str = data.get("next_action", "wait")
            try:
                action_type = ActionType(action_type_str)
            except ValueError:
                action_type = ActionType.WAIT
            
            # Actionオブジェクト作成
            action = Action(
                action_type=action_type,
                parameters=data.get("parameters", {}),
                reasoning=data.get("reasoning", "")
            )
            
            # AIAnalysis作成
            analysis = AIAnalysis(
                current_state=data.get("current_state", "不明"),
                next_action=action,
                is_complete=data.get("is_complete", False),
                confidence=data.get("confidence", 0.5),
                reasoning=data.get("reasoning", ""),
                raw_response=response
            )
            
            return analysis
        
        except Exception as e:
            print(f"⚠️ レスポンスパース失敗: {e}")
            print(f"レスポンス内容:\n{response}")
            
            # フォールバック: waitアクション
            return AIAnalysis(
                current_state="パースエラー",
                next_action=Action(
                    action_type=ActionType.WAIT,
                    parameters={"duration": 2},
                    reasoning=f"レスポンスパースエラー: {e}"
                ),
                is_complete=False,
                confidence=0.0,
                reasoning=f"エラー: {e}",
                raw_response=response
            )


# ===== テスト用 =====

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python manaos_computer_use_vision.py <screenshot_path> <task>")
        sys.exit(1)
    
    screenshot_path = sys.argv[1]
    task = sys.argv[2]
    
    print("🔍 Vision Engine テスト")
    print("=" * 60)
    print(f"スクリーンショット: {screenshot_path}")
    print(f"タスク: {task}")
    print()
    
    # Claude使用（デフォルト）
    engine = VisionEngine(provider="claude")
    
    print("📸 画像分析中...")
    analysis = engine.analyze_screenshot(screenshot_path, task, [])
    
    print("\n✅ 分析結果:")
    print("-" * 60)
    print(f"現在の状態: {analysis.current_state}")
    print(f"次のアクション: {analysis.next_action.action_type.value}")
    print(f"パラメータ: {analysis.next_action.parameters}")
    print(f"理由: {analysis.reasoning}")
    print(f"完了: {analysis.is_complete}")
    print(f"確信度: {analysis.confidence}")
    print("-" * 60)

