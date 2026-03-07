"""
Unit tests for scripts/misc/personality_thought_system.py
"""
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh_inst = MagicMock()
_eh.ManaOSErrorHandler = MagicMock(return_value=_eh_inst)
sys.modules.setdefault("manaos_error_handler", _eh)

sys.modules.setdefault("flask_cors", MagicMock())
sys.modules.setdefault("flask", MagicMock())

import pytest
from scripts.misc.personality_thought_system import (
    CoreValue,
    MoodState,
    PersonalityThoughtSystem,
    ThoughtEntry,
    ValueScore,
    ContradictionWarning,
    PersonalityEvolutionEntry,
    _load_json,
    _save_json,
)


# ── helpers ───────────────────────────────────────────────────────────────

def _make_pts(tmp_path: Path) -> PersonalityThoughtSystem:
    """データを tmp_path に向けた PersonalityThoughtSystem"""
    import scripts.misc.personality_thought_system as pts_mod
    with (
        patch.object(pts_mod, "_VALUE_SCORES_PATH", tmp_path / "value_scores.json"),
        patch.object(pts_mod, "_THOUGHT_LOG_PATH", tmp_path / "thought_log.json"),
        patch.object(pts_mod, "_EVOLUTION_LOG_PATH", tmp_path / "evolution_log.json"),
        patch.object(pts_mod, "_MOOD_STATE_PATH", tmp_path / "mood_state.json"),
    ):
        return PersonalityThoughtSystem()


@pytest.fixture
def pts(tmp_path):
    return _make_pts(tmp_path)


# ── TestCoreValue ─────────────────────────────────────────────────────────
class TestCoreValue:
    def test_values(self):
        assert CoreValue.HONESTY.value == "honesty"
        assert CoreValue.HELPFULNESS.value == "helpfulness"
        assert CoreValue.CURIOSITY.value == "curiosity"
        assert CoreValue.EMPATHY.value == "empathy"
        assert CoreValue.EFFICIENCY.value == "efficiency"
        assert CoreValue.CREATIVITY.value == "creativity"

    def test_is_str_subclass(self):
        assert isinstance(CoreValue.HONESTY, str)


# ── TestMoodState ─────────────────────────────────────────────────────────
class TestMoodState:
    def test_values(self):
        assert MoodState.ENERGETIC.value == "energetic"
        assert MoodState.CALM.value == "calm"
        assert MoodState.TIRED.value == "tired"

    def test_is_str_subclass(self):
        assert isinstance(MoodState.CALM, str)


# ── TestLoadSaveJson ──────────────────────────────────────────────────────
class TestLoadSaveJson:
    def test_save_and_load(self, tmp_path):
        path = tmp_path / "data.json"
        _save_json(path, {"key": "value"})
        result = _load_json(path, {})
        assert result["key"] == "value"

    def test_default_when_missing(self, tmp_path):
        path = tmp_path / "notexist.json"
        result = _load_json(path, {"default": 1})
        assert result == {"default": 1}


# ── TestInit ──────────────────────────────────────────────────────────────
class TestInit:
    def test_value_scores_initialized(self, pts):
        for v in CoreValue:
            assert v.value in pts._value_scores

    def test_default_mood_calm(self, pts):
        assert pts._current_mood == MoodState.CALM

    def test_empty_logs(self, pts):
        assert pts._thought_log == []
        assert pts._evolution_log == []


# ── TestGetMood ───────────────────────────────────────────────────────────
class TestGetMood:
    def test_returns_mood_info(self, pts):
        result = pts.get_mood()
        assert "mood" in result
        assert "description" in result
        assert result["mood"] == pts._current_mood.value


# ── TestSetMood ───────────────────────────────────────────────────────────
class TestSetMood:
    def test_sets_mood(self, pts):
        mood = pts.set_mood("energetic")
        assert mood == MoodState.ENERGETIC
        assert pts._current_mood == MoodState.ENERGETIC

    def test_invalid_mood_raises(self, pts):
        with pytest.raises(ValueError):
            pts.set_mood("invalid_mood_xyz")


# ── TestDetectAndUpdateMood ───────────────────────────────────────────────
class TestDetectAndUpdateMood:
    def test_detects_energetic(self, pts):
        mood = pts.detect_and_update_mood("頑張る！目標に向かってスタートするぞ")
        assert mood == MoodState.ENERGETIC

    def test_detects_tired(self, pts):
        mood = pts.detect_and_update_mood("疲れてしんどい、眠い")
        assert mood == MoodState.TIRED

    def test_detects_curious(self, pts):
        mood = pts.detect_and_update_mood("なぜこうなるのか気になる、仕組みを調べたい")
        assert mood == MoodState.CURIOUS

    def test_no_keyword_keeps_current(self, pts):
        pts._current_mood = MoodState.FOCUSED
        pts.detect_and_update_mood("hello world")
        assert pts._current_mood == MoodState.FOCUSED


# ── TestGetValueScores ────────────────────────────────────────────────────
class TestGetValueScores:
    def test_returns_all_values(self, pts):
        scores = pts.get_value_scores()
        for v in CoreValue:
            assert v.value in scores

    def test_score_range(self, pts):
        scores = pts.get_value_scores()
        for k, v in scores.items():
            assert 0.0 <= v["score"] <= 1.0


# ── TestReinforceValue ────────────────────────────────────────────────────
class TestReinforceValue:
    def test_increases_score(self, pts):
        before = pts._value_scores["honesty"].score
        pts.reinforce_value("honesty", delta=0.05)
        after = pts._value_scores["honesty"].score
        assert after > before

    def test_capped_at_1(self, pts):
        pts._value_scores["honesty"].score = 0.99
        pts.reinforce_value("honesty", delta=0.5)
        assert pts._value_scores["honesty"].score == 1.0

    def test_example_stored(self, pts):
        pts.reinforce_value("honesty", example="誠実な回答")
        assert "誠実な回答" in pts._value_scores["honesty"].examples

    def test_invalid_value_raises(self, pts):
        with pytest.raises(ValueError):
            pts.reinforce_value("nonexistent_value")


# ── TestWeakenValue ───────────────────────────────────────────────────────
class TestWeakenValue:
    def test_decreases_score(self, pts):
        pts._value_scores["honesty"].score = 0.8
        pts.weaken_value("honesty", delta=0.05)
        assert pts._value_scores["honesty"].score < 0.8

    def test_floored_at_0(self, pts):
        pts._value_scores["honesty"].score = 0.01
        pts.weaken_value("honesty", delta=0.5)
        assert pts._value_scores["honesty"].score == 0.0

    def test_invalid_value_raises(self, pts):
        with pytest.raises(ValueError):
            pts.weaken_value("nonexistent_value")


# ── TestCheckContradiction ────────────────────────────────────────────────
class TestCheckContradiction:
    def test_detects_honesty_violation(self, pts):
        warnings = pts.check_contradiction("これは絶対に正しいです")
        assert any(w.value_violated == "honesty" for w in warnings)

    def test_no_warnings_for_clean_text(self, pts):
        warnings = pts.check_contradiction("解決策を提示します")
        assert len(warnings) == 0

    def test_returns_contradiction_warnings(self, pts):
        warnings = pts.check_contradiction("100%保証します")
        assert all(isinstance(w, ContradictionWarning) for w in warnings)


# ── TestLogThought ────────────────────────────────────────────────────────
class TestLogThought:
    def test_adds_entry(self, pts):
        pts.log_thought("テスト入力", context="chat")
        assert len(pts._thought_log) == 1

    def test_returns_thought_entry(self, pts):
        entry = pts.log_thought("テスト入力")
        assert isinstance(entry, ThoughtEntry)

    def test_truncates_input(self, pts):
        long_input = "a" * 200
        entry = pts.log_thought(long_input)
        assert len(entry.user_input_summary) <= 100

    def test_custom_reflection(self, pts):
        entry = pts.log_thought("入力", reflection="カスタム内省")
        assert entry.reflection == "カスタム内省"


# ── TestAutoReflect ───────────────────────────────────────────────────────
class TestAutoReflect:
    def test_report_context(self, pts):
        r = pts._auto_reflect("今日の報告です", "report")
        assert "報告" in r

    def test_planning_context(self, pts):
        r = pts._auto_reflect("計画を立てます", "planning")
        assert "計画" in r

    def test_error_keyword(self, pts):
        r = pts._auto_reflect("エラーが発生しました", "chat")
        assert r  # 何かしら返る


# ── TestGetRecentThoughts ─────────────────────────────────────────────────
class TestGetRecentThoughts:
    def test_returns_recent(self, pts):
        for i in range(5):
            pts.log_thought(f"入力{i}")
        recent = pts.get_recent_thoughts(n=3)
        assert len(recent) == 3


# ── TestRecordEvolution ───────────────────────────────────────────────────
class TestRecordEvolution:
    def test_records_entry(self, pts):
        pts.record_evolution("test trigger", "テスト進化")
        assert len(pts._evolution_log) == 1

    def test_applies_delta(self, pts):
        before = pts._value_scores["honesty"].score
        pts.record_evolution("trigger", "進化", value_deltas={"honesty": 0.05})
        assert pts._value_scores["honesty"].score > before


# ── TestGetEvolutionTimeline ──────────────────────────────────────────────
class TestGetEvolutionTimeline:
    def test_empty_initially(self, pts):
        assert pts.get_evolution_timeline() == []

    def test_returns_after_record(self, pts):
        pts.record_evolution("trig", "desc")
        timeline = pts.get_evolution_timeline()
        assert len(timeline) == 1


# ── TestGetMoodAdjustedPrefix ─────────────────────────────────────────────
class TestGetMoodAdjustedPrefix:
    def test_returns_string_for_all_moods(self, pts):
        for mood in MoodState:
            pts._current_mood = mood
            prefix = pts.get_mood_adjusted_prefix()
            assert isinstance(prefix, str)


# ── TestBuildThoughtContext ───────────────────────────────────────────────
class TestBuildThoughtContext:
    def test_empty_when_no_thoughts(self, pts):
        assert pts.build_thought_context() == ""

    def test_returns_context_string(self, pts):
        pts.log_thought("入力", reflection="内省コメント")
        ctx = pts.build_thought_context(recent_n=1)
        assert "内省コメント" in ctx
