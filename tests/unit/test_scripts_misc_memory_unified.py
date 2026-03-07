"""
Unit tests for scripts/misc/memory_unified.py
"""
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

# obsidian_integration mock (OBSIDIAN_AVAILABLE = False path)
sys.modules.setdefault("obsidian_integration", MagicMock())

import pytest
import scripts.misc.memory_unified as mu
from scripts.misc.memory_unified import UnifiedMemory, ObsidianError


@pytest.fixture
def mem(tmp_path):
    """Obsidianなし、tmp_path をキャッシュにした UnifiedMemory"""
    um = UnifiedMemory(
        vault_path=str(tmp_path / "vault"),
        cache_dir=str(tmp_path / "cache"),
    )
    um.obsidian = None  # ensure no real obsidian
    return um


# ── TestFormatContent ──────────────────────────────────────────────────────
class TestFormatContent:
    def test_id_is_string(self, mem):
        result = mem._format_content({"content": "hello"}, "conversation")
        assert isinstance(result["id"], str)

    def test_type_stored(self, mem):
        result = mem._format_content({"content": "hello"}, "memo")
        assert result["type"] == "memo"

    def test_input_type_set_for_input_types(self, mem):
        for t in mu.UnifiedMemory.INPUT_TYPES:
            result = mem._format_content({"content": "x"}, t)
            assert result.get("input_type") == t

    def test_output_type_set_for_output_types(self, mem):
        for t in mu.UnifiedMemory.OUTPUT_TYPES:
            result = mem._format_content({"content": "x"}, t)
            assert result.get("output_type") == t

    def test_metadata_from_content(self, mem):
        result = mem._format_content({"content": "hi", "metadata": {"k": "v"}}, "system")
        assert result["metadata"]["k"] == "v"

    def test_source_set_for_output_type(self, mem):
        result = mem._format_content({"content": "x", "source": "src123"}, "summary")
        assert result["source"] == "src123"


# ── TestGetFolderForType ───────────────────────────────────────────────────
class TestGetFolderForType:
    def test_known_types(self, mem):
        assert mem._get_folder_for_type("conversation") == "Conversations"
        assert mem._get_folder_for_type("memo") == "Memos"
        assert mem._get_folder_for_type("research") == "Research"
        assert mem._get_folder_for_type("system") == "System"
        assert mem._get_folder_for_type("summary") == "Summaries"
        assert mem._get_folder_for_type("judgment") == "Judgments"
        assert mem._get_folder_for_type("action") == "Actions"
        assert mem._get_folder_for_type("learning") == "Learning"

    def test_unknown_type_returns_misc(self, mem):
        assert mem._get_folder_for_type("unknown_xyz") == "Misc"


# ── TestGenerateTitle ─────────────────────────────────────────────────────
class TestGenerateTitle:
    def test_conversation_title_prefix(self, mem):
        fc = {"type": "conversation", "timestamp": "2026-03-08T10:00:00", "content": "hi"}
        title = mem._generate_title(fc)
        assert "会話" in title
        assert "2026-03-08" in title

    def test_summary_title_prefix(self, mem):
        fc = {"type": "summary", "timestamp": "2026-03-08T10:00:00", "content": "x"}
        title = mem._generate_title(fc)
        assert "要約" in title

    def test_unknown_type_uses_type_name(self, mem):
        fc = {"type": "unknown_type", "timestamp": "2026-03-08T10:00:00", "content": "x"}
        title = mem._generate_title(fc)
        assert "unknown_type" in title


# ── TestFormatToMarkdown ───────────────────────────────────────────────────
class TestFormatToMarkdown:
    def test_contains_content_section(self, mem):
        fc = {"type": "memo", "content": "テスト内容", "timestamp": "2026-03-08T10:00:00", "metadata": {}}
        md = mem._format_to_markdown(fc)
        assert "## コンテンツ" in md
        assert "テスト内容" in md

    def test_metadata_section_present_when_non_empty(self, mem):
        fc = {"type": "memo", "content": "x", "timestamp": "ts", "metadata": {"key": "val"}}
        md = mem._format_to_markdown(fc)
        assert "## メタデータ" in md
        assert "key" in md

    def test_source_section_present_for_output(self, mem):
        fc = {"type": "summary", "content": "x", "timestamp": "ts", "metadata": {}, "source": "id123"}
        md = mem._format_to_markdown(fc)
        assert "## ソース" in md
        assert "id123" in md


# ── TestGenerateTags ──────────────────────────────────────────────────────
class TestGenerateTags:
    def test_base_tags_present(self, mem):
        fc = {"type": "system", "metadata": {}}
        tags = mem._generate_tags(fc)
        assert "ManaOS" in tags
        assert "UnifiedMemory" in tags

    def test_type_tag_added(self, mem):
        fc = {"type": "research", "metadata": {}}
        tags = mem._generate_tags(fc)
        assert "research" in tags

    def test_metadata_tags_extended(self, mem):
        fc = {"type": "memo", "metadata": {"tags": ["tag_a", "tag_b"]}}
        tags = mem._generate_tags(fc)
        assert "tag_a" in tags
        assert "tag_b" in tags


# ── TestDetectFormatType ───────────────────────────────────────────────────
class TestDetectFormatType:
    def test_conversation_keyword(self, mem):
        assert mem._detect_format_type({"content": "this is a conversation"}) == "conversation"

    def test_japanese_memo_keyword(self, mem):
        assert mem._detect_format_type({"content": "メモに追加"}) == "memo"

    def test_summary_keyword(self, mem):
        assert mem._detect_format_type({"content": "summary of the meeting"}) == "summary"

    def test_default_is_system(self, mem):
        assert mem._detect_format_type({"content": "random text xyz"}) == "system"


# ── TestSaveToLocalCache ───────────────────────────────────────────────────
class TestSaveToLocalCache:
    def test_saves_file_and_returns_id(self, mem, tmp_path):
        fc = {"id": "test_id_001", "type": "memo", "content": "hello", "timestamp": "2026-03-08T00:00:00"}
        cache_id = mem._save_to_local_cache(fc)
        assert cache_id is not None
        assert isinstance(cache_id, str)

    def test_saved_file_is_valid_json(self, mem, tmp_path):
        fc = {"id": "test_id_002", "type": "system", "content": "data", "timestamp": "2026-03-08T00:00:00"}
        mem._save_to_local_cache(fc)
        # find the saved file
        files = list(mem.cache_dir.glob("*.json"))
        assert len(files) >= 1
        with open(files[0], encoding="utf-8") as f:
            data = json.load(f)
        assert data["content"] == "data"


# ── TestStore (fallback path) ─────────────────────────────────────────────
class TestStore:
    def test_store_falls_back_to_cache_when_no_obsidian(self, mem):
        """obsidian=None なので必ずローカルキャッシュに保存される"""
        mem_id = mem.store({"content": "test store"}, "memo")
        assert isinstance(mem_id, str)
        assert len(mem_id) > 0

    def test_store_auto_detect(self, mem):
        mem_id = mem.store({"content": "会話テスト"})
        assert isinstance(mem_id, str)
