"""
Unit tests for scripts/misc/content_generation_loop.py
"""
import sys
from datetime import datetime
from unittest.mock import MagicMock

# ── module-level mocks ─────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh.ManaOSErrorHandler = MagicMock(return_value=MagicMock(
    handle_exception=MagicMock(return_value=MagicMock(message="err"))
))
_eh.ErrorCategory = MagicMock()
_eh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout_config = MagicMock(return_value={"llm_call": 30.0})
sys.modules.setdefault("manaos_timeout_config", _tc)

_cv_mod = MagicMock()
_cv_mod.ConfigValidator = MagicMock(return_value=MagicMock(
    validate_config=MagicMock(return_value=(True, []))
))
sys.modules.setdefault("manaos_config_validator", _cv_mod)

_paths_mod = sys.modules.get("_paths") or MagicMock()
_paths_mod.OLLAMA_PORT = 11434
_paths_mod.RAG_MEMORY_PORT = 5600
sys.modules["_paths"] = _paths_mod

_flask_mod = MagicMock()
_flask_mod.Flask.return_value = MagicMock()
_flask_mod.jsonify = MagicMock(side_effect=lambda x: x)
sys.modules.setdefault("flask", _flask_mod)
sys.modules.setdefault("flask_cors", MagicMock())

import pytest  # noqa: E402
from scripts.misc.content_generation_loop import (  # noqa: E402
    ContentGenerationLoop,
    GeneratedContent,
)


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def loop(tmp_path):
    return ContentGenerationLoop(
        db_path=tmp_path / "cgl.db",
        config_path=tmp_path / "no_config.json",  # 存在しない → default config
    )


# ── TestGeneratedContent ───────────────────────────────────────────────────
class TestGeneratedContent:
    def test_fields_accessible(self):
        gc = GeneratedContent(
            content_id="c1",
            source_type="daily_report",
            source_id="r1",
            content_type="blog_draft",
            title="My Blog",
            content="body text",
            status="draft",
            created_at=datetime.now().isoformat(),
            published_at=None,
            metadata={"key": "val"},
        )
        assert gc.content_id == "c1"
        assert gc.status == "draft"
        assert gc.metadata["key"] == "val"

    def test_published_at_none(self):
        gc = GeneratedContent(
            content_id="c2",
            source_type="x",
            source_id="s",
            content_type="y",
            title="t",
            content="c",
            status="draft",
            created_at=datetime.now().isoformat(),
            published_at=None,
            metadata={},
        )
        assert gc.published_at is None


# ── TestGetDefaultConfig ───────────────────────────────────────────────────
class TestGetDefaultConfig:
    def test_has_required_keys(self, loop):
        cfg = loop._get_default_config()
        assert "ollama_url" in cfg
        assert "model" in cfg
        assert "auto_generate" in cfg

    def test_default_auto_generate_is_true(self, loop):
        cfg = loop._get_default_config()
        assert cfg["auto_generate"] is True

    def test_generation_rules_has_three_rules(self, loop):
        cfg = loop._get_default_config()
        rules = cfg.get("generation_rules", {})
        assert "daily_report" in rules
        assert "config_log" in rules
        assert "image_generation" in rules


# ── TestSaveAndGetContents ─────────────────────────────────────────────────
class TestSaveAndGetContents:
    def _make_content(self, cid: str, ctype: str = "blog_draft") -> GeneratedContent:
        return GeneratedContent(
            content_id=cid,
            source_type="daily_report",
            source_id="src1",
            content_type=ctype,
            title=f"Title {cid}",
            content=f"Body {cid}",
            status="draft",
            created_at=datetime.now().isoformat(),
            published_at=None,
            metadata={"gen": "test"},
        )

    def test_save_and_retrieve(self, loop):
        content = self._make_content("cnt1")
        loop._save_content(content)
        results = loop.get_generated_contents()
        found = [r for r in results if r.content_id == "cnt1"]
        assert len(found) == 1
        assert found[0].title == "Title cnt1"

    def test_filter_by_content_type(self, loop):
        loop._save_content(self._make_content("cnt2", "blog_draft"))
        loop._save_content(self._make_content("cnt3", "note_article"))
        blogs = loop.get_generated_contents(content_type="blog_draft")
        assert all(r.content_type == "blog_draft" for r in blogs)

    def test_filter_by_status(self, loop):
        c = self._make_content("cnt4")
        c.status = "published"
        loop._save_content(c)
        loop._save_content(self._make_content("cnt5"))
        published = loop.get_generated_contents(status="published")
        assert all(r.status == "published" for r in published)

    def test_empty_db_returns_empty_list(self, loop):
        results = loop.get_generated_contents()
        assert isinstance(results, list)
        assert results == []

    def test_limit_respected(self, loop):
        for i in range(5):
            loop._save_content(self._make_content(f"lmt{i}"))
        results = loop.get_generated_contents(limit=3)
        assert len(results) <= 3


# ── TestCreateTemplateFromImage ────────────────────────────────────────────
class TestCreateTemplateFromImage:
    def test_returns_generated_content(self, loop):
        image_info = {
            "id": "img1",
            "prompt": "a cat on a bed",
            "image_path": "/tmp/cat.png",
            "quality_score": 0.85,
        }
        result = loop.create_template_from_image(image_info)
        assert result is not None
        assert isinstance(result, GeneratedContent)

    def test_content_type_is_template_product(self, loop):
        result = loop.create_template_from_image({
            "id": "img2",
            "prompt": "mountain",
            "image_path": "/tmp/mountain.png",
            "quality_score": 0.8,
        })
        assert result.content_type == "template_product"

    def test_low_quality_skipped(self, loop):
        result = loop.create_template_from_image({
            "id": "img3",
            "prompt": "blur",
            "image_path": "/tmp/blur.png",
            "quality_score": 0.3,
        })
        assert result is None

    def test_template_saved_to_db(self, loop):
        loop.create_template_from_image({
            "id": "img4",
            "prompt": "sunset",
            "image_path": "/tmp/sun.png",
            "quality_score": 0.9,
        })
        results = loop.get_generated_contents(content_type="template_product")
        assert len(results) == 1
