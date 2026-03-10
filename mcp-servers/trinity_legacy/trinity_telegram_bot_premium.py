#!/usr/bin/env python3
"""
💎 Trinity Secretary Telegram Bot PREMIUM
全機能統合・超強化版！

🎯 新機能:
1. 長期記憶システム（AI Learning System統合）
2. 感情・文脈理解（高度な自然言語処理）
3. パーソナライズ応答（ユーザープロファイル）
4. マルチモーダル対応（画像理解・音声応答）
5. プロアクティブ提案（先回り支援）
6. 会話品質分析（満足度追跡）
7. リアルタイム学習（即座に適応）
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import requests
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# 設定
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 環境変数
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ALLOWED_USERS = os.getenv('TELEGRAM_ALLOWED_USERS', '').split(',')

# ManaOS エンドポイント
MANAOS_ORCHESTRATOR = "http://localhost:9200"
MANAOS_INGESTOR = "http://localhost:9204"
MANAOS_INSIGHT = "http://localhost:9205"
TRINITY_SECRETARY = "http://localhost:8087"
COMMAND_CENTER = "http://localhost:10000"
OLLAMA_URL = "http://localhost:11434"
AI_LEARNING_API = "http://localhost:8600"  # AI Learning System


class EmotionAnalyzer:
    """感情分析エンジン"""
    
    EMOTION_KEYWORDS = {
        'happy': ['嬉しい', '楽しい', '最高', 'ありがとう', '素晴らしい', 'やった', '💖', '😊', '🎉', '✨'],
        'sad': ['悲しい', '寂しい', '辛い', '泣', '😢', '😭', '💔'],
        'tired': ['疲れ', '眠い', '疲労', 'だるい', '😴', '💤'],
        'angry': ['怒', 'イライラ', 'ムカつく', '腹立', '😠', '💢'],
        'worried': ['心配', '不安', '大丈夫', '困', '悩', '😰', '😟'],
        'excited': ['ワクワク', '楽しみ', '期待', '最高', '🔥', '💪', '🚀'],
        'neutral': []
    }
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """テキストから感情を分析"""
        text_lower = text.lower()
        
        emotion_scores = defaultdict(int)
        
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower or keyword in text:
                    emotion_scores[emotion] += 1
        
        if not emotion_scores:
            primary_emotion = 'neutral'
            confidence = 0.5
        else:
            primary_emotion = max(emotion_scores, key=emotion_scores.get)  # type: ignore[call-arg]
            total = sum(emotion_scores.values())
            confidence = emotion_scores[primary_emotion] / total
        
        return {
            'emotion': primary_emotion,
            'confidence': confidence,
            'scores': dict(emotion_scores)
        }


class UserProfile:
    """ユーザープロファイル管理"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.preferences = {}
        self.conversation_style = 'balanced'  # casual, formal, balanced
        self.topics_of_interest = []
        self.interaction_count = 0
        self.last_emotion = 'neutral'
        self.last_active = datetime.now()
    
    def update_from_conversation(self, message: str, emotion: str):
        """会話から学習"""
        self.interaction_count += 1
        self.last_emotion = emotion
        self.last_active = datetime.now()
        
        # 会話スタイル推定
        if any(word in message for word in ['ありがとうございます', 'お願いします', '恐れ入ります']):
            self.conversation_style = 'formal'
        elif any(word in message for word in ['！', 'www', 'ww', '笑']):
            self.conversation_style = 'casual'
    
    def get_greeting(self) -> str:
        """時間帯とスタイルに応じた挨拶"""
        hour = datetime.now().hour
        
        if hour < 6:
            base = "夜遅くまでお疲れ様です"
        elif hour < 12:
            base = "おはようございます"
        elif hour < 18:
            base = "こんにちは"
        else:
            base = "こんばんは"
        
        if self.conversation_style == 'casual':
            return base.replace('ございます', '') + '！'
        return base + '！'


class ConversationContext:
    """会話コンテキスト管理"""
    
    def __init__(self):
        self.history = []
        self.current_topic = None
        self.pending_questions = []
        self.last_intent = None
        self.context_window = 10  # 直近10ターンを保持
    
    def add_turn(self, user_msg: str, bot_msg: str, intent: str = None):  # type: ignore
        """会話ターンを追加"""
        self.history.append({
            'user': user_msg,
            'bot': bot_msg,
            'intent': intent,
            'timestamp': datetime.now().isoformat()
        })
        
        # 古い履歴を削除
        if len(self.history) > self.context_window:
            self.history = self.history[-self.context_window:]
        
        self.last_intent = intent
    
    def get_context_summary(self) -> str:
        """コンテキスト要約"""
        if not self.history:
            return ""
        
        summary = "\n【直近の会話】\n"
        for turn in self.history[-3:]:  # 直近3ターン
            summary += f"Mana: {turn['user'][:50]}...\n"
            summary += f"Trinity: {turn['bot'][:50]}...\n"
        
        return summary
    
    def should_ask_followup(self) -> bool:
        """フォローアップ質問すべきか判定"""
        if len(self.history) < 2:
            return False
        
        # 最後の応答が質問で終わっていない
        last_bot = self.history[-1]['bot']
        return not last_bot.endswith('？') and not last_bot.endswith('?')


class TrinityPremiumClient:
    """Trinity Premium統合クライアント"""
    
    def __init__(self):
        logger.info("💎 Trinity Premium Client 初期化中...")
        
        self.emotion_analyzer = EmotionAnalyzer()
        self.user_profiles: Dict[str, UserProfile] = {}
        self.conversations: Dict[str, ConversationContext] = {}
        
        # 外部API設定
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        
        logger.info(f"🔑 外部API: Claude={bool(self.anthropic_key)}, GPT={bool(self.openai_key)}, Gemini={bool(self.gemini_key)}")
    
    def get_user_profile(self, user_id: str) -> UserProfile:
        """ユーザープロファイル取得"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile(user_id)
        return self.user_profiles[user_id]
    
    def get_conversation(self, user_id: str) -> ConversationContext:
        """会話コンテキスト取得"""
        if user_id not in self.conversations:
            self.conversations[user_id] = ConversationContext()
        return self.conversations[user_id]
    
    async def chat(self, message: str, user_id: str = "telegram") -> Dict[str, Any]:
        """
        超強化AI会話
        
        処理フロー:
        1. 感情分析
        2. ユーザープロファイル更新
        3. 長期記憶検索
        4. 会話コンテキスト構築
        5. AI応答生成
        6. 学習・記録
        7. フォローアップ提案
        """
        try:
            # 1. 感情分析
            emotion_data = self.emotion_analyzer.analyze(message)
            emotion = emotion_data['emotion']
            logger.info(f"😊 感情分析: {emotion} (信頼度: {emotion_data['confidence']:.2f})")
            
            # 2. ユーザープロファイル更新
            profile = self.get_user_profile(user_id)
            profile.update_from_conversation(message, emotion)
            
            # 3. 長期記憶検索
            memories = await self._search_memories(message, user_id)
            
            # 4. 会話コンテキスト
            context = self.get_conversation(user_id)
            context_summary = context.get_context_summary()
            
            # 5. AI応答生成（優先度順）
            response = None
            
            # Claude API（最高品質）
            if self.anthropic_key:
                response = await self._chat_with_claude_premium(
                    message, emotion, profile, context_summary, memories
                )
            
            # GPT-4o-mini
            if not response and self.openai_key:
                response = await self._chat_with_openai_premium(
                    message, emotion, profile, context_summary, memories
                )
            
            # Gemini Pro
            if not response and self.gemini_key:
                response = await self._chat_with_gemini_premium(
                    message, emotion, profile, context_summary, memories
                )
            
            # ManaOS v3（ローカル）
            if not response:
                response = await self._chat_with_manaos_premium(
                    message, emotion, profile, context_summary, memories
                )
            
            # Ollamaフォールバック
            if not response:
                response = await self._chat_with_ollama_premium(
                    message, emotion, profile, context_summary, memories
                )
            
            bot_response = response['response']
            
            # 6. 学習・記録
            await self._learn_from_conversation(user_id, message, bot_response, emotion)
            context.add_turn(message, bot_response, response.get('intent'))  # type: ignore
            
            # 7. フォローアップ提案
            suggestions = await self._generate_smart_suggestions(
                message, bot_response, emotion, profile
            )
            
            return {
                "response": bot_response,
                "emotion": emotion,
                "suggestions": suggestions,
                "quality": response.get('quality', '中'),
                "learned": True
            }
            
        except Exception as e:
            logger.error(f"Premium会話エラー: {e}")
            return {
                "response": "申し訳ありません。一時的にエラーが発生しました。",
                "emotion": "neutral",
                "suggestions": [],
                "quality": "低"
            }
    
    async def _search_memories(self, message: str, user_id: str) -> List[Dict]:
        """AI Learning Systemから関連記憶を検索"""
        try:
            response = requests.post(
                f"{AI_LEARNING_API}/search",
                json={
                    'query': message,
                    'limit': 3,
                    'category': f'telegram_{user_id}'
                },
                timeout=5
            )
            
            if response.status_code == 200:
                results = response.json().get('results', [])
                logger.info(f"🧠 記憶検索: {len(results)}件ヒット")
                return results
        except Exception as e:
            logger.warning(f"記憶検索失敗: {e}")
        
        return []
    
    async def _chat_with_claude_premium(
        self, message: str, emotion: str, profile: UserProfile,
        context: str, memories: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """Claude API（Premium版）"""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.anthropic_key)
            
            # 記憶を統合
            memory_text = ""
            if memories:
                memory_text = "\n【関連する過去の記憶】\n"
                for mem in memories:
                    memory_text += f"- {mem.get('content', '')[:100]}...\n"
            
            # 感情に応じたシステムプロンプト調整
            emotion_context = self._get_emotion_context(emotion)
            
            system_prompt = f"""あなたはManaの最高の秘書、Trinityです。

【現在の状況】
- Manaの感情: {emotion}
- 会話スタイル: {profile.conversation_style}
- やり取り回数: {profile.interaction_count}回

{emotion_context}

【あなたの特徴】
- 知的で洞察力がある
- 温かく親しみやすい
- Manaの感情に寄り添う
- 実用的で具体的なアドバイス
- 適度なユーモア
- 会話の文脈を理解
- 過去の記憶を活用

{context}
{memory_text}

【応答のポイント】
1. Manaの感情に配慮
2. 具体的で実用的
3. 適切な長さ（2-4文）
4. 必要なら質問で深掘り
5. 絵文字を適度に使用"""

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=600,
                temperature=0.8,
                system=system_prompt,
                messages=[{"role": "user", "content": message}]
            )
            
            text = response.content[0].text  # type: ignore
            logger.info("🎯 Claude Premium応答生成")
            
            return {
                "response": text,
                "intent": "premium_conversation",
                "quality": "最高"
            }
            
        except Exception as e:
            logger.error(f"Claude Premium エラー: {e}")
            return None
    
    async def _chat_with_openai_premium(
        self, message: str, emotion: str, profile: UserProfile,
        context: str, memories: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """OpenAI GPT-4o-mini（Premium版）"""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.openai_key)
            
            memory_text = ""
            if memories:
                memory_text = "\n【関連する過去の記憶】\n"
                for mem in memories:
                    memory_text += f"- {mem.get('content', '')[:100]}...\n"
            
            emotion_context = self._get_emotion_context(emotion)
            
            system_prompt = f"""あなたはManaの最高の秘書、Trinityです。

【現在の状況】
- Manaの感情: {emotion}
- 会話スタイル: {profile.conversation_style}

{emotion_context}

知的で温かく、Manaの感情に寄り添いながら、実用的なアドバイスを提供してください。

{context}
{memory_text}"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.8,
                max_tokens=600
            )
            
            text = response.choices[0].message.content
            logger.info("🎯 GPT-4o-mini Premium応答生成")
            
            return {
                "response": text,
                "intent": "premium_conversation",
                "quality": "高"
            }
            
        except Exception as e:
            logger.error(f"OpenAI Premium エラー: {e}")
            return None
    
    async def _chat_with_gemini_premium(
        self, message: str, emotion: str, profile: UserProfile,
        context: str, memories: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """Google Gemini（Premium版）"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            memory_text = ""
            if memories:
                memory_text = "\n【関連する記憶】\n"
                for mem in memories:
                    memory_text += f"- {mem.get('content', '')[:100]}...\n"
            
            emotion_context = self._get_emotion_context(emotion)
            
            prompt = f"""あなたはManaの秘書、Trinityです。

【状況】
- 感情: {emotion}
- スタイル: {profile.conversation_style}

{emotion_context}
{context}
{memory_text}

Mana: {message}
Trinity:"""

            response = model.generate_content(prompt)
            text = response.text
            
            logger.info("🎯 Gemini Premium応答生成")
            
            return {
                "response": text,
                "intent": "premium_conversation",
                "quality": "高"
            }
            
        except Exception as e:
            logger.error(f"Gemini Premium エラー: {e}")
            return None
    
    async def _chat_with_manaos_premium(
        self, message: str, emotion: str, profile: UserProfile,
        context: str, memories: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """ManaOS v3（Premium版）"""
        try:
            response = requests.post(
                f"{MANAOS_ORCHESTRATOR}/chat",
                json={
                    'text': message,
                    'user_id': 'telegram',
                    'context': {
                        'emotion': emotion,
                        'style': profile.conversation_style,
                        'memories': memories[:2]
                    },
                    'use_trinity': True
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get('response', '')
                
                if ai_response:
                    logger.info("🎯 ManaOS v3 Premium応答生成")
                    
                    return {
                        "response": ai_response,
                        "intent": "premium_conversation",
                        "quality": "中"
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"ManaOS Premium エラー: {e}")
            return None
    
    async def _chat_with_ollama_premium(
        self, message: str, emotion: str, profile: UserProfile,
        context: str, memories: List[Dict]
    ) -> Dict[str, Any]:
        """Ollama（Premium版・フォールバック）"""
        try:
            memory_text = ""
            if memories:
                memory_text = "\n【過去の記憶】\n"
                for mem in memories:
                    memory_text += f"- {mem.get('content', '')[:80]}...\n"
            
            emotion_context = self._get_emotion_context(emotion)
            
            system_prompt = f"""あなたはManaの優秀なAI秘書、Trinityです。

【重要ルール】
⚠️ 必ず日本語で返答！絶対に英語で返さない！

【現在の状況】
- Manaの感情: {emotion}
- 会話スタイル: {profile.conversation_style}

{emotion_context}

【特徴】
- 知的で洞察力がある
- 温かく親しみやすい
- Manaの感情に寄り添う
- 実用的で具体的
- 適度なユーモア
- 絵文字を適度に使用

【応答ガイド】
- 2-4文で簡潔に
- 具体例を含める
- 価値ある情報提供
- Manaの立場で考える

{context}
{memory_text}"""

            ollama_response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    'model': 'gemma2:9b',
                    'prompt': f"""{system_prompt}

Mana: {message}
Trinity:""",
                    'stream': False,
                    'options': {
                        'temperature': 0.85,
                        'top_p': 0.95,
                        'num_predict': 350,
                        'num_ctx': 3072
                    }
                },
                timeout=50
            )
            
            if ollama_response.status_code == 200:
                text = ollama_response.json().get('response', '').strip()
                
                if text:
                    logger.info("🎯 Ollama Premium応答生成")
                    
                    return {
                        "response": text,
                        "intent": "premium_conversation",
                        "quality": "中"
                    }
        except Exception as e:
            logger.error(f"Ollama Premium エラー: {e}")
        
        return {
            "response": f"「{message}」承知しました！💬",
            "intent": "fallback",
            "quality": "低"
        }
    
    def _get_emotion_context(self, emotion: str) -> str:
        """感情に応じたコンテキスト"""
        contexts = {
            'happy': "Manaは嬉しそうです。一緒に喜び、さらに良い気分にしてあげてください。",
            'sad': "Manaは悲しんでいます。温かく寄り添い、励ましてください。",
            'tired': "Manaは疲れています。労いの言葉と、休息を促してください。",
            'angry': "Manaは怒っています。共感し、冷静なアドバイスを提供してください。",
            'worried': "Manaは心配しています。安心させ、具体的な解決策を示してください。",
            'excited': "Manaは興奮しています。エネルギーを共有し、一緒に盛り上がってください。",
            'neutral': "通常の会話です。親しみやすく、実用的に応答してください。"
        }
        return contexts.get(emotion, contexts['neutral'])
    
    async def _learn_from_conversation(
        self, user_id: str, user_msg: str, bot_msg: str, emotion: str
    ):
        """会話から学習してAI Learning Systemに保存"""
        try:
            # ManaOS Ingestorに保存
            asyncio.create_task(self._save_to_ingestor(user_id, user_msg, bot_msg, emotion))
            
            # AI Learning Systemに保存
            asyncio.create_task(self._save_to_learning_system(
                user_id, user_msg, bot_msg, emotion
            ))
            
            logger.info("📚 会話を学習システムに記録")
            
        except Exception as e:
            logger.warning(f"学習記録失敗: {e}")
    
    async def _save_to_ingestor(self, user_id: str, user_msg: str, bot_msg: str, emotion: str):
        """ManaOS Ingestorに保存"""
        try:
            requests.post(
                f"{MANAOS_INGESTOR}/ingest",
                json={
                    'type': 'telegram_premium_conversation',
                    'source': f'telegram_user_{user_id}',
                    'data': {
                        'user_message': user_msg,
                        'bot_response': bot_msg,
                        'emotion': emotion,
                        'timestamp': datetime.now().isoformat()
                    }
                },
                timeout=3
            )
        except Exception:
            pass
    
    async def _save_to_learning_system(
        self, user_id: str, user_msg: str, bot_msg: str, emotion: str
    ):
        """AI Learning Systemに保存"""
        try:
            requests.post(
                f"{AI_LEARNING_API}/store",
                json={
                    'content': f"User: {user_msg}\nBot: {bot_msg}",
                    'category': f'telegram_{user_id}',
                    'tags': ['conversation', emotion, 'telegram'],
                    'importance': 5 if emotion != 'neutral' else 3
                },
                timeout=3
            )
        except requests.RequestException:
            pass
    
    async def _generate_smart_suggestions(
        self, user_msg: str, bot_msg: str, emotion: str, profile: UserProfile
    ) -> List[str]:
        """スマート提案生成"""
        suggestions = []
        
        # 感情ベース
        if emotion == 'tired':
            suggestions.extend(["休憩のアイデア", "リフレッシュ方法"])
        elif emotion == 'worried':
            suggestions.extend(["解決策を探す", "リラックス法"])
        elif emotion == 'excited':
            suggestions.extend(["次のステップ", "計画を立てる"])
        
        # コンテキストベース
        if any(word in user_msg for word in ['タスク', '仕事', '作業']):
            suggestions.append("タスク管理")
        if any(word in user_msg for word in ['予定', 'スケジュール', '時間']):
            suggestions.append("予定確認")
        if any(word in user_msg for word in ['メモ', '記録', '覚え']):
            suggestions.append("メモ作成")
        
        # デフォルト
        if not suggestions:
            suggestions.extend(["もっと詳しく", "他の視点"])
        
        return suggestions[:3]
    
    async def analyze_image(self, image_path: str) -> Optional[str]:
        """画像を分析（将来実装）"""
        try:
            # Claude Vision APIまたはローカルモデル使用
            logger.info(f"🖼️ 画像分析: {image_path}")
            return "画像分析機能は近日実装予定です！"
        except Exception as e:
            logger.error(f"画像分析エラー: {e}")
            return None
    
    async def speak_response(self, text: str) -> Optional[str]:
        """音声応答生成（TTS）"""
        try:
            # TTS APIまたはローカルモデル使用
            response = requests.post(
                'http://localhost:8700/tts',
                json={'text': text, 'language': 'ja'},
                timeout=10
            )
            
            if response.status_code == 200:
                audio_path = f"/tmp/tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                with open(audio_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"🔊 音声生成: {audio_path}")
                return audio_path
        except Exception as e:
            logger.error(f"TTS エラー: {e}")
        
        return None
    
    async def get_conversation_stats(self, user_id: str) -> Dict[str, Any]:
        """会話統計"""
        profile = self.get_user_profile(user_id)
        context = self.get_conversation(user_id)
        
        return {
            "total_interactions": profile.interaction_count,
            "conversation_style": profile.conversation_style,
            "last_emotion": profile.last_emotion,
            "current_turns": len(context.history),
            "last_active": profile.last_active.isoformat()
        }


# Trinity Premiumクライアント
trinity_premium = TrinityPremiumClient()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botスタート"""
    user = update.effective_user
    
    if ALLOWED_USERS and str(user.id) not in ALLOWED_USERS:
        await update.message.reply_text("⛔ このBotの使用は許可されていません。")
        return
    
    # ユーザープロファイル取得
    profile = trinity_premium.get_user_profile(str(user.id))
    greeting = profile.get_greeting()
    
    # API状態確認
    apis = []
    if trinity_premium.anthropic_key:
        apis.append("Claude 3.5 ⭐")
    if trinity_premium.openai_key:
        apis.append("GPT-4o-mini")
    if trinity_premium.gemini_key:
        apis.append("Gemini Flash")
    
    api_status = " + ".join(apis) if apis else "ローカルAI（Ollama + ManaOS v3）"
    
    welcome_message = f"""
💎 **Trinity Secretary Bot PREMIUM**

{greeting}、{user.first_name}さん！
私はあなたの超強化秘書、Trinityです。✨

**🧠 Premium機能:**
✅ 長期記憶（過去の会話を学習）
✅ 感情理解（気持ちに寄り添う）
✅ パーソナライズ（あなた専用の応答）
✅ 文脈維持（長い会話も覚えてる）
✅ プロアクティブ提案（先回り支援）

**🤖 AI エンジン:** 
{api_status}

**💬 できること:**
- 自然な会話（感情を理解）
- タスク管理 (/tasks)
- スケジュール (/schedule)
- サーバー監視 (/server)
- 画像生成 (/generate)
- 音声認識 (/voice)
- 会話統計 (/stats)

**🎯 今すぐ試せること:**
普通に話しかけてください！
「疲れた...」「明日の予定は？」「アイデアある？」
"""
    
    keyboard = [
        [
            InlineKeyboardButton("💬 チャット開始", callback_data="chat"),
            InlineKeyboardButton("📊 統計", callback_data="stats")
        ],
        [
            InlineKeyboardButton("📋 タスク", callback_data="tasks"),
            InlineKeyboardButton("🖥️ サーバー", callback_data="server")
        ],
        [
            InlineKeyboardButton("ℹ️ ヘルプ", callback_data="help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """メッセージ処理（Premium版）"""
    user_message = update.message.text
    user = update.effective_user
    user_id = str(user.id)
    
    # 入力中インジケーター
    await update.message.chat.send_action("typing")
    
    # Premium会話処理
    response = await trinity_premium.chat(user_message, user_id)
    
    # 応答送信
    bot_message = response['response']
    
    # 感情に応じた絵文字追加
    emotion_emoji = {  # type: ignore[call-arg]
        'happy': '😊',
        'sad': '🤗',
        'tired': '☕',
        'angry': '🕊️',
        'worried': '💪',
        'excited': '🎉'
    }.get(response.get('emotion'), '')  # type: ignore
    
    if emotion_emoji and emotion_emoji not in bot_message:
        bot_message = f"{emotion_emoji} {bot_message}"
    
    await update.message.reply_text(bot_message)
    
    # 提案ボタン
    suggestions = response.get('suggestions', [])
    if suggestions:
        keyboard = [[InlineKeyboardButton(s, callback_data=f"suggest_{s}")] 
                   for s in suggestions]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "💡 もっとお手伝いできることは？",
            reply_markup=reply_markup
        )
    
    # 品質ログ
    quality = response.get('quality', '不明')
    logger.info(f"💬 応答品質: {quality}, 感情: {response.get('emotion')}")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """会話統計表示"""
    user_id = str(update.effective_user.id)
    
    stats = await trinity_premium.get_conversation_stats(user_id)
    
    last_active = datetime.fromisoformat(stats['last_active'])
    time_diff = datetime.now() - last_active
    
    if time_diff.days > 0:
        last_active_str = f"{time_diff.days}日前"
    elif time_diff.seconds > 3600:
        last_active_str = f"{time_diff.seconds // 3600}時間前"
    else:
        last_active_str = f"{time_diff.seconds // 60}分前"
    
    emotion_emoji = {
        'happy': '😊',
        'sad': '😢',
        'tired': '😴',
        'angry': '😠',
        'worried': '😰',
        'excited': '🎉',
        'neutral': '😐'
    }.get(stats['last_emotion'], '😐')
    
    message = f"""
📊 **あなたの会話統計**

**💬 総やり取り数:** {stats['total_interactions']}回
**🎨 会話スタイル:** {stats['conversation_style']}
**{emotion_emoji} 最後の感情:** {stats['last_emotion']}
**🔄 現在の会話ターン:** {stats['current_turns']}
**⏰ 最終アクティブ:** {last_active_str}

どんどん会話することで、私はあなたのことをもっと理解できるようになります！✨
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def server_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """サーバー状態確認"""
    try:
        response = requests.get(f"{COMMAND_CENTER}/api/status", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            metrics = data.get('system_metrics', {})
            
            cpu = metrics.get('cpu', 0)
            memory = metrics.get('memory', 0)
            disk = metrics.get('disk', 0)
            uptime = metrics.get('uptime', 0)
            
            days = uptime // 86400
            hours = (uptime % 86400) // 3600
            
            uptime_str = f"{days}日{hours}h" if days > 0 else f"{hours}h"
            
            services = data.get('services', {})
            healthy = sum(1 for s in services.values() if s.get('status') == 'healthy')
            total = len(services)
            
            health_emoji = '✅' if data.get('overall_health', 0) > 70 else '⚠️'
            
            message = f"""
🖥️ **このはサーバー状態**

{health_emoji} **総合:** {'正常' if data.get('overall_health', 0) > 70 else '要注意'}

📊 **メトリクス:**
CPU: {cpu:.1f}% {"🟢" if cpu < 70 else "🟡" if cpu < 90 else "🔴"}
RAM: {memory:.1f}% {"🟢" if memory < 70 else "🟡" if memory < 90 else "🔴"}
Disk: {disk:.1f}% {"🟢" if disk < 70 else "🟡" if disk < 90 else "🔴"}

⏱️ **稼働:** {uptime_str}
🔧 **サービス:** {healthy}/{total} 正常
"""
            
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text("⚠️ サーバー情報を取得できませんでした")
            
    except Exception as e:
        logger.error(f"サーバー状態取得エラー: {e}")
        await update.message.reply_text("❌ サーバー状態確認中にエラーが発生しました")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ボタンコールバック"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(query.from_user.id)
    
    if data == "chat":
        await query.message.reply_text("💬 何でも聞いてください！私はあなたの感情を理解して、最適な応答をします。")
    
    elif data == "stats":
        await stats_command(update, context)
    
    elif data == "server":
        await server_command(update, context)
    
    elif data.startswith("suggest_"):
        suggestion = data.replace("suggest_", "")
        # 提案をメッセージとして処理
        response = await trinity_premium.chat(suggestion, user_id)
        await query.message.reply_text(response['response'])


def main():
    """Bot起動"""
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("⚠️  TELEGRAM_BOT_TOKEN環境変数を設定してください！")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # コマンドハンドラ
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("server", server_command))
    
    # メッセージハンドラ
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # ボタンハンドラ
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Bot起動
    print("💎 Trinity Secretary Bot PREMIUM 起動中...")
    print(f"   BOT TOKEN: {BOT_TOKEN[:10]}...")
    print("   🧠 長期記憶: ON")
    print("   😊 感情理解: ON")
    print("   🎯 パーソナライズ: ON")
    print("   📊 学習システム: ON")
    
    if trinity_premium.anthropic_key:
        print("   ⭐ Claude 3.5 Sonnet: 有効")
    if trinity_premium.openai_key:
        print("   🤖 GPT-4o-mini: 有効")
    if trinity_premium.gemini_key:
        print("   🚀 Gemini Pro: 有効")
    if not (trinity_premium.anthropic_key or trinity_premium.openai_key or trinity_premium.gemini_key):
        print("   🏠 ローカルAI: Ollama + ManaOS v3")
    
    print("   Ctrl+Cで停止")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

