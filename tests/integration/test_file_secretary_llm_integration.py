#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Secretary LLM統合テスト
常時起動LLM（Ollama）との統合確認
"""

import sys
from pathlib import Path
from datetime import datetime

import pytest
import httpx

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from file_secretary_db import FileSecretaryDB
from file_secretary_organizer import FileOrganizer
from file_secretary_schemas import FileRecord, FileType, FileStatus, FileSource

def _ollama_ready() -> bool:
    try:
        response = httpx.get("http://127.0.0.1:11434/api/tags", timeout=5.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


def test_ollama_connection():
    if not _ollama_ready():
        pytest.skip("Ollama is not available")

    response = httpx.get("http://127.0.0.1:11434/api/tags", timeout=5.0)
    assert response.status_code == 200


def test_llm_tag_inference():
    if not _ollama_ready():
        pytest.skip("Ollama is not available")

    db = FileSecretaryDB("file_secretary.db")
    try:
        organizer = FileOrganizer(db)
        test_file = FileRecord(
            id="test_llm_001",
            source=FileSource.MOTHER,
            path="test_日報_2026年1月.pdf",
            original_name="test_日報_2026年1月.pdf",
            created_at=datetime.now().isoformat(),
            status=FileStatus.TRIAGED,
            type=FileType.PDF,
            size=1024,
        )
        tags = organizer._infer_tags_llm(test_file)
        assert isinstance(tags, list)
    finally:
        db.close()


def test_keyword_fallback():
    db = FileSecretaryDB("file_secretary.db")
    try:
        organizer = FileOrganizer(db)
        test_file = FileRecord(
            id="test_keyword_001",
            source=FileSource.MOTHER,
            path="test_日報.pdf",
            original_name="test_日報.pdf",
            created_at=datetime.now().isoformat(),
            status=FileStatus.TRIAGED,
            type=FileType.PDF,
            size=1024,
        )
        tags = organizer._infer_tags_simple(test_file)
        assert isinstance(tags, list)
    finally:
        db.close()























