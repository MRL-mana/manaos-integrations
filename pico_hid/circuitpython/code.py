# Pico 2 W HID - シリアルでコマンドを受信しマウス・キーボードを操作
# インポート失敗時は「受信で LED 点滅」の診断モードで動く

import time
import usb_cdc


# 最初に LED を点滅させて「code.py が動いた」ことを示す
def _blink(times=1):
    try:
        import board
        import digitalio

        led_pin = getattr(board, "LED", None)
        if led_pin is not None:
            d = digitalio.DigitalInOut(led_pin)
            d.direction = digitalio.Direction.OUTPUT
            for _ in range(times):
                d.value = True
                time.sleep(0.08)
                d.value = False
                time.sleep(0.08)
    except Exception:
        pass


_blink(3)  # 起動時 3 回点滅

# HID は try 内で初期化（失敗しても診断モードで動く）
mouse = None
keyboard = None
layout = None
KEY_MAP = {}

try:
    import usb_hid
    from adafruit_hid.mouse import Mouse
    from adafruit_hid.keyboard import Keyboard
    from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
    from adafruit_hid.keycode import Keycode

    mouse = Mouse(usb_hid.devices)
    keyboard = Keyboard(usb_hid.devices)
    layout = KeyboardLayoutUS(keyboard)
    for i in range(ord("A"), ord("Z") + 1):
        KEY_MAP[chr(i)] = getattr(Keycode, chr(i))
    for k in (
        "ENTER",
        "TAB",
        "SPACE",
        "ESCAPE",
        "BACKSPACE",
        "DELETE",
        "UP",
        "DOWN",
        "LEFT",
        "RIGHT",
        "HOME",
        "END",
        "PAGEUP",
        "PAGEDOWN",
        "CONTROL",
        "ALT",
        "SHIFT",
        "GUI",
    ):
        KEY_MAP[k] = getattr(Keycode, k, None)
    KEY_MAP = {k: v for k, v in KEY_MAP.items() if v is not None}
except Exception as e:
    pass  # HID なし = 診断モード（受信で LED だけ点滅）


# 起動時に HID の成否を log に書く（確認用）
def _log_start():
    try:
        with open("/log.txt", "w") as f:
            if mouse and keyboard and layout:
                f.write("HID: ok\n")
            else:
                f.write("HID: fail (no mouse/keyboard)\n")
    except Exception:
        pass


_log_start()


def _log_received(line):
    """受信ログを CIRCUITPY に書き、LED なしでも確認できるようにする"""
    try:
        with open("/log.txt", "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def parse_and_run(line):
    line = (line or "").strip()
    if not line:
        return
    _blink(1)  # 何か受信したら 1 回点滅
    _log_received(line)  # 受信内容を log.txt に追記
    if mouse is None or keyboard is None or layout is None:
        return  # 診断モードではここまで
    if line.upper().startswith("T,"):
        parts = ["T", line[2:]]
    else:
        parts = line.split(",", 2)
    cmd = (parts[0] or "").upper()
    if cmd == "M" and len(parts) >= 3:
        try:
            dx, dy = int(parts[1]), int(parts[2])
            mouse.move(dx, dy, 0)
        except ValueError:
            pass
    elif cmd == "C" and len(parts) >= 2:
        btn = (parts[1] or "").lower()
        if btn == "left":
            mouse.click(Mouse.LEFT_BUTTON)
        elif btn == "right":
            mouse.click(Mouse.RIGHT_BUTTON)
        elif btn == "middle":
            mouse.click(Mouse.MIDDLE_BUTTON)
    elif cmd == "W" and len(parts) >= 2:
        try:
            mouse.move(0, 0, int(parts[1]))
        except ValueError:
            pass
    elif cmd == "K" and len(parts) >= 2:
        key = (parts[1] or "").strip().upper()
        if key in KEY_MAP:
            keyboard.press(KEY_MAP[key])
            keyboard.release_all()
        elif len(key) == 1:
            layout.write(key)
    elif cmd == "T" and len(parts) >= 2:
        layout.write(parts[1])


# console と data の両方から読む
_streams = []
if usb_cdc.console:
    _streams.append(usb_cdc.console)
if usb_cdc.data and usb_cdc.data is not usb_cdc.console:
    _streams.append(usb_cdc.data)
if not _streams:
    _streams = [None]

buf = ""
while True:
    got = False
    for serial in _streams:
        if serial is None:
            continue
        if serial.in_waiting:
            b = serial.read(1)
            if b:
                got = True
                try:
                    buf += b.decode("utf-8")
                except Exception:
                    buf += "?"
                while "\n" in buf or "\r" in buf:
                    line, sep, buf = buf.partition("\n")
                    if not sep:
                        line, sep, buf = buf.partition("\r")
                    if sep:
                        parse_and_run(line)
                break
    if not got:
        time.sleep(0.01)
