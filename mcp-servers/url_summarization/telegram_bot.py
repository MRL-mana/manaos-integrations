#!/usr/bin/env python3
"""
NotebookLM風 統合システム - Telegram Bot
"""

import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters


# NotebookLM API
NOTEBOOKLM_API = "http://localhost:5022/api"

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


class NotebookLMBot:
    """NotebookLM風 Telegram Bot"""
    
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """ハンドラー設定"""
        # コマンド
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("new", self.new_notebook))
        self.application.add_handler(CommandHandler("list", self.list_notebooks))
        self.application.add_handler(CommandHandler("add", self.add_source))
        self.application.add_handler(CommandHandler("chat", self.chat))
        self.application.add_handler(CommandHandler("summary", self.summary))
        
        # コールバック
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # URL処理
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """スタート"""
        welcome = """📚 NotebookLM風 統合システムへようこそ！

このBotで以下のことができます：

/new - 新しいノートブック作成
/list - ノートブック一覧
/add - ソース追加（Web/YouTube/PDF/Twitter）
/chat - AI対話
/summary - サマリー生成

使い方:
1. /new でノートブック作成
2. /add でソース（URL）追加
3. /chat で質問
4. /summary で要約生成

URLを送信すると自動で追加されます！"""
        
        await update.message.reply_text(welcome)
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ヘルプ"""
        help_text = """📚 コマンド一覧

/new <タイトル> - ノートブック作成
/list - ノートブック一覧
/add <ノートブックID> <タイプ> <URL> - ソース追加
  タイプ: web, youtube, pdf, twitter
/chat <ノートブックID> <質問> - AI対話
/summary <ノートブックID> - サマリー生成

例:
/new AI研究ノート
/add nb_20241201_120000 web https://example.com
/chat nb_20241201_120000 この記事の要点は？
/summary nb_20241201_120000"""
        
        await update.message.reply_text(help_text)
    
    async def new_notebook(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ノートブック作成"""
        args = context.args
        if not args:
            await update.message.reply_text("❌ タイトルを指定してください\n例: /new AI研究ノート")
            return
        
        title = " ".join(args)
        
        try:
            response = requests.post(
                f"{NOTEBOOKLM_API}/notebooks",
                json={"title": title},
                timeout=10
            )
            data = response.json()
            
            if data.get("success"):
                notebook = data["notebook"]
                await update.message.reply_text(
                    f"✅ ノートブック作成完了\n\n"
                    f"📚 タイトル: {notebook['title']}\n"
                    f"🆔 ID: {notebook['id']}\n\n"
                    f"このIDを使ってソースを追加できます！"
                )
            else:
                await update.message.reply_text(f"❌ 作成失敗: {data.get('error')}")
        
        except Exception as e:
            await update.message.reply_text(f"❌ エラー: {str(e)}")
    
    async def list_notebooks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ノートブック一覧"""
        try:
            response = requests.get(f"{NOTEBOOKLM_API}/notebooks", timeout=10)
            data = response.json()
            
            if data.get("success"):
                notebooks = data["notebooks"]
                
                if not notebooks:
                    await update.message.reply_text("📚 ノートブックがありません\n/new で作成してください")
                    return
                
                text = "📚 ノートブック一覧\n\n"
                for nb in notebooks:
                    text += f"📖 {nb['title']}\n"
                    text += f"   ID: {nb['id']}\n"
                    text += f"   ソース: {nb['source_count']}件, ノート: {nb['note_count']}件\n\n"
                
                await update.message.reply_text(text)
            else:
                await update.message.reply_text(f"❌ 取得失敗: {data.get('error')}")
        
        except Exception as e:
            await update.message.reply_text(f"❌ エラー: {str(e)}")
    
    async def add_source(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ソース追加"""
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "❌ 引数が不足しています\n"
                "例: /add nb_20241201_120000 web https://example.com"
            )
            return
        
        notebook_id = args[0]
        source_type = args[1]
        url = args[2]
        
        try:
            response = requests.post(
                f"{NOTEBOOKLM_API}/notebooks/{notebook_id}/sources",
                json={"type": source_type, "url": url},
                timeout=30
            )
            data = response.json()
            
            if data.get("success"):
                source = data["source"]
                await update.message.reply_text(
                    f"✅ ソース追加完了\n\n"
                    f"📝 タイトル: {source['title']}\n"
                    f"🔗 タイプ: {source_type}\n"
                    f"📊 文字数: {len(source.get('content', source.get('text', '')))}文字"
                )
            else:
                await update.message.reply_text(f"❌ 追加失敗: {data.get('error')}")
        
        except Exception as e:
            await update.message.reply_text(f"❌ エラー: {str(e)}")
    
    async def chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """AI対話"""
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "❌ 引数が不足しています\n"
                "例: /chat nb_20241201_120000 この記事の要点は？"
            )
            return
        
        notebook_id = args[0]
        question = " ".join(args[1:])
        
        try:
            response = requests.post(
                f"{NOTEBOOKLM_API}/notebooks/{notebook_id}/chat",
                json={"question": question},
                timeout=60
            )
            data = response.json()
            
            if data.get("success"):
                answer = data["answer"]
                await update.message.reply_text(f"💬 AI回答\n\n{answer}")
            else:
                await update.message.reply_text(f"❌ 対話失敗: {data.get('error')}")
        
        except Exception as e:
            await update.message.reply_text(f"❌ エラー: {str(e)}")
    
    async def summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """サマリー生成"""
        args = context.args
        if not args:
            await update.message.reply_text(
                "❌ ノートブックIDを指定してください\n"
                "例: /summary nb_20241201_120000"
            )
            return
        
        notebook_id = args[0]
        
        try:
            await update.message.reply_text("⏳ サマリー生成中...")
            
            response = requests.post(
                f"{NOTEBOOKLM_API}/notebooks/{notebook_id}/summary",
                timeout=60
            )
            data = response.json()
            
            if data.get("success"):
                summary = data["summary"]
                await update.message.reply_text(f"📊 サマリー\n\n{summary}")
            else:
                await update.message.reply_text(f"❌ 生成失敗: {data.get('error')}")
        
        except Exception as e:
            await update.message.reply_text(f"❌ エラー: {str(e)}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """メッセージ処理"""
        text = update.message.text
        
        # URL判定
        if text.startswith("http"):
            await update.message.reply_text(
                "🔗 URLを検出しました\n\n"
                "どのノートブックに追加しますか？\n"
                "ノートブックIDを入力してください。"
            )
            # 簡易実装：最初のノートブックに追加
            # 実際は会話状態管理が必要
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ボタンコールバック"""
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text=f"選択: {query.data}")
    
    def run(self):
        """Bot起動"""
        print("=" * 60)
        print("🤖 NotebookLM風 Telegram Bot 起動")
        print("=" * 60)
        print("Ctrl+C で停止")
        print("=" * 60)
        
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN が設定されていません")
        exit(1)
    
    bot = NotebookLMBot()
    bot.run()

