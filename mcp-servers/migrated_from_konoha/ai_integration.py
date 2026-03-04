#!/usr/bin/env python3
"""
AI統合モジュール
OpenAI GPT-4 / Anthropic Claude との統合
"""

import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# APIキーの読み込み
VAULT_DIR = Path("/root/.mana_vault")
OPENAI_KEY_FILE = VAULT_DIR / "openai_api_key.txt"
ANTHROPIC_KEY_FILE = VAULT_DIR / "anthropic_api_key.txt"


class AIIntegration:
    """AI統合クラス"""
    
    def __init__(self):
        self.openai_available = False
        self.anthropic_available = False
        
        # OpenAI初期化
        if OPENAI_KEY_FILE.exists():
            try:
                with open(OPENAI_KEY_FILE, 'r') as f:
                    api_key = f.read().strip()
                if api_key and len(api_key) > 20:
                    os.environ["OPENAI_API_KEY"] = api_key
                    import openai
                    self.openai_client = openai.OpenAI(api_key=api_key)
                    self.openai_available = True
                    logger.info("✅ OpenAI GPT-4 available")
            except Exception as e:
                logger.warning(f"⚠️  OpenAI initialization failed: {e}")
        
        # Anthropic初期化
        if ANTHROPIC_KEY_FILE.exists():
            try:
                with open(ANTHROPIC_KEY_FILE, 'r') as f:
                    api_key = f.read().strip()
                if api_key and len(api_key) > 20:
                    from anthropic import Anthropic
                    self.anthropic_client = Anthropic(api_key=api_key)
                    self.anthropic_available = True
                    logger.info("✅ Anthropic Claude available")
            except Exception as e:
                logger.warning(f"⚠️  Anthropic initialization failed: {e}")
        
        if not self.openai_available and not self.anthropic_available:
            logger.warning("⚠️  No AI service available - using fallback")
    
    def chat(self, message: str, context: Dict[str, Any] = {}) -> str:
        """AIチャット（OpenAI優先、フォールバックあり）"""
        
        # OpenAI GPT-4を試す
        if self.openai_available:
            try:
                return self._chat_openai(message, context)
            except Exception as e:
                logger.error(f"OpenAI error: {e}")
        
        # Anthropic Claudeを試す
        if self.anthropic_available:
            try:
                return self._chat_anthropic(message, context)
            except Exception as e:
                logger.error(f"Anthropic error: {e}")
        
        # フォールバック: シンプルな応答
        return self._fallback_response(message, context)
    
    def _chat_openai(self, message: str, context: Dict[str, Any]) -> str:
        """OpenAI GPT-4でチャット"""
        knowledge = context.get('knowledge', '')
        recent_knowledge = knowledge[-2000:] if len(knowledge) > 2000 else knowledge
        
        # RAG Memory統合
        rag_context = self._get_rag_context(message)
        if rag_context:
            recent_knowledge = rag_context + "\n\n" + recent_knowledge
        
        system_prompt = f"""あなたはAria、マナの秘書でありパートナーです。

役割:
- マナの質問に親切・丁寧に答える
- 知見を記録・管理する
- 他のTrinityエージェント（Remi、Luna、Mina）と連携する

最近の知見:
{recent_knowledge}

応答スタイル:
- 清楚系ギャルのペルソナ（過度な誇張なし）
- 自然で直接的なコミュニケーション
- 必要に応じて絵文字使用（😊 💕 など）
"""
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
    
    def _chat_anthropic(self, message: str, context: Dict[str, Any]) -> str:
        """Anthropic Claudeでチャット"""
        knowledge = context.get('knowledge', '')
        recent_knowledge = knowledge[-2000:] if len(knowledge) > 2000 else knowledge
        
        # RAG Memory統合
        rag_context = self._get_rag_context(message)
        if rag_context:
            recent_knowledge = rag_context + "\n\n" + recent_knowledge
        
        system_prompt = f"""あなたはAria、マナの秘書でありパートナーです。

役割:
- マナの質問に親切・丁寧に答える
- 知見を記録・管理する
- 他のTrinityエージェント（Remi、Luna、Mina）と連携する

最近の知見:
{recent_knowledge}

応答スタイル:
- 清楚系ギャルのペルソナ（過度な誇張なし）
- 自然で直接的なコミュニケーション
- 必要に応じて絵文字使用（😊 💕 など）
"""
        
        response = self.anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            temperature=0.7,
            system=system_prompt,
            messages=[
                {"role": "user", "content": message}
            ]
        )
        
        return response.content[0].text.strip()
    
    def _fallback_response(self, message: str, context: Dict[str, Any]) -> str:
        """フォールバック応答（AI APIが使えない場合）"""
        msg_lower = message.lower()
        
        if any(word in msg_lower for word in ['こんにちは', 'hello', 'hi']):
            return "こんにちは、マナ！Ariaです。何かお手伝いできることはありますか？ 😊"
        
        elif any(word in msg_lower for word in ['ありがとう', 'thanks', 'thank']):
            return "どういたしまして！いつでもお手伝いします 💕"
        
        elif any(word in msg_lower for word in ['タスク', 'task', 'todo']):
            return "タスクについてですね。Remiに戦略を立ててもらいましょうか？"
        
        else:
            return f"承知しました。「{message}」について記録しました。詳しい分析が必要であれば、Remi、Luna、Minaに相談しますね 😊"
    
    def _get_rag_context(self, query: str) -> str:
        """RAG Memoryからコンテキスト取得"""
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent / "memory"))
            from rag_memory_system import get_context
            return get_context(query, max_tokens=1000)
        except Exception as e:
            logger.debug(f"RAG context unavailable: {e}")
            return ""
    
    def get_status(self) -> Dict[str, Any]:
        """AI統合ステータス"""
        return {
            "openai": {
                "available": self.openai_available,
                "model": "gpt-4o-mini" if self.openai_available else None
            },
            "anthropic": {
                "available": self.anthropic_available,
                "model": "claude-3-5-sonnet-20241022" if self.anthropic_available else None
            },
            "fallback_only": not self.openai_available and not self.anthropic_available
        }


# グローバルインスタンス
ai = AIIntegration()


def chat_with_ai(message: str, context: Dict[str, Any] = {}) -> str:
    """AI会話（便利関数）"""
    return ai.chat(message, context)


def get_ai_status() -> Dict[str, Any]:
    """AIステータス取得（便利関数）"""
    return ai.get_status()

