"""
tests/e2e/conftest.py

E2E テスト用設定。
実サービス (localhost:9502-9509) が起動していない場合は全テストをスキップ。

使い方:
  # サービス起動後に実行
  E2E_SERVICES=1 python -m pytest tests/e2e/ -v
"""

import pytest
import socket
import os


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """TCP ポートに接続できるか確認する。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def _services_available() -> bool:
    """最低限 Unified API (9502) が応答しているか確認する。"""
    if os.environ.get("E2E_SERVICES") == "1":
        return True
    return _port_open("localhost", 9502, timeout=0.5)


_SKIP_REASON = (
    "E2E テストには実サービスが必要です。"
    "サービスを起動してから E2E_SERVICES=1 python -m pytest tests/e2e/ で実行してください。"
)

_SERVICES_UP = _services_available()


# ──────────────────────────────────────────────────────────────────────────────
# サービス未起動時は http_session / wait_for_services を sync スタブに差し替える。
# async フィクスチャを pytest が処理しようとして発生する PytestRemovedIn9Warning
# (→ ERROR) を避けるため、同名の sync フィクスチャで上書きする。
# ──────────────────────────────────────────────────────────────────────────────

if not _SERVICES_UP:
    @pytest.fixture(scope="session")
    def http_session():  # type: ignore[misc]
        pytest.skip(_SKIP_REASON)
        yield None

    @pytest.fixture(scope="session")
    def wait_for_services(http_session):  # type: ignore[misc]
        pytest.skip(_SKIP_REASON)
        yield None

