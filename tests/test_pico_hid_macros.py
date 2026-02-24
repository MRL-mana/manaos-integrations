#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from unittest.mock import MagicMock, patch


def test_run_macro_dry_run_ok():
    from pico_hid.pc.pico_hid_macros import run_macro

    r = run_macro("start_services", dry_run=True)
    assert r.success is True
    assert r.executed_steps > 0


def test_run_macro_uses_client_calls():
    from pico_hid.pc import pico_hid_macros

    mock_client = MagicMock()
    mock_client.key_combo.return_value = True
    mock_client.type_text.return_value = True
    mock_client.key_press.return_value = True

    with patch.object(pico_hid_macros, "get_client", return_value=mock_client):
        r = pico_hid_macros.run_macro("health_check", dry_run=False)

    assert r.success is True
    assert mock_client.key_combo.called
    assert mock_client.type_text.called
    assert mock_client.key_press.called


def test_click_then_type_macro_calls_mouse_and_type():
    from pico_hid.pc import pico_hid_macros

    mock_client = MagicMock()
    mock_client.mouse_click_at.return_value = True
    mock_client.type_text.return_value = True

    with patch.object(pico_hid_macros, "get_client", return_value=mock_client):
        r = pico_hid_macros.run_macro(
            "click_then_type",
            dry_run=False,
            args={"x": 123, "y": 456, "text": "hello"},
        )

    assert r.success is True
    mock_client.mouse_click_at.assert_called_once_with(123, 456, "left")
    mock_client.type_text.assert_called_once_with("hello")


def test_guided_click_then_type_auto_collects_screenshots():
    from pico_hid.pc import pico_hid_macros

    mock_client = MagicMock()

    with (
        patch.object(pico_hid_macros, "get_client", return_value=mock_client),
        patch.object(pico_hid_macros, "take_screenshot", return_value="pre.png"),
        patch.object(pico_hid_macros, "click_then_type_auto", return_value=(True, "post.png")),
    ):
        r = pico_hid_macros.run_macro(
            "guided_click_then_type_auto",
            dry_run=False,
            args={"x": 10, "y": 20, "text": "abc"},
        )

    assert r.success is True
    assert r.artifacts["screenshots"] == ["pre.png", "post.png"]
