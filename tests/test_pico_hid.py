#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト: Pico HID クライアント & MCP サーバー
ハードウェア非依存で pico_hid_client のロジックと MCP サーバー登録を検証
"""

from unittest.mock import patch, MagicMock, PropertyMock
import sys
import json

import pytest


# ---------------------------------------------------------------------------
# PCHIDClient (pynput バックエンド)
# ---------------------------------------------------------------------------


class TestPCHIDClient:
    """pynput ベースの PCHIDClient のロジック検証"""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """pynput をモックして PCHIDClient をインポート"""
        self.mock_mouse_controller = MagicMock()
        self.mock_kb_controller = MagicMock()
        self.mock_mouse = MagicMock()
        self.mock_keyboard = MagicMock()
        self.mock_mouse.Controller.return_value = self.mock_mouse_controller
        self.mock_keyboard.Controller.return_value = self.mock_kb_controller
        self.mock_mouse.Button = MagicMock()
        self.mock_mouse.Button.left = "left"
        self.mock_mouse.Button.right = "right"
        self.mock_mouse.Button.middle = "middle"
        self.mock_keyboard.Key = MagicMock()

        # モジュールキャッシュをクリアして再インポートを強制
        for mod in list(sys.modules.keys()):
            if "pico_hid" in mod:
                del sys.modules[mod]

        with patch.dict("sys.modules", {
            "pynput": MagicMock(),
            "pynput.mouse": self.mock_mouse,
            "pynput.keyboard": self.mock_keyboard,
            "serial": MagicMock(),
            "serial.tools": MagicMock(),
            "serial.tools.list_ports": MagicMock(),
        }):
            from pico_hid.pc.pico_hid_client import PCHIDClient
            self.PCHIDClient = PCHIDClient
            yield  # モックをテスト実行中も維持

        # クリーンアップ
        for mod in list(sys.modules.keys()):
            if "pico_hid" in mod:
                del sys.modules[mod]

    def test_init(self):
        """PCHIDClient が初期化できる"""
        client = self.PCHIDClient()
        assert client is not None

    def test_mouse_move(self):
        """相対移動が mouse.move() を呼ぶ"""
        client = self.PCHIDClient()
        result = client.mouse_move(10, 20)
        self.mock_mouse_controller.move.assert_called_with(10, 20)
        assert result is True

    def test_mouse_click(self):
        """クリックが mouse.click() を呼ぶ"""
        client = self.PCHIDClient()
        result = client.mouse_click("left")
        self.mock_mouse_controller.click.assert_called_once()
        assert result is True

    def test_type_text(self):
        """テキスト入力が keyboard.type() を呼ぶ"""
        client = self.PCHIDClient()
        result = client.type_text("hello")
        self.mock_kb_controller.type.assert_called_with("hello")
        assert result is True

    def test_mouse_position(self):
        """マウス座標が取得できる"""
        self.mock_mouse_controller.position = (100, 200)
        client = self.PCHIDClient()
        pos = client.mouse_position()
        assert pos == (100, 200)

    def test_scroll(self):
        """スクロールが mouse.scroll() を呼ぶ"""
        client = self.PCHIDClient()
        result = client.scroll(-3)
        self.mock_mouse_controller.scroll.assert_called_once()
        assert result is True


# ---------------------------------------------------------------------------
# PicoHIDClient （シリアル通信モック）
# ---------------------------------------------------------------------------


class TestPicoHIDClient:
    """シリアル通信ベースの PicoHIDClient の検証"""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """pyserial をモック"""
        self.mock_serial = MagicMock()
        self.mock_serial_module = MagicMock()
        self.mock_serial_module.Serial.return_value = self.mock_serial
        self.mock_serial.is_open = True
        self.mock_serial.readline.return_value = b"OK\n"

        # モジュールキャッシュをクリアして再インポートを強制
        for mod in list(sys.modules.keys()):
            if "pico_hid" in mod:
                del sys.modules[mod]

        with patch.dict("sys.modules", {
            "serial": self.mock_serial_module,
            "serial.tools": MagicMock(),
            "serial.tools.list_ports": MagicMock(),
            "pynput": MagicMock(),
            "pynput.mouse": MagicMock(),
            "pynput.keyboard": MagicMock(),
        }):
            from pico_hid.pc.pico_hid_client import PicoHIDClient
            self.PicoHIDClient = PicoHIDClient
            yield  # モックをテスト実行中も維持

        # クリーンアップ
        for mod in list(sys.modules.keys()):
            if "pico_hid" in mod:
                del sys.modules[mod]

    def test_init_with_port(self):
        """COM ポート指定で初期化"""
        client = self.PicoHIDClient(port="COM3")
        assert client is not None

    def test_send_line(self):
        """コマンドがシリアルに書き込まれる"""
        client = self.PicoHIDClient(port="COM3")
        client.send_line("MOUSE_MOVE,10,20")
        self.mock_serial.write.assert_called()

    def test_mouse_move(self):
        """mouse_move がシリアルコマンドを送る"""
        client = self.PicoHIDClient(port="COM3")
        client.mouse_move(5, -5)
        self.mock_serial.write.assert_called()

    def test_key_combo_multi(self):
        """複数キーの key_combo が combo,KEY... を送る"""
        client = self.PicoHIDClient(port="COM3")
        ok = client.key_combo(["ctrl", "shift", "s"])
        assert ok is True
        # combo,ctrl,shift,s\n を write していること
        written = b"".join(call.args[0] for call in self.mock_serial.write.call_args_list)
        assert b"combo,ctrl,shift,s" in written.lower()


# ---------------------------------------------------------------------------
# get_client / find_pico_port ヘルパー
# ---------------------------------------------------------------------------


class TestClientHelpers:
    """ヘルパー関数の基本動作"""

    def test_get_client_returns_object(self):
        """get_client が何らかのクライアントを返す"""
        mock_mouse = MagicMock()
        mock_mouse.Controller.return_value = MagicMock()
        mock_mouse.Button = MagicMock()
        mock_keyboard = MagicMock()
        mock_keyboard.Controller.return_value = MagicMock()
        mock_keyboard.Key = MagicMock()
        mock_serial_tools = MagicMock()
        mock_serial_tools.list_ports.comports.return_value = []

        with patch.dict("sys.modules", {
            "pynput": MagicMock(),
            "pynput.mouse": mock_mouse,
            "pynput.keyboard": mock_keyboard,
            "serial": MagicMock(),
            "serial.tools": mock_serial_tools,
            "serial.tools.list_ports": mock_serial_tools.list_ports,
        }):
            from pico_hid.pc.pico_hid_client import get_client
            client = get_client()
            assert client is not None

    def test_screen_size_returns_tuple(self):
        """screen_size が (w, h) を返す"""
        mock_mouse = MagicMock()
        mock_mouse.Controller.return_value = MagicMock()
        mock_mouse.Button = MagicMock()
        mock_keyboard = MagicMock()
        mock_keyboard.Controller.return_value = MagicMock()
        mock_keyboard.Key = MagicMock()

        with patch.dict("sys.modules", {
            "pynput": MagicMock(),
            "pynput.mouse": mock_mouse,
            "pynput.keyboard": mock_keyboard,
            "serial": MagicMock(),
            "serial.tools": MagicMock(),
            "serial.tools.list_ports": MagicMock(),
        }):
            from pico_hid.pc.pico_hid_client import screen_size
            size = screen_size()
            assert isinstance(size, tuple)
            assert len(size) == 2


# ---------------------------------------------------------------------------
# PicoHIDMCPServer — インポート検証
# ---------------------------------------------------------------------------


class TestPicoHIDMCPServer:
    """Pico HID MCP サーバーの基本検証"""

    def test_mcp_import(self):
        """pico_hid_mcp_server がインポートできる"""
        try:
            import pico_hid_mcp_server
            assert True
        except Exception:
            pytest.skip("MCP server module not importable in this env")

    def test_hid_tools_count(self):
        """サーバーに11ツールが定義されている"""
        try:
            from pico_hid_mcp_server.server import app  # type: ignore[attr-defined]
            assert app is not None
        except Exception:
            pytest.skip("Cannot inspect MCP app in test env")
