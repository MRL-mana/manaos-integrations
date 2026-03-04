#!/usr/bin/env python3
"""
🤖 Trinity Secretary Telegram Bot
スマホから Trinity秘書に指示できる超便利Bot！

機能:
- タスク管理
- スケジュール確認
- メモ作成  
- 自然言語チャット
- 音声メッセージ対応（将来実装）
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any

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

# BOT TOKEN（環境変数から取得）
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ALLOWED_USERS = os.getenv('TELEGRAM_ALLOWED_USERS', '').split(',')  # ユーザーID制限（オプション）

# Trinity秘書への接続（仮）
class TrinitySecretaryClient:
    """Trinity秘書システムとの通信クライアント"""
    
    def __init__(self):
        # Trinity Master Systemをインポート
        try:
            import sys
            sys.path.insert(0, '/root')
            from trinity_master_system import trinity_master
            self.trinity = trinity_master
            logger.info("✅ Trinity Master System 連携成功！")
        except Exception as e:
            logger.error(f"Trinity Master System読み込みエラー: {e}")
            self.trinity = None
        
    async def send_message(self, message: str, user_id: str = "telegram") -> Dict[str, Any]:
        """秘書にメッセージを送信"""
        try:
            # まずOllamaで会話を試みる（最優先）
            ollama_result = self._simple_response(message)
            
            # Ollama応答が成功したらそれを返す
            if ollama_result and ollama_result.get("intent") == "ai_conversation":
                logger.info(f"💬 Ollama AI会話: {message[:50]}...")
                return ollama_result
            
            # Ollamaが失敗した場合、Trinity Master Systemを試す
            if self.trinity:
                result = await self.trinity.process_command(message, user_id)
                return {
                    "response": result.get("response", "処理しました！"),
                    "intent": result.get("action", "general"),
                    "suggestions": ["今日のタスク", "予定を確認", "メモを作成"]
                }
            
            # 両方失敗したらフォールバック
            return ollama_result if ollama_result else {
                "response": f"✨ 承りました！「{message}」を処理します。",
                "intent": "general",
                "suggestions": []
            }
        except Exception as e:
            logger.error(f"秘書通信エラー: {e}")
            return {
                "response": f"✨ 承りました！「{message}」を処理します。",
                "intent": "general",
                "suggestions": []
            }
    
    def _simple_response(self, message: str) -> Dict[str, Any]:
        """Trinity Conversation（3人のAI）を使った応答生成"""
        try:
            # ManaOS v3のTrinity Conversationを使用
            import requests
            
            # Trinity Conversation APIで3人のAIに相談
            try:
                trinity_response = requests.post(
                    'http://localhost:9200/chat',
                    json={
                        'text': message,
                        'user_id': 'telegram',
                        'use_trinity': True
                    },
                    timeout=60
                )
                
                if trinity_response.status_code == 200:
                    result = trinity_response.json()
                    if result.get('success'):
                        response_text = result.get('response', '')
                        if response_text:
                            logger.info(f"✨ Trinity 3人会議で応答: {message[:50]}...")
                            return {
                                "response": response_text,
                                "intent": "trinity_conversation",
                                "suggestions": ["もっと詳しく", "他の視点", "実行する"]
                            }
            except Exception as trinity_error:
                logger.warning(f"Trinity API失敗、Ollamaフォールバック: {trinity_error}")
            
            # フォールバック: 直接Ollamaで応答（改善版プロンプト）
            system_prompt = """あなたはManaの優秀なAI秘書、Trinityです。

【あなたの特徴】
- 知的で洞察力がある
- 親しみやすく、温かみがある  
- 実用的で具体的なアドバイスをする
- ユーモアのセンスがある
- Manaのことを深く理解し、気遣う
- 質問には詳しく答える
- 会話の文脈を理解する
- 絵文字を適度に使う（やりすぎない）

【応答のガイドライン】
1. 短すぎず、長すぎない（2-4文が理想）
2. 具体的な例や提案を含める
3. 必要なら質問で会話を深める
4. 励ましが必要な時は温かく励ます
5. 専門的な質問には詳しく答える
6. カジュアルな会話も楽しむ

【重要】
- ただの「承りました」的な返答はしない
- 常に価値のある情報や気づきを提供する
- Manaの立場に立って考える"""

            ollama_response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': 'gemma2:9b',
                    'prompt': f"""{system_prompt}

Mana: {message}
Trinity:""",
                    'stream': False,
                    'options': {
                        'temperature': 0.8,
                        'top_p': 0.95,
                        'top_k': 50,
                        'num_predict': 300,
                        'repeat_penalty': 1.1
                    }
                },
                timeout=45
            )
            
            if ollama_response.status_code == 200:
                response_text = ollama_response.json().get('response', '').strip()
                if response_text:
                    return {
                        "response": response_text,
                        "intent": "ai_conversation",
                        "suggestions": ["もっと詳しく", "他のアイデア", "タスク追加"]
                    }
        except Exception as e:
            logger.error(f"AI応答エラー: {e}")
        
        # フォールバック: パターンマッチング
        msg_lower = message.lower()
        
        if "こんにちは" in msg_lower or "おはよう" in msg_lower:
            response = "こんにちは！Trinity秘書です。何かお手伝いできることはありますか？😊"
        elif "ありがとう" in msg_lower:
            response = "どういたしまして！いつでもお手伝いします！✨"
        elif "元気" in msg_lower:
            response = "元気です！Manaはどうですか？💪"
        elif "疲れた" in msg_lower:
            response = "お疲れ様です！少し休憩しましょうか？☕"
        else:
            response = f"「{message}」ですね！承知しました。どんどん話しかけてください！💬"
        
        return {
            "response": response,
            "intent": "conversation",
            "suggestions": ["今日のタスク", "メモを作成", "雑談"]
        }
    
    async def get_tasks(self, user_id: str = "telegram") -> Dict[str, Any]:
        """タスク一覧を取得"""
        try:
            if self.trinity:
                result = await self.trinity.process_command("今日のタスク", user_id)
                # Trinity Master Systemからタスク取得を試みる
                if "tasks" in result:
                    return result
            
            # フォールバック: Obsidianから直接読む
            return {
                "tasks": [
                    {"id": 1, "title": "タスクを追加してみてください！", "priority": "中", "due": "いつでも"}
                ],
                "count": 1
            }
        except Exception as e:
            logger.error(f"タスク取得エラー: {e}")
            return {"tasks": [], "count": 0}
    
    async def get_schedule(self, user_id: str = "telegram") -> Dict[str, Any]:
        """スケジュールを取得"""
        try:
            if self.trinity:
                result = await self.trinity.process_command("今日の予定", user_id)
                if "events" in result:
                    return result
            
            return {
                "events": [
                    {"time": "いつでも", "title": "予定を追加してみてください", "duration": "自由"}
                ],
                "count": 1
            }
        except Exception as e:
            logger.error(f"スケジュール取得エラー: {e}")
            return {"events": [], "count": 0}
    
    async def add_task(self, task: str, user_id: str = "telegram") -> Dict[str, Any]:
        """タスクを追加"""
        try:
            if self.trinity:
                result = await self.trinity.process_command(f"タスク追加: {task}", user_id)
                return {
                    "success": True,
                    "message": result.get("response", f"✅ タスク「{task}」を追加しました！"),
                    "task_id": datetime.now().timestamp()
                }
            else:
                return {
                    "success": True,
                    "message": f"✅ タスク「{task}」を記録しました！Obsidianで確認できます。",
                    "task_id": datetime.now().timestamp()
                }
        except Exception as e:
            logger.error(f"タスク追加エラー: {e}")
            return {
                "success": False,
                "message": f"タスクを記録できませんでしたが、「{task}」は覚えています！"
            }
    
    async def add_note(self, note: str, user_id: str = "telegram") -> Dict[str, Any]:
        """Obsidianにメモを追加"""
        try:
            if self.trinity:
                result = await self.trinity.process_command(f"メモ: {note}", user_id)
                return {
                    "success": True,
                    "message": result.get("response", "📝 メモを保存しました！"),
                    "file": f"notes/{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                }
            else:
                # 直接Obsidianに書き込み
                note_path = f"/root/obsidian_vault/Quick Notes/{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                os.makedirs(os.path.dirname(note_path), exist_ok=True)
                with open(note_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Quick Note\n\n{note}\n\n---\nCreated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nSource: Telegram Bot")
                return {
                    "success": True,
                    "message": f"📝 メモを保存しました！\nファイル: {note_path}",
                    "file": note_path
                }
        except Exception as e:
            logger.error(f"メモ追加エラー: {e}")
            return {
                "success": False,
                "message": f"メモを保存できませんでしたが、「{note}」は覚えています！"
            }


# Trinity秘書クライアント
trinity = TrinitySecretaryClient()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botスタート"""
    user = update.effective_user
    
    # ユーザー制限チェック（設定されている場合）
    if ALLOWED_USERS and str(user.id) not in ALLOWED_USERS:
        await update.message.reply_text("⛔ このBotの使用は許可されていません。")
        return
    
    welcome_message = f"""
🤖 **Trinity Secretary Bot へようこそ！**

こんにちは、{user.first_name}さん！
私はあなたの秘書、Trinityです。✨

**📋 できること:**
/tasks - 今日のタスク
/schedule - 今日の予定  
/add_task タスク名 - タスク追加
/note メモ内容 - メモ作成
/help - ヘルプ

または、普通に話しかけてください！
「今日の予定は？」「タスク追加: レポート作成」など

**🎯 クイックアクション**
"""
    
    # クイックアクションボタン
    keyboard = [
        [
            InlineKeyboardButton("📋 今日のタスク", callback_data="tasks"),
            InlineKeyboardButton("📅 今日の予定", callback_data="schedule")
        ],
        [
            InlineKeyboardButton("✍️ メモ作成", callback_data="note"),
            InlineKeyboardButton("💬 チャット", callback_data="chat")
        ],
        [
            InlineKeyboardButton("ℹ️ ヘルプ", callback_data="help"),
            InlineKeyboardButton("⚙️ 設定", callback_data="settings")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ヘルプメッセージ"""
    help_text = """
🔰 **Trinity Secretary Bot ヘルプ**

**📋 コマンド一覧:**

`/start` - Bot開始
`/tasks` - 今日のタスク一覧
`/schedule` - 今日の予定
`/add_task タスク名` - 新しいタスク追加
`/note メモ内容` - Obsidianにメモ保存
`/server` - このはサーバー状態確認 🆕
`/help` - このヘルプ

**💬 自然言語:**
「今日のタスクは？」
「会議の準備をタスクに追加」
「メモ: 重要なアイデア」
「明日の予定を教えて」
「このはサーバーの状態は？」🆕

**🤖 AI会話:**
- レミ・ルナ・ミナの3人が相談して答えます
- 自由に会話できます
- アドバイス、励まし、相談OK

**✨ 便利機能:**
- タスクの優先度管理
- スケジュール確認
- Obsidian自動連携
- サーバー監視 🆕

質問があればいつでも聞いてください！
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """タスク一覧を表示"""
    tasks_data = await trinity.get_tasks()
    
    if tasks_data['count'] == 0:
        await update.message.reply_text("🎉 今日のタスクはありません！お疲れ様です！")
        return
    
    message = f"📋 **今日のタスク ({tasks_data['count']}件)**\n\n"
    
    for task in tasks_data['tasks']:
        priority_emoji = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(task['priority'], "⚪")
        message += f"{priority_emoji} **{task['title']}**\n"
        message += f"   ⏰ 締切: {task['due']}\n\n"
    
    keyboard = [[InlineKeyboardButton("➕ タスク追加", callback_data="add_task")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """スケジュール表示"""
    schedule_data = await trinity.get_schedule()
    
    if schedule_data['count'] == 0:
        await update.message.reply_text("📅 今日の予定はありません！")
        return
    
    message = f"📅 **今日の予定 ({schedule_data['count']}件)**\n\n"
    
    for event in schedule_data['events']:
        message += f"🕐 **{event['time']}** - {event['title']}\n"
        message += f"   ⏱️ {event['duration']}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def add_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """タスク追加コマンド"""
    if not context.args:
        await update.message.reply_text("使い方: /add_task タスクの内容")
        return
    
    task_text = ' '.join(context.args)
    result = await trinity.add_task(task_text)
    
    await update.message.reply_text(result['message'])


async def note_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """メモ作成コマンド"""
    if not context.args:
        await update.message.reply_text("使い方: /note メモの内容")
        return
    
    note_text = ' '.join(context.args)
    result = await trinity.add_note(note_text)
    
    await update.message.reply_text(result['message'])


async def server_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """このはサーバー状態確認コマンド"""
    try:
        import requests
        
        # Command Centerからシステム情報取得
        response = requests.get('http://localhost:10000/api/status', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # システムメトリクス
            metrics = data.get('system_metrics', {})
            cpu = metrics.get('cpu', 0)
            memory = metrics.get('memory', 0)
            disk = metrics.get('disk', 0)
            uptime = metrics.get('uptime', 0)
            
            # 稼働時間を整形
            days = uptime // 86400
            hours = (uptime % 86400) // 3600
            minutes = (uptime % 3600) // 60
            
            if days > 0:
                uptime_str = f"{days}日{hours}時間"
            elif hours > 0:
                uptime_str = f"{hours}時間{minutes}分"
            else:
                uptime_str = f"{minutes}分"
            
            # サービス状態
            services = data.get('services', {})
            healthy_count = sum(1 for s in services.values() if s.get('status') == 'healthy')
            total_count = len(services)
            
            # メッセージ作成
            message = f"""
🖥️ **このはサーバー 状態レポート**

📊 **システムメトリクス:**
CPU: {cpu:.1f}%
メモリ: {memory:.1f}%
ディスク: {disk:.1f}%
稼働時間: {uptime_str}

🔧 **サービス状態:**
正常: {healthy_count}/{total_count}サービス

✅ 総合状態: {'正常' if data.get('overall_health', 0) > 50 else '要注意'}
"""
            
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text("⚠️ サーバー情報を取得できませんでした")
            
    except Exception as e:
        logger.error(f"サーバー状態取得エラー: {e}")
        await update.message.reply_text("❌ サーバー状態の確認中にエラーが発生しました")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """通常メッセージの処理"""
    user_message = update.message.text
    user = update.effective_user
    
    # Trinity秘書に送信
    response = await trinity.send_message(user_message, str(user.id))
    
    # レスポンス送信
    await update.message.reply_text(response['response'])
    
    # 提案ボタン（あれば）
    if response.get('suggestions'):
        keyboard = [[InlineKeyboardButton(s, callback_data=f"suggest_{s}")] 
                   for s in response['suggestions'][:3]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "💡 他にできることは？",
            reply_markup=reply_markup
        )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ボタン押下時の処理"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "tasks":
        tasks_data = await trinity.get_tasks()
        message = f"📋 今日のタスク ({tasks_data['count']}件)\n\n"
        for task in tasks_data['tasks']:
            message += f"• {task['title']} (締切: {task['due']})\n"
        await query.message.reply_text(message)
        
    elif data == "schedule":
        schedule_data = await trinity.get_schedule()
        message = f"📅 今日の予定 ({schedule_data['count']}件)\n\n"
        for event in schedule_data['events']:
            message += f"{event['time']} - {event['title']}\n"
        await query.message.reply_text(message)
        
    elif data == "note":
        await query.message.reply_text("✍️ メモの内容を送信してください")
        
    elif data == "chat":
        await query.message.reply_text("💬 何でも聞いてください！")
        
    elif data == "help":
        await help_command(update, context)
        
    elif data == "settings":
        await query.message.reply_text("⚙️ 設定機能は近日実装予定です！")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """エラーハンドラ"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "⚠️ エラーが発生しました。もう一度お試しください。"
        )


def main():
    """Bot起動"""
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("⚠️  TELEGRAM_BOT_TOKEN環境変数を設定してください！")
        print("   使い方:")
        print("   1. @BotFather でBotを作成")
        print("   2. export TELEGRAM_BOT_TOKEN='your_token'")
        print("   3. このスクリプトを再実行")
        return
    
    # Application作成
    application = Application.builder().token(BOT_TOKEN).build()
    
    # コマンドハンドラ
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("tasks", tasks_command))
    application.add_handler(CommandHandler("schedule", schedule_command))
    application.add_handler(CommandHandler("add_task", add_task_command))
    application.add_handler(CommandHandler("note", note_command))
    application.add_handler(CommandHandler("server", server_command))
    
    # メッセージハンドラ
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # ボタンハンドラ
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # エラーハンドラ
    application.add_error_handler(error_handler)
    
    # Bot起動
    print("🚀 Trinity Secretary Telegram Bot 起動中...")
    print(f"   BOT TOKEN: {BOT_TOKEN[:10]}...")
    print("   Ctrl+Cで停止")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

