#!/usr/bin/env python3
"""
定例自動化: 朝昼夕の情報通知
"""
import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import httpx
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# ログ設定
log_dir = Path("/root/logs/daily_automation")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "daily_notifier.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===== 設定 =====
class Config:
    """設定"""
    # 通知先
    LINE_NOTIFY_TOKEN = os.getenv("LINE_NOTIFY_TOKEN", "")
    SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

    # API URL
    TRINITY_API_URL = os.getenv("TRINITY_API_URL", "http://localhost:5015")
    OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:5016")
    FLUX_API_URL = os.getenv("FLUX_API_URL", "http://localhost:5017")

    # 天気API（OpenWeatherMap）
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
    WEATHER_CITY = "Akita,JP"  # 秋田市


# ===== 通知関数 =====
async def send_line_notify(message: str):
    """LINE通知送信"""
    if not Config.LINE_NOTIFY_TOKEN:
        logger.warning("LINE_NOTIFY_TOKEN未設定")
        return False

    try:
        response = requests.post(
            "https://notify-api.line.me/api/notify",
            headers={"Authorization": f"Bearer {Config.LINE_NOTIFY_TOKEN}"},
            data={"message": message}
        )
        response.raise_for_status()
        logger.info("✅ LINE通知送信成功")
        return True
    except Exception as e:
        logger.error(f"❌ LINE通知エラー: {e}")
        return False


async def send_slack_notify(message: str):
    """Slack通知送信"""
    if not Config.SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL未設定")
        return False

    try:
        response = requests.post(
            Config.SLACK_WEBHOOK_URL,
            json={"text": message}
        )
        response.raise_for_status()
        logger.info("✅ Slack通知送信成功")
        return True
    except Exception as e:
        logger.error(f"❌ Slack通知エラー: {e}")
        return False


async def send_notification(message: str):
    """通知送信（LINE/Slack）"""
    await asyncio.gather(
        send_line_notify(message),
        send_slack_notify(message),
        return_exceptions=True
    )


# ===== 情報取得関数 =====
async def get_weather() -> str:
    """天気情報を取得"""
    if not Config.WEATHER_API_KEY:
        return "天気情報: APIキー未設定"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": Config.WEATHER_CITY,
                    "appid": Config.WEATHER_API_KEY,
                    "units": "metric",
                    "lang": "ja"
                }
            )
            response.raise_for_status()
            data = response.json()

            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            return f"🌤️ {desc} {temp}°C"
    except Exception as e:
        logger.error(f"天気取得エラー: {e}")
        return "天気情報: 取得失敗"


async def get_today_tasks() -> List[str]:
    """今日のタスクを取得（Trinity API経由）"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{Config.TRINITY_API_URL}/task",
                json={
                    "description": "今日のやること3つをリストアップしてください",
                    "use_langgraph": False
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                # 簡易実装: 実際の実装では結果をパース
                return ["タスク1", "タスク2", "タスク3"]
    except Exception as e:
        logger.error(f"タスク取得エラー: {e}")

    return []


# ===== 通知メッセージ生成 =====
async def generate_morning_message() -> str:
    """朝の通知メッセージ生成"""
    weather = await get_weather()
    tasks = await get_today_tasks()

    message = f"""🌅 おはようございます！

📅 {datetime.now().strftime('%Y年%m月%d日 %H:%M')}

{weather}

📋 今日のやること:
"""
    for i, task in enumerate(tasks[:3], 1):
        message += f"  {i}. {task}\n"

    message += "\n💪 今日も頑張りましょう！"
    return message


async def generate_noon_message() -> str:
    """昼の通知メッセージ生成"""
    message = f"""☀️ お昼です！

⏰ {datetime.now().strftime('%H:%M')}

📊 進捗確認の時間です。

🎨 1枚フライヤー案を生成しますか？
"""
    return message


async def generate_evening_message() -> str:
    """夜の通知メッセージ生成"""
    message = f"""🌙 お疲れ様でした！

⏰ {datetime.now().strftime('%Y年%m月%d日 %H:%M')}

📝 日報を作成しますか？

📋 明日の優先タスクを準備しますか？

🤖 AIフィードバックを取得しますか？
"""
    return message


# ===== スケジューラー =====
scheduler = AsyncIOScheduler()


@scheduler.scheduled_job(CronTrigger(hour=8, minute=0))
async def morning_notification():
    """朝の通知（08:00）"""
    logger.info("🌅 朝の通知開始")
    message = await generate_morning_message()
    await send_notification(message)


@scheduler.scheduled_job(CronTrigger(hour=11, minute=0))
async def noon_notification():
    """昼の通知（11:00）"""
    logger.info("☀️ 昼の通知開始")
    message = await generate_noon_message()
    await send_notification(message)


@scheduler.scheduled_job(CronTrigger(hour=14, minute=0))
async def afternoon_notification():
    """午後の通知（14:00）"""
    logger.info("📊 午後の通知開始")
    message = await generate_noon_message()
    await send_notification(message)


@scheduler.scheduled_job(CronTrigger(hour=17, minute=0))
async def evening_notification():
    """夕方の通知（17:00）"""
    logger.info("🌆 夕方の通知開始")
    message = await generate_evening_message()
    await send_notification(message)


@scheduler.scheduled_job(CronTrigger(hour=20, minute=0))
async def night_notification():
    """夜の通知（20:00）"""
    logger.info("🌙 夜の通知開始")
    message = await generate_evening_message()
    await send_notification(message)


# ===== メイン =====
async def main():
    """メイン関数"""
    logger.info("🚀 Daily Notifier 起動中...")

    scheduler.start()
    logger.info("✅ スケジューラー起動完了")
    logger.info("📅 通知スケジュール:")
    logger.info("  08:00 - 朝の通知")
    logger.info("  11:00 - 昼の通知")
    logger.info("  14:00 - 午後の通知")
    logger.info("  17:00 - 夕方の通知")
    logger.info("  20:00 - 夜の通知")

    # 無限ループ
    try:
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        logger.info("🛑 シャットダウン中...")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

