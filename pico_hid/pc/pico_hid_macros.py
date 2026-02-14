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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .pico_hid_client import get_client


@dataclass(frozen=True)
class MacroResult:
    name: str
    success: bool
    executed_steps: int
    failed_step_index: int | None = None
    error: str | None = None


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

            if dry_run:
                continue

            if client is None:
                return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="no client")

            if op == "key_combo":
                ok = client.key_combo(step.get("keys") or [])
                if not ok:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="key_combo failed")
            elif op == "key_press":
                ok = client.key_press(str(step.get("key") or ""))
                if not ok:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="key_press failed")
            elif op == "type_text":
                text = _format(str(step.get("text") or ""), args or {})
                ok = client.type_text(text)
                if not ok:
                    return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error="type_text failed")
            else:
                return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=idx, error=f"unknown op: {op}")

        return MacroResult(name=name, success=True, executed_steps=executed)
    except Exception as e:
        return MacroResult(name=name, success=False, executed_steps=executed, failed_step_index=executed or None, error=str(e))
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


_MACROS: dict[str, Callable[..., list[dict[str, Any]]]] = {
    "start_services": _macro_start_services,
    "health_check": _macro_health_check,
    "restart_unified_api": _macro_restart_unified_api,
    "emergency_stop": _macro_emergency_stop,
    "open_nanokvm": _macro_open_nanokvm,
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
