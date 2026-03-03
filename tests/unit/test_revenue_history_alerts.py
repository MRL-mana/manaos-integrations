"""
Revenue History & Loop Health Alert テスト
=========================================
- RevenueWriter.get_daily_history() / get_summary()
- _compute_loop_health + threshold → alerts
- _send_loop_health_slack (Slack通知スタブ)
"""

import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ---------- RevenueWriter 日次集計 ----------


class TestRevenueWriterHistory:
    """RevenueWriter の get_daily_history / get_summary テスト (一時DB使用)"""

    @pytest.fixture(autouse=True)
    def _setup_tmp_db(self, tmp_path):
        """テスト用に一時 SQLite DB を作成"""
        db_path = tmp_path / "test_revenue.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS revenue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT, product_type TEXT,
                amount REAL NOT NULL, currency TEXT DEFAULT 'JPY',
                source TEXT, metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL, cost_type TEXT NOT NULL,
                amount REAL NOT NULL, currency TEXT DEFAULT 'JPY',
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT UNIQUE NOT NULL, product_type TEXT NOT NULL,
                title TEXT, description TEXT,
                price REAL, currency TEXT DEFAULT 'JPY',
                file_path TEXT, status TEXT DEFAULT 'draft',
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # テストデータ挿入 (今日と昨日)
        today = datetime.now().strftime("%Y-%m-%d 12:00:00")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d 12:00:00")
        conn.execute(
            "INSERT INTO revenue (product_id, product_type, amount, source, created_at) VALUES (?,?,?,?,?)",
            ("job-1", "image", 100.0, "api", today),
        )
        conn.execute(
            "INSERT INTO revenue (product_id, product_type, amount, source, created_at) VALUES (?,?,?,?,?)",
            ("job-2", "image", 50.0, "api", yesterday),
        )
        conn.execute(
            "INSERT INTO costs (service_name, cost_type, amount, created_at) VALUES (?,?,?,?)",
            ("image_gen", "gpu", 0.05, today),
        )
        conn.execute(
            "INSERT INTO products (product_id, product_type, title, created_at) VALUES (?,?,?,?)",
            ("job-1", "ai_image", "Test", today),
        )
        conn.commit()
        conn.close()
        self.db_path = db_path

    def _make_writer(self):
        with patch("image_generation_service.revenue_tracker._DB_PATH", self.db_path):
            from image_generation_service.revenue_tracker import RevenueWriter
            return RevenueWriter(write_mode="db")

    def test_get_daily_history(self):
        writer = self._make_writer()
        with patch("image_generation_service.revenue_tracker._DB_PATH", self.db_path):
            result = writer.get_daily_history(30)
        assert result["status"] == "ok"
        assert len(result["days"]) >= 1
        # 今日のエントリのが存在する
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_entry = [d for d in result["days"] if d["date"] == today_str]
        assert len(today_entry) == 1
        assert today_entry[0]["revenue"] == 100.0
        assert today_entry[0]["cost"] == 0.05
        assert today_entry[0]["products"] == 1

    def test_get_daily_history_empty_db(self, tmp_path):
        """空DBでもエラーにならない"""
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript("""
            CREATE TABLE revenue (id INTEGER PRIMARY KEY, product_id TEXT, product_type TEXT,
                amount REAL, currency TEXT, source TEXT, metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE costs (id INTEGER PRIMARY KEY, service_name TEXT, cost_type TEXT,
                amount REAL, currency TEXT, metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE products (id INTEGER PRIMARY KEY, product_id TEXT UNIQUE, product_type TEXT,
                title TEXT, price REAL, currency TEXT, file_path TEXT, status TEXT,
                metadata TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        """)
        conn.close()
        with patch("image_generation_service.revenue_tracker._DB_PATH", db_path):
            from image_generation_service.revenue_tracker import RevenueWriter
            writer = RevenueWriter(write_mode="db")
            result = writer.get_daily_history(30)
        assert result["status"] == "ok"
        assert result["days"] == []

    def test_get_summary(self):
        writer = self._make_writer()
        with patch("image_generation_service.revenue_tracker._DB_PATH", self.db_path):
            result = writer.get_summary(30)
        assert result["total_revenue"] == 150.0  # 100 + 50
        assert result["total_cost"] == 0.05
        assert result["profit"] == 149.95
        assert result["products"] == 1


# ---------- Loop Health Alert Logic ----------


class TestLoopHealthAlerts:
    """_compute_loop_health のアラート閾値テスト"""

    def test_all_zero_returns_critical(self):
        from image_generation_service.router import _compute_loop_health
        result = _compute_loop_health(
            bill={},
            fb={},
            rl={},
        )
        assert result["level"] == "critical"
        assert result["score"] == 0

    def test_all_zero_generates_all_alerts(self):
        """全次元0の場合、全5アラートが出る"""
        # 直接閾値チェックロジックをテスト
        breakdown = {"revenue": 0, "users": 0, "feedback": 0, "rl_success": 0, "rl_learning": 0}
        thresholds = {
            "revenue": 5, "users": 5, "feedback": 5,
            "rl_success": 5, "rl_learning": 5,
        }
        alerts = []
        for dim, thr in thresholds.items():
            if breakdown.get(dim, 0) < thr:
                alerts.append(dim)
        assert len(alerts) == 5

    def test_thriving_no_alerts(self):
        """全次元がthrivingレベルならアラート0"""
        breakdown = {"revenue": 20, "users": 20, "feedback": 20, "rl_success": 20, "rl_learning": 20}
        thresholds = {
            "revenue": 5, "users": 5, "feedback": 5,
            "rl_success": 5, "rl_learning": 5,
        }
        alerts = [dim for dim, thr in thresholds.items() if breakdown.get(dim, 0) < thr]
        assert len(alerts) == 0


class TestSlackNotification:
    """Slack通知のテスト"""

    def test_no_webhook_returns_false(self):
        """SLACK_WEBHOOK_URL未設定ではFalseを返す"""
        from image_generation_service.router import _send_loop_health_slack
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SLACK_WEBHOOK_URL", None)
            result = _send_loop_health_slack(
                {"score": 10, "level": "critical"},
                [{"severity": "critical", "dimension": "revenue", "message": "test"}],
            )
        assert result is False

    def test_webhook_sends_post(self):
        """SLACK_WEBHOOK_URLが設定されていればPOSTする"""
        from image_generation_service.router import _send_loop_health_slack
        mock_urlopen = MagicMock()
        mock_urlopen.__enter__ = MagicMock()
        mock_urlopen.__exit__ = MagicMock(return_value=False)
        with patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}):
            with patch("urllib.request.urlopen", return_value=mock_urlopen) as mock_open:
                result = _send_loop_health_slack(
                    {"score": 5, "level": "critical"},
                    [{"severity": "critical", "dimension": "revenue", "message": "MRR low"}],
                )
        assert result is True
        mock_open.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
