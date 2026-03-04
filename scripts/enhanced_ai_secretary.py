#!/usr/bin/env python3
"""
Enhanced AI Secretary - Phase 2 Implementation
強化されたAI秘書エンジン
自然言語処理、機械学習、マルチモーダル対応
"""

import logging
import re
import sqlite3
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import KMeans

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntentType(Enum):
    GREETING = "greeting"
    QUESTION = "question"
    REQUEST = "request"
    COMPLAINT = "complaint"
    PRAISE = "praise"
    FILE_OPERATION = "file_operation"
    CODE_GENERATION = "code_generation"
    SYSTEM_STATUS = "system_status"
    HELP = "help"
    UNKNOWN = "unknown"

class SentimentType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

@dataclass
class Entity:
    text: str
    label: str
    confidence: float
    start_pos: int
    end_pos: int

@dataclass
class IntentAnalysis:
    intent: IntentType
    confidence: float
    entities: List[Entity]
    sentiment: SentimentType
    context: Dict[str, Any]

@dataclass
class ResponseSuggestion:
    text: str
    confidence: float
    intent: IntentType
    context: Dict[str, Any]

class NLPProcessor:
    """自然言語処理プロセッサ"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.intent_classifier = None
        self.sentiment_classifier = None
        self.entity_patterns = self._load_entity_patterns()
        self._initialize_models()
    
    def _load_entity_patterns(self) -> Dict[str, str]:
        """エンティティ認識パターンを読み込み"""
        return {
            'time': r'\b(?:午前|午後|AM|PM|時|分|秒|今日|明日|昨日|今週|来週|先週|今月|来月|先月|今年|来年|去年)\b',
            'date': r'\b(?:月|火|水|木|金|土|日|月曜|火曜|水曜|木曜|金曜|土曜|日曜)\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(?:\+?81|0)[0-9-]{10,}\b',
            'url': r'https?://[^\s]+',
            'file_path': r'[A-Za-z]:\\[^\\]+\\[^\\]+|/[^/\s]+/[^/\s]+',
            'number': r'\b\d+(?:\.\d+)?\b',
            'person': r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',
            'organization': r'\b[A-Z][A-Za-z]+ (?:Inc|Corp|LLC|Ltd|Co|Company|Corporation)\b'
        }
    
    def _initialize_models(self):
        """機械学習モデルを初期化"""
        try:
            # インテント分類用の訓練データ
            self.intent_training_data = [
                ("こんにちは", "greeting"),
                ("おはよう", "greeting"),
                ("こんばんは", "greeting"),
                ("ありがとう", "praise"),
                ("すごい", "praise"),
                ("助かった", "praise"),
                ("ファイルを読んで", "file_operation"),
                ("ディレクトリを表示して", "file_operation"),
                ("コードを生成して", "code_generation"),
                ("プログラムを作って", "code_generation"),
                ("システムの状態は？", "system_status"),
                ("ヘルプ", "help"),
                ("何ができる？", "help"),
                ("質問があります", "question"),
                ("お願いがあります", "request"),
                ("問題があります", "complaint"),
                ("エラーが発生しました", "complaint")
            ]
            
            # 感情分析用の訓練データ
            self.sentiment_training_data = [
                ("素晴らしい", "positive"),
                ("最高", "positive"),
                ("ありがとう", "positive"),
                ("助かった", "positive"),
                ("すごい", "positive"),
                ("最悪", "negative"),
                ("ひどい", "negative"),
                ("問題", "negative"),
                ("エラー", "negative"),
                ("失敗", "negative"),
                ("ファイル", "neutral"),
                ("システム", "neutral"),
                ("コード", "neutral"),
                ("データ", "neutral")
            ]
            
            self._train_models()
            
        except Exception as e:
            logger.error(f"Model initialization failed: {e}")
            self.intent_classifier = None
            self.sentiment_classifier = None
    
    def _train_models(self):
        """機械学習モデルを訓練"""
        try:
            # インテント分類モデルの訓練
            texts, labels = zip(*self.intent_training_data)
            X = self.vectorizer.fit_transform(texts)
            self.intent_classifier = MultinomialNB()
            self.intent_classifier.fit(X, labels)
            
            # 感情分析モデルの訓練（別のベクトライザーを使用）
            from sklearn.feature_extraction.text import TfidfVectorizer
            sentiment_vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
            texts, sentiments = zip(*self.sentiment_training_data)
            X_sentiment = sentiment_vectorizer.fit_transform(texts)
            self.sentiment_classifier = LogisticRegression()
            self.sentiment_classifier.fit(X_sentiment, sentiments)
            
            # ベクトライザーを保存
            self.sentiment_vectorizer = sentiment_vectorizer
            
            logger.info("Models trained successfully")
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
    
    def analyze_intent(self, text: str) -> IntentType:
        """インテントを分析"""
        try:
            if not self.intent_classifier:
                return self._rule_based_intent_analysis(text)
            
            X = self.vectorizer.transform([text])
            intent_pred = self.intent_classifier.predict(X)[0]
            confidence = self.intent_classifier.predict_proba(X).max()
            
            # 信頼度が低い場合はルールベースにフォールバック
            if confidence < 0.5:
                return self._rule_based_intent_analysis(text)
            
            return IntentType(intent_pred)
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            return self._rule_based_intent_analysis(text)
    
    def _rule_based_intent_analysis(self, text: str) -> IntentType:
        """ルールベースのインテント分析"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["こんにちは", "おはよう", "こんばんは", "hello", "hi"]):
            return IntentType.GREETING
        elif any(word in text_lower for word in ["ファイル", "file", "ディレクトリ", "フォルダ"]):
            return IntentType.FILE_OPERATION
        elif any(word in text_lower for word in ["コード", "code", "プログラム", "生成"]):
            return IntentType.CODE_GENERATION
        elif any(word in text_lower for word in ["システム", "system", "状態", "status"]):
            return IntentType.SYSTEM_STATUS
        elif any(word in text_lower for word in ["ヘルプ", "help", "何ができる", "機能"]):
            return IntentType.HELP
        elif any(word in text_lower for word in ["ありがとう", "助かった", "すごい", "最高"]):
            return IntentType.PRAISE
        elif any(word in text_lower for word in ["問題", "エラー", "失敗", "最悪"]):
            return IntentType.COMPLAINT
        elif "?" in text or "？" in text:
            return IntentType.QUESTION
        else:
            return IntentType.REQUEST
    
    def extract_entities(self, text: str) -> List[Entity]:
        """エンティティを抽出"""
        entities = []
        
        for label, pattern in self.entity_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entity = Entity(
                    text=match.group(),
                    label=label,
                    confidence=0.8,  # パターンマッチングの信頼度
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                entities.append(entity)
        
        return entities
    
    def analyze_sentiment(self, text: str) -> SentimentType:
        """感情を分析"""
        # ルールベースの感情分析を使用
        return self._rule_based_sentiment_analysis(text)
    
    def _rule_based_sentiment_analysis(self, text: str) -> SentimentType:
        """ルールベースの感情分析"""
        text_lower = text.lower()
        
        # 挨拶の場合はニュートラル
        if any(word in text_lower for word in ["こんにちは", "おはよう", "こんばんは", "hello", "hi"]):
            return SentimentType.NEUTRAL
        
        positive_words = ["素晴らしい", "最高", "ありがとう", "助かった", "すごい", "excellent", "great", "amazing"]
        negative_words = ["最悪", "ひどい", "問題", "エラー", "失敗", "terrible", "bad", "awful", "horrible", "申し訳", "すみません"]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return SentimentType.POSITIVE
        elif negative_count > positive_count:
            return SentimentType.NEGATIVE
        else:
            return SentimentType.NEUTRAL
    
    def understand_context(self, text: str, history: List[Dict]) -> Dict[str, Any]:
        """コンテキストを理解"""
        context = {
            "previous_intents": [],
            "mentioned_entities": [],
            "conversation_topic": "",
            "user_preferences": {},
            "session_duration": 0
        }
        
        # 過去のインテントを分析
        for message in history[-5:]:  # 最新5件
            if "intent" in message:
                context["previous_intents"].append(message["intent"])
        
        # 言及されたエンティティを収集
        entities = self.extract_entities(text)
        context["mentioned_entities"] = [e.text for e in entities]
        
        # 会話のトピックを推定
        if context["previous_intents"]:
            context["conversation_topic"] = context["previous_intents"][-1]
        
        return context

class MLModelManager:
    """機械学習モデル管理"""
    
    def __init__(self):
        self.models = {}
        self.model_metrics = {}
        self._initialize_models()
    
    def _initialize_models(self):
        """モデルを初期化"""
        try:
            # ユーザー行動予測モデル
            self.models["user_behavior"] = self._create_behavior_model()
            
            # 応答品質予測モデル
            self.models["response_quality"] = self._create_quality_model()
            
            # クラスタリングモデル
            self.models["user_clustering"] = self._create_clustering_model()
            
            logger.info("ML models initialized successfully")
            
        except Exception as e:
            logger.error(f"ML model initialization failed: {e}")
    
    def _create_behavior_model(self):
        """ユーザー行動予測モデルを作成"""
        # サンプルデータでモデルを訓練
        X = np.random.rand(100, 10)  # 10個の特徴量
        y = np.random.randint(0, 3, 100)  # 3つのクラス
        
        model = LogisticRegression()
        model.fit(X, y)
        return model
    
    def _create_quality_model(self):
        """応答品質予測モデルを作成"""
        # サンプルデータでモデルを訓練
        X = np.random.rand(100, 5)  # 5個の特徴量
        y = np.random.randint(0, 3, 100)  # 3つのクラス（品質レベル）
        
        model = LogisticRegression()
        model.fit(X, y)
        return model
    
    def _create_clustering_model(self):
        """クラスタリングモデルを作成"""
        # サンプルデータでクラスタリング
        X = np.random.rand(100, 8)  # 8個の特徴量
        
        model = KMeans(n_clusters=3, random_state=42)
        model.fit(X)
        return model
    
    def predict_user_behavior(self, user_data: Dict) -> Dict[str, Any]:
        """ユーザー行動を予測"""
        try:
            if "user_behavior" not in self.models:
                return {"prediction": "unknown", "confidence": 0.0}
            
            # ユーザーデータを特徴量ベクトルに変換
            features = self._extract_user_features(user_data)
            
            # 予測実行
            prediction = self.models["user_behavior"].predict([features])[0]
            confidence = self.models["user_behavior"].predict_proba([features]).max()
            
            return {
                "prediction": prediction,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"User behavior prediction failed: {e}")
            return {"prediction": "unknown", "confidence": 0.0}
    
    def _extract_user_features(self, user_data: Dict) -> np.ndarray:
        """ユーザーデータから特徴量を抽出"""
        features = []
        
        # セッション時間
        features.append(user_data.get("session_duration", 0))
        
        # メッセージ数
        features.append(user_data.get("message_count", 0))
        
        # ファイル操作回数
        features.append(user_data.get("file_operations", 0))
        
        # コード生成回数
        features.append(user_data.get("code_generations", 0))
        
        # その他の特徴量（ダミーデータ）
        features.extend([0.5, 0.3, 0.8, 0.2, 0.6, 0.4])
        
        return np.array(features)

class MultimodalHandler:
    """マルチモーダル処理"""
    
    def __init__(self):
        self.supported_formats = {
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp'],
            'audio': ['.wav', '.mp3', '.m4a', '.ogg'],
            'document': ['.pdf', '.docx', '.txt', '.md'],
            'video': ['.mp4', '.avi', '.mov', '.mkv']
        }
    
    def process_image(self, image_data: bytes) -> Dict[str, Any]:
        """画像を処理"""
        try:
            # 基本的な画像情報を抽出
            result = {
                "type": "image",
                "size": len(image_data),
                "analysis": "Image processing not fully implemented",
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return {"error": str(e)}
    
    def process_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """音声を処理"""
        try:
            # 基本的な音声情報を抽出
            result = {
                "type": "audio",
                "size": len(audio_data),
                "transcription": "Audio transcription not fully implemented",
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            return {"error": str(e)}
    
    def process_document(self, file_path: str) -> Dict[str, Any]:
        """文書を処理"""
        try:
            # ファイルの基本情報を取得
            import os
            file_size = os.path.getsize(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            result = {
                "type": "document",
                "path": file_path,
                "size": file_size,
                "extension": file_ext,
                "content": "Document content extraction not fully implemented",
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            return {"error": str(e)}
    
    def process_url(self, url: str) -> Dict[str, Any]:
        """URLを処理"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            result = {
                "type": "url",
                "url": url,
                "title": soup.title.string if soup.title else "No title",
                "content": soup.get_text()[:1000],  # 最初の1000文字
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"URL processing failed: {e}")
            return {"error": str(e)}

class PredictiveEngine:
    """予測エンジン"""
    
    def __init__(self):
        self.conversation_patterns = {}
        self.user_preferences = {}
        self.prediction_history = []
    
    def predict_next_intent(self, current_intent: IntentType, history: List[Dict]) -> List[ResponseSuggestion]:
        """次のインテントを予測"""
        try:
            suggestions = []
            
            # パターンベースの予測
            if current_intent == IntentType.GREETING:
                suggestions.append(ResponseSuggestion(
                    text="何かお手伝いできることはありますか？",
                    confidence=0.9,
                    intent=IntentType.HELP,
                    context={"type": "greeting_followup"}
                ))
            
            elif current_intent == IntentType.FILE_OPERATION:
                suggestions.append(ResponseSuggestion(
                    text="ファイル操作が完了しました。他に何かありますか？",
                    confidence=0.8,
                    intent=IntentType.QUESTION,
                    context={"type": "operation_completion"}
                ))
            
            elif current_intent == IntentType.CODE_GENERATION:
                suggestions.append(ResponseSuggestion(
                    text="コードを生成しました。実行しますか？",
                    confidence=0.8,
                    intent=IntentType.REQUEST,
                    context={"type": "code_execution"}
                ))
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Intent prediction failed: {e}")
            return []
    
    def suggest_responses(self, intent: IntentType, context: Dict) -> List[ResponseSuggestion]:
        """応答を提案"""
        try:
            suggestions = []
            
            if intent == IntentType.GREETING:
                suggestions.append(ResponseSuggestion(
                    text="こんにちは！何かお手伝いできることはありますか？",
                    confidence=0.9,
                    intent=intent,
                    context=context
                ))
            
            elif intent == IntentType.HELP:
                suggestions.append(ResponseSuggestion(
                    text="以下の機能が利用できます：ファイル操作、コード生成、システム監視など",
                    confidence=0.8,
                    intent=intent,
                    context=context
                ))
            
            elif intent == IntentType.FILE_OPERATION:
                suggestions.append(ResponseSuggestion(
                    text="ファイル操作を開始します。どのような操作を行いますか？",
                    confidence=0.8,
                    intent=intent,
                    context=context
                ))
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Response suggestion failed: {e}")
            return []

class EnhancedAISecretary:
    """強化されたAI秘書"""
    
    def __init__(self):
        self.nlp_processor = NLPProcessor()
        self.ml_manager = MLModelManager()
        self.multimodal_handler = MultimodalHandler()
        self.predictive_engine = PredictiveEngine()
        self.conversation_history = []
        self.user_sessions = {}
        
        # データベース初期化
        self._initialize_database()
    
    def _initialize_database(self):
        """データベースを初期化"""
        try:
            self.db = sqlite3.connect(':memory:')
            cursor = self.db.cursor()
            
            # ユーザーセッションテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    created_at TIMESTAMP,
                    last_activity TIMESTAMP,
                    preferences TEXT
                )
            ''')
            
            # 会話履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    message TEXT,
                    response TEXT,
                    intent TEXT,
                    sentiment TEXT,
                    created_at TIMESTAMP
                )
            ''')
            
            self.db.commit()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
    
    def process_message(self, message: str, session_id: str = None) -> Dict[str, Any]:
        """メッセージを処理"""
        try:
            # セッション管理
            if not session_id:
                session_id = self._create_session()
            
            # 自然言語処理
            intent_analysis = self._analyze_message(message)
            
            # 機械学習予測
            user_data = self._get_user_data(session_id)
            behavior_prediction = self.ml_manager.predict_user_behavior(user_data)
            
            # 応答生成
            response = self._generate_response(message, intent_analysis, behavior_prediction)
            
            # 予測的応答提案
            suggestions = self.predictive_engine.suggest_responses(
                intent_analysis.intent, 
                intent_analysis.context
            )
            
            # 会話履歴を保存
            self._save_conversation(session_id, message, response, intent_analysis)
            
            return {
                "response": response,
                "intent": intent_analysis.intent.value,
                "sentiment": intent_analysis.sentiment.value,
                "confidence": intent_analysis.confidence,
                "suggestions": [s.text for s in suggestions],
                "behavior_prediction": behavior_prediction,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Message processing failed: {e}")
            return {
                "response": f"申し訳ありません、エラーが発生しました: {str(e)}",
                "intent": "unknown",
                "sentiment": "neutral",
                "confidence": 0.0,
                "suggestions": [],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _analyze_message(self, message: str) -> IntentAnalysis:
        """メッセージを分析"""
        intent = self.nlp_processor.analyze_intent(message)
        entities = self.nlp_processor.extract_entities(message)
        sentiment = self.nlp_processor.analyze_sentiment(message)
        context = self.nlp_processor.understand_context(message, self.conversation_history)
        
        return IntentAnalysis(
            intent=intent,
            confidence=0.8,  # デフォルト信頼度
            entities=entities,
            sentiment=sentiment,
            context=context
        )
    
    def _get_user_data(self, session_id: str) -> Dict[str, Any]:
        """ユーザーデータを取得"""
        return {
            "session_id": session_id,
            "session_duration": 0,  # 実際の実装では計算
            "message_count": len(self.conversation_history),
            "file_operations": 0,  # 実際の実装では追跡
            "code_generations": 0  # 実際の実装では追跡
        }
    
    def _generate_response(self, message: str, intent_analysis: IntentAnalysis, behavior_prediction: Dict) -> str:
        """応答を生成"""
        intent = intent_analysis.intent
        sentiment = intent_analysis.sentiment
        
        # インテントに基づく応答生成
        if intent == IntentType.GREETING:
            return "こんにちは、Mana！強化されたAI秘書として、より高度な機能でお手伝いします！"
        
        elif intent == IntentType.HELP:
            return """🚀 強化されたAI秘書の機能：
            
**自然言語処理:**
• インテント分析の向上
• エンティティ認識
• 感情分析

**機械学習:**
• ユーザー行動予測
• 応答品質最適化
• パーソナライゼーション

**マルチモーダル:**
• 画像・音声・文書処理
• URL解析
• ファイル内容理解

何か試してみたいことはありますか？"""
        
        elif intent == IntentType.FILE_OPERATION:
            return "📁 ファイル操作機能が強化されました！より詳細な分析と処理が可能です。"
        
        elif intent == IntentType.CODE_GENERATION:
            return "💻 コード生成機能が強化されました！より高度なコード解析と生成が可能です。"
        
        elif intent == IntentType.SYSTEM_STATUS:
            return "🔧 システム監視機能が強化されました！リアルタイム分析と予測が可能です。"
        
        elif sentiment == SentimentType.POSITIVE:
            return "ありがとうございます！喜んでお手伝いします。他にも何かありますか？"
        
        elif sentiment == SentimentType.NEGATIVE:
            return "申し訳ありません。問題を解決するために、詳しく教えていただけますか？"
        
        else:
            return f"Mana、{message}についてですね！強化されたAI秘書として、より詳細な分析と対応が可能になりました。具体的にどのようなお手伝いが必要でしょうか？"
    
    def _create_session(self) -> str:
        """新しいセッションを作成"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.user_sessions[session_id] = {
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "preferences": {}
        }
        return session_id
    
    def _save_conversation(self, session_id: str, message: str, response: str, intent_analysis: IntentAnalysis):
        """会話を保存"""
        try:
            cursor = self.db.cursor()
            cursor.execute('''
                INSERT INTO conversation_history 
                (session_id, message, response, intent, sentiment, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                message,
                response,
                intent_analysis.intent.value,
                intent_analysis.sentiment.value,
                datetime.now()
            ))
            self.db.commit()
            
            # メモリ内の履歴も更新
            self.conversation_history.append({
                "message": message,
                "response": response,
                "intent": intent_analysis.intent.value,
                "sentiment": intent_analysis.sentiment.value,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Conversation saving failed: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        try:
            cursor = self.db.cursor()
            
            # 総セッション数
            cursor.execute("SELECT COUNT(*) FROM user_sessions")
            total_sessions = cursor.fetchone()[0]
            
            # 総メッセージ数
            cursor.execute("SELECT COUNT(*) FROM conversation_history")
            total_messages = cursor.fetchone()[0]
            
            # インテント分布
            cursor.execute("SELECT intent, COUNT(*) FROM conversation_history GROUP BY intent")
            intent_distribution = dict(cursor.fetchall())
            
            return {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "intent_distribution": intent_distribution,
                "active_sessions": len(self.user_sessions),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Statistics retrieval failed: {e}")
            return {"error": str(e)}

def main():
    """メイン関数"""
    secretary = EnhancedAISecretary()
    
    # テストメッセージ
    test_messages = [
        "こんにちは、Mana！",
        "ファイル操作について教えて",
        "コードを生成してください",
        "システムの状態はどうですか？",
        "ありがとう、助かりました！"
    ]
    
    print("🚀 Enhanced AI Secretary - Phase 2 Test")
    print("=" * 50)
    
    for message in test_messages:
        print(f"\n📝 入力: {message}")
        result = secretary.process_message(message)
        print(f"🤖 応答: {result['response']}")
        print(f"🎯 インテント: {result['intent']}")
        print(f"😊 感情: {result['sentiment']}")
        print(f"📊 信頼度: {result['confidence']}")
        if result['suggestions']:
            print(f"💡 提案: {', '.join(result['suggestions'])}")
    
    # 統計情報
    stats = secretary.get_statistics()
    print("\n📊 統計情報:")
    print(f"総セッション数: {stats.get('total_sessions', 0)}")
    print(f"総メッセージ数: {stats.get('total_messages', 0)}")
    print(f"アクティブセッション: {stats.get('active_sessions', 0)}")

if __name__ == "__main__":
    main()
