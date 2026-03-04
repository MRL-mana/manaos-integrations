"""Pico HID macro runner.

目的:
- Pico(USB HID) / PC(pynput) のどちらでも、同じ手順を「マクロ」として実行する
- NanoKVM と組み合わせて、遠隔から復旧/起動の定型操作を再現しやすくする

注意:
- 入力はUS配列前提。
- 実行環境の状態（フォーカス/IME/権限）により失敗します。
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from .pico_hid_client import (
    get_client,
    take_screenshot,
    type_text_auto,
    clear_input_then_type_auto,
    click_then_type_auto,
)


@dataclass(frozen=True)
class MacroResult:
    name: str
    success: bool
    executed_steps: int
    failed_step_index: int | None = None
    error: str | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)


def _repo_root() -> Path:
    # .../manaos_integrations/pico_hid/pc -> parents[2] == manaos_integrations
    return Path(__file__).resolve().parents[2]


def _sleep(seconds: float, speed: float):
    if seconds <= 0:
        return
    time.sleep(seconds * max(speed, 0.05))


def _format(text: str, args: dict[str, Any]) -> str:
    try:
        return text.format(**(args or {}))
    except Exception:
        return text


def _parse_int(value: Any, args: dict[str, Any], *, field: str) -> Optional[int]:
    """Parse an int from value (supports format placeholders)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if value is None:
        return None
    s = _format(str(value), args).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except Exception:
        return None


def list_macros() -> list[str]:
    return sorted(_MACROS.keys())


def run_macro(
    name: str,
    *,
    args: dict[str, Any] | None = None,
    speed: float = 1.0,
    dry_run: bool = False,
    confirm_token: str | None = None,
) -> MacroResult:
    """Run a named macro.

    Args:
        name: macro name.
        args: formatting args used in some steps.
        speed: multiply sleep durations (1.0 = default).
        dry_run: if True, no input is sent.

    Returns:
        MacroResult.
    """
    macro = _MACROS.get((name or "").strip())
    if macro is None:
        return MacroResult(name=name, success=False, executed_steps=0, error="unknown macro")

    required = os.environ.get("PICO_HID_MACRO_CONFIRM_TOKEN", "").strip()
    if required:
        if (confirm_token or "").strip() != required:
            return MacroResult(name=name, success=False, executed_steps=0, error="confirm_token required")

    executed = 0
    artifacts: dict[str, Any] = {"screenshots": []}
    client = None
    try:
        if not dry_run:
            client = get_client()

        for idx, step in enumerate(macro(args=args or {}), start=1):
            executed = idx
            op = step.get("op")
            if op == "sleep":
                _sleep(float(step.get("seconds", 0.0)), speed)
                continue

            if op == "screenshot":
                if dry_run:
                    continue
                path = step.get("path")
                saved = take_screenshot(
                    _format(str(path), args or {}) if path else None
                )
                if not saved:
                    return MacroResult(
                        name=name,
                        success=False,
                        executed_steps=executed,
                        failed_step_index=idx,
                        error="screenshot failed",
                        artifacts=artifacts,
                    )
                artifacts.setdefault("screenshots", []).append(saved)
                continue

            if dry_run:
                continue

            if client is None:
                return MacroResult(
                    name=name,
                    success=False,
                    executed_steps=executed,
                    failed_step_index=idx,
                    error="no client",
                    artifacts=artifacts,
                )

            if op == "key_combo":
                ok = client.key_combo(step.get("keys") or [])
                if not ok:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="key_combo failed", artifacts=artifacts)
            elif op == "key_press":
                ok = client.key_press(str(step.get("key") or ""))
                if not ok:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="key_press failed", artifacts=artifacts)
            elif op == "type_text":
                text = _format(str(step.get("text") or ""), args or {})
                ok = client.type_text(text)
                if not ok:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="type_text failed", artifacts=artifacts)
            elif op == "mouse_move":
                dx = _parse_int(step.get("dx"), args or {}, field="dx")
                dy = _parse_int(step.get("dy"), args or {}, field="dy")
                if dx is None or dy is None:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="mouse_move invalid dx/dy", artifacts=artifacts)
                ok = client.mouse_move(dx, dy)
                if not ok:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="mouse_move failed", artifacts=artifacts)
            elif op in ("mouse_move_abs", "mouse_move_absolute"):
                x = _parse_int(step.get("x"), args or {}, field="x")
                y = _parse_int(step.get("y"), args or {}, field="y")
                if x is None or y is None:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="mouse_move_abs invalid x/y", artifacts=artifacts)
                ok = client.mouse_move_absolute(x, y)
                if not ok:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="mouse_move_abs failed", artifacts=artifacts)
            elif op == "mouse_click":
                ok = client.mouse_click(str(step.get("button") or "left"))
                if not ok:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="mouse_click failed", artifacts=artifacts)
            elif op == "mouse_click_at":
                x = _parse_int(step.get("x"), args or {}, field="x")
                y = _parse_int(step.get("y"), args or {}, field="y")
                if x is None or y is None:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="mouse_click_at invalid x/y", artifacts=artifacts)
                ok = client.mouse_click_at(x, y, str(step.get("button") or "left"))
                if not ok:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="mouse_click_at failed", artifacts=artifacts)
            elif op in ("scroll", "mouse_scroll", "mouse_wheel"):
                delta = _parse_int(step.get("delta", step.get("amount")), args or {}, field="delta")
                if delta is None:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="scroll invalid delta", artifacts=artifacts)
                ok = client.scroll(delta)
                if not ok:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="scroll failed", artifacts=artifacts)
            elif op == "type_text_auto":
                text = _format(str(step.get("text") or ""), args or {})
                ok, path = type_text_auto(text)
                if path:
                    artifacts.setdefault("screenshots", []).append(path)
                if not ok:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="type_text_auto failed", artifacts=artifacts)
            elif op in ("clear_and_retype_auto", "clear_input_then_type_auto"):
                text = _format(str(step.get("text") or ""), args or {})
                ok, path = clear_input_then_type_auto(text)
                if path:
                    artifacts.setdefault("screenshots", []).append(path)
                if not ok:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="clear_and_retype_auto failed", artifacts=artifacts)
            elif op == "click_then_type_auto":
                x = _parse_int(step.get("x"), args or {}, field="x")
                y = _parse_int(step.get("y"), args or {}, field="y")
                text = _format(str(step.get("text") or ""), args or {})
                if x is None or y is None:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="click_then_type_auto invalid x/y", artifacts=artifacts)
                ok, path = click_then_type_auto(x, y, text)
                if path:
                    artifacts.setdefault("screenshots", []).append(path)
                if not ok:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="click_then_type_auto failed", artifacts=artifacts)
            else:
                return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error=f"unknown op: {op}", artifacts=artifacts)

        return MacroResult(name=name, success=True, executed_steps=executed, artifacts=artifacts)
    except Exception as e:
        return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=executed or None, error=str(e), artifacts=artifacts)
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


def _run_dialog(command: str, args: dict[str, Any]):
    # Win+R -> type -> Enter
    return [
        {"op": "key_combo", "keys": ["gui", "r"]},
        {"op": "sleep", "seconds": 0.35},
        {"op": "type_text", "text": _format(command, args)},
        {"op": "sleep", "seconds": 0.10},
        {"op": "key_press", "key": "ENTER"},
        {"op": "sleep", "seconds": 0.35},
    ]


def _macro_start_services(*, args: dict[str, Any]):
    root = str(_repo_root())
    py = args.get("py") or "py -3.10"
    cmd = f'{py} "{root}\\start_vscode_cursor_services.py"'
    return _run_dialog(cmd, args)


def _macro_health_check(*, args: dict[str, Any]):
    root = str(_repo_root())
    py = args.get("py") or "py -3.10"
    cmd = f'{py} "{root}\\check_services_health.py"'
    return _run_dialog(cmd, args)


def _macro_restart_unified_api(*, args: dict[str, Any]):
    root = str(_repo_root())
    # できるだけ短い: restart_unified_api_port9502.ps1
    cmd = f'pwsh -NoProfile -ExecutionPolicy Bypass -File "{root}\\restart_unified_api_port9502.ps1"'
    return _run_dialog(cmd, args)


def _macro_emergency_stop(*, args: dict[str, Any]):
    root = str(_repo_root())
    py = args.get("py") or "py -3.10"
    cmd = f'{py} "{root}\\emergency_stop.py"'
    return _run_dialog(cmd, args)


def _macro_open_nanokvm(*, args: dict[str, Any]):
    url = str(args.get("nanokvm_url") or "")
    if not url:
        # 空なら何もしない（安全）
        return [{"op": "sleep", "seconds": 0.05}]
    cmd = f'cmd /c start "" "{url}"'
    return _run_dialog(cmd, args)


def _macro_click_then_type(*, args: dict[str, Any]):
        """Click at (x,y) then type text.

        Args expected in args:
            - x: int
            - y: int
            - text: str
        """
        return [
                {"op": "mouse_click_at", "x": "{x}", "y": "{y}", "button": "left"},
                {"op": "sleep", "seconds": 0.25},
                {"op": "type_text", "text": "{text}"},
        ]


def _macro_guided_click_then_type_auto(*, args: dict[str, Any]):
        """Screenshot -> click+IME-switch+type -> screenshot.

        Notes:
            - click part works on PC backend only; Pico backend will skip click in helper.
            - does NOT press Enter; verify screenshots first.

        Args expected in args:
            - x: int
            - y: int
            - text: str
        """
        return [
                {"op": "screenshot"},
                {"op": "sleep", "seconds": 0.15},
                {"op": "click_then_type_auto", "x": "{x}", "y": "{y}", "text": "{text}"},
        ]


_MACROS: dict[str, Callable[..., list[dict[str, Any]]]] = {
    "start_services": _macro_start_services,
    "health_check": _macro_health_check,
    "restart_unified_api": _macro_restart_unified_api,
    "emergency_stop": _macro_emergency_stop,
    "open_nanokvm": _macro_open_nanokvm,
    "click_then_type": _macro_click_then_type,
    "guided_click_then_type_auto": _macro_guided_click_then_type_auto,
}


def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Run Pico HID macros")
    parser.add_argument("name", help=f"macro name: {', '.join(list_macros())}")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-token", default="", help="required if PICO_HID_MACRO_CONFIRM_TOKEN is set")
    parser.add_argument("--args", default="{}", help='JSON object, e.g. {"nanokvm_url":"http://1.2.3.4"}')
    ns = parser.parse_args()

    try:
        args = json.loads(ns.args)
        if not isinstance(args, dict):
            raise ValueError("args must be JSON object")
    except Exception:
        args = {}

    result = run_macro(
        ns.name,
        args=args,
        speed=ns.speed,
        dry_run=ns.dry_run,
        confirm_token=(ns.confirm_token or "").strip() or None,
    )
    print(json.dumps(result.__dict__, ensure_ascii=False))
    raise SystemExit(0 if result.success else 1)


if __name__ == "__main__":
    main()
