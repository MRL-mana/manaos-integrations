#!/usr/bin/env python3
"""
NotebookLM風 統合システム - Slack Bot
"""

import os
import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler


# NotebookLM API
NOTEBOOKLM_API = "http://localhost:5022/api"

# Slack設定
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

# Slack App初期化
app = App(token=SLACK_BOT_TOKEN)


@app.command("/notebook-new")
def new_notebook_command(ack, respond, command):
    """ノートブック作成コマンド"""
    ack()
    
    args = command.get('text', '').strip()
    if not args:
        respond("❌ タイトルを指定してください\n例: /notebook-new AI研究ノート")
        return
    
    try:
        response = requests.post(
            f"{NOTEBOOKLM_API}/notebooks",
            json={"title": args},
            timeout=10
        )
        data = response.json()
        
        if data.get("success"):
            notebook = data["notebook"]
            respond(
                f"✅ ノートブック作成完了\n\n"
                f"📚 タイトル: {notebook['title']}\n"
                f"🆔 ID: {notebook['id']}"
            )
        else:
            respond(f"❌ 作成失敗: {data.get('error')}")
    
    except Exception as e:
        respond(f"❌ エラー: {str(e)}")


@app.command("/notebook-list")
def list_notebooks_command(ack, respond, command):
    """ノートブック一覧コマンド"""
    ack()
    
    try:
        response = requests.get(f"{NOTEBOOKLM_API}/notebooks", timeout=10)
        data = response.json()
        
        if data.get("success"):
            notebooks = data["notebooks"]
            
            if not notebooks:
                respond("📚 ノートブックがありません\n/notebook-new で作成してください")
                return
            
            text = "📚 ノートブック一覧\n\n"
            for nb in notebooks:
                text += f"📖 *{nb['title']}*\n"
                text += f"   ID: `{nb['id']}`\n"
                text += f"   ソース: {nb['source_count']}件, ノート: {nb['note_count']}件\n\n"
            
            respond(text)
        else:
            respond(f"❌ 取得失敗: {data.get('error')}")
    
    except Exception as e:
        respond(f"❌ エラー: {str(e)}")


@app.command("/notebook-add")
def add_source_command(ack, respond, command):
    """ソース追加コマンド"""
    ack()
    
    args = command.get('text', '').strip().split()
    if len(args) < 3:
        respond(
            "❌ 引数が不足しています\n"
            "例: /notebook-add nb_20241201_120000 web https://example.com"
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
            respond(
                f"✅ ソース追加完了\n\n"
                f"📝 タイトル: {source['title']}\n"
                f"🔗 タイプ: {source_type}\n"
                f"📊 文字数: {len(source.get('content', source.get('text', '')))}文字"
            )
        else:
            respond(f"❌ 追加失敗: {data.get('error')}")
    
    except Exception as e:
        respond(f"❌ エラー: {str(e)}")


@app.command("/notebook-chat")
def chat_command(ack, respond, command):
    """AI対話コマンド"""
    ack()
    
    args = command.get('text', '').strip().split(maxsplit=1)
    if len(args) < 2:
        respond(
            "❌ 引数が不足しています\n"
            "例: /notebook-chat nb_20241201_120000 この記事の要点は？"
        )
        return
    
    notebook_id = args[0]
    question = args[1]
    
    try:
        response = requests.post(
            f"{NOTEBOOKLM_API}/notebooks/{notebook_id}/chat",
            json={"question": question},
            timeout=60
        )
        data = response.json()
        
        if data.get("success"):
            answer = data["answer"]
            respond(f"💬 AI回答\n\n{answer}")
        else:
            respond(f"❌ 対話失敗: {data.get('error')}")
    
    except Exception as e:
        respond(f"❌ エラー: {str(e)}")


@app.command("/notebook-summary")
def summary_command(ack, respond, command):
    """サマリー生成コマンド"""
    ack()
    
    args = command.get('text', '').strip()
    if not args:
        respond(
            "❌ ノートブックIDを指定してください\n"
            "例: /notebook-summary nb_20241201_120000"
        )
        return
    
    notebook_id = args
    
    try:
        respond("⏳ サマリー生成中...")
        
        response = requests.post(
            f"{NOTEBOOKLM_API}/notebooks/{notebook_id}/summary",
            timeout=60
        )
        data = response.json()
        
        if data.get("success"):
            summary = data["summary"]
            respond(f"📊 サマリー\n\n{summary}")
        else:
            respond(f"❌ 生成失敗: {data.get('error')}")
    
    except Exception as e:
        respond(f"❌ エラー: {str(e)}")


@app.event("app_mention")
def handle_mention(event, say):
    """メンション処理"""
    text = event["text"]
    user = event["user"]
    
    # URL検出
    if "http" in text:
        say(f"<@{user}> 🔗 URLを検出しました！\n/notebook-add コマンドでノートブックに追加できます。")
    else:
        say(f"<@{user}> 📚 NotebookLM風 統合システムへようこそ！\n/notebook-new でノートブックを作成してください。")


@app.event("message")
def handle_message_events(body, logger):
    """メッセージイベント"""
    logger.info(body)


def main():
    """メイン"""
    print("=" * 60)
    print("💬 NotebookLM風 Slack Bot 起動")
    print("=" * 60)
    print("Ctrl+C で停止")
    print("=" * 60)
    
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()


if __name__ == "__main__":
    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
        print("❌ SLACK_BOT_TOKEN または SLACK_APP_TOKEN が設定されていません")
        exit(1)
    
    main()

