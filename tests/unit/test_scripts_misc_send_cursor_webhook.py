"""Tests for scripts/misc/send_cursor_webhook.py"""
import sys
import hmac
import hashlib
import json
from unittest.mock import MagicMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _prep(monkeypatch, secret="testsecret", url=None, resp_status=200):
    sys.modules.pop("send_cursor_webhook", None)
    monkeypatch.syspath_prepend(str(_MISC))
    if secret:
        monkeypatch.setenv("CURSOR_WEBHOOK_SECRET", secret)
    else:
        monkeypatch.delenv("CURSOR_WEBHOOK_SECRET", raising=False)
    if url:
        monkeypatch.setenv("CURSOR_WEBHOOK_URL", url)
    else:
        monkeypatch.delenv("CURSOR_WEBHOOK_URL", raising=False)

    mock_resp = MagicMock()
    mock_resp.status_code = resp_status
    mock_resp.text = "OK"
    mock_req = MagicMock()
    mock_req.post.return_value = mock_resp
    monkeypatch.setitem(sys.modules, "requests", mock_req)
    with patch("builtins.print"):
        import send_cursor_webhook as m
    return m, mock_req


class TestSendCursorWebhookImport:
    def test_imports(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        assert "send_cursor_webhook" in sys.modules

    def test_url_from_env(self, monkeypatch):
        m, _ = _prep(monkeypatch, url="http://custom:9999/webhook")
        assert m.URL == "http://custom:9999/webhook"

    def test_default_url(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        assert "9700" in m.URL or "cursor/webhook" in m.URL

    def test_body_has_content(self, monkeypatch):
        m, _ = _prep(monkeypatch)
        assert "content" in m.BODY
        assert "metadata" in m.BODY

    def test_requests_post_called(self, monkeypatch):
        _, mock_req = _prep(monkeypatch)
        mock_req.post.assert_called_once()

    def test_signature_header_present_when_secret_set(self, monkeypatch):
        _, mock_req = _prep(monkeypatch, secret="mysecret")
        call_kwargs = mock_req.post.call_args
        headers = call_kwargs[1].get("headers") or call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {}
        if not headers:
            # check keyword arg
            headers = mock_req.post.call_args.kwargs.get("headers", {})
        assert "X-Cursor-Signature" in headers

    def test_no_signature_header_when_no_secret(self, monkeypatch):
        _, mock_req = _prep(monkeypatch, secret="")
        call_kwargs = mock_req.post.call_args
        headers = call_kwargs.kwargs.get("headers", {})
        assert "X-Cursor-Signature" not in headers

    def test_hmac_signature_is_valid(self, monkeypatch):
        """HMAC-SHA256 署名が正しく計算されることを確認"""
        secret = "test_secret_123"
        m, mock_req = _prep(monkeypatch, secret=secret)
        headers = mock_req.post.call_args.kwargs.get("headers", {})
        sig = headers.get("X-Cursor-Signature", "")
        if sig:
            # extract hex after 'sha256='
            mac_hex = sig.replace("sha256=", "")
            raw = json.dumps(m.BODY).encode("utf-8")
            expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
            assert mac_hex == expected

    def test_post_includes_timestamp_header(self, monkeypatch):
        _, mock_req = _prep(monkeypatch)
        headers = mock_req.post.call_args.kwargs.get("headers", {})
        assert "X-Cursor-Timestamp" in headers

    def test_post_includes_nonce_header(self, monkeypatch):
        _, mock_req = _prep(monkeypatch)
        headers = mock_req.post.call_args.kwargs.get("headers", {})
        assert "X-Cursor-Nonce" in headers
