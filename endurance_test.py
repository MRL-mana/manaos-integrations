"""AI画像生成API 48時間耐久テストスクリプト。"""

from __future__ import annotations

import json
import logging
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx

API_URL = "http://localhost:5560/api/v1/images/generate"
API_KEY = "default"
TEST_PROMPT = "manaos endurance test"
MAX_ATTEMPTS = 1000
TIME_LIMIT_HOURS = 48
INTERVAL_SECONDS = 2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("endurance_test")


def run_test() -> dict:
    start = datetime.now()
    end = start + timedelta(hours=TIME_LIMIT_HOURS)
    success = 0
    fail = 0
    failures = []

    headers = {"X-API-Key": API_KEY}

    with httpx.Client(timeout=30) as client:
        for i in range(MAX_ATTEMPTS):
            if datetime.now() > end:
                break

            payload = {
                "prompt": TEST_PROMPT,
                "width": random.choice([512, 1024]),
                "height": random.choice([512, 1024]),
                "steps": random.choice([20, 30]),
                "cfg_scale": random.choice([7.0, 10.0]),
                "auto_improve": True,
            }

            try:
                response = client.post(API_URL, json=payload, headers=headers)
                if response.status_code == 200:
                    job_id = response.json().get("job_id")
                    logger.info("[%s] success job_id=%s", i + 1, job_id)
                    success += 1
                else:
                    logger.warning(
                        "[%s] fail status=%s body=%s",
                        i + 1,
                        response.status_code,
                        response.text[:200],
                    )
                    fail += 1
                    failures.append(
                        {
                            "attempt": i + 1,
                            "status": response.status_code,
                            "body": response.text[:200],
                        }
                    )
            except Exception as exc:
                logger.error("[%s] exception=%s", i + 1, exc)
                fail += 1
                failures.append({"attempt": i + 1, "exception": str(exc)})

            time.sleep(INTERVAL_SECONDS)

    summary = {
        "started_at": start.isoformat(),
        "ended_at": datetime.now().isoformat(),
        "time_limit_hours": TIME_LIMIT_HOURS,
        "max_attempts": MAX_ATTEMPTS,
        "success": success,
        "fail": fail,
        "success_rate": round(success / max(1, success + fail), 4),
        "failed_samples": failures[:20],
    }

    result_path = Path("endurance_test_result.json")
    result_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("Test finished: success=%s fail=%s", success, fail)
    logger.info("Result saved: %s", result_path)

    if fail > 0:
        logger.warning("Slack通知: エラー発生 (stub)")

    return summary


if __name__ == "__main__":
    run_test()
