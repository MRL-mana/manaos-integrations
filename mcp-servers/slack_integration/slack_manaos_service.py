#!/usr/bin/env python3
"""
Slack統合サービス（ManaOS専用）
チャンネル別通知・スレッド返信・インタラクティブメッセージ
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ディレクトリ設定（Windows/Linux 共通）
WORK_DIR = Path(os.environ.get("SLACK_WORK_DIR", str(Path(__file__).parent)))
LOGS_DIR = WORK_DIR / "logs"
CONFIG_DIR = WORK_DIR / "config"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Slack設定（環境変数 or 設定ファイル）
SLACK_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
if not SLACK_TOKEN:
    token_file = CONFIG_DIR / "slack_token.txt"
    if token_file.exists():
        SLACK_TOKEN = token_file.read_text().strip()

# デフォルトチャンネル設定
DEFAULT_CHANNELS = {
    "alerts": "alerts",      # アラート用
    "logs": "logs",          # ログ用
    "reports": "reports",    # レポート用
    "general": "general"     # 一般
}


def log(message):
    """ログ記録"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    
    log_file = LOGS_DIR / f"slack_{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_message + "\n")


def send_slack_message(channel, text, thread_ts=None, blocks=None):
    """
    Slackメッセージ送信
    
    Args:
        channel: チャンネル名またはID
        text: メッセージテキスト
        thread_ts: スレッドタイムスタンプ（返信する場合）
        blocks: Block Kit（インタラクティブメッセージ）
    """
    if not SLACK_TOKEN:
        log("❌ Slackトークン未設定")
        return {"success": False, "error": "トークン未設定"}
    
    try:
        payload = {
            "channel": channel,
            "text": text
        }
        
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        if blocks:
            payload["blocks"] = blocks
        
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {SLACK_TOKEN}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=10
        )
        
        result = response.json()
        
        if result.get("ok"):
            log(f"✅ Slack送信成功: #{channel}")
            return {
                "success": True,
                "channel": channel,
                "ts": result.get("ts"),
                "message": text[:50]
            }
        else:
            log(f"❌ Slack送信失敗: {result.get('error')}")
            return {"success": False, "error": result.get("error")}
    
    except Exception as e:
        log(f"❌ Slack送信エラー: {e}")
        return {"success": False, "error": str(e)}


def create_interactive_message(title, message, buttons):
    """
    インタラクティブメッセージ作成（Block Kit）
    
    Args:
        title: タイトル
        message: メッセージ本文
        buttons: [{"text": "承認", "value": "approve", "style": "primary"}, ...]
    """
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": title
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message
            }
        }
    ]
    
    if buttons:
        button_elements = []
        for btn in buttons:
            button_element = {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": btn["text"]
                },
                "value": btn.get("value", btn["text"]),
                "action_id": f"button_{btn.get('value', btn['text'])}"
            }
            
            # styleがある場合のみ追加（Noneを避ける）
            if btn.get("style"):
                button_element["style"] = btn["style"]
            
            button_elements.append(button_element)
        
        blocks.append({
            "type": "actions",
            "elements": button_elements
        })
    
    return blocks


# ===== API エンドポイント =====

@app.route('/health')
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "service": "Slack ManaOS Integration",
        "token_configured": SLACK_TOKEN is not None,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/send', methods=['POST'])
def send_message():
    """メッセージ送信"""
    try:
        data = request.json
        channel = data.get('channel', 'general')
        text = data.get('text', '')
        thread_ts = data.get('thread_ts')
        
        result = send_slack_message(channel, text, thread_ts)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/send/alert', methods=['POST'])
def send_alert():
    """アラート送信（#alertsチャンネル）"""
    try:
        data = request.json
        level = data.get('level', 'info')
        title = data.get('title', 'Alert')
        message = data.get('message', '')
        
        icon_map = {
            'info': ':information_source:',
            'warning': ':warning:',
            'error': ':x:',
            'critical': ':rotating_light:'
        }
        
        icon = icon_map.get(level, ':bell:')
        
        text = f"{icon} *{level.upper()}: {title}*\n\n{message}\n\n_Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
        
        result = send_slack_message(DEFAULT_CHANNELS.get('alerts', 'alerts'), text)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/send/log', methods=['POST'])
def send_log():
    """ログ送信（#logsチャンネル）"""
    try:
        data = request.json
        log_level = data.get('level', 'INFO')
        source = data.get('source', 'ManaOS')
        message = data.get('message', '')
        
        text = f"`[{log_level}]` *{source}*\n```{message}```"
        
        result = send_slack_message(DEFAULT_CHANNELS.get('logs', 'logs'), text)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/send/report', methods=['POST'])
def send_report():
    """レポート送信（#reportsチャンネル）"""
    try:
        data = request.json
        title = data.get('title', 'Report')
        content = data.get('content', '')
        
        text = f":bar_chart: *{title}*\n\n{content}\n\n_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
        
        result = send_slack_message(DEFAULT_CHANNELS.get('reports', 'reports'), text)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/send/interactive', methods=['POST'])
def send_interactive():
    """インタラクティブメッセージ送信"""
    try:
        data = request.json
        channel = data.get('channel', 'general')
        title = data.get('title', '')
        message = data.get('message', '')
        buttons = data.get('buttons', [])
        
        blocks = create_interactive_message(title, message, buttons)
        
        result = send_slack_message(channel, message, blocks=blocks)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/send/manaos_event', methods=['POST'])
def send_manaos_event():
    """ManaOSイベント通知（チャンネル自動振り分け）"""
    try:
        data = request.json
        event_type = data.get('type', 'info')  # success, error, warning, task, etc.
        title = data.get('title', 'ManaOS Event')
        content = data.get('content', '')
        
        # イベントタイプによってチャンネル振り分け
        channel_map = {
            'error': 'alerts',
            'critical': 'alerts',
            'warning': 'alerts',
            'success': 'general',
            'task': 'reports',
            'backup': 'reports',
            'log': 'logs'
        }
        
        channel = channel_map.get(event_type, 'general')
        
        icon_map = {
            'success': ':white_check_mark:',
            'error': ':x:',
            'warning': ':warning:',
            'info': ':information_source:',
            'task': ':clipboard:',
            'backup': ':floppy_disk:'
        }
        
        icon = icon_map.get(event_type, ':robot_face:')
        
        text = f"{icon} *{title}*\n\n{content}\n\n_Time: {datetime.now().strftime('%H:%M:%S')}_"
        
        result = send_slack_message(channel, text)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/slack/commands', methods=['POST'])
def handle_slash_command():
    """Slackスラッシュコマンド処理 (/manaos)"""
    try:
        command = request.form.get('command')
        text = request.form.get('text', '')
        user_name = request.form.get('user_name')
        channel_id = request.form.get('channel_id')
        
        log(f"⚡ コマンド受信: {command} {text} from @{user_name}")
        
        if command == '/manaos':
            response = handle_manaos_command(text, user_name, channel_id)  # type: ignore
            return jsonify(response)
        
        return jsonify({
            "response_type": "ephemeral",
            "text": "❌ 未知のコマンドです"
        })
    
    except Exception as e:
        log(f"❌ コマンド処理エラー: {e}")
        return jsonify({
            "response_type": "ephemeral",
            "text": f"エラー: {str(e)}"
        }), 500


def handle_manaos_command(text: str, user: str, channel: str) -> dict:
    """
    /manaos コマンドのサブコマンド処理
    
    使用例:
      /manaos status - システム状態確認
      /manaos help - ヘルプ表示
      /manaos run <text> - Orchestrator実行
    """
    
    args = text.strip().split() if text else []
    subcommand = args[0] if args else 'help'
    
    if subcommand == 'status':
        # システムステータス表示
        return {
            "response_type": "in_channel",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🖥️ ManaOS Status"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "✅ *Orchestrator*: Running\n✅ *Trinity*: Active\n✅ *Slack Integration*: Connected"
                    }
                }
            ]
        }
    
    elif subcommand == 'help':
        # ヘルプ表示
        return {
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📚 ManaOS Commands"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "*使用可能なコマンド:*\n\n"
                            "• `/manaos status` - システム状態確認\n"
                            "• `/manaos run <text>` - Orchestrator実行\n"
                            "• `/manaos services` - サービス一覧\n"
                            "• `/manaos logs` - 最新ログ表示\n"
                            "• `/manaos help` - このヘルプを表示"
                        )
                    }
                }
            ]
        }
    
    elif subcommand == 'run':
        # Orchestrator実行
        query = ' '.join(args[1:]) if len(args) > 1 else ''
        
        if not query:
            return {
                "response_type": "ephemeral",
                "text": "❌ 実行するテキストを指定してください\n例: `/manaos run 今日の予定を教えて`"
            }
        
        # 実行中メッセージ
        return {
            "response_type": "in_channel",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🤖 実行中: *{query}*\n\n_@{user}さんからのリクエスト_"
                    }
                }
            ]
        }
        
        # TODO: 実際のOrchestrator呼び出しはここに実装
        # result = requests.post('http://localhost:8080/v3/run', json={'text': query})
    
    elif subcommand == 'services':
        # サービス一覧
        return {
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "*🚀 ManaOS Services*\n\n"
                            "🟢 Orchestrator (port 8080)\n"
                            "🟢 Trinity Secretary (port 8000)\n"
                            "🟢 AI Learning System (port 3000)\n"
                            "🟢 Slack Integration (port 5020)\n"
                            "🟢 Screen Sharing (port 5008)"
                        )
                    }
                }
            ]
        }
    
    elif subcommand == 'logs':
        # ログ表示（簡易版）
        return {
            "response_type": "ephemeral",
            "text": "📋 最新ログ:\n```\n[12:34:56] Orchestrator started\n[12:35:10] Intent detected: get_calendar\n[12:35:12] Execution success\n```"
        }
    
    else:
        return {
            "response_type": "ephemeral",
            "text": f"❌ 未知のサブコマンド: `{subcommand}`\n`/manaos help` でヘルプを表示"
        }


@app.route('/slack/interactions', methods=['POST'])
def handle_interactions():
    """Slackインタラクション処理（ボタンクリック等）"""
    try:
        # Slackはapplication/x-www-form-urlencodedで送信
        payload_str = request.form.get('payload')
        if not payload_str:
            return jsonify({"error": "No payload"}), 400
        
        payload = json.loads(payload_str)
        
        # インタラクションタイプ
        interaction_type = payload.get('type')
        user = payload.get('user', {})
        actions = payload.get('actions', [])
        
        log(f"📱 インタラクション受信: type={interaction_type}, user={user.get('name')}")
        
        if interaction_type == 'block_actions' and actions:
            action = actions[0]
            action_id = action.get('action_id')
            value = action.get('value')
            
            log(f"🔘 ボタンクリック: {action_id} = {value}")
            
            # アクション別処理
            response_text = handle_button_action(value, user.get('name'))
            
            # 元のメッセージに返信
            channel = payload.get('container', {}).get('channel_id')
            thread_ts = payload.get('container', {}).get('message_ts')
            
            if channel and thread_ts:
                send_slack_message(
                    channel,
                    response_text,
                    thread_ts=thread_ts
                )
            
            # Slackに即座に応答（200 OK）
            return jsonify({
                "response_type": "in_channel",
                "text": f"✅ 処理中: {value}"
            })
        
        return jsonify({"ok": True})
    
    except Exception as e:
        log(f"❌ インタラクション処理エラー: {e}")
        return jsonify({"error": str(e)}), 500


def handle_button_action(action_value, username):
    """
    ボタンアクション処理
    
    Args:
        action_value: ボタンのvalue
        username: クリックしたユーザー名
    
    Returns:
        応答メッセージ
    """
    action_responses = {
        'approve': f'✅ @{username}さんが承認しました！\n処理を開始します...',
        'cancel': f'❌ @{username}さんがキャンセルしました。',
        'details': '📋 詳細情報を表示します...',
        'download_pdf': '📥 PDFレポートを生成中...',
        'view_report': '📊 レポート画面を開きます...',
        'postpone': f'⏸️ @{username}さんが延期を選択しました。',
        'a100': '🎮 A100 GPUを割り当てます...',
        '4090': '🎮 RTX 4090を割り当てます...',
    }
    
    return action_responses.get(
        action_value,
        f'🤖 アクション「{action_value}」を@{username}さんが実行しました。'
    )


@app.route('/send/rich', methods=['POST'])
def send_rich_message():
    """リッチメッセージ送信（画像・フィールド・divider対応）"""
    try:
        data = request.json
        channel = data.get('channel', 'general')
        title = data.get('title', '')
        description = data.get('description', '')
        fields = data.get('fields', [])  # [{"title": "CPU", "value": "42%", "short": true}, ...]
        image_url = data.get('image_url')
        thumbnail_url = data.get('thumbnail_url')
        footer = data.get('footer')
        color = data.get('color', '#36a64f')  # good, warning, danger or hex
        
        blocks = []
        
        # ヘッダー
        if title:
            blocks.append({
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title
                }
            })
        
        # 説明文 + サムネイル
        if description:
            section = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": description
                }
            }
            if thumbnail_url:
                section["accessory"] = {
                    "type": "image",
                    "image_url": thumbnail_url,
                    "alt_text": "thumbnail"
                }
            blocks.append(section)
        
        # Divider
        if title or description:
            blocks.append({"type": "divider"})
        
        # フィールド（2列レイアウト）
        if fields:
            field_objects = []
            for field in fields:
                field_objects.append({
                    "type": "mrkdwn",
                    "text": f"*{field.get('title')}*\n{field.get('value')}"
                })
            
            blocks.append({
                "type": "section",
                "fields": field_objects
            })
        
        # 画像（大きく表示）
        if image_url:
            blocks.append({
                "type": "image",
                "image_url": image_url,
                "alt_text": "image"
            })
        
        # フッター
        if footer:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": footer
                    }
                ]
            })
        
        fallback_text = title or description or "Rich message"
        result = send_slack_message(channel, fallback_text, blocks=blocks)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/slack/webhook', methods=['POST'])
def slack_webhook():
    """Slack Incoming Webhook（汎用 – POST text/user/channel）"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        text = data.get("text", "")
        user = data.get("user", "unknown")
        channel = data.get("channel", "general")
        if not text:
            return jsonify({"status": "error", "error": "text is required"}), 400
        log(f"Webhook受信: user={user} channel={channel} text={text[:80]}")
        return jsonify({"status": "ok", "received": True, "user": user, "channel": channel})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/send/status_board', methods=['POST'])
def send_status_board():
    """ステータスボード送信（システム状態の可視化）"""
    try:
        data = request.json
        channel = data.get('channel', 'general')
        services = data.get('services', [])  # [{"name": "API", "status": "healthy", "uptime": "99.9%"}, ...]
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🖥️ ManaOS System Status"
                }
            },
            {"type": "divider"}
        ]
        
        status_icons = {
            'healthy': ':large_green_circle:',
            'warning': ':large_yellow_circle:',
            'error': ':red_circle:',
            'offline': ':white_circle:'
        }
        
        for service in services:
            name = service.get('name', 'Unknown')
            status = service.get('status', 'unknown')
            uptime = service.get('uptime', 'N/A')
            icon = status_icons.get(status, ':question:')
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{icon} *{name}*\nUptime: {uptime}"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "詳細"
                    },
                    "value": f"service_{name.lower()}",
                    "action_id": f"button_service_{name.lower()}"
                }
            })
        
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
                }
            ]
        })
        
        result = send_slack_message(channel, "System Status", blocks=blocks)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    log("=" * 60)
    log("💬 Slack統合サービス起動")
    log("=" * 60)
    log(f"トークン設定: {'✅ 済' if SLACK_TOKEN else '❌ 未設定'}")
    _port = int(os.getenv("PORT", "5590"))
    log(f"API起動中... (http://0.0.0.0:{_port})")
    log("エンドポイント:")
    log("  - /health")
    log("  - /send")
    log("  - /send/alert")
    log("  - /send/log")
    log("  - /send/report")
    log("  - /send/interactive")
    log("  - /send/rich")
    log("  - /send/status_board")
    log("  - /send/manaos_event")
    log("  - /slack/interactions")
    log("Ctrl+C で停止")
    
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", "5590")), debug=os.getenv("DEBUG", "False").lower() == "true")

