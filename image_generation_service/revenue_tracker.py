"""
Revenue Tracker — 収益 DB 書き込みクライアント
================================================
image_generation_service から revenue_tracker.db に
生成コスト・商品情報・収益を書き込む。

Revenue API Server (port 5117) の HTTP クライアント版。
ローカル DB 直書きとHTTP API 両方をサポート。
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

_log = logging.getLogger("manaos.revenue_writer")

# DB パスは revenue_api_server.py と同じ
_DB_PATH = Path(os.getenv(
    "REVENUE_DB_PATH",
    str(Path(__file__).resolve().parent.parent / "revenue_tracker.db"),
))

_REVENUE_API_URL = os.getenv("REVENUE_API_URL", "http://localhost:5117")

# 書き込みモード: "db" (直接) or "api" (HTTP経由)
_WRITE_MODE = os.getenv("REVENUE_WRITE_MODE", "db")


@contextmanager
def _get_db():
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _post_api(endpoint: str, data: dict) -> bool:
    """Revenue API に HTTP POST"""
    try:
        url = f"{_REVENUE_API_URL}{endpoint}"
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        _log.warning("Revenue API POST %s failed: %s", endpoint, e)
        return False


class RevenueWriter:
    """収益追跡データの書き込み"""

    def __init__(self, write_mode: Optional[str] = None):
        self._mode = write_mode or _WRITE_MODE
        _log.info("RevenueWriter initialized (mode=%s, db=%s)", self._mode, _DB_PATH)

    def record_generation_cost(
        self,
        job_id: str,
        cost_yen: float,
        width: int = 512,
        height: int = 512,
        steps: int = 20,
    ) -> bool:
        """画像生成のGPUコストを記録"""
        metadata = json.dumps({
            "job_id": job_id,
            "width": width,
            "height": height,
            "steps": steps,
            "timestamp": datetime.now().isoformat(),
        })

        if self._mode == "api":
            return _post_api("/api/costs", {
                "service_name": "image_generation",
                "cost_type": "gpu_compute",
                "amount": cost_yen,
                "currency": "JPY",
                "metadata": metadata,
            })

        # DB 直書き
        try:
            with _get_db() as conn:
                conn.execute(
                    "INSERT INTO costs (service_name, cost_type, amount, currency, metadata) "
                    "VALUES (?, ?, ?, ?, ?)",
                    ("image_generation", "gpu_compute", cost_yen, "JPY", metadata),
                )
            _log.debug("Cost recorded: job=%s ¥%.4f", job_id, cost_yen)
            return True
        except Exception as e:
            _log.error("Failed to record cost: %s", e)
            return False

    def record_product(
        self,
        job_id: str,
        prompt: str,
        price_yen: Optional[float] = None,
        file_path: Optional[str] = None,
        product_type: str = "ai_image",
        status: str = "generated",
    ) -> bool:
        """生成画像を商品として登録"""
        title = f"AI Image: {prompt[:80]}"
        metadata = json.dumps({
            "job_id": job_id,
            "full_prompt": prompt[:500],
            "timestamp": datetime.now().isoformat(),
        })

        if self._mode == "api":
            return _post_api("/api/products", {
                "product_id": job_id,
                "product_type": product_type,
                "title": title,
                "price": price_yen,
                "file_path": file_path,
                "status": status,
                "metadata": metadata,
            })

        try:
            with _get_db() as conn:
                conn.execute(
                    "INSERT INTO products "
                    "(product_id, product_type, title, price, file_path, status, metadata) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (job_id, product_type, title, price_yen, file_path, status, metadata),
                )
            _log.debug("Product registered: %s", job_id)
            return True
        except Exception as e:
            _log.error("Failed to record product: %s", e)
            return False

    def record_revenue(
        self,
        job_id: str,
        amount_yen: float,
        source: str = "api_usage",
        product_type: str = "image_generation",
    ) -> bool:
        """収益を記録（有料プランのユーザーが生成した場合）"""
        metadata = json.dumps({
            "job_id": job_id,
            "timestamp": datetime.now().isoformat(),
        })

        if self._mode == "api":
            return _post_api("/api/revenue", {
                "product_id": job_id,
                "product_type": product_type,
                "amount": amount_yen,
                "source": source,
                "metadata": metadata,
            })

        try:
            with _get_db() as conn:
                conn.execute(
                    "INSERT INTO revenue "
                    "(product_id, product_type, amount, currency, source, metadata) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (job_id, product_type, amount_yen, "JPY", source, metadata),
                )
            _log.debug("Revenue recorded: %s ¥%.2f", job_id, amount_yen)
            return True
        except Exception as e:
            _log.error("Failed to record revenue: %s", e)
            return False
