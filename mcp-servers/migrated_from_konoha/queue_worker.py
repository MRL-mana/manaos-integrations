#!/usr/bin/env python3
"""
manaOS Command Hub - Image Job Queue Worker

キューを監視して、n8n / SD WebUI に画像生成ジョブを送信するワーカー
"""

import json
import time
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import os

load_dotenv()

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/manaos_command_hub/logs/queue_worker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 設定
QUEUE_FILE = Path("/root/manaos_command_hub/queues/image_jobs.jsonl")
PROCESSED_FILE = Path("/root/manaos_command_hub/queues/image_jobs_processed.jsonl")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://127.0.0.1:5678/webhook/image-generation")
SD_WEBUI_URL = os.getenv("SD_WEBUI_URL", "http://127.0.0.1:7860")
USE_N8N = os.getenv("USE_N8N", "true").lower() == "true"
POLL_INTERVAL = int(os.getenv("QUEUE_POLL_INTERVAL", "5"))  # 秒


def read_queue_file() -> list:
    """キューファイルから未処理のジョブを読み込む"""
    if not QUEUE_FILE.exists():
        return []

    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 処理済みジョブを読み込む
        processed_jobs = set()
        if PROCESSED_FILE.exists():
            with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            job = json.loads(line)
                            processed_jobs.add(job.get("created_at"))
                        except:
                            pass

        # 未処理のジョブを返す
        unprocessed = []
        for line in lines:
            if line.strip():
                try:
                    job = json.loads(line)
                    if job.get("created_at") not in processed_jobs:
                        unprocessed.append(job)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON in queue: {e}")

        return unprocessed
    except Exception as e:
        logger.error(f"Failed to read queue file: {e}")
        return []


def mark_as_processed(job: Dict[str, Any]):
    """ジョブを処理済みとしてマーク"""
    try:
        PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(job, ensure_ascii=False) + "\n")
        logger.info(f"Job marked as processed: {job.get('created_at')}")
    except Exception as e:
        logger.error(f"Failed to mark job as processed: {e}")


def send_to_n8n(job: Dict[str, Any]) -> bool:
    """n8n Webhookにジョブを送信"""
    try:
        payload = {
            "prompt": job.get("prompt"),
            "negative_prompt": job.get("negative_prompt"),
            "steps": job.get("steps", 20),
            "sampler": job.get("sampler", "Euler a"),
            "cfg_scale": job.get("cfg_scale", 7.0),
            "seed": job.get("seed", -1),
            "job_id": job.get("created_at"),
        }

        response = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        logger.info(f"✅ Job sent to n8n: {job.get('created_at')}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send job to n8n: {e}")
        return False


def send_to_sd_webui(job: Dict[str, Any]) -> bool:
    """SD WebUI APIにジョブを送信"""
    try:
        # SD WebUIのtxt2img API
        api_url = f"{SD_WEBUI_URL}/sdapi/v1/txt2img"

        payload = {
            "prompt": job.get("prompt"),
            "negative_prompt": job.get("negative_prompt", ""),
            "steps": job.get("steps", 20),
            "sampler_name": job.get("sampler", "Euler a"),
            "cfg_scale": job.get("cfg_scale", 7.0),
            "seed": job.get("seed", -1) if job.get("seed", -1) >= 0 else -1,
            "width": 512,
            "height": 512,
        }

        response = requests.post(
            api_url,
            json=payload,
            timeout=60,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        result = response.json()
        logger.info(f"✅ Job sent to SD WebUI: {job.get('created_at')}, images: {len(result.get('images', []))}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send job to SD WebUI: {e}")
        return False


def process_job(job: Dict[str, Any]) -> bool:
    """ジョブを処理（n8n or SD WebUI）"""
    logger.info(f"Processing job: {job.get('created_at')}")

    success = False
    if USE_N8N:
        success = send_to_n8n(job)
    else:
        success = send_to_sd_webui(job)

    if success:
        mark_as_processed(job)

    return success


def main():
    """メインループ"""
    logger.info("🚀 Image Job Queue Worker started")
    logger.info(f"Queue file: {QUEUE_FILE}")
    logger.info(f"Poll interval: {POLL_INTERVAL} seconds")
    logger.info(f"Target: {'n8n' if USE_N8N else 'SD WebUI'}")
    logger.info(f"n8n URL: {N8N_WEBHOOK_URL}")
    logger.info(f"SD WebUI URL: {SD_WEBUI_URL}")

    while True:
        try:
            jobs = read_queue_file()

            if jobs:
                logger.info(f"Found {len(jobs)} unprocessed job(s)")
                for job in jobs:
                    process_job(job)
            else:
                # ログを減らすため、ジョブがない時は静かに待つ
                pass

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("🛑 Worker stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()








