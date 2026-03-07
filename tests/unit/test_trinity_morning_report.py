"""Unit tests for tools/trinity_morning_report.py — parse_weather."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))

# __init__ は /root/.mana_vault などを参照するが、ファイルが存在しなければスキップされる。
# Windows 環境では安全にインスタンス化できる。
from trinity_morning_report import MorningReport


def _make_mr() -> MorningReport:
    """ファイル読み込みをスキップして MorningReport を生成するヘルパー。"""
    with patch("pathlib.Path.exists", return_value=False):
        mr = MorningReport()
    return mr


# ─────────────────────────────────────────────────────────────────────────────
# parse_weather
# ─────────────────────────────────────────────────────────────────────────────

class TestParseWeather:
    def test_empty_text_returns_defaults(self):
        mr = _make_mr()
        result = mr.parse_weather("")
        assert result["weather"] == "🌤️ 天気不明"
        assert result["temperature"] == "温度不明"
        assert result["wind"] == "風速不明"
        assert result["humidity"] == "湿度不明"

    def test_fahrenheit_converted_to_celsius(self):
        mr = _make_mr()
        # 68°F = 20℃
        result = mr.parse_weather("Temperature: 68°F today")
        assert result["temperature"] == "20℃"

    def test_negative_fahrenheit_converted(self):
        mr = _make_mr()
        # -40°F = -40℃
        result = mr.parse_weather("-40°F reading")
        # マイナス符号パターン確認
        assert "℃" in result["temperature"]

    def test_humidity_extracted(self):
        mr = _make_mr()
        result = mr.parse_weather("Humidity: 75% right now")
        assert result["humidity"] == "75%"

    def test_wind_mph_extracted(self):
        mr = _make_mr()
        result = mr.parse_weather("Wind: ↑ 12 mph steady")
        assert "12" in result["wind"]
        assert "mph" in result["wind"]

    def test_wind_kmh_extracted(self):
        mr = _make_mr()
        result = mr.parse_weather("Wind 25 km/h from north")
        assert "25" in result["wind"]
        assert "km/h" in result["wind"]

    def test_sunny_weather_detected(self):
        mr = _make_mr()
        result = mr.parse_weather("☀ 晴れの天気")
        assert result["weather"] == "☀️ 晴れ"

    def test_cloudy_weather_detected(self):
        mr = _make_mr()
        result = mr.parse_weather("⛅ 曇りです")
        assert result["weather"] == "☁️ 曇り"

    def test_rainy_weather_detected(self):
        mr = _make_mr()
        result = mr.parse_weather("🌧 雨が降ります")
        assert result["weather"] == "🌧️ 雨"

    def test_snowy_weather_detected(self):
        mr = _make_mr()
        result = mr.parse_weather("❄ 雪です")
        assert result["weather"] == "❄️ 雪"

    def test_return_dict_has_expected_keys(self):
        mr = _make_mr()
        result = mr.parse_weather("")
        assert set(result.keys()) == {"weather", "temperature", "wind", "humidity", "forecast"}

    def test_forecast_dict_has_four_slots(self):
        mr = _make_mr()
        result = mr.parse_weather("")
        assert set(result["forecast"].keys()) == {"morning", "afternoon", "evening", "night"}

    def test_multiple_fields_in_one_text(self):
        mr = _make_mr()
        text = "☀ 晴れ 68°F Humidity: 65% Wind 15 km/h"
        result = mr.parse_weather(text)
        assert result["weather"] == "☀️ 晴れ"
        assert result["temperature"] == "20℃"
        assert result["humidity"] == "65%"
        assert "15" in result["wind"]
