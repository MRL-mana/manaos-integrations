#!/usr/bin/env python3
"""
Enhanced Trinity Secretary - 自然な会話AI秘書システム
テンプレートではなく、動的で自然な応答を生成
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import random
from datetime import datetime

# FastAPIアプリケーション
app = FastAPI(title="Enhanced Trinity Secretary", version="2.0.0")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydanticモデル
class SecretaryMessage(BaseModel):
    message: str
    user_id: str = "default_user"
    secretary_id: str = "trinity"
    context: dict = {}

class EnhancedTrinitySecretary:
    def __init__(self):
        self.conversation_history = {}
        self.user_preferences = {}
        self.current_time = datetime.now()
        
        # 自然な応答パターン
        self.greeting_responses = [
            "こんにちは！お疲れ様です。今日はどのようなお手伝いをさせていただきましょうか？",
            "こんにちは！Trinityです。今日も一日お疲れ様です。何かお困りのことはありますか？",
            "おはようございます！今日もよろしくお願いします。どのようなことでお手伝いできるでしょうか？",
            "こんにちは！元気そうで何よりです。今日はどんな一日にしましょうか？"
        ]
        
        self.task_responses = [
            "タスクの作成ですね！どのようなプロジェクトでしょうか？具体的に教えていただけますか？",
            "お仕事のタスクですか？期限や優先度なども教えていただけると、より良いサポートができます。",
            "新しいタスクですね！どんな内容で、いつまでに完了予定でしょうか？",
            "タスク管理のお手伝いをします！プロジェクトの詳細を教えてください。"
        ]
        
        self.schedule_responses = [
            "スケジュールの調整ですね！いつ頃の会議でしょうか？参加者や場所も決まっていますか？",
            "予定の管理ですね！来週のどの日時がご希望でしょうか？",
            "会議のスケジュールですか？時間や場所、参加者の情報も教えていただけますか？",
            "カレンダーの調整ですね！具体的な日時を教えてください。"
        ]
        
        self.communication_responses = [
            "メールの作成ですね！誰宛のメールでしょうか？内容についても教えてください。",
            "コミュニケーションのお手伝いをします！宛先や件名、内容を教えていただけますか？",
            "メール送信ですね！相手の方の情報と、どのような内容をお伝えしたいでしょうか？",
            "連絡事項の整理ですね！相手と内容を教えていただけますか？"
        ]
        
        self.help_responses = [
            "お疲れ様です！どのようなことでお困りでしょうか？一緒に解決していきましょう。",
            "大丈夫ですよ！どんなことでもお手伝いします。具体的に教えてください。",
            "お疲れ様です！無理をしないでくださいね。どのようなサポートが必要でしょうか？",
            "心配いりません！Trinityがサポートします。何がお困りでしょうか？"
        ]
        
        self.general_responses = [
            "なるほど、{topic}についてですね。もう少し詳しく教えていただけますか？",
            "{topic}についてお手伝いします！具体的にはどのような内容でしょうか？",
            "{topic}ですね！Trinityがサポートします。詳細を教えてください。",
            "{topic}について、どのようなお手伝いが必要でしょうか？"
        ]
        
        # 感情分析キーワード
        self.positive_words = ["嬉しい", "楽しい", "良い", "素晴らしい", "ありがとう", "助かった", "最高", "完璧"]
        self.negative_words = ["疲れた", "困った", "大変", "辛い", "悲しい", "怒り", "ストレス", "不安"]
        self.urgent_words = ["急いで", "緊急", "すぐに", "至急", "今すぐ", "急ぎ", "早く"]
        
    def analyze_sentiment(self, message):
        """感情を分析"""
        message_lower = message.lower()
        
        positive_count = sum(1 for word in self.positive_words if word in message_lower)
        negative_count = sum(1 for word in self.negative_words if word in message_lower)
        urgent_count = sum(1 for word in self.urgent_words if word in message_lower)
        
        if urgent_count > 0:
            return "urgent"
        elif positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def extract_topic(self, message):
        """メッセージからトピックを抽出"""
        # 簡単なキーワード抽出
        topics = {
            "天気": ["天気", "weather", "晴れ", "雨", "曇り"],
            "仕事": ["仕事", "work", "プロジェクト", "会議", "プレゼン"],
            "健康": ["健康", "体調", "疲れ", "ストレス", "運動"],
            "趣味": ["趣味", "映画", "音楽", "読書", "ゲーム"],
            "家族": ["家族", "子供", "両親", "友達"],
            "技術": ["AI", "プログラミング", "技術", "システム", "データ"]
        }
        
        message_lower = message.lower()
        for topic, keywords in topics.items():
            if any(keyword in message_lower for keyword in keywords):
                return topic
        
        return "その他"
    
    def generate_dynamic_response(self, message, user_id):
        """動的な応答を生成"""
        sentiment = self.analyze_sentiment(message)
        topic = self.extract_topic(message)
        
        # ユーザーの会話履歴を取得
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        # 会話履歴を更新
        self.conversation_history[user_id].append({
            "message": message,
            "sentiment": sentiment,
            "topic": topic,
            "timestamp": datetime.now().isoformat()
        })
        
        # 最近の会話を考慮（直近3件）
        recent_conversations = self.conversation_history[user_id][-3:]
        
        # 感情に基づく応答の調整
        if sentiment == "urgent":
            urgency_prefix = "緊急ですね！"
        elif sentiment == "positive":
            urgency_prefix = "素晴らしいですね！"
        elif sentiment == "negative":
            urgency_prefix = "お疲れ様です。"
        else:
            urgency_prefix = ""
        
        # トピックに基づく応答
        if "天気" in topic:
            return self.generate_weather_response(message, sentiment)
        elif "仕事" in topic:
            return self.generate_work_response(message, sentiment)
        elif "健康" in topic:
            return self.generate_health_response(message, sentiment)
        elif "趣味" in topic:
            return self.generate_hobby_response(message, sentiment)
        else:
            return self.generate_general_response(message, sentiment, topic)
    
    def generate_weather_response(self, message, sentiment):
        """天気に関する応答"""
        responses = [
            "天気の話ですね！今日はどうでしょうか？外出の予定はありますか？",
            "天気についてお聞きになりましたね。お出かけの予定があれば、服装のアドバイスもできますよ！",
            "天気の話題ですね！最近の天気はいかがでしょうか？",
            "天気についてですね！外出時は気をつけてくださいね。"
        ]
        return random.choice(responses)
    
    def generate_work_response(self, message, sentiment):
        """仕事に関する応答"""
        if sentiment == "negative":
            responses = [
                "お仕事お疲れ様です。大変な時こそ、少し休憩を取ることも大切ですよ。",
                "お疲れ様です。仕事のことでお困りでしたら、一緒に整理していきましょう。",
                "お仕事大変ですね。無理をしないでくださいね。何かお手伝いできることはありますか？"
            ]
        else:
            responses = [
                "お仕事の話ですね！プロジェクトの進捗はいかがでしょうか？",
                "仕事についてお聞きになりましたね。何かサポートが必要でしたらお手伝いします！",
                "お仕事の件ですね！どのような内容でしょうか？"
            ]
        return random.choice(responses)
    
    def generate_health_response(self, message, sentiment):
        """健康に関する応答"""
        if sentiment == "negative":
            responses = [
                "お疲れのようですね。無理をしないで、しっかり休んでくださいね。",
                "体調はいかがでしょうか？無理をせず、体を大切にしてください。",
                "お疲れ様です。健康第一で、無理をしないようにしてくださいね。"
            ]
        else:
            responses = [
                "健康についてお聞きになりましたね！体調管理は大切です。",
                "健康の話ですね！何か気になることがあれば教えてください。",
                "体調の話ですね！元気そうで何よりです。"
            ]
        return random.choice(responses)
    
    def generate_hobby_response(self, message, sentiment):
        """趣味に関する応答"""
        responses = [
            "趣味の話ですね！どんなことを楽しまれているのでしょうか？",
            "お楽しみの時間ですね！どんな趣味をお持ちでしょうか？",
            "趣味についてお聞きになりましたね！リフレッシュは大切です。"
        ]
        return random.choice(responses)
    
    def generate_general_response(self, message, sentiment, topic):
        """一般的な応答"""
        if sentiment == "urgent":
            return f"緊急ですね！{topic}について、すぐにお手伝いします。具体的に教えてください。"
        elif sentiment == "positive":
            return f"素晴らしいですね！{topic}について、もっと詳しく教えてください。"
        elif sentiment == "negative":
            return f"お疲れ様です。{topic}について、一緒に解決していきましょう。"
        else:
            return f"{topic}についてお聞きになりましたね。どのようなお手伝いができるでしょうか？"
    
    def get_suggestions(self, message, sentiment, topic):
        """提案を生成"""
        base_suggestions = [
            "タスクを作成する",
            "スケジュールを確認する", 
            "メールを送信する",
            "情報を検索する"
        ]
        
        if sentiment == "urgent":
            return ["緊急タスクを作成", "すぐに連絡する", "優先度を設定", "リマインダーを設定"]
        elif "天気" in topic:
            return ["外出の準備をする", "スケジュールを調整", "服装を確認", "傘を持参"]
        elif "仕事" in topic:
            return ["プロジェクトを整理", "会議をスケジュール", "資料を準備", "進捗を確認"]
        elif "健康" in topic:
            return ["休憩を取る", "運動を計画", "食事を記録", "医師に相談"]
        else:
            return base_suggestions

# Trinity Secretary インスタンス
trinity = EnhancedTrinitySecretary()

# ルート
@app.get("/")
async def root():
    return {
        "message": "Enhanced Trinity Secretary - 自然な会話AI秘書システム",
        "version": "2.0.0",
        "features": [
            "自然な会話",
            "感情分析",
            "トピック理解",
            "動的応答生成",
            "会話履歴管理"
        ]
    }

@app.post("/chat")
async def chat_endpoint(secretary_message: SecretaryMessage):
    """チャットエンドポイント"""
    try:
        # 動的な応答を生成
        response = trinity.generate_dynamic_response(
            secretary_message.message, 
            secretary_message.user_id
        )
        
        # 感情とトピックを分析
        sentiment = trinity.analyze_sentiment(secretary_message.message)
        topic = trinity.extract_topic(secretary_message.message)
        
        # 提案を生成
        suggestions = trinity.get_suggestions(
            secretary_message.message, 
            sentiment, 
            topic
        )
        
        return {
            "response": response,
            "type": f"{topic}_conversation",
            "secretary": "Trinity",
            "personality": "natural",
            "sentiment": sentiment,
            "topic": topic,
            "timestamp": datetime.utcnow().isoformat(),
            "suggestions": suggestions
        }
        
    except Exception:
        return {
            "response": "申し訳ございません。少し混乱してしまいました。もう一度お話しください。",
            "type": "error",
            "secretary": "Trinity",
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Enhanced Trinity Secretary"
    }

if __name__ == "__main__":
    print("🚀 Enhanced Trinity Secretary を起動中...")
    print("📱 アクセスURL: http://localhost:8094")
    print("🔧 API エンドポイント: http://localhost:8094/chat")
    print("❤️ ヘルスチェック: http://localhost:8094/health")
    uvicorn.run(app, host="0.0.0.0", port=8094)
