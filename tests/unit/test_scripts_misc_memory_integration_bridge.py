"""
Unit tests for scripts/misc/memory_integration_bridge.py
"""
import sys
from unittest.mock import MagicMock

# ── external module mocks ──────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

# Block optional dependencies at import time
sys.modules.setdefault("memory_unified", MagicMock())
sys.modules.setdefault("phase2_reflection_memo", MagicMock())

import pytest  # noqa: E402
import scripts.misc.memory_integration_bridge as mib  # noqa: E402


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def mock_um():
    """モック UnifiedMemory"""
    um = MagicMock()
    um.store.return_value = "mem_001"
    um.recall.return_value = [
        {"id": "1", "content": "result1"},
        {"id": "2", "content": "result2"},
    ]
    return um


@pytest.fixture
def mock_mem0():
    """モック Mem0 integration"""
    m = MagicMock()
    m.is_available.return_value = True
    return m


# ── TestMemoryStore ────────────────────────────────────────────────────────
class TestMemoryStore:
    def test_returns_memory_id(self, mock_um):
        result = mib.memory_store({"content": "hello"}, memory_unified=mock_um)
        assert result == "mem_001"

    def test_calls_um_store(self, mock_um):
        mib.memory_store({"content": "x"}, "auto", memory_unified=mock_um)
        mock_um.store.assert_called_once_with({"content": "x"}, "auto")

    def test_no_um_returns_local_only(self):
        # MEMORY_UNIFIED_AVAILABLE=False の場合
        orig = mib.MEMORY_UNIFIED_AVAILABLE
        mib.MEMORY_UNIFIED_AVAILABLE = False
        result = mib.memory_store({"content": "x"}, memory_unified=None)
        mib.MEMORY_UNIFIED_AVAILABLE = orig
        assert result == "local_only"

    def test_um_exception_propagates(self, mock_um):
        mock_um.store.side_effect = Exception("store failed")
        with pytest.raises(Exception, match="store failed"):
            mib.memory_store({"content": "x"}, memory_unified=mock_um)

    def test_forwards_to_mem0(self, mock_um, mock_mem0):
        mib.memory_store(
            {"content": "hello", "metadata": {"user_id": "u1"}},
            memory_unified=mock_um,
            mem0_integration=mock_mem0,
        )
        mock_mem0.add_memory.assert_called_once()

    def test_no_mem0_forward_when_unavailable(self, mock_um):
        mock_mem0 = MagicMock()
        mock_mem0.is_available.return_value = False
        mib.memory_store({"content": "x"}, memory_unified=mock_um, mem0_integration=mock_mem0)
        mock_mem0.add_memory.assert_not_called()

    def test_mem0_no_hasattr_is_available(self, mock_um):
        """is_available 属性がないオブジェクトを渡しても落ちない"""
        mem0_no_attr = object()
        result = mib.memory_store(
            {"content": "x"}, memory_unified=mock_um, mem0_integration=mem0_no_attr
        )
        assert result == "mem_001"

    def test_mem0_exception_does_not_raise(self, mock_um, mock_mem0):
        mock_mem0.add_memory.side_effect = Exception("mem0 error")
        # Should not raise - mem0 errors are logged and swallowed
        result = mib.memory_store(
            {"content": "x"}, memory_unified=mock_um, mem0_integration=mock_mem0
        )
        assert result == "mem_001"


# ── TestMemoryRecall ───────────────────────────────────────────────────────
class TestMemoryRecall:
    def test_returns_list(self, mock_um):
        result = mib.memory_recall("test query", memory_unified=mock_um)
        assert isinstance(result, list)

    def test_returns_results_from_um(self, mock_um):
        result = mib.memory_recall("query", memory_unified=mock_um)
        assert len(result) == 2

    def test_calls_um_recall_with_correct_args(self, mock_um):
        mib.memory_recall("query", scope="recent", limit=5, memory_unified=mock_um)
        mock_um.recall.assert_called_once_with("query", "recent", 5)

    def test_no_um_returns_empty_list(self):
        orig = mib.MEMORY_UNIFIED_AVAILABLE
        mib.MEMORY_UNIFIED_AVAILABLE = False
        result = mib.memory_recall("query", include_phase2=False, memory_unified=None)
        mib.MEMORY_UNIFIED_AVAILABLE = orig
        assert result == []

    def test_um_exception_returns_partial_results(self, mock_um):
        mock_um.recall.side_effect = Exception("recall error")
        result = mib.memory_recall("query", memory_unified=mock_um)
        assert isinstance(result, list)

    def test_phase2_disabled(self, mock_um):
        result = mib.memory_recall("query", include_phase2=False, memory_unified=mock_um)
        # Only UM results
        assert len(result) == 2
