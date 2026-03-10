#!/usr/bin/env python3
"""
💎 Trinity Secretary Telegram Bot PREMIUM v2
完全強化版！検索・システム把握・記憶共有・秘書力すべて統合

🎯 新機能 v2:
1. 🔍 統合検索（会話・Obsidian・ログ・メトリクス）
2. 🖥️ ManaOSシステム状況把握
3. 🤝 トリニティ達との記憶共有
4. 🧠 強化版会話コンテキスト（指示語解決・文脈補完）
5. 💼 高度秘書機能（先回り支援・習慣トラッキング）
6. 📊 インテリジェント分析・推奨
7. 🚀 プロアクティブ提案

既存機能:
- 感情分析・パーソナライズ・マルチAI
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List
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

# 新機能モジュールのインポート
from trinity_search_engine import TrinitySearchEngine
from manaos_system_inspector import ManaOSSystemInspector
from trinity_memory_hub import TrinityMemoryHub
from conversation_context_enhanced import EnhancedConversationContext
from secretary_intelligence import SecretaryIntelligence
from reminder_system import ReminderSystem
from image_understanding_system import ImageUnderstandingSystem
from voice_processing_system import VoiceProcessingSystem
from x280_remote_control import X280RemoteControl
from manaos_telegram_bridge import ManaOSTelegramBridge

# 設定
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 環境変数
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ALLOWED_USERS = os.getenv('TELEGRAM_ALLOWED_USERS', '').split(',')

# エンドポイント
MANAOS_ORCHESTRATOR = "http://localhost:9200"
OLLAMA_URL = "http://localhost:11434"
AI_LEARNING_API = "http://localhost:8600"


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
        self.conversation_style = 'balanced'
        self.topics_of_interest = []
        self.interaction_count = 0
        self.last_emotion = 'neutral'
        self.last_active = datetime.now()
    
    def update_from_conversation(self, message: str, emotion: str):
        """会話から学習"""
        self.interaction_count += 1
        self.last_emotion = emotion
        self.last_active = datetime.now()
        
        if any(word in message for word in ['ありがとうございます', 'お願いします']):
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


class TrinityPremiumV2Client:
    """Trinity Premium v2統合クライアント"""
    
    def __init__(self):
        logger.info("💎 Trinity Premium v2 Client 初期化中...")
        
        # 基本機能
        self.emotion_analyzer = EmotionAnalyzer()
        self.user_profiles: Dict[str, UserProfile] = {}
        
        # v2新機能
        self.search_engine = TrinitySearchEngine()
        self.system_inspector = ManaOSSystemInspector()
        self.memory_hub = TrinityMemoryHub()
        self.secretary = SecretaryIntelligence()
        self.reminder_system = ReminderSystem()  # リマインダー
        self.image_understanding = ImageUnderstandingSystem()  # 画像理解
        self.voice_processing = VoiceProcessingSystem()  # 音声処理
        self.x280_control = X280RemoteControl()  # X280制御
        self.manaos_bridge = ManaOSTelegramBridge()  # ManaOS統合
        
        # 強化版コンテキスト（ユーザーごと）
        self.conversations: Dict[str, EnhancedConversationContext] = {}
        
        # 外部API
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        
        logger.info("✅ Premium v2 初期化完了")
        logger.info(f"   🔑 Claude={bool(self.anthropic_key)}, GPT={bool(self.openai_key)}, Gemini={bool(self.gemini_key)}")
    
    def get_user_profile(self, user_id: str) -> UserProfile:
        """ユーザープロファイル取得"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile(user_id)
        return self.user_profiles[user_id]
    
    def get_conversation(self, user_id: str) -> EnhancedConversationContext:
        """強化版会話コンテキスト取得"""
        if user_id not in self.conversations:
            self.conversations[user_id] = EnhancedConversationContext()
        return self.conversations[user_id]
    
    async def chat(self, message: str, user_id: str = "telegram") -> Dict[str, Any]:
        """
        超強化AI会話（v2）
        
        処理フロー:
        1. 感情分析
        2. ユーザープロファイル更新
        3. 文脈理解（指示語解決）
        4. 共有メモリから情報取得
        5. AI応答生成
        6. 記憶を全トリニティに共有
        7. プロアクティブ提案生成
        """
        try:
            # 1. 感情分析
            emotion_data = self.emotion_analyzer.analyze(message)
            emotion = emotion_data['emotion']
            
            # 2. ユーザープロファイル更新
            profile = self.get_user_profile(user_id)
            profile.update_from_conversation(message, emotion)
            
            # 3. 文脈理解（強化版）
            context = self.get_conversation(user_id)
            understood_context = context.understand_context(message)
            
            # 指示語を解決したメッセージ
            resolved_message = message
            for ref, target in understood_context['resolved_references'].items():
                resolved_message = resolved_message.replace(ref, target)
            
            # 4. 共有メモリから情報取得
            shared_context = await self.memory_hub.retrieve_shared_context(user_id)
            
            # 5. AI応答生成
            response = await self._generate_ai_response(
                resolved_message,
                emotion,
                profile,
                understood_context,
                shared_context
            )
            
            bot_response = response['response']
            
            # 6. 記憶を全トリニティに共有
            await self.memory_hub.sync_memory_to_trinity({
                'type': 'conversation',
                'content': f"User: {message}\nBot: {bot_response}",
                'user_id': user_id,
                'timestamp': datetime.now().isoformat(),
                'emotion': emotion,
                'importance': 7 if emotion != 'neutral' else 5
            })
            
            # 7. 会話コンテキストに追加
            context.add_turn(message, bot_response, response.get('intent'), emotion)
            
            # 8. プロアクティブ提案生成
            suggestions = await self._generate_smart_suggestions(
                message, bot_response, emotion, profile, user_id
            )
            
            return {
                "response": bot_response,
                "emotion": emotion,
                "suggestions": suggestions,
                "understood_context": understood_context,
                "quality": response.get('quality', '中')
            }
            
        except Exception as e:
            logger.error(f"Premium v2会話エラー: {e}")
            return {
                "response": "申し訳ありません。一時的にエラーが発生しました。",
                "emotion": "neutral",
                "suggestions": []
            }
    
    async def _generate_ai_response(
        self, message: str, emotion: str, profile: UserProfile,
        context: Dict, shared_context: Dict
    ) -> Dict[str, Any]:
        """AI応答生成（優先度順）"""
        
        # Claude API
        if self.anthropic_key:
            try:
                return await self._chat_with_claude(message, emotion, profile, context)  # type: ignore
            except Exception as e:
                logger.warning(f"Claude failed: {e}")
        
        # GPT-4o-mini
        if self.openai_key:
            try:
                return await self._chat_with_openai(message, emotion, profile, context)  # type: ignore
            except Exception as e:
                logger.warning(f"OpenAI failed: {e}")
        
        # Gemini
        if self.gemini_key:
            try:
                return await self._chat_with_gemini(message, emotion, profile, context)  # type: ignore
            except Exception as e:
                logger.warning(f"Gemini failed: {e}")
        
        # Ollama（ローカル）
        return await self._chat_with_ollama(message, emotion, profile, context)
    
    async def _chat_with_ollama(
        self, message: str, emotion: str, profile: UserProfile, context: Dict
    ) -> Dict[str, Any]:
        """Ollama応答生成"""
        try:
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
- Manaの立場で考える"""

            ollama_response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    'model': 'gemma2:9b',
                    'prompt': f"{system_prompt}\n\nMana: {message}\nTrinity:",
                    'stream': False,
                    'options': {
                        'temperature': 0.85,
                        'top_p': 0.95,
                        'num_predict': 350
                    }
                },
                timeout=50
            )
            
            if ollama_response.status_code == 200:
                text = ollama_response.json().get('response', '').strip()
                if text:
                    return {
                        "response": text,
                        "intent": "conversation",
                        "quality": "中"
                    }
        except Exception as e:
            logger.error(f"Ollama error: {e}")
        
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
    
    async def _generate_smart_suggestions(
        self, user_msg: str, bot_msg: str, emotion: str, profile: UserProfile, user_id: str
    ) -> List[str]:
        """スマート提案生成（v2強化版）"""
        
        # 秘書機能からプロアクティブ提案を取得
        mana_context = {
            'current_time': datetime.now(),
            'last_emotion': emotion,
            'tasks': [],  # 実際のタスクは別途取得
            'schedule': [],
            'recent_activity': user_msg
        }
        
        proactive_suggestions = await self.secretary.proactive_assistance(mana_context)
        
        # 上位3件を返す
        return [s['message'] for s in proactive_suggestions[:3]]


# グローバルクライアント
trinity_v2 = TrinityPremiumV2Client()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botスタート"""
    user = update.effective_user
    
    if ALLOWED_USERS and str(user.id) not in ALLOWED_USERS:
        await update.message.reply_text("⛔ このBotの使用は許可されていません。")
        return
    
    profile = trinity_v2.get_user_profile(str(user.id))
    greeting = profile.get_greeting()
    
    welcome_message = f"""
💎 **Trinity Secretary Bot PREMIUM v2**

{greeting}、{user.first_name}さん！
私はあなたの超強化秘書、Trinity v2です。✨

**🎯 v2新機能:**
✅ 🔍 統合検索（/search）
✅ 🖥️ システム状況把握（/system）
✅ 🤝 トリニティ達との記憶共有
✅ 🧠 強化版会話理解（指示語解決）
✅ 💼 高度秘書機能（先回り支援）

**💬 できること:**
- 自然な会話（感情理解・文脈把握）
- 全データ検索 (/search キーワード)
- システム監視 (/system)
- タスク管理 (/tasks)
- 会話統計 (/stats)

**🎯 今すぐ試せること:**
普通に話しかけてください！
「疲れた...」「それについて詳しく」「昨日の会話検索して」
"""
    
    keyboard = [
        [
            InlineKeyboardButton("💬 チャット", callback_data="chat"),
            InlineKeyboardButton("🔍 検索", callback_data="search")
        ],
        [
            InlineKeyboardButton("🖥️ システム", callback_data="system"),
            InlineKeyboardButton("📊 統計", callback_data="stats")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """メッセージ処理（Premium v2版）"""
    user_message = update.message.text
    user = update.effective_user
    user_id = str(user.id)
    
    await update.message.chat.send_action("typing")
    
    # Premium v2会話処理
    response = await trinity_v2.chat(user_message, user_id)
    
    # 応答送信
    bot_message = response['response']
    
    # 感情に応じた絵文字
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
        keyboard = [[InlineKeyboardButton(s[:30], callback_data=f"suggest_{i}")] 
                   for i, s in enumerate(suggestions)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("💡 もっとお手伝いできることは？", reply_markup=reply_markup)


async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """検索コマンド（ManaSearch Nexus統合版）"""
    query = ' '.join(context.args) if context.args else ''
    
    if not query:
        await update.message.reply_text(
            "🔍 **統合検索**\n\n"
            "使い方: `/search キーワード`\n\n"
            "**2つの検索エンジン:**\n"
            "📝 ローカル（会話・Obsidian・ログ）\n"
            "🌟 ManaSearch（AI+Web・最新情報）\n\n"
            "例: `/search AI技術トレンド 2025`",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        "🔍 検索中...\n\n"
        "📝 ローカルデータ検索中\n"
        "🌟 ManaSearch Nexus（AI+Web）検索中",
        parse_mode='Markdown'
    )
    await update.message.chat.send_action("typing")
    
    # 1. ローカル検索（Trinity）
    local_results = await trinity_v2.search_engine.universal_search(query)
    
    # 2. ManaSearch Nexus（AI + Web）
    manasearch_available = False
    manasearch_results = None
    
    try:
        from manasearch_helper import manasearch
        manasearch_results = await manasearch(query, use_web=True)
        manasearch_available = True
    except Exception as e:
        logger.warning(f"ManaSearch not available: {e}")
    
    # 結果整形
    response = f"🔍 **統合検索結果：「{query}」**\n\n"
    
    # ManaSearch結果
    if manasearch_available and manasearch_results:
        response += "**🌟 ManaSearch Nexus（AI+Web）**\n\n"
        
        summary = manasearch_results.get('summary', '')
        if summary:
            response += f"{summary[:400]}...\n\n"
        
        # Web検索結果
        web_results = manasearch_results.get('web_results', [])
        if web_results:
            response += "**🌐 最新Web情報:**\n"
            for i, result in enumerate(web_results[:3], 1):
                title = result.get('title', '')[:50]
                score = result.get('score', 0)
                response += f"{i}. {title}（関連性{score}%）\n"
            
            confidence = manasearch_results.get('confidence', 0)
            response += f"\n信頼スコア: {confidence}%\n\n"
    
    # ローカル検索結果
    if local_results['matches']:
        response += f"**📝 ローカルデータ:** {len(local_results['matches'])}件\n\n"
        
        for i, match in enumerate(local_results['matches'][:3], 1):
            match_type = match.get('type', 'unknown')
            
            if match_type == 'conversation':
                response += f"{i}. 会話: {match['content'][:60]}...\n"
            elif match_type == 'obsidian_note':
                response += f"{i}. Obsidian: {match['file']}\n"
            elif match_type == 'system_metric':
                response += f"{i}. メトリクス: CPU {match['cpu']:.1f}%\n"
    
    elif not manasearch_available:
        response += "**結果が見つかりませんでした**"
    
    await update.message.reply_text(response, parse_mode='Markdown')


async def handle_system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """システム状況確認"""
    await update.message.chat.send_action("typing")
    
    status = await trinity_v2.system_inspector.get_full_system_status()
    
    metrics = status['system_metrics']
    services = status['services']
    online = sum(1 for s in services.values() if s['status'] == 'online')
    total = len(services)
    
    response = f"""
🖥️ **ManaOS システム状況**

{status['overall_health']} **健全性: {status['health_score']}/100**

📊 **メトリクス**
├ CPU: {metrics.get('cpu_percent', 0)}%
├ RAM: {metrics.get('memory_percent', 0)}%
├ Disk: {metrics.get('disk_percent', 0)}%
└ Processes: {metrics.get('process_count', 0)}

🔧 **サービス:** {online}/{total} 稼働中

"""
    
    # 推奨事項
    if status['recommendations']:
        response += "**💡 推奨事項:**\n"
        for rec in status['recommendations'][:2]:
            response += f"  {rec}\n"
    
    await update.message.reply_text(response, parse_mode='Markdown')


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """会話統計表示"""
    user_id = str(update.effective_user.id)
    profile = trinity_v2.get_user_profile(user_id)
    conv_context = trinity_v2.get_conversation(user_id)
    
    message = f"""
📊 **あなたの会話統計**

**💬 総やり取り:** {profile.interaction_count}回
**🎨 スタイル:** {profile.conversation_style}
**😊 最後の感情:** {profile.last_emotion}
**🔄 会話ターン:** {len(conv_context.short_term)}

どんどん会話することで、私はあなたのことをもっと理解できます！✨
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def handle_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """リマインダーコマンド"""
    user_id = str(update.effective_user.id)
    
    if not context.args:
        # リマインダー一覧表示
        reminders = await trinity_v2.reminder_system.get_user_reminders(user_id)
        text = trinity_v2.reminder_system.format_reminder_list(reminders)
        await update.message.reply_text(text, parse_mode='Markdown')
        return
    
    # リマインダー作成
    text = ' '.join(context.args)
    parsed = trinity_v2.reminder_system.parse_reminder_request(text)
    
    if parsed:
        reminder = await trinity_v2.reminder_system.create_reminder(
            user_id=user_id,
            message=parsed['message'],
            trigger_time=parsed['trigger_time'],
            repeat=parsed.get('repeat')
        )
        
        trigger_str = parsed['trigger_time'].strftime('%Y-%m-%d %H:%M')
        repeat_str = " (繰り返し)" if parsed.get('repeat') else ""
        
        await update.message.reply_text(
            f"⏰ リマインダーを設定しました{repeat_str}\n\n"
            f"**{parsed['message']}**\n"
            f"📅 {trigger_str}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "⚠️ リマインダーの設定に失敗しました。\n\n"
            "**使い方:**\n"
            "`/remind 30分後にプレゼンの準備をリマインド`\n"
            "`/remind 明日10時に会議をリマインド`\n"
            "`/remind 毎日9時に日報をリマインド`",
            parse_mode='Markdown'
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """画像を受信して分析"""
    user_id = str(update.effective_user.id)
    
    await update.message.reply_text("📸 画像を分析しています...")
    await update.message.chat.send_action("typing")
    
    # 最大サイズの画像を取得
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    
    # 画像データをダウンロード
    image_bytes = await file.download_as_bytearray()
    
    # 画像分析
    result = await trinity_v2.image_understanding.analyze_image(
        bytes(image_bytes),
        mode='general'
    )
    
    # 結果送信
    response = f"📸 **画像分析結果**\n\n{result['analysis']}\n\n"
    response += f"_分析方法: {result['method']} (信頼度: {result['confidence']}%)_"
    
    await update.message.reply_text(response, parse_mode='Markdown')
    
    # タスク抽出
    tasks = trinity_v2.image_understanding.extract_tasks_from_analysis(result['analysis'])
    
    if tasks:
        task_text = "📋 **抽出されたタスク:**\n\n"
        for i, task in enumerate(tasks[:5], 1):
            task_text += f"{i}. {task}\n"
        
        keyboard = [[InlineKeyboardButton("タスクとして保存", callback_data="save_image_tasks")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(task_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # 提案生成
    suggestions = trinity_v2.image_understanding.generate_suggestions(result['analysis'])
    
    if suggestions:
        sug_keyboard = [[InlineKeyboardButton(s, callback_data=f"img_sug_{i}")] 
                       for i, s in enumerate(suggestions)]
        sug_markup = InlineKeyboardMarkup(sug_keyboard)
        
        await update.message.reply_text(
            "💡 **おすすめアクション:**",
            reply_markup=sug_markup
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """音声メッセージを処理"""
    user_id = str(update.effective_user.id)
    
    await update.message.reply_text("🎤 音声を認識しています...")
    await update.message.chat.send_action("typing")
    
    # 音声ファイルを取得
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    
    # 一時ファイルにダウンロード
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp_file:
        await file.download_to_drive(tmp_file.name)
        tmp_path = tmp_file.name
    
    try:
        # 音声認識
        result = await trinity_v2.voice_processing.transcribe_voice(tmp_path)
        
        if result.get('text'):
            text = result['text']
            
            # 認識結果を送信
            await update.message.reply_text(
                f"🎤 音声認識: 「{text}」\n\n処理中...",
                parse_mode='Markdown'
            )
            
            # コマンド抽出
            command = trinity_v2.voice_processing.extract_command(text)
            
            if command:
                # コマンドとして処理
                if command == 'search':
                    # 検索として処理
                    search_query = text.replace('検索', '').strip()
                    results = await trinity_v2.search_engine.universal_search(search_query)
                    
                    response = f"🔍 検索結果: {len(results['matches'])}件"
                    await update.message.reply_text(response)
                
                elif command == 'system':
                    # システム状況
                    status = await trinity_v2.system_inspector.get_full_system_status()
                    response = f"🖥️ システム健全性: {status['health_score']}/100"
                    await update.message.reply_text(response)
                
                else:
                    # 通常の会話として処理
                    response = await trinity_v2.chat(text, user_id)
                    await update.message.reply_text(response['response'])
            else:
                # 通常の会話として処理
                response = await trinity_v2.chat(text, user_id)
                await update.message.reply_text(response['response'])
        
        else:
            # 認識失敗
            error_msg = result.get('error', '音声認識に失敗しました')
            await update.message.reply_text(f"⚠️ {error_msg}")
    
    finally:
        # 一時ファイルを削除
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


async def handle_trinity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """トリニティ会議コマンド（Remi・Luna・Minaに質問）"""
    query = ' '.join(context.args) if context.args else ''
    user_id = str(update.effective_user.id)
    
    if not query:
        await update.message.reply_text(
            "🎯 **Trinity会議**\n\n"
            "トリニティ3人（Remi・Luna・Mina）に質問します\n\n"
            "使い方: `/trinity 質問内容`\n\n"
            "例: `/trinity 今日のタスクは？`\n"
            "例: `/trinity プロジェクトの進め方は？`",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        "🎯 Trinity会議を開催中...\n\n"
        "👑 Remi（司令官）に確認中\n"
        "💼 Luna（実務）に確認中\n"
        "📊 Mina（分析）に確認中",
        parse_mode='Markdown'
    )
    await update.message.chat.send_action("typing")
    
    # Trinity全員に質問
    result = await trinity_v2.manaos_bridge.ask_trinity(query, user_id)
    
    if result['success']:
        await update.message.reply_text(
            result['integrated_message'],
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "⚠️ Trinity会議を開催できませんでした。\n"
            "ManaOS v3が起動しているか確認してください。"
        )


async def handle_manaos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ManaOSコマンド（特定のアクターで処理）"""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "🤖 **ManaOS v3統合**\n\n"
            "使い方: `/manaos [アクター] [メッセージ]`\n\n"
            "**アクター:**\n"
            "• `remi` - 司令官（戦略的判断）\n"
            "• `luna` - 実務担当（実行重視）\n"
            "• `mina` - 分析担当（データ分析）\n\n"
            "例: `/manaos remi プロジェクトの優先順位は？`",
            parse_mode='Markdown'
        )
        return
    
    actor = context.args[0].lower()
    message = ' '.join(context.args[1:])
    user_id = str(update.effective_user.id)
    
    if actor not in ['remi', 'luna', 'mina']:
        await update.message.reply_text(
            "⚠️ アクターは `remi`, `luna`, `mina` のいずれかを指定してください"
        )
        return
    
    actor_names = {
        'remi': '👑 Remi（司令官）',
        'luna': '💼 Luna（実務）',
        'mina': '📊 Mina（分析）'
    }
    
    await update.message.reply_text(
        f"{actor_names[actor]} が処理中...",
        parse_mode='Markdown'
    )
    await update.message.chat.send_action("typing")
    
    # 指定アクターで処理
    result = await trinity_v2.manaos_bridge.process_with_manaos(message, user_id, actor)
    
    if result['success']:
        response = f"**{actor_names[actor]}**\n\n{result['message']}"
        await update.message.reply_text(response, parse_mode='Markdown')
    else:
        await update.message.reply_text(
            f"⚠️ {actor_names[actor]} との通信に失敗しました"
        )


async def handle_x280(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """X280操作コマンド"""
    if not context.args:
        await update.message.reply_text(
            "🖥️ **X280リモート操作**\n\n"
            "使い方: `/x280 コマンド`\n\n"
            "**利用可能なコマンド:**\n"
            "• `dir` - ディレクトリ一覧\n"
            "• `systeminfo` - システム情報\n"
            "• `tasklist` - プロセス一覧\n"
            "• `diskusage` - ディスク使用量\n\n"
            "**例:** `/x280 dir`",
            parse_mode='Markdown'
        )
        return
    
    await update.message.chat.send_action("typing")
    
    command = context.args[0]
    args = ' '.join(context.args[1:]) if len(context.args) > 1 else ""
    
    # 実行
    result = await trinity_v2.x280_control.execute_command(command, args)
    
    if result['success']:
        output = result['output']
        
        # 長すぎる場合は切り詰め
        if len(output) > 3000:
            output = output[:3000] + "\n\n... (以下省略)"
        
        await update.message.reply_text(
            f"🖥️ **X280実行結果**\n\n```\n{output}\n```",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"⚠️ X280実行失敗\n\n{result['output']}"
        )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ボタンコールバック"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(query.from_user.id)
    
    if data == "chat":
        await query.message.reply_text("💬 何でも聞いてください！")
    elif data == "search":
        await query.message.reply_text("🔍 検索: `/search キーワード`", parse_mode='Markdown')
    elif data == "system":
        await handle_system_status(update, context)
    elif data == "stats":
        await stats_command(update, context)
    elif data == "x280":
        await query.message.reply_text("🖥️ X280: `/x280 コマンド`", parse_mode='Markdown')
    
    # リマインダーボタン
    elif data.startswith("reminder_done_"):
        reminder_id = data.replace("reminder_done_", "")
        await trinity_v2.reminder_system.cancel_reminder(reminder_id)
        await query.message.edit_text("✅ リマインダーを完了しました！")
    
    elif data.startswith("reminder_snooze_"):
        reminder_id = data.replace("reminder_snooze_", "")
        await trinity_v2.reminder_system.snooze_reminder(reminder_id, minutes=5)
        await query.message.edit_text("⏰ 5分後に再度リマインドします")


def main():
    """Bot起動"""
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("⚠️  TELEGRAM_BOT_TOKEN環境変数を設定してください！")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # コマンドハンドラ
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", handle_search))
    application.add_handler(CommandHandler("system", handle_system_status))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("remind", handle_reminder))
    application.add_handler(CommandHandler("reminders", handle_reminder))
    application.add_handler(CommandHandler("trinity", handle_trinity))
    application.add_handler(CommandHandler("manaos", handle_manaos))
    application.add_handler(CommandHandler("x280", handle_x280))
    
    # メッセージハンドラ
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 画像ハンドラ
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # 音声ハンドラ
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    # ボタンハンドラ
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Bot起動
    print("💎 Trinity Secretary Bot PREMIUM v2 起動中...")
    print(f"   BOT TOKEN: {BOT_TOKEN[:10]}...")
    print("   🔍 統合検索: ON")
    print("   🖥️ システム把握: ON")
    print("   🤝 記憶共有: ON")
    print("   🧠 文脈理解: ON")
    print("   💼 秘書機能: ON")
    print("   ⏰ リマインダー: ON")
    print("   📸 画像理解: ON")
    print("   🎤 音声認識: ON")
    print("   🖥️ X280操作: ON")
    print("   🌟 ManaSearch統合: ON")
    print("   🤖 ManaOS v3統合: ON")
    print("   👑 Trinity会議: ON")
    print("   Ctrl+Cで停止")
    
    # リマインダーシステムにBotインスタンスを設定してから起動
    async def post_init(application):
        """アプリケーション起動後の初期化"""
        trinity_v2.reminder_system.bot = application.bot
        await trinity_v2.reminder_system.start()
    
    # 起動時に実行
    application.post_init = post_init
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

