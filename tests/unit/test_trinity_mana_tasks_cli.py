"""Unit tests for tools/trinity_mana_tasks_cli.py pure helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# core.db_manager が存在しないため、インポート前にモックで埋める
_mock_core = MagicMock()
sys.modules.setdefault("core", _mock_core)
sys.modules.setdefault("core.db_manager", _mock_core.db_manager)

# tabulate と click が未インストールの場合にスタブを注入
if "tabulate" not in sys.modules:
    _tabulate_mod = MagicMock()
    _tabulate_mod.tabulate = MagicMock(return_value="")
    sys.modules["tabulate"] = _tabulate_mod
if "click" not in sys.modules:
    sys.modules.setdefault("click", MagicMock())

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
from trinity_mana_tasks_cli import (
    Colors,
    colorize,
    format_agent,
    format_priority,
    format_status,
)

# ─────────────────────────────────────────────────────────────────────────────
# colorize
# ─────────────────────────────────────────────────────────────────────────────

class TestColorize:
    def test_wraps_text_with_color_and_reset(self):
        result = colorize("hello", Colors.OKGREEN)
        assert result.startswith(Colors.OKGREEN)
        assert result.endswith(Colors.ENDC)
        assert "hello" in result

    def test_empty_color_still_appends_endc(self):
        result = colorize("text", "")
        assert result.endswith(Colors.ENDC)
        assert "text" in result


# ─────────────────────────────────────────────────────────────────────────────
# format_priority
# ─────────────────────────────────────────────────────────────────────────────

class TestFormatPriority:
    def test_urgent_returns_fail_color(self):
        result = format_priority("urgent")
        assert Colors.FAIL in result
        assert "URGENT" in result

    def test_high_returns_warning_color(self):
        result = format_priority("high")
        assert Colors.WARNING in result
        assert "HIGH" in result

    def test_medium_returns_okblue_color(self):
        result = format_priority("medium")
        assert Colors.OKBLUE in result
        assert "MEDIUM" in result

    def test_low_returns_okcyan_color(self):
        result = format_priority("low")
        assert Colors.OKCYAN in result
        assert "LOW" in result

    def test_unknown_priority_uppercased(self):
        result = format_priority("someunknown")
        assert "SOMEUNKNOWN" in result


# ─────────────────────────────────────────────────────────────────────────────
# format_status
# ─────────────────────────────────────────────────────────────────────────────

class TestFormatStatus:
    def test_todo_has_icon(self):
        result = format_status("todo")
        assert "📝" in result
        assert "todo" in result

    def test_in_progress_has_icon(self):
        result = format_status("in_progress")
        assert "🔄" in result

    def test_done_has_check_icon(self):
        result = format_status("done")
        assert "✅" in result

    def test_blocked_has_stop_icon(self):
        result = format_status("blocked")
        assert "🚫" in result

    def test_unknown_status_has_question_icon(self):
        result = format_status("unknown_xyz")
        assert "❓" in result
        assert "unknown_xyz" in result


# ─────────────────────────────────────────────────────────────────────────────
# format_agent
# ─────────────────────────────────────────────────────────────────────────────

class TestFormatAgent:
    def test_remi_has_target_icon(self):
        result = format_agent("Remi")
        assert "🎯" in result
        assert "Remi" in result

    def test_luna_has_moon_icon(self):
        result = format_agent("Luna")
        assert "🌙" in result

    def test_mina_has_search_icon(self):
        result = format_agent("Mina")
        assert "🔍" in result

    def test_aria_has_book_icon(self):
        result = format_agent("Aria")
        assert "📖" in result

    def test_unknown_agent_has_person_icon(self):
        result = format_agent("UnknownBot")
        assert "👤" in result
        assert "UnknownBot" in result
