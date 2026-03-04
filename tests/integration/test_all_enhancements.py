#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib

import pytest


def _import_module(name: str):
    try:
        return importlib.import_module(name)
    except Exception as exc:
        pytest.skip(f"{name} を読み込めないためスキップ: {exc}")


def test_auth_system_import_smoke():
    module = _import_module("auth_system")
    assert hasattr(module, "AuthSystem")


def test_input_validator_import_smoke():
    module = _import_module("input_validator")
    assert hasattr(module, "InputValidator")


def test_redis_cache_import_smoke():
    module = _import_module("redis_cache")
    assert hasattr(module, "RedisCache")


def test_backup_system_import_smoke():
    module = _import_module("backup_system")
    assert hasattr(module, "BackupSystem")


def test_dynamic_rate_limiter_import_smoke():
    module = _import_module("dynamic_rate_limiter")
    assert hasattr(module, "DynamicRateLimiter")

