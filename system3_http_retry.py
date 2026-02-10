#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System 3 HTTP リトライユーティリティ
指数バックオフで API 呼び出しをリトライする
"""

import json
import os
import time
import urllib.request
from typing import Dict, Any, Optional

_DEFAULT_TIMEOUT = int(os.getenv("SYSTEM3_HTTP_TIMEOUT", "10"))


def http_get_json_retry(
    url: str,
    timeout: Optional[int] = None,
    retries: int = 3,
    base_delay: float = 1.0,
) -> Optional[Dict[str, Any]]:
    """GET JSON with exponential backoff retry."""
    timeout = timeout if timeout is not None else _DEFAULT_TIMEOUT
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            return json.loads(raw.decode("utf-8"))
        except Exception:
            if attempt < retries - 1:
                time.sleep(base_delay * (2**attempt))
    return None


def http_post_json_retry(
    url: str,
    data: Dict[str, Any],
    timeout: Optional[int] = None,
    retries: int = 3,
    base_delay: float = 1.0,
) -> Optional[Dict[str, Any]]:
    """POST JSON with exponential backoff retry."""
    timeout = timeout if timeout is not None else _DEFAULT_TIMEOUT
    body = json.dumps(data).encode("utf-8")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            return json.loads(raw.decode("utf-8"))
        except Exception:
            if attempt < retries - 1:
                time.sleep(base_delay * (2**attempt))
    return None
