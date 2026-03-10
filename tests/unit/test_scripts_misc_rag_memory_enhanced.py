"""
Unit tests for scripts/misc/rag_memory_enhanced.py
（RAGMemoryEnhancedV2 への互換ラッパー）
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ─── Module-level mocking (before any import of the target module) ─────────────
class _FakeRAGV2:
    """テスト用の RAGMemoryEnhancedV2 スタブ（args を属性として保存）"""
    def __init__(self, db_path=None, ollama_url=None, model=None, **kwargs):
        self.db_path = db_path
        self.ollama_url = ollama_url
        self.model = model

    def semantic_search(self, query, limit=10, min_importance=0.0):
        return []


_v2_mod = MagicMock()
_v2_mod.RAGMemoryEnhancedV2 = _FakeRAGV2
_v2_mod.MemoryEntry = MagicMock()
# Force-set (not setdefault) because rag_memory_enhanced_v2 is a local custom module
sys.modules["rag_memory_enhanced_v2"] = _v2_mod

_paths_mod = sys.modules.get("_paths") or MagicMock()
_paths_mod.OLLAMA_PORT = 11434  # type: ignore
sys.modules.setdefault("_paths", _paths_mod)

_ul_mod = MagicMock()
_ul_mod.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("unified_logging", _ul_mod)

# Remove existing cached import so fresh mock-backed import is used
for _key in ("scripts.misc.rag_memory_enhanced", "rag_memory_enhanced"):
    sys.modules.pop(_key, None)

from scripts.misc.rag_memory_enhanced import RAGMemoryEnhanced  # noqa: E402


# ─── Init ─────────────────────────────────────────────────────────────────────
class TestRAGMemoryEnhancedInit:
    def test_default_db_path_used_when_none(self):
        """db_path=None のとき rag_memory.db がデフォルトになる"""
        obj = RAGMemoryEnhanced()
        assert obj.db_path.name == "rag_memory.db"

    def test_config_path_overrides_url_and_model(self, tmp_path: Path):
        """config_path が存在するとき、その設定で上書きされる"""
        config = {"ollama_url": "http://custom:11435", "model": "custom-model:7b"}
        cfg_path = tmp_path / "cfg.json"
        cfg_path.write_text(json.dumps(config), encoding="utf-8")

        obj = RAGMemoryEnhanced(config_path=cfg_path)

        assert obj.ollama_url == "http://custom:11435"
        assert obj.model == "custom-model:7b"

    def test_config_path_not_exists_uses_defaults(self, tmp_path: Path):
        """config_path が存在しない場合はデフォルトをそのまま渡す"""
        non_existent = tmp_path / "no_cfg.json"
        obj = RAGMemoryEnhanced(config_path=non_existent)
        assert obj.model == "qwen2.5:14b"

    def test_invalid_config_json_does_not_raise(self, tmp_path: Path):
        """config_path が壊れた JSON でもクラッシュしない"""
        cfg_path = tmp_path / "bad.json"
        cfg_path.write_text("NOT JSON", encoding="utf-8")
        # 例外を投げずに初期化が完了する
        obj = RAGMemoryEnhanced(config_path=cfg_path)
        assert obj is not None

    def test_explicit_db_path_passed_through(self, tmp_path: Path):
        """明示的に指定した db_path がそのまま渡される"""
        db = tmp_path / "my.db"
        obj = RAGMemoryEnhanced(db_path=db)
        assert obj.db_path == db


# ─── search method ────────────────────────────────────────────────────────────
class TestRAGMemoryEnhancedSearch:
    def _make_obj(self, fake_results):
        """super().__init__ を避けてオブジェクトを直接組み立てる"""
        obj = RAGMemoryEnhanced.__new__(RAGMemoryEnhanced)
        obj.semantic_search = MagicMock(return_value=fake_results)
        return obj

    def test_search_returns_only_entries(self):
        e1, e2 = MagicMock(), MagicMock()
        obj = self._make_obj([(e1, 0.9), (e2, 0.7)])
        result = obj.search("test query")
        assert result == [e1, e2]

    def test_search_calls_semantic_search_with_correct_args(self):
        obj = self._make_obj([])
        obj.search("my query", limit=5, min_importance=0.3)
        obj.semantic_search.assert_called_once_with("my query", 5, 0.3)  # type: ignore

    def test_search_default_args(self):
        obj = self._make_obj([])
        obj.search("q")
        obj.semantic_search.assert_called_once_with("q", 10, 0.0)  # type: ignore

    def test_search_returns_empty_list_when_no_results(self):
        obj = self._make_obj([])
        result = obj.search("nothing")
        assert result == []
