#!/usr/bin/env python3
"""
Enhanced Conversation AI
会話機能を大幅に強化したAI秘書エンジン
"""

import logging
import sqlite3
import uuid
import random
from datetime import datetime
from typing import Dict, Any
from enum import Enum
from collections import deque
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntentType(Enum):
    GREETING = "greeting"
    QUESTION = "question"
    REQUEST = "request"
    COMPLAINT = "complaint"
    PRAISE = "praise"
    GOODBYE = "goodbye"
    HELP = "help"
    CHAT = "chat"
    EMOTIONAL_SUPPORT = "emotional_support"
    TECHNICAL_SUPPORT = "technical_support"
    SCHEDULING = "scheduling"
    REMINDER = "reminder"

class SentimentType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    EXCITED = "excited"
    WORRIED = "worried"
    CONFUSED = "confused"

class ConversationContext:
    """会話コンテキスト管理"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.conversation_history = deque(maxlen=20)
        self.user_preferences = {}
        self.current_topic = None
        self.emotional_state = SentimentType.NEUTRAL
        self.last_interaction = datetime.now()
        self.conversation_flow = []
        self.user_mood_history = deque(maxlen=10)
        self.interests = set()
        self.personality_traits = {}
    
    def add_message(self, message: str, response: str, intent: IntentType, sentiment: SentimentType):
        """メッセージを履歴に追加"""
        self.conversation_history.append({
            "timestamp": datetime.now(),
            "message": message,
            "response": response,
            "intent": intent.value,
            "sentiment": sentiment.value
        })
        self.last_interaction = datetime.now()
        self.user_mood_history.append(sentiment)
        self._update_emotional_state()
    
    def _update_emotional_state(self):
        """感情状態を更新"""
        if len(self.user_mood_history) >= 3:
            recent_sentiments = list(self.user_mood_history)[-3:]
            positive_count = sum(1 for s in recent_sentiments if s in [SentimentType.POSITIVE, SentimentType.EXCITED])
            negative_count = sum(1 for s in recent_sentiments if s in [SentimentType.NEGATIVE, SentimentType.WORRIED])
            
            if positive_count > negative_count:
                self.emotional_state = SentimentType.POSITIVE
            elif negative_count > positive_count:
                self.emotional_state = SentimentType.NEGATIVE
            else:
                self.emotional_state = SentimentType.NEUTRAL
    
    def get_context_summary(self) -> Dict[str, Any]:
        """コンテキストサマリーを取得"""
        return {
            "conversation_length": len(self.conversation_history),
            "current_topic": self.current_topic,
            "emotional_state": self.emotional_state.value,
            "last_interaction": self.last_interaction.isoformat(),
            "interests": list(self.interests),
            "personality_traits": self.personality_traits
        }

class EnhancedConversationAI:
    """強化された会話AI"""
    
    def __init__(self):
        self.db = sqlite3.connect(':memory:')
        self.contexts: Dict[str, ConversationContext] = {}
        self._initialize_database()
        self._initialize_models()
        self._load_conversation_templates()
        self._initialize_personality()
    
    def _initialize_database(self):
        """データベースを初期化"""
        cursor = self.db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                message TEXT,
                response TEXT,
                intent TEXT,
                sentiment TEXT,
                timestamp TIMESTAMP,
                quality_score REAL
            )
        ''')
        self.db.commit()
    
    def _initialize_models(self):
        """機械学習モデルを初期化"""
        try:
            # 意図分析用のベクトライザー
            self.intent_vectorizer = TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 2),
                stop_words=None
            )
            
            # 感情分析用のベクトライザー
            self.sentiment_vectorizer = TfidfVectorizer(
                max_features=500,
                ngram_range=(1, 3),
                stop_words=None
            )
            
            # 訓練データ
            self._train_models()
            
            logger.info("Enhanced conversation models initialized successfully")
            
        except Exception as e:
            logger.error(f"Model initialization failed: {e}")
            self.intent_vectorizer = None
            self.sentiment_vectorizer = None
            self.intent_model = None
            self.sentiment_model = None
    
    def _train_models(self):
        """モデルを訓練"""
        # 意図分析の訓練データ
        intent_data = [
            ("こんにちは", "greeting"),
            ("おはよう", "greeting"),
            ("こんばんは", "greeting"),
            ("hello", "greeting"),
            ("hi", "greeting"),
            ("ありがとう", "praise"),
            ("すごい", "praise"),
            ("最高", "praise"),
            ("助かった", "praise"),
            ("どうして", "question"),
            ("なぜ", "question"),
            ("何", "question"),
            ("どこ", "question"),
            ("いつ", "question"),
            ("誰", "question"),
            ("お願い", "request"),
            ("頼む", "request"),
            ("手伝って", "request"),
            ("ヘルプ", "help"),
            ("助けて", "help"),
            ("困った", "complaint"),
            ("問題", "complaint"),
            ("エラー", "complaint"),
            ("失敗", "complaint"),
            ("さようなら", "goodbye"),
            ("またね", "goodbye"),
            ("bye", "goodbye"),
            ("元気", "chat"),
            ("調子", "chat"),
            ("天気", "chat"),
            ("今日", "chat"),
            ("明日", "scheduling"),
            ("予定", "scheduling"),
            ("スケジュール", "scheduling"),
            ("思い出して", "reminder"),
            ("忘れないで", "reminder"),
            ("覚えて", "reminder"),
            ("心配", "emotional_support"),
            ("不安", "emotional_support"),
            ("悲しい", "emotional_support"),
            ("落ち込む", "emotional_support"),
            ("パソコン", "technical_support"),
            ("ソフトウェア", "technical_support"),
            ("バグ", "technical_support"),
            ("設定", "technical_support")
        ]
        
        # 感情分析の訓練データ
        sentiment_data = [
            ("素晴らしい", "positive"),
            ("最高", "positive"),
            ("ありがとう", "positive"),
            ("助かった", "positive"),
            ("すごい", "positive"),
            ("excellent", "positive"),
            ("great", "positive"),
            ("amazing", "positive"),
            ("wonderful", "positive"),
            ("最悪", "negative"),
            ("ひどい", "negative"),
            ("問題", "negative"),
            ("エラー", "negative"),
            ("失敗", "negative"),
            ("terrible", "negative"),
            ("bad", "negative"),
            ("awful", "negative"),
            ("horrible", "negative"),
            ("申し訳", "negative"),
            ("すみません", "negative"),
            ("こんにちは", "neutral"),
            ("おはよう", "neutral"),
            ("こんばんは", "neutral"),
            ("hello", "neutral"),
            ("hi", "neutral"),
            ("今日", "neutral"),
            ("明日", "neutral"),
            ("元気", "neutral"),
            ("調子", "neutral"),
            ("ワクワク", "excited"),
            ("興奮", "excited"),
            ("楽しい", "excited"),
            ("excited", "excited"),
            ("thrilled", "excited"),
            ("心配", "worried"),
            ("不安", "worried"),
            ("怖い", "worried"),
            ("worried", "worried"),
            ("anxious", "worried"),
            ("混乱", "confused"),
            ("分からない", "confused"),
            ("confused", "confused"),
            ("puzzled", "confused")
        ]
        
        # 意図分析モデルを訓練
        if intent_data:
            X_intent = [item[0] for item in intent_data]
            y_intent = [item[1] for item in intent_data]
            
            X_intent_vec = self.intent_vectorizer.fit_transform(X_intent)
            self.intent_model = MultinomialNB(alpha=0.1)
            self.intent_model.fit(X_intent_vec, y_intent)
        
        # 感情分析モデルを訓練
        if sentiment_data:
            X_sentiment = [item[0] for item in sentiment_data]
            y_sentiment = [item[1] for item in sentiment_data]
            
            X_sentiment_vec = self.sentiment_vectorizer.fit_transform(X_sentiment)
            self.sentiment_model = MultinomialNB(alpha=0.1)
            self.sentiment_model.fit(X_sentiment_vec, y_sentiment)
    
    def _load_conversation_templates(self):
        """会話テンプレートを読み込み"""
        self.conversation_templates = {
            IntentType.GREETING: {
                "morning": [
                    "おはようございます！今日も一日頑張りましょう！",
                    "おはよう！素敵な一日になりますように✨",
                    "おはようございます！何かお手伝いできることはありますか？",
                    "Good morning! How can I help you today?"
                ],
                "afternoon": [
                    "こんにちは！午後も頑張りましょう！",
                    "こんにちは！調子はいかがですか？",
                    "こんにちは！何かお困りのことはありませんか？",
                    "Good afternoon! How are you doing?"
                ],
                "evening": [
                    "こんばんは！お疲れ様です！",
                    "こんばんは！今日はどうでしたか？",
                    "こんばんは！ゆっくり休んでくださいね",
                    "Good evening! How was your day?"
                ],
                "general": [
                    "こんにちは！いらっしゃいませ！",
                    "Hello! Nice to meet you!",
                    "こんにちは！何かお手伝いできることはありますか？",
                    "Hi there! How can I assist you today?"
                ]
            },
            IntentType.QUESTION: {
                "general": [
                    "良い質問ですね！詳しく教えていただけますか？",
                    "なるほど、その件について説明いたします！",
                    "興味深い質問です！一緒に考えてみましょう",
                    "That's a great question! Let me help you with that."
                ],
                "technical": [
                    "技術的な質問ですね！詳しく調べてみます",
                    "その問題について調査いたします",
                    "技術的なサポートが必要ですね！",
                    "I'll help you with this technical issue."
                ]
            },
            IntentType.REQUEST: {
                "help": [
                    "もちろんお手伝いします！何をすればいいですか？",
                    "喜んでサポートいたします！",
                    "どのようなお手伝いが必要ですか？",
                    "I'd be happy to help! What do you need?"
                ],
                "information": [
                    "情報を調べてみますね！",
                    "その件について詳しく調べます",
                    "必要な情報を集めてみます",
                    "Let me gather that information for you."
                ]
            },
            IntentType.PRAISE: {
                "general": [
                    "ありがとうございます！嬉しいです！",
                    "お褒めいただき、ありがとうございます！",
                    "とても嬉しいです！",
                    "Thank you so much! That means a lot to me!"
                ]
            },
            IntentType.COMPLAINT: {
                "general": [
                    "申し訳ございません。改善いたします",
                    "ご不便をおかけして申し訳ありません",
                    "その問題について対処いたします",
                    "I apologize for the inconvenience. Let me fix that."
                ]
            },
            IntentType.EMOTIONAL_SUPPORT: {
                "worried": [
                    "大丈夫ですよ。一緒に考えましょう",
                    "心配いりません。サポートします",
                    "あなたは一人じゃありません。応援しています",
                    "Don't worry, I'm here to support you."
                ],
                "sad": [
                    "辛い時もありますね。話を聞かせてください",
                    "悲しい気持ち、分かります。一緒に乗り越えましょう",
                    "あなたの気持ちに寄り添います",
                    "I understand you're going through a tough time. I'm here for you."
                ]
            }
        }
    
    def _initialize_personality(self):
        """AIの人格を初期化"""
        self.personality = {
            "name": "Mana",
            "traits": {
                "helpful": 0.9,
                "friendly": 0.8,
                "professional": 0.7,
                "empathetic": 0.8,
                "curious": 0.6,
                "humorous": 0.4
            },
            "speaking_style": {
                "formality": 0.6,  # 0=カジュアル, 1=フォーマル
                "enthusiasm": 0.7,  # 0=控えめ, 1=熱心
                "empathy": 0.8,  # 0=冷静, 1=共感的
                "humor": 0.3  # 0=真面目, 1=ユーモア
            }
        }
    
    def get_context(self, user_id: str) -> ConversationContext:
        """ユーザーのコンテキストを取得"""
        if user_id not in self.contexts:
            self.contexts[user_id] = ConversationContext(user_id)
        return self.contexts[user_id]
    
    def analyze_intent(self, text: str) -> IntentType:
        """意図を分析"""
        try:
            if self.intent_model and self.intent_vectorizer:
                text_vec = self.intent_vectorizer.transform([text])
                intent_proba = self.intent_model.predict_proba(text_vec)[0]
                intent_classes = self.intent_model.classes_
                
                max_prob_idx = np.argmax(intent_proba)
                confidence = intent_proba[max_prob_idx]
                
                if confidence > 0.3:
                    return IntentType(intent_classes[max_prob_idx])
            
            # ルールベースのフォールバック
            return self._rule_based_intent_analysis(text)
            
        except Exception as e:
            logger.error(f"Intent analysis error: {e}")
            return self._rule_based_intent_analysis(text)
    
    def _rule_based_intent_analysis(self, text: str) -> IntentType:
        """ルールベースの意図分析"""
        text_lower = text.lower()
        
        # 挨拶
        if any(word in text_lower for word in ["こんにちは", "おはよう", "こんばんは", "hello", "hi", "hey"]):
            return IntentType.GREETING
        
        # 質問
        if any(word in text_lower for word in ["どうして", "なぜ", "何", "どこ", "いつ", "誰", "how", "what", "why", "where", "when", "who"]):
            return IntentType.QUESTION
        
        # 依頼
        if any(word in text_lower for word in ["お願い", "頼む", "手伝って", "help", "please"]):
            return IntentType.REQUEST
        
        # 褒め言葉
        if any(word in text_lower for word in ["ありがとう", "すごい", "最高", "助かった", "thank", "great", "amazing"]):
            return IntentType.PRAISE
        
        # 不満
        if any(word in text_lower for word in ["問題", "エラー", "失敗", "困った", "problem", "error", "issue"]):
            return IntentType.COMPLAINT
        
        # 別れ
        if any(word in text_lower for word in ["さようなら", "またね", "bye", "goodbye", "see you"]):
            return IntentType.GOODBYE
        
        # 感情的なサポート
        if any(word in text_lower for word in ["心配", "不安", "悲しい", "落ち込む", "worried", "sad", "anxious"]):
            return IntentType.EMOTIONAL_SUPPORT
        
        # 技術サポート
        if any(word in text_lower for word in ["パソコン", "ソフトウェア", "バグ", "設定", "computer", "software", "bug", "setting"]):
            return IntentType.TECHNICAL_SUPPORT
        
        # スケジューリング
        if any(word in text_lower for word in ["明日", "予定", "スケジュール", "tomorrow", "schedule", "plan"]):
            return IntentType.SCHEDULING
        
        # リマインダー
        if any(word in text_lower for word in ["思い出して", "忘れないで", "覚えて", "remind", "remember"]):
            return IntentType.REMINDER
        
        return IntentType.CHAT
    
    def analyze_sentiment(self, text: str) -> SentimentType:
        """感情を分析"""
        try:
            if self.sentiment_model and self.sentiment_vectorizer:
                text_vec = self.sentiment_vectorizer.transform([text])
                sentiment_proba = self.sentiment_model.predict_proba(text_vec)[0]
                sentiment_classes = self.sentiment_model.classes_
                
                max_prob_idx = np.argmax(sentiment_proba)
                confidence = sentiment_proba[max_prob_idx]
                
                if confidence > 0.3:
                    return SentimentType(sentiment_classes[max_prob_idx])
            
            # ルールベースのフォールバック
            return self._rule_based_sentiment_analysis(text)
            
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return self._rule_based_sentiment_analysis(text)
    
    def _rule_based_sentiment_analysis(self, text: str) -> SentimentType:
        """ルールベースの感情分析"""
        text_lower = text.lower()
        
        # 挨拶の場合はニュートラル
        if any(word in text_lower for word in ["こんにちは", "おはよう", "こんばんは", "hello", "hi"]):
            return SentimentType.NEUTRAL
        
        # ポジティブな言葉
        positive_words = ["素晴らしい", "最高", "ありがとう", "助かった", "すごい", "excellent", "great", "amazing", "wonderful", "ワクワク", "楽しい"]
        negative_words = ["最悪", "ひどい", "問題", "エラー", "失敗", "terrible", "bad", "awful", "horrible", "申し訳", "すみません", "心配", "不安", "悲しい"]
        excited_words = ["ワクワク", "興奮", "楽しい", "excited", "thrilled", "awesome"]
        worried_words = ["心配", "不安", "怖い", "worried", "anxious", "nervous"]
        confused_words = ["混乱", "分からない", "confused", "puzzled", "lost"]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        excited_count = sum(1 for word in excited_words if word in text_lower)
        worried_count = sum(1 for word in worried_words if word in text_lower)
        confused_count = sum(1 for word in confused_words if word in text_lower)
        
        if excited_count > 0:
            return SentimentType.EXCITED
        elif worried_count > 0:
            return SentimentType.WORRIED
        elif confused_count > 0:
            return SentimentType.CONFUSED
        elif positive_count > negative_count:
            return SentimentType.POSITIVE
        elif negative_count > positive_count:
            return SentimentType.NEGATIVE
        else:
            return SentimentType.NEUTRAL
    
    def generate_response(self, message: str, intent: IntentType, sentiment: SentimentType, context: ConversationContext) -> str:
        """応答を生成"""
        try:
            # 時間帯を取得
            current_hour = datetime.now().hour
            time_period = self._get_time_period(current_hour)
            
            # 基本応答を生成
            base_response = self._generate_base_response(intent, sentiment, time_period)
            
            # コンテキストに基づくカスタマイズ
            customized_response = self._customize_response(base_response, context, intent, sentiment)
            
            # 人格に基づく調整
            final_response = self._apply_personality(customized_response, sentiment)
            
            # コンテキストを更新
            context.add_message(message, final_response, intent, sentiment)
            
            # データベースに保存
            self._save_conversation(context.user_id, message, final_response, intent, sentiment)
            
            return final_response
            
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            return "申し訳ございません。少し混乱してしまいました。もう一度お話しください。"
    
    def _get_time_period(self, hour: int) -> str:
        """時間帯を取得"""
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        else:
            return "evening"
    
    def _generate_base_response(self, intent: IntentType, sentiment: SentimentType, time_period: str) -> str:
        """基本応答を生成"""
        templates = self.conversation_templates.get(intent, {})
        
        if intent == IntentType.GREETING:
            template_list = templates.get(time_period, templates.get("general", ["こんにちは！"]))
        elif intent == IntentType.EMOTIONAL_SUPPORT:
            template_list = templates.get(sentiment.value, templates.get("general", ["大丈夫ですよ。"]))
        else:
            template_list = templates.get("general", ["はい、分かりました。"])
        
        return random.choice(template_list)
    
    def _customize_response(self, response: str, context: ConversationContext, intent: IntentType, sentiment: SentimentType) -> str:
        """応答をカスタマイズ"""
        # 感情に基づく調整
        if sentiment == SentimentType.EXCITED:
            response = f"わあ！{response} 私もワクワクします！"
        elif sentiment == SentimentType.WORRIED:
            response = f"大丈夫ですよ。{response} 心配いりません。"
        elif sentiment == SentimentType.CONFUSED:
            response = f"分からない気持ち、よく分かります。{response} 一緒に整理しましょう。"
        
        # 会話履歴に基づく調整
        if len(context.conversation_history) > 0:
            last_message = context.conversation_history[-1]
            if last_message["intent"] == intent.value:
                response = f"先ほどの件についてですが、{response}"
        
        return response
    
    def _apply_personality(self, response: str, sentiment: SentimentType) -> str:
        """人格に基づいて応答を調整"""
        # ユーモアの追加
        if self.personality["speaking_style"]["humor"] > 0.5 and random.random() < 0.3:
            humor_phrases = ["😊", "✨", "💪", "🎉"]
            response += f" {random.choice(humor_phrases)}"
        
        # 共感の表現
        if self.personality["speaking_style"]["empathy"] > 0.7:
            if sentiment in [SentimentType.NEGATIVE, SentimentType.WORRIED]:
                response = f"お気持ち、よく分かります。{response}"
        
        # 熱意の表現
        if self.personality["speaking_style"]["enthusiasm"] > 0.7:
            if sentiment == SentimentType.POSITIVE:
                response = f"素晴らしいですね！{response}"
        
        return response
    
    def _save_conversation(self, user_id: str, message: str, response: str, intent: IntentType, sentiment: SentimentType):
        """会話をデータベースに保存"""
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                INSERT INTO conversations 
                (id, user_id, message, response, intent, sentiment, timestamp, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()),
                user_id,
                message,
                response,
                intent.value,
                sentiment.value,
                datetime.now(),
                0.8  # デフォルト品質スコア
            ))
            self.db.commit()
        except Exception as e:
            logger.error(f"Conversation save error: {e}")
    
    def get_conversation_analytics(self, user_id: str) -> Dict[str, Any]:
        """会話分析を取得"""
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                SELECT intent, sentiment, COUNT(*) as count
                FROM conversations 
                WHERE user_id = ?
                GROUP BY intent, sentiment
            ''', (user_id,))
            
            results = cursor.fetchall()
            analytics = {
                "total_conversations": len(results),
                "intent_distribution": {},
                "sentiment_distribution": {},
                "conversation_quality": 0.8
            }
            
            for intent, sentiment, count in results:
                if intent not in analytics["intent_distribution"]:
                    analytics["intent_distribution"][intent] = 0
                analytics["intent_distribution"][intent] += count
                
                if sentiment not in analytics["sentiment_distribution"]:
                    analytics["sentiment_distribution"][sentiment] = 0
                analytics["sentiment_distribution"][sentiment] += count
            
            return analytics
            
        except Exception as e:
            logger.error(f"Analytics error: {e}")
            return {}

def main():
    """メイン関数"""
    ai = EnhancedConversationAI()
    
    print("🤖 Enhanced Conversation AI - テスト")
    print("=" * 50)
    
    # テスト会話
    test_messages = [
        "こんにちは！",
        "今日は調子が悪いです",
        "ありがとうございます！",
        "パソコンが動かないんですが",
        "ワクワクします！",
        "心配で眠れません"
    ]
    
    user_id = "test_user"
    context = ai.get_context(user_id)
    
    for message in test_messages:
        print(f"\n👤 ユーザー: {message}")
        
        intent = ai.analyze_intent(message)
        sentiment = ai.analyze_sentiment(message)
        
        print(f"📊 意図: {intent.value}, 感情: {sentiment.value}")
        
        response = ai.generate_response(message, intent, sentiment, context)
        print(f"🤖 Mana: {response}")
    
    # 分析結果
    analytics = ai.get_conversation_analytics(user_id)
    print("\n📈 会話分析:")
    print(f"総会話数: {analytics['total_conversations']}")
    print(f"意図分布: {analytics['intent_distribution']}")
    print(f"感情分布: {analytics['sentiment_distribution']}")
    
    print("\n✅ Enhanced Conversation AI が準備完了しました！")

if __name__ == "__main__":
    main()
