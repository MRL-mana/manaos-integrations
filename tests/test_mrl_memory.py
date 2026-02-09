#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト: MRL Memory Extractor / Retriever
Scratchpad への書き込み・読み取り、パターン抽出、スレッド安全性を検証
"""

import json
import threading
from pathlib import Path
from datetime import datetime

import pytest

from mrl_memory_extractor import MRLMemoryExtractor, MRLMemoryRetriever, MemoryEntry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def memory_dir(tmp_path):
    """テスト用の空メモリディレクトリを返す"""
    d = tmp_path / "mrl_memory"
    d.mkdir()
    return d


@pytest.fixture()
def extractor(memory_dir):
    return MRLMemoryExtractor(memory_dir=memory_dir)


@pytest.fixture()
def retriever(memory_dir):
    return MRLMemoryRetriever(memory_dir=memory_dir)


# ---------------------------------------------------------------------------
# MRLMemoryExtractor
# ---------------------------------------------------------------------------


class TestExtract:
    """テキストからメモリエントリを抽出するテスト"""

    def test_extract_proper_noun(self, extractor):
        text = "田中さんに連絡する"
        entries = extractor.extract(text, source="test")
        # 固有名詞パターンに「さん」が含まれている場合
        assert isinstance(entries, list)

    def test_extract_number_pattern(self, extractor):
        text = "予算は150万円です"
        entries = extractor.extract(text, source="budget")
        assert isinstance(entries, list)
        # 数値パターンでマッチするはず
        values = [e.value for e in entries]
        matching = [v for v in values if "150" in v or "万" in v]
        assert len(matching) >= 1, f"Number not extracted from: {values}"

    def test_extract_todo_pattern(self, extractor):
        text = "TODO: レポートを完成させる"
        entries = extractor.extract(text, source="note")
        assert isinstance(entries, list)
        values = [e.value for e in entries]
        matching = [v for v in values if "レポート" in v or "TODO" in v]
        assert len(matching) >= 1, f"TODO not extracted from: {values}"

    def test_extract_returns_memoryentry(self, extractor):
        entries = extractor.extract("テスト文", source="unit_test")
        for entry in entries:
            assert isinstance(entry, MemoryEntry)
            assert entry.source == "unit_test"
            assert entry.timestamp  # 空でない

    def test_extract_empty_text(self, extractor):
        entries = extractor.extract("", source="test")
        assert entries == []


class TestScratchpad:
    """Scratchpad への書き込み・読み取りのテスト"""

    def test_append_and_read(self, extractor):
        entry = MemoryEntry(
            timestamp=datetime.now().isoformat(),
            source="test",
            key="proper_noun",
            value="テストユーザー",
            confidence="high",
            ttl="1d",
        )
        extractor.append_to_scratchpad([entry])
        recent = extractor.get_recent_entries(hours=1, limit=10)
        assert len(recent) >= 1
        assert any("テストユーザー" in str(r.get("value", "")) for r in recent)

    def test_process_text_writes_scratchpad(self, extractor):
        text = "TODO: テストを書く 締切は2026年3月1日"
        entries = extractor.process_text(text, source="ci")
        # process_text = extract + append
        recent = extractor.get_recent_entries(hours=1, limit=50)
        assert len(recent) >= len(entries)

    def test_scratchpad_file_created(self, extractor, memory_dir):
        entry = MemoryEntry(
            timestamp=datetime.now().isoformat(),
            source="test",
            key="test",
            value="file_check",
            confidence="med",
            ttl="1h",
        )
        extractor.append_to_scratchpad([entry])
        assert (memory_dir / "scratchpad.jsonl").exists()

    def test_scratchpad_jsonl_format(self, extractor, memory_dir):
        entry = MemoryEntry(
            timestamp=datetime.now().isoformat(),
            source="test",
            key="k1",
            value="v1",
            confidence="low",
            ttl="1h",
        )
        extractor.append_to_scratchpad([entry])
        lines = (memory_dir / "scratchpad.jsonl").read_text(encoding="utf-8").strip().splitlines()
        for line in lines:
            data = json.loads(line)
            assert "value" in data


class TestConcurrentScratchpad:
    """スレッド安全性のテスト"""

    def test_concurrent_writes_no_corruption(self, extractor, memory_dir):
        """複数スレッドから同時書き込みしても JSONL が壊れない"""
        errors = []

        def writer(thread_id):
            try:
                for i in range(20):
                    entry = MemoryEntry(
                        timestamp=datetime.now().isoformat(),
                        source=f"thread_{thread_id}",
                        key="concurrent",
                        value=f"val_{thread_id}_{i}",
                        confidence="med",
                        ttl="1h",
                    )
                    extractor.append_to_scratchpad([entry])
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors during concurrent writes: {errors}"

        # 全行が有効な JSON であること
        path = memory_dir / "scratchpad.jsonl"
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 100  # 5 threads × 20 writes
        for i, line in enumerate(lines):
            json.loads(line)  # パースできなければ AssertionError


# ---------------------------------------------------------------------------
# MRLMemoryRetriever
# ---------------------------------------------------------------------------


class TestRetriever:

    def test_retrieve_empty(self, retriever):
        results = retriever.retrieve("テスト", limit=5)
        assert results == []

    def test_retrieve_finds_matching(self, extractor, retriever):
        entries = [
            MemoryEntry(
                timestamp=datetime.now().isoformat(),
                source="test",
                key="proper_noun",
                value="Pythonの学習",
                confidence="high",
                ttl="7d",
            ),
            MemoryEntry(
                timestamp=datetime.now().isoformat(),
                source="test",
                key="decision",
                value="Rustを導入する",
                confidence="med",
                ttl="7d",
            ),
        ]
        extractor.append_to_scratchpad(entries)
        results = retriever.retrieve("Python", limit=5)
        assert len(results) >= 1
        assert any("Python" in str(r) for r in results)

    def test_get_context_for_llm(self, extractor, retriever):
        entry = MemoryEntry(
            timestamp=datetime.now().isoformat(),
            source="test",
            key="fact",
            value="ManaOSはメモリベースのAIアシスタント",
            confidence="high",
            ttl="7d",
        )
        extractor.append_to_scratchpad([entry])
        ctx = retriever.get_context_for_llm("ManaOSとは", limit=5)
        assert isinstance(ctx, str)
