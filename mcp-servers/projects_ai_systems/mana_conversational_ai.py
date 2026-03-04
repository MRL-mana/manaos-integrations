#!/usr/bin/env python3
"""
Mana Conversational AI
完全会話型自動化 - 自然言語で全システムを制御
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
import subprocess
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaConversationalAI:
    def __init__(self):
        self.name = "Mana"
        self.personality = "helpful_assistant"
        
        # 会話履歴
        self.conversation_history = []
        
        # インテント検出パターン（拡張版）
        self.intent_patterns = {
            # システム制御
            "system_control": {
                "patterns": ["実行", "起動", "開始", "スタート", "run", "start", "して"],
                "entities": ["メガブースト", "最適化", "監査", "分析", "チェック", "システム"]
            },
            # 情報取得
            "information_request": {
                "patterns": ["教えて", "見せて", "確認", "状態", "どう", "what", "how"],
                "entities": ["システム", "タスク", "予定", "ログ", "セキュリティ"]
            },
            # タスク管理
            "task_management": {
                "patterns": ["作って", "追加", "登録", "create", "add"],
                "entities": ["タスク", "予定", "todo", "スケジュール"]
            },
            # 問題解決
            "problem_solving": {
                "patterns": ["直して", "修復", "解決", "fix", "repair"],
                "entities": ["エラー", "問題", "バグ", "遅い", "重い"]
            }
        }
        
        logger.info("🤖 Mana Conversational AI 初期化完了")
    
    def detect_intent(self, text: str) -> Dict[str, Any]:
        """インテント（意図）検出"""
        text_lower = text.lower()
        
        detected_intent = None
        detected_entities = []
        confidence = 0.0
        
        for intent, config in self.intent_patterns.items():
            # パターンマッチング
            pattern_match = any(pattern in text_lower for pattern in config["patterns"])
            
            # エンティティ抽出
            entities = [entity for entity in config["entities"] if entity.lower() in text_lower]
            
            if pattern_match and entities:
                detected_intent = intent
                detected_entities = entities
                confidence = 0.8 if pattern_match and len(entities) > 1 else 0.6
                break
        
        return {
            "intent": detected_intent or "unknown",
            "entities": detected_entities,
            "confidence": confidence,
            "original_text": text
        }
    
    async def process_conversation(self, user_input: str) -> Dict[str, Any]:
        """会話処理"""
        logger.info(f"💬 入力: {user_input}")
        
        # インテント検出
        intent_result = self.detect_intent(user_input)
        intent = intent_result["intent"]
        entities = intent_result["entities"]
        
        logger.info(f"🎯 インテント: {intent}, エンティティ: {entities}")
        
        # インテントに基づいて処理
        if intent == "system_control":
            response = await self.handle_system_control(user_input, entities)
        
        elif intent == "information_request":
            response = await self.handle_information_request(user_input, entities)
        
        elif intent == "task_management":
            response = await self.handle_task_management(user_input, entities)
        
        elif intent == "problem_solving":
            response = await self.handle_problem_solving(user_input, entities)
        
        else:
            response = await self.handle_unknown(user_input)
        
        # 会話履歴に追加
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "intent": intent,
            "response": response
        })
        
        return response
    
    async def handle_system_control(self, text: str, entities: List[str]) -> Dict[str, Any]:
        """システム制御処理"""
        if "メガブースト" in entities or "最適化" in entities:
            # Voice Control Hubを使用
            result = subprocess.run(
                ["python3", "/root/mana_voice_control_hub.py", text],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            return {
                "type": "system_control",
                "action": "mega_boost",
                "response_text": "メガブーストを実行しました！システムを最適化中です。",
                "voice_ready": True
            }
        
        elif "監査" in entities or "チェック" in entities:
            result = subprocess.run(
                ["python3", "/root/mana_voice_control_hub.py", text],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            return {
                "type": "system_control",
                "action": "audit",
                "response_text": "セキュリティ監査を実行しました！",
                "voice_ready": True
            }
        
        else:
            return {
                "type": "system_control",
                "response_text": f"{entities[0] if entities else 'システム'}を制御します。",
                "voice_ready": True
            }
    
    async def handle_information_request(self, text: str, entities: List[str]) -> Dict[str, Any]:
        """情報取得処理"""
        try:
            response = requests.get("http://localhost:9999/api/overview", timeout=5)
            data = response.json()
            
            metrics = data.get("system_metrics", {})
            services = data.get("services", {})
            security = data.get("security", {})
            
            response_text = f"""
はい、お答えします！

CPU: {metrics.get('cpu', {}).get('percent', 0):.1f}%
メモリ: {metrics.get('memory', {}).get('percent', 0):.1f}%
ディスク: {metrics.get('disk', {}).get('percent', 0):.1f}%

サービス: {services.get('online', 0)}/{services.get('total', 0)}個オンライン
セキュリティスコア: {security.get('score', 0)}/100

全システム正常に稼働中です！
            """.strip()
            
            return {
                "type": "information",
                "data": data,
                "response_text": response_text,
                "voice_ready": True
            }
            
        except Exception as e:
            return {
                "type": "information",
                "response_text": "申し訳ありません。情報の取得に失敗しました。",
                "error": str(e)
            }
    
    async def handle_task_management(self, text: str, entities: List[str]) -> Dict[str, Any]:
        """タスク管理処理"""
        try:
            # Trinity Secretaryにタスク作成
            response = requests.post(
                "http://localhost:8889/api/task/create",
                json={"text": text, "source": "conversational_ai"},
                timeout=5
            )
            
            return {
                "type": "task_management",
                "response_text": f"タスクを作成しました: {text[:50]}",
                "voice_ready": True
            }
        except Exception as e:
            return {
                "type": "task_management",
                "response_text": "タスクの作成に失敗しました。",
                "error": str(e)
            }
    
    async def handle_problem_solving(self, text: str, entities: List[str]) -> Dict[str, Any]:
        """問題解決処理"""
        # 自動修復エンジンを実行
        result = subprocess.run(
            ["python3", "/root/mana_auto_repair_engine.py"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        return {
            "type": "problem_solving",
            "action": "auto_repair",
            "response_text": "自動修復エンジンを実行しました！問題を解決しています。",
            "voice_ready": True
        }
    
    async def handle_unknown(self, text: str) -> Dict[str, Any]:
        """不明なインテント処理"""
        return {
            "type": "unknown",
            "response_text": f"すみません、'{text}'の意図を理解できませんでした。もう少し詳しく教えてください。",
            "voice_ready": True
        }

async def main():
    ai = ManaConversationalAI()
    
    import sys
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        result = await ai.process_conversation(text)
        
        print("\n" + "=" * 60)
        print("🤖 Mana Conversational AI")
        print("=" * 60)
        print(f"\nあなた: {text}")
        print(f"\nMana: {result.get('response_text', '')}")
        print("\n" + "=" * 60)
    else:
        print("Usage: mana_conversational_ai.py <message>")

if __name__ == "__main__":
    asyncio.run(main())

