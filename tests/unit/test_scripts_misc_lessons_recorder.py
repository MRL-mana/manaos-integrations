"""
Unit tests for scripts/misc/lessons_recorder.py
Uses :memory: SQLite to avoid disk I/O.
"""
import sys
import pytest
from unittest.mock import MagicMock

# manaos_logger optional — file has try/except fallback
sys.modules.setdefault("manaos_logger", MagicMock(
    get_service_logger=MagicMock(return_value=MagicMock())
))

# 他のテストがモックを注入している可能性があるので強制リロード
sys.modules.pop("lessons_recorder", None)

sys.path.insert(0, "scripts/misc")
from lessons_recorder import (
    Lesson,
    LessonsRecorder,
    CORRECTION_KEYWORDS,
    CATEGORIES,
    get_lessons_recorder,
)


# ── Lesson.make_id ───────────────────────────────────────────────────────────

class TestLessonMakeId:
    def test_returns_string(self):
        lid = Lesson.make_id("some instruction")
        assert isinstance(lid, str)

    def test_deterministic(self):
        l1 = Lesson.make_id("test")
        l2 = Lesson.make_id("test")
        assert l1 == l2

    def test_different_instructions_different_ids(self):
        l1 = Lesson.make_id("aaa")
        l2 = Lesson.make_id("bbb")
        assert l1 != l2

    def test_id_length_is_twelve(self):
        lid = Lesson.make_id("hello world")
        assert len(lid) == 12

    def test_id_is_hex(self):
        lid = Lesson.make_id("data")
        assert all(c in "0123456789abcdef" for c in lid)


# ── LessonsRecorder.detect_correction ────────────────────────────────────────

class TestDetectCorrection:
    def test_detects_japanese_keyword(self):
        assert LessonsRecorder.detect_correction("それは違います") is True

    def test_detects_english_keyword(self):
        assert LessonsRecorder.detect_correction("That is wrong") is True

    def test_no_keyword_returns_false(self):
        assert LessonsRecorder.detect_correction("Thank you very much") is False

    def test_empty_string_returns_false(self):
        assert LessonsRecorder.detect_correction("") is False

    def test_修正_keyword(self):
        assert LessonsRecorder.detect_correction("修正してください") is True

    def test_case_insensitive(self):
        assert LessonsRecorder.detect_correction("WRONG answer") is True


# ── LessonsRecorder.extract_lesson ───────────────────────────────────────────

class TestExtractLesson:
    def test_returns_string(self):
        result = LessonsRecorder.extract_lesson("短く書いてください")
        assert isinstance(result, str)

    def test_returns_longest_sentence(self):
        text = "短い。もっと長い文を選んでください。短い。"
        result = LessonsRecorder.extract_lesson(text)
        assert "長い文を選んでください" in result

    def test_single_sentence_returned_as_is(self):
        text = "3行以内に収めること"
        result = LessonsRecorder.extract_lesson(text)
        assert "3行以内に収めること" in result

    def test_strips_whitespace(self):
        result = LessonsRecorder.extract_lesson("   clean text   ")
        assert result == result.strip()


# ── LessonsRecorder.record_lesson ────────────────────────────────────────────

class TestRecordLesson:
    def setup_method(self):
        self.lr = LessonsRecorder(db_path=":memory:")

    def test_returns_lesson_instance(self):
        lesson = self.lr.record_lesson("3行以内にまとめよ")
        assert isinstance(lesson, Lesson)

    def test_instruction_stored(self):
        lesson = self.lr.record_lesson("keep it short")
        assert lesson.instruction == "keep it short"

    def test_default_category_is_other(self):
        lesson = self.lr.record_lesson("x")
        assert lesson.category == "other"

    def test_custom_category_stored(self):
        lesson = self.lr.record_lesson("format issue", category="output_format")
        assert lesson.category == "output_format"

    def test_unknown_category_falls_back_to_other(self):
        lesson = self.lr.record_lesson("x", category="nonexistent")
        assert lesson.category == "other"

    def test_access_count_starts_at_one(self):
        lesson = self.lr.record_lesson("new lesson")
        assert lesson.access_count == 1

    def test_duplicate_increments_access_count(self):
        self.lr.record_lesson("same lesson")
        result = self.lr.record_lesson("same lesson")
        assert result.access_count == 2

    def test_duplicate_same_id(self):
        l1 = self.lr.record_lesson("identical")
        l2 = self.lr.record_lesson("identical")
        assert l1.lesson_id == l2.lesson_id

    def test_tags_stored(self):
        lesson = self.lr.record_lesson("x", tags=["tag1", "tag2"])
        assert "tag1" in lesson.tags

    def test_session_id_stored(self):
        lesson = self.lr.record_lesson("x", session_id="sess-abc")
        assert lesson.session_id == "sess-abc"

    def test_trigger_text_stored(self):
        lesson = self.lr.record_lesson("x", trigger_text="original trigger")
        assert lesson.trigger_text == "original trigger"


# ── LessonsRecorder.search_lessons ───────────────────────────────────────────

class TestSearchLessons:
    def setup_method(self):
        self.lr = LessonsRecorder(db_path=":memory:")

    def test_empty_returns_empty_list(self):
        assert self.lr.search_lessons("test") == []

    def test_finds_matching_instruction(self):
        self.lr.record_lesson("output format must be short")
        results = self.lr.search_lessons("format")
        assert len(results) == 1
        assert "format" in results[0].instruction

    def test_no_match_returns_empty(self):
        self.lr.record_lesson("something else")
        assert self.lr.search_lessons("nomatch") == []

    def test_filter_by_category(self):
        self.lr.record_lesson("tech issue", category="technical")
        self.lr.record_lesson("format issue", category="output_format")
        results = self.lr.search_lessons(category="technical")
        assert all(r.category == "technical" for r in results)

    def test_filter_by_category_and_query(self):
        self.lr.record_lesson("tech problem X", category="technical")
        self.lr.record_lesson("tech problem Y", category="output_format")
        results = self.lr.search_lessons("tech", category="technical")
        assert len(results) == 1

    def test_empty_query_returns_all(self):
        self.lr.record_lesson("lesson one")
        self.lr.record_lesson("lesson two")
        results = self.lr.search_lessons()
        assert len(results) == 2

    def test_limit_respected(self):
        for i in range(10):
            self.lr.record_lesson(f"lesson {i}")
        results = self.lr.search_lessons(limit=3)
        assert len(results) <= 3

    def test_returns_list_of_lesson(self):
        self.lr.record_lesson("x")
        results = self.lr.search_lessons()
        assert all(isinstance(r, Lesson) for r in results)


# ── LessonsRecorder.get_context_text ─────────────────────────────────────────

class TestGetContextText:
    def setup_method(self):
        self.lr = LessonsRecorder(db_path=":memory:")

    def test_empty_recorder_returns_empty_string(self):
        assert self.lr.get_context_text() == ""

    def test_returns_string(self):
        self.lr.record_lesson("keep output short")
        result = self.lr.get_context_text()
        assert isinstance(result, str)

    def test_contains_lesson_instruction(self):
        self.lr.record_lesson("use markdown format")
        text = self.lr.get_context_text()
        assert "use markdown format" in text

    def test_header_present(self):
        self.lr.record_lesson("x")
        text = self.lr.get_context_text()
        assert "教訓" in text or "指摘" in text

    def test_multiple_lessons_numbered(self):
        self.lr.record_lesson("lesson one")
        self.lr.record_lesson("lesson two")
        text = self.lr.get_context_text()
        assert "1." in text
        assert "2." in text

    def test_repeated_lesson_shows_count(self):
        self.lr.record_lesson("keep it short")
        self.lr.record_lesson("keep it short")  # duplicate → access_count=2
        text = self.lr.get_context_text()
        assert "2回" in text

    def test_limit_controls_number_of_lessons(self):
        for i in range(10):
            self.lr.record_lesson(f"lesson {i}")
        text = self.lr.get_context_text(limit=3)
        # Count number of lines starting with a digit
        digit_lines = [l for l in text.split("\n") if l and l[0].isdigit()]
        assert len(digit_lines) <= 3


# ── LessonsRecorder.delete_lesson ────────────────────────────────────────────

class TestDeleteLesson:
    def setup_method(self):
        self.lr = LessonsRecorder(db_path=":memory:")

    def test_delete_returns_true(self):
        lesson = self.lr.record_lesson("to be deleted")
        assert self.lr.delete_lesson(lesson.lesson_id) is True

    def test_deleted_lesson_not_in_search(self):
        lesson = self.lr.record_lesson("delete this")
        self.lr.delete_lesson(lesson.lesson_id)
        results = self.lr.search_lessons("delete this")
        assert len(results) == 0

    def test_delete_nonexistent_returns_true(self):
        # Implementation always returns True
        assert self.lr.delete_lesson("no-such-id") is True


# ── LessonsRecorder.stats ────────────────────────────────────────────────────

class TestStats:
    def setup_method(self):
        self.lr = LessonsRecorder(db_path=":memory:")

    def test_stats_returns_dict(self):
        assert isinstance(self.lr.stats(), dict)

    def test_total_zero_on_empty(self):
        assert self.lr.stats()["total"] == 0

    def test_total_increments_on_record(self):
        self.lr.record_lesson("x")
        self.lr.record_lesson("y")
        assert self.lr.stats()["total"] == 2

    def test_by_category_tracks_categories(self):
        self.lr.record_lesson("x", category="technical")
        stats = self.lr.stats()
        assert "technical" in stats["by_category"]

    def test_top_repeated_list(self):
        self.lr.record_lesson("repeat", )
        self.lr.record_lesson("repeat")  # access_count=2
        stats = self.lr.stats()
        assert isinstance(stats["top_repeated"], list)


# ── CATEGORIES / CORRECTION_KEYWORDS constants ───────────────────────────────

class TestConstants:
    def test_categories_list_not_empty(self):
        assert len(CATEGORIES) > 0

    def test_other_in_categories(self):
        assert "other" in CATEGORIES

    def test_correction_keywords_not_empty(self):
        assert len(CORRECTION_KEYWORDS) > 0

    def test_correction_keywords_include_japanese(self):
        japanese_kws = [k for k in CORRECTION_KEYWORDS if any(
            '\u3000' <= c <= '\u9fff' for c in k
        )]
        assert len(japanese_kws) > 0


# ── get_lessons_recorder singleton ──────────────────────────────────────────

class TestGetLessonsRecorder:
    def test_returns_lessons_recorder(self):
        import lessons_recorder as lr_mod
        lr_mod._instance = None
        instance = get_lessons_recorder(":memory:")
        assert isinstance(instance, LessonsRecorder)

    def test_singleton_behavior(self):
        import lessons_recorder as lr_mod
        lr_mod._instance = None
        i1 = get_lessons_recorder(":memory:")
        i2 = get_lessons_recorder()
        assert i1 is i2
