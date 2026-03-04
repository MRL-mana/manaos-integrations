#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Drive Indexerテスト
"""

import sys
import os
from pathlib import Path
import pytest

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from file_secretary_db import FileSecretaryDB
from file_secretary_drive_indexer import GoogleDriveIndexer

def test_drive_indexer_smoke():
    db = FileSecretaryDB("file_secretary.db")
    try:
        indexer = GoogleDriveIndexer(db, drive_folder_name="INBOX")
        if (
            not indexer.drive_integration
            or not indexer.drive_integration.is_available()
        ):
            return

        assert indexer.drive_folder_id
        files = indexer.list_drive_files()
        assert isinstance(files, list)
    finally:
        db.close()






















