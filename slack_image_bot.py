"""
Slack Image Bot — Slack 画像生成注文受付
=========================================
/generate [prompt] コマンドでスレッドに進捗通知し、完成画像を自動投稿。

起動方法:
  export SLACK_BOT_TOKEN=xoxb-...
  export SLACK_SIGNING_SECRET=...
  python slack_image_bot.py

依存:
  pip install slack-bolt httpx
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

import httpx

_log = logging.getLogger("manaos.slack_image_bot")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")
IMAGE_GEN_URL = os.getenv("IMAGE_GENERATION_URL", "http://127.0.0.1:5560")
GALLERY_URL = os.getenv("GALLERY_API_URL", "http://127.0.0.1:5559")

_client = httpx.Client(timeout=60)


# ─── Slack Helpers ───────────────────────────────────

def _post_message(channel: str, text: str, thread_ts: Optional[str] = None) -> dict:
    """Slack にメッセージ投稿"""
    payload = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    resp = _client.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        json=payload,
    )
    return resp.json()


def _upload_image(channel: str, image_path: str, title: str, thread_ts: Optional[str] = None):
    """Slack に画像をアップロード"""
    import pathlib
    fp = pathlib.Path(image_path)
    if not fp.exists():
        _log.warning("Image file not found: %s", image_path)
        return
    with open(fp, "rb") as f:
        resp = _client.post(
            "https://slack.com/api/files.upload",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            data={
                "channels": channel,
                "title": title,
                "thread_ts": thread_ts or "",
            },
            files={"file": (fp.name, f, "image/png")},
        )
    return resp.json()


# ─── Image Generation Bridge ────────────────────────

def _generate_image(prompt: str, style: Optional[str] = None, quality: str = "standard") -> dict:
    """Image Generation Service に生成リクエスト"""
    payload = {
        "prompt": prompt,
        "quality_mode": quality,
        "auto_improve": quality == "best",
    }
    if style:
        payload["style"] = style
    resp = _client.post(f"{IMAGE_GEN_URL}/api/v1/images/generate", json=payload)
    return resp.json()


def _poll_job(job_id: str, timeout: int = 120) -> dict:
    """ジョブ完了までポーリング"""
    start = time.time()
    while time.time() - start < timeout:
        resp = _client.get(f"{IMAGE_GEN_URL}/api/v1/images/{job_id}")
        data = resp.json()
        status = data.get("status", "unknown")
        if status in ("completed", "failed"):
            return data
        time.sleep(3)
    return {"status": "timeout", "job_id": job_id}


# ─── Command Parser ─────────────────────────────────

def _parse_generate_command(text: str) -> dict:
    """
    /generate <prompt> [--style anime] [--quality best]
    """
    parts = text.split("--")
    prompt = parts[0].strip()
    style = None
    quality = "standard"

    for part in parts[1:]:
        part = part.strip()
        if part.startswith("style "):
            style = part[6:].strip()
        elif part.startswith("quality "):
            quality = part[8:].strip()

    return {"prompt": prompt, "style": style, "quality": quality}


# ─── Main Handler ────────────────────────────────────

def handle_generate_command(channel: str, user: str, text: str, thread_ts: Optional[str] = None):
    """
    /generate コマンドを処理:
      1. Ack → スレッドで進捗通知
      2. 生成リクエスト送信
      3. ポーリング → 完了通知
      4. 画像アップロード
    """
    parsed = _parse_generate_command(text)

    if not parsed["prompt"]:
        _post_message(channel, "❌ プロンプトを指定してください: `/generate 美しい風景画`", thread_ts)
        return

    # 1) 受付通知
    ack = _post_message(
        channel,
        f"🎨 <@{user}> 画像生成を開始します...\n"
        f"📝 *プロンプト:* {parsed['prompt'][:100]}\n"
        f"🎭 *スタイル:* {parsed['style'] or 'デフォルト'}\n"
        f"⚡ *品質:* {parsed['quality']}",
        thread_ts,
    )
    parent_ts = ack.get("ts") or thread_ts

    try:
        # 2) 生成リクエスト
        result = _generate_image(parsed["prompt"], parsed["style"], parsed["quality"])
        job_id = result.get("job_id", "unknown")

        _post_message(channel, f"⏳ ジョブ投入完了 (`{job_id}`) — 生成中...", parent_ts)

        # 3) ポーリング
        final = _poll_job(job_id)
        status = final.get("status", "unknown")

        if status == "completed":
            quality_score = None
            if final.get("result", {}).get("quality_score"):
                qs = final["result"]["quality_score"]
                quality_score = qs.get("overall")

            gen_time = final.get("result", {}).get("generation_time_ms")
            cost = final.get("result", {}).get("cost_estimate_yen")
            image_url = final.get("result", {}).get("image_url")

            msg = f"✅ 生成完了！\n"
            if quality_score is not None:
                msg += f"⭐ 品質: {quality_score:.1f}/10\n"
            if gen_time:
                msg += f"⏱️ 生成時間: {gen_time}ms\n"
            if cost:
                msg += f"💰 コスト: ¥{cost:.4f}\n"

            _post_message(channel, msg, parent_ts)

            # 4) 画像アップロード
            if image_url:
                _upload_image(channel, image_url, parsed["prompt"][:50], parent_ts)

        elif status == "failed":
            error_msg = final.get("result", {}).get("message", "不明なエラー")
            _post_message(channel, f"❌ 生成失敗: {error_msg}", parent_ts)

        else:
            _post_message(channel, f"⏰ タイムアウト — ジョブ `{job_id}` は引き続き処理中", parent_ts)

    except httpx.ConnectError:
        _post_message(channel, "❌ 画像生成サービスに接続できません。", parent_ts)
    except Exception as e:
        _log.error("Generate command error: %s", e)
        _post_message(channel, f"❌ エラー: {e}", parent_ts)


# ─── Slack Bolt App (optional) ───────────────────────

def create_slack_app():
    """Slack Bolt アプリケーション作成（Bolt インストール済みの場合）"""
    try:
        from slack_bolt import App
        from slack_bolt.adapter.socket_mode import SocketModeHandler
    except ImportError:
        _log.error("slack-bolt not installed: pip install slack-bolt")
        return None

    app = App(
        token=SLACK_BOT_TOKEN,
        signing_secret=SLACK_SIGNING_SECRET,
    )

    @app.command("/generate")
    def cmd_generate(ack, command):
        ack("🎨 画像生成をリクエスト中...")
        handle_generate_command(
            channel=command["channel_id"],
            user=command["user_id"],
            text=command["text"],
        )

    @app.message("generate:")
    def msg_generate(message, say):
        text = message.get("text", "").replace("generate:", "").strip()
        handle_generate_command(
            channel=message["channel"],
            user=message["user"],
            text=text,
            thread_ts=message.get("thread_ts"),
        )

    @app.command("/imgstatus")
    def cmd_status(ack, command):
        ack()
        try:
            resp = _client.get(f"{IMAGE_GEN_URL}/api/v1/images/dashboard")
            data = resp.json()
            stats = data.get("stats", {})
            msg = (
                f"📊 *画像生成ダッシュボード*\n"
                f"• 生成: {stats.get('total', 0)} 枚\n"
                f"• 成功: {stats.get('success', 0)} | 失敗: {stats.get('failed', 0)}\n"
                f"• 改善: {stats.get('improved', 0)} 回"
            )
            _post_message(command["channel_id"], msg)
        except Exception as e:
            _post_message(command["channel_id"], f"❌ ダッシュボード取得失敗: {e}")

    return app


# ─── HTTP Webhook Mode (Bolt 不要) ──────────────────

def create_webhook_app():
    """Flask ベースの Webhook 受信サーバー (Bolt 不要の軽量版)"""
    try:
        from flask import Flask, request as flask_request, jsonify
    except ImportError:
        _log.error("flask not installed: pip install flask")
        return None

    webapp = Flask(__name__)

    @webapp.route("/slack/commands", methods=["POST"])
    def slack_command():
        form = flask_request.form
        cmd = form.get("command", "")
        text = form.get("text", "")
        channel = form.get("channel_id", "")
        user = form.get("user_id", "")

        if cmd == "/generate":
            # 即レスポンス (3秒以内)
            import threading
            threading.Thread(
                target=handle_generate_command,
                args=(channel, user, text),
                daemon=True,
            ).start()
            return jsonify({"response_type": "in_channel", "text": "🎨 画像生成をリクエスト中..."})

        elif cmd == "/imgstatus":
            try:
                resp = _client.get(f"{IMAGE_GEN_URL}/api/v1/images/dashboard")
                data = resp.json()
                stats = data.get("stats", {})
                return jsonify({
                    "response_type": "in_channel",
                    "text": f"📊 生成: {stats.get('total', 0)} | 成功: {stats.get('success', 0)} | 失敗: {stats.get('failed', 0)}",
                })
            except Exception as e:
                return jsonify({"text": f"❌ {e}"})

        return jsonify({"text": "Unknown command"})

    @webapp.route("/health")
    def health():
        return jsonify({"status": "healthy", "service": "slack_image_bot"})

    return webapp


# ─── Main ────────────────────────────────────────────

def main():
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="ManaOS Slack Image Bot")
    parser.add_argument("--mode", choices=["bolt", "webhook"], default="webhook",
                        help="bolt: Socket Mode, webhook: HTTP server")
    parser.add_argument("--port", type=int, default=5570, help="Webhook server port")
    args = parser.parse_args()

    if not SLACK_BOT_TOKEN:
        _log.error("SLACK_BOT_TOKEN not set")
        return

    if args.mode == "bolt":
        app = create_slack_app()
        if app:
            socket_token = os.getenv("SLACK_APP_TOKEN", "")
            if socket_token:
                from slack_bolt.adapter.socket_mode import SocketModeHandler
                handler = SocketModeHandler(app, socket_token)
                _log.info("Starting Slack Bolt (Socket Mode)...")
                handler.start()
            else:
                _log.info("Starting Slack Bolt (HTTP)... port=%d", args.port)
                app.start(port=args.port)
    else:
        webapp = create_webhook_app()
        if webapp:
            _log.info("Starting Webhook server on port %d", args.port)
            webapp.run(host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
