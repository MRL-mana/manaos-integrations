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

    # ─── 読み取り (集計) ──────────────────────────────

    def get_daily_history(self, days: int = 30) -> dict:
        """日次収益・コスト・利益の推移を取得

        Returns:
            {"days": [{"date": "2026-03-01", "revenue": 120.5,
                       "cost": 0.3, "profit": 120.2, "products": 5}, ...]}
        """
        try:
            with _get_db() as conn:
                rows_rev = conn.execute(
                    "SELECT DATE(created_at) AS d, SUM(amount) AS total "
                    "FROM revenue WHERE created_at >= DATE('now', ?) "
                    "GROUP BY d ORDER BY d",
                    (f"-{days} days",),
                ).fetchall()

                rows_cost = conn.execute(
                    "SELECT DATE(created_at) AS d, SUM(amount) AS total "
                    "FROM costs WHERE created_at >= DATE('now', ?) "
                    "GROUP BY d ORDER BY d",
                    (f"-{days} days",),
                ).fetchall()

                rows_prod = conn.execute(
                    "SELECT DATE(created_at) AS d, COUNT(*) AS cnt "
                    "FROM products WHERE created_at >= DATE('now', ?) "
                    "GROUP BY d ORDER BY d",
                    (f"-{days} days",),
                ).fetchall()

            rev_map = {r["d"]: r["total"] for r in rows_rev}
            cost_map = {r["d"]: r["total"] for r in rows_cost}
            prod_map = {r["d"]: r["cnt"] for r in rows_prod}

            all_dates = sorted(set(rev_map) | set(cost_map) | set(prod_map))
            result = []
            for d in all_dates:
                rev = rev_map.get(d, 0.0)
                cost = cost_map.get(d, 0.0)
                result.append({
                    "date": d,
                    "revenue": round(rev, 2),
                    "cost": round(cost, 4),
                    "profit": round(rev - cost, 2),
                    "products": prod_map.get(d, 0),
                })
            return {"status": "ok", "days": result, "period": days}
        except Exception as e:
            _log.error("Failed to get daily history: %s", e)
            return {"status": "error", "days": [], "error": str(e)}

    def get_summary(self, days: int = 30) -> dict:
        """期間サマリ (合計収益/コスト/利益率)"""
        try:
            with _get_db() as conn:
                rev = conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) FROM revenue "
                    "WHERE created_at >= DATE('now', ?)",
                    (f"-{days} days",),
                ).fetchone()[0]
                cost = conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) FROM costs "
                    "WHERE created_at >= DATE('now', ?)",
                    (f"-{days} days",),
                ).fetchone()[0]
                prod = conn.execute(
                    "SELECT COUNT(*) FROM products "
                    "WHERE created_at >= DATE('now', ?)",
                    (f"-{days} days",),
                ).fetchone()[0]
            margin = round((rev - cost) / rev * 100, 1) if rev > 0 else 0.0
            return {
                "total_revenue": round(rev, 2),
                "total_cost": round(cost, 4),
                "profit": round(rev - cost, 2),
                "margin_pct": margin,
                "products": prod,
                "period_days": days,
            }
        except Exception as e:
            _log.error("Failed to get summary: %s", e)
            return {"total_revenue": 0, "total_cost": 0, "profit": 0,
                    "margin_pct": 0, "products": 0, "period_days": days}
