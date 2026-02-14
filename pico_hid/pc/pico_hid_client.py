"""
Pico 2 W HID クライアント
母艦からシリアルでコマンドを送り、Pico がマウス・キーボードを操作する。
ローカルLLMやCursorのMCPツールから呼び出す想定。

環境変数:
  PICO_HID_PORT  … COM ポート指定（例: COM3）
  PICO_HID_USE_PC … 1 にすると Pico を使わず PC 側でマウス・キー操作（pynput）
"""

import os
import sys
import time
from typing import Callable, Optional

# pyserial は optional（Pico 接続時のみ必要）
try:
    import serial
    import serial.tools.list_ports

    _has_serial = True
except ImportError:
    serial = None
    _has_serial = False

# pynput は PC 側フォールバック用（PICO_HID_USE_PC=1 または Pico なし時）
try:
    from pynput.mouse import Button, Controller as MouseController
    from pynput.keyboard import Key, Controller as KeyboardController

    _has_pynput = True
except ImportError:
    _has_pynput = False

# スクリーンショット用（pyautogui または PIL）
_screenshot_fn: Optional[Callable[[str], None]] = None
try:
    import pyautogui

    def _pyautogui_screenshot(path: str) -> None:
        pyautogui.screenshot().save(path)

    _screenshot_fn = _pyautogui_screenshot
    _has_screenshot = True
except Exception:
    try:
        from PIL import ImageGrab

        def _pillow_screenshot(path: str) -> None:
            ImageGrab.grab().save(path)

        _screenshot_fn = _pillow_screenshot
        _has_screenshot = True
    except ImportError:
        _has_screenshot = False
        _screenshot_fn = None


def find_pico_port():
    """Raspberry Pi Pico 2 W (CircuitPython) の COM ポートを検出する。"""
    # 環境変数で指定されていればそれを優先
    env_port = os.environ.get("PICO_HID_PORT", "").strip()
    if env_port:
        return env_port
    if not _has_serial:
        return None
    for port in serial.tools.list_ports.comports():
        desc = (port.description or "").upper()
        hwid = (port.hwid or "").upper()
        # Pico / CircuitPython の典型的な名前、または Windows の「USB Serial Device」
        if (
            "PICO" in desc
            or "PICO" in hwid
            or "CIRCUITPY" in desc
            or "RP2040" in hwid
            or "RP2350" in hwid
            or "USB SERIAL" in desc
            or "CDC" in desc
        ):
            return port.device
    # COM1 以外が1つだけある場合はそれを試す（CircuitPython が汎用名で出る場合）
    ports = [p.device for p in serial.tools.list_ports.comports()]
    others = [p for p in ports if p.upper() != "COM1"]
    if len(others) == 1:
        return others[0]
    return None


def get_serial_ports():
    """利用可能な COM ポート一覧を返す（デバッグ用）。"""
    if not _has_serial:
        return []
    return [p.device for p in serial.tools.list_ports.comports()]


def take_screenshot(path=None):
    """
    画面をキャプチャして PNG で保存する。
    path が None の場合は一時ファイルに保存し、そのパスを返す。
    戻り値: 保存したファイルのパス。失敗時は None。
    """
    if not _has_screenshot or _screenshot_fn is None:
        return None
    if path is None:
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".png", prefix="pico_hid_screen_")
        try:
            os.close(fd)
            _screenshot_fn(path)
            return path
        except Exception:
            try:
                os.unlink(path)
            except OSError:
                pass
            return None
    try:
        _screenshot_fn(path)
        return path
    except Exception:
        return None


def screen_size():
    """画面サイズ (width, height) を返す。取得できない場合は (0, 0)。"""
    if not _has_screenshot:
        return (0, 0)
    try:
        import pyautogui as _pyautogui

        return _pyautogui.size()
    except Exception:
        try:
            from PIL import ImageGrab as _ImageGrab

            return _ImageGrab.grab().size
        except Exception:
            return (0, 0)


def use_pc_backend():
    """PC 側（pynput）を使うか。

    デフォルトは PC（pynput があれば）。Pico を使うときは PICO_HID_USE_PICO=1。
    """
    if os.environ.get("PICO_HID_USE_PICO", "").strip() in ("1", "true", "yes"):
        return False
    if os.environ.get("PICO_HID_USE_PC", "").strip() in ("1", "true", "yes"):
        return True
    # デフォルト: pynput があれば PC で操作（そのまま動く）
    return _has_pynput


class PCHIDClient:
    """PC 側でマウス・キーボードを操作（pynput）。Pico が使えないときのフォールバック。"""

    def __init__(self):
        if not _has_pynput:
            raise RuntimeError("PC 操作には pynput が必要です: pip install pynput")
        self._mouse = MouseController()
        self._keyboard = KeyboardController()
        self._key_map = {
            "ENTER": Key.enter,
            "TAB": Key.tab,
            "SPACE": Key.space,
            "ESCAPE": Key.esc,
            "BACKSPACE": Key.backspace,
            "DELETE": Key.delete,
            "UP": Key.up,
            "DOWN": Key.down,
            "LEFT": Key.left,
            "RIGHT": Key.right,
            "HOME": Key.home,
            "END": Key.end,
            "PAGEUP": Key.page_up,
            "PAGEDOWN": Key.page_down,
            "SHIFT": Key.shift,
            "CONTROL": Key.ctrl,
            "CTRL": Key.ctrl,
            "ALT": Key.alt,
            "GUI": Key.cmd,
            "WINDOWS": Key.cmd,
        }

    def mouse_move(self, dx: int, dy: int) -> bool:
        try:
            self._mouse.move(dx, dy)
            return True
        except Exception:
            return False

    def mouse_position(self):
        """現在のマウス座標 (x, y) を返す。"""
        try:
            return self._mouse.position
        except Exception:
            return (0, 0)

    def mouse_move_absolute(self, x: int, y: int) -> bool:
        """画面上の絶対座標 (x, y) にマウスを移動する。"""
        try:
            self._mouse.position = (x, y)
            return True
        except Exception:
            return False

    def mouse_click_at(self, x: int, y: int, button: str = "left") -> bool:
        """画面上の絶対座標 (x, y) をクリックする。"""
        try:
            self._mouse.position = (x, y)
            btn = Button.left
            normalized = (button or "").strip().lower()
            if normalized == "right":
                btn = Button.right
            elif normalized == "middle":
                btn = Button.middle
            self._mouse.click(btn)
            return True
        except Exception:
            return False

    def key_combo(self, keys: list) -> bool:
        """キーコンボ（例: ["ctrl", "c"] で Ctrl+C）を押す。"""
        if not keys:
            return False
        try:
            key_objs = []
            for k in keys:
                k = (k or "").strip().upper()
                if k in self._key_map:
                    key_objs.append(self._key_map[k])
                elif len(k) == 1:
                    key_objs.append(k.lower())
                else:
                    return False
            for key in key_objs:
                self._keyboard.press(key)
            for key in reversed(key_objs):
                self._keyboard.release(key)
            return True
        except Exception:
            return False

    def mouse_click(self, button: str = "left") -> bool:
        try:
            btn = Button.left
            normalized = (button or "").strip().lower()
            if normalized == "right":
                btn = Button.right
            elif normalized == "middle":
                btn = Button.middle
            self._mouse.click(btn)
            return True
        except Exception:
            return False

    def scroll(self, delta: int) -> bool:
        try:
            self._mouse.scroll(0, 1 if delta > 0 else -1)
            return True
        except Exception:
            return False

    def key_press(self, key: str) -> bool:
        if "," in key:
            return False
        try:
            k = (key or "").strip().upper()
            if k in self._key_map:
                self._keyboard.press(self._key_map[k])
                self._keyboard.release(self._key_map[k])
            elif len(k) == 1:
                self._keyboard.press(k)
                self._keyboard.release(k)
            return True
        except Exception:
            return False

    def type_text(self, text: str) -> bool:
        try:
            self._keyboard.type(text.split("\n")[0])
            return True
        except Exception:
            return False

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class PicoHIDClient:
    """Pico 2 W にシリアルで HID コマンドを送るクライアント。"""

    def __init__(self, port=None, baud=115200, timeout=0.5):
        if serial is None:
            raise RuntimeError("pyserial が必要です: pip install pyserial")
        env_port = os.environ.get("PICO_HID_PORT", "").strip()
        self.port = port or env_port or find_pico_port()
        self.baud = baud
        self.timeout = timeout
        self._ser = None

    def _ensure_open(self):
        if self._ser is not None and self._ser.is_open:
            return True
        if not self.port:
            self.port = find_pico_port()
        if not self.port:
            return False
        try:
            self._ser = serial.Serial(
                self.port,
                self.baud,
                timeout=self.timeout,
            )
            time.sleep(0.05)  # 接続直後のゴミ対策
            return True
        except Exception:
            self._ser = None
            return False

    def send_line(self, line: str) -> bool:
        """1行送信（末尾に改行を付与）。"""
        if not line.endswith("\n"):
            line = line + "\n"
        if not self._ensure_open():
            return False
        try:
            self._ser.write(line.encode("utf-8"))
            self._ser.flush()
            time.sleep(0.08)  # Pico が受信するまで少し待つ
            return True
        except Exception:
            self._ser = None
            return False

    def mouse_move(self, dx: int, dy: int) -> bool:
        return self.send_line(f"m,{dx},{dy}")

    def mouse_position(self):
        return (0, 0)  # Pico 側では未対応

    def mouse_move_absolute(self, x: int, y: int) -> bool:
        del x, y
        return False  # Pico 側では未対応（PC のみ）

    def mouse_click_at(self, x: int, y: int, button: str = "left") -> bool:
        del x, y, button
        return False  # Pico 側では未対応（PC のみ）

    def key_combo(self, keys: list) -> bool:
        if not keys:
            return False
        # Pico 側の COMBO プロトコル対応（例: combo,CTRL,SHIFT,S）
        cleaned = []
        for k in keys:
            k = (k or "").strip()
            if not k or "," in k:
                return False
            cleaned.append(k)
        if len(cleaned) == 1:
            return self.key_press(cleaned[0])
        payload = ",".join(["combo"] + cleaned)
        return self.send_line(payload)

    def mouse_click(self, button: str = "left") -> bool:
        return self.send_line(f"c,{button.strip().lower()}")

    def scroll(self, delta: int) -> bool:
        return self.send_line(f"w,{delta}")

    def key_press(self, key: str) -> bool:
        # カンマが含まれるとプロトコルが壊れるので禁止
        if "," in key:
            return False
        return self.send_line(f"k,{key}")

    def type_text(self, text: str) -> bool:
        # プロトコル: "t," のあと改行までがペイロード（カンマ・改行そのまま可）
        line = "t," + text.replace("\r\n", "\n").split("\n")[0]
        return self.send_line(line)

    def close(self):
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def type_text_auto(text: str):
    """
    ［全自動］IME 切替を試行 → 文字列入力 → スクリーンショットを一括実行。
    PC 時のみ IME 切替（Alt+` と Ctrl+Shift+0）を試行。呼び出し元でスクショを確認し、
    OK なら Enter 2回を送ること。
    戻り値: (ok: bool, screenshot_path: str)
    """
    client = get_client()
    try:
        if use_pc_backend():
            for combo in [["alt", "`"], ["ctrl", "shift", "0"]]:
                try:
                    client.key_combo(combo)
                except Exception:
                    pass
                time.sleep(0.35)
        ok = client.type_text(text)
        time.sleep(0.2)
        path = take_screenshot()
        return (ok, path or "")
    finally:
        client.close()


def clear_input_then_type_auto(text: str):
    """
    ［打ち直し］入力欄を全選択→削除してから、type_text_auto を実行。
    戻り値: (ok: bool, screenshot_path: str)
    """
    client = get_client()
    try:
        client.key_combo(["ctrl", "a"])
        time.sleep(0.15)
        client.key_press("DELETE")
        time.sleep(0.2)
    except Exception:
        pass
    finally:
        client.close()
    return type_text_auto(text)


def click_then_type_auto(x: int, y: int, text: str):
    """
    ［入力場所を指定］指定座標 (x, y) をクリックしてフォーカスを合わせてから、
    type_text_auto を実行。入力欄の座標は事前にスクショで確認すること。
    戻り値: (ok: bool, screenshot_path: str)
    """
    client = get_client()
    try:
        if use_pc_backend():
            client.mouse_click_at(x, y, "left")
            time.sleep(0.3)
    except Exception:
        pass
    finally:
        client.close()
    return type_text_auto(text)


def get_client(port=None):
    """
    デフォルトで PC 側（pynput）で操作。Pico を使うときは PICO_HID_USE_PICO=1。
    """
    if use_pc_backend() and _has_pynput:
        return PCHIDClient()
    if not use_pc_backend() and _has_serial:
        p = port or find_pico_port()
        if p:
            return PicoHIDClient(port=p)
    if _has_pynput:
        return PCHIDClient()
    if _has_serial:
        raise RuntimeError(
            "Pico の COM ポートが見つかりません。"
            "pynput で PC 操作: pip install pynput のあと PICO_HID_USE_PC=1"
        )
    raise RuntimeError(
        "pyserial か pynput が必要です: pip install pyserial または pip install pynput"
    )


def main():
    """CLI テスト: python -m pico_hid.pc.pico_hid_client m 10 0 など。"""
    try:
        client = get_client()
    except RuntimeError as e:
        print(e)
        sys.exit(1)
    backend = (
        "PC (pynput)"
        if isinstance(client, PCHIDClient)
        else f"Pico ({client.port})"
    )
    print("使用:", backend)
    argv = sys.argv[1:]
    if not argv:
        print(
            "使い方: m dx dy | ma x y | c [left] | ca x y [left] | k KEY | "
            "combo ctrl c | t TEXT | w delta | pos | screen [path]"
        )
        print("例: m 10 0  ma 100 200  ca 50 50  combo ctrl c")
        print("     t hello  pos  screen")
        print("Pico で操作するとき: 環境変数 PICO_HID_USE_PICO=1")
        client.close()
        return
    cmd = (argv[0] or "").lower()
    ok = False
    if cmd == "m" and len(argv) >= 3:
        ok = client.mouse_move(int(argv[1]), int(argv[2]))
    elif cmd == "ma" and len(argv) >= 3:
        ok = client.mouse_move_absolute(int(argv[1]), int(argv[2]))
    elif cmd == "c":
        ok = client.mouse_click(argv[1] if len(argv) >= 2 else "left")
    elif cmd == "ca" and len(argv) >= 3:
        ok = client.mouse_click_at(
            int(argv[1]),
            int(argv[2]),
            argv[3] if len(argv) >= 4 else "left",
        )
    elif cmd == "k" and len(argv) >= 2:
        ok = client.key_press(argv[1])
    elif cmd == "combo" and len(argv) >= 2:
        ok = client.key_combo(argv[1:])
    elif cmd == "t" and len(argv) >= 2:
        ok = client.type_text(argv[1])
    elif cmd == "w" and len(argv) >= 2:
        ok = client.scroll(int(argv[1]))
    elif cmd == "pos":
        x, y = client.mouse_position()
        print(f"マウス座標: {x}, {y}")
        ok = True
    elif cmd in ("screen", "screenshot") and _has_screenshot:
        path = take_screenshot(argv[1] if len(argv) >= 2 else None)
        if path:
            print(f"スクリーンショット: {path}")
            ok = True
        else:
            print("スクリーンショット失敗")
    else:
        print("不明なコマンドまたは引数不足")
    client.close()
    print("OK" if ok else "送信失敗")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
