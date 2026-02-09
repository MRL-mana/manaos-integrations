#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト: ManaOS Logger
統一ロガーの初期化、ローテーション設定、get_logger の冪等性を検証
"""

import logging
from pathlib import Path

import pytest

from manaos_logger import setup_logger, get_logger, LOG_DIR


class TestSetupLogger:

    def test_returns_logger(self):
        logger = setup_logger("test_setup", console=True, file=False)
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_setup"

    def test_console_handler_added(self):
        logger = setup_logger("test_console", console=True, file=False)
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "StreamHandler" in handler_types

    def test_file_handler_added(self, tmp_path):
        log_file = tmp_path / "test.log"
        logger = setup_logger("test_file", log_file=log_file, console=False, file=True)
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "RotatingFileHandler" in handler_types

    def test_log_output_to_file(self, tmp_path):
        log_file = tmp_path / "output.log"
        logger = setup_logger("test_output", log_file=log_file, console=False, file=True)
        logger.info("テストメッセージ")
        # ハンドラーをフラッシュ
        for h in logger.handlers:
            h.flush()
        content = log_file.read_text(encoding="utf-8")
        assert "テストメッセージ" in content


class TestGetLogger:

    def test_get_logger_creates_if_missing(self):
        logger = get_logger("brand_new_logger")
        assert isinstance(logger, logging.Logger)
        assert len(logger.handlers) > 0

    def test_get_logger_idempotent(self):
        logger1 = get_logger("idempotent_test")
        handler_count = len(logger1.handlers)
        logger2 = get_logger("idempotent_test")
        assert logger1 is logger2
        assert len(logger2.handlers) == handler_count  # ハンドラーが増えない

    def test_log_dir_exists(self):
        assert LOG_DIR.exists()
        assert LOG_DIR.is_dir()
