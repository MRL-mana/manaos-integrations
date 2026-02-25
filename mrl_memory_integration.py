#!/usr/bin/env python3
"""Compat entrypoint for MRL Memory Integration.

The docker-compose service runs: `python -m mrl_memory_integration`.
Historically this module lived at repo root, while the implementation now lives
under `mrl_memory/mrl_memory_integration.py` with flat (non-package) imports.

This shim keeps the original module name working by:
- adding `mrl_memory/` to `sys.path` so flat imports resolve
- loading the implementation module under an internal name
- starting the Flask app the same way the implementation does

"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


def _load_impl() -> object:
    repo_root = Path(__file__).resolve().parent
    impl_dir = repo_root / "mrl_memory"
    impl_path = impl_dir / "mrl_memory_integration.py"

    if not impl_path.exists():
        raise FileNotFoundError(f"Missing implementation: {impl_path}")

    # Make flat imports like `from mrl_memory_system import ...` work.
    sys.path.insert(0, str(impl_dir))

    spec = importlib.util.spec_from_file_location(
        "_mrl_memory_integration_impl",
        str(impl_path),
    )
    if spec is None or spec.loader is None:
        raise ImportError("Failed to load mrl_memory integration implementation")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    impl = _load_impl()

    app = getattr(impl, "app", None)
    flask_available = bool(getattr(impl, "FLASK_AVAILABLE", False))

    if not flask_available or app is None:
        raise RuntimeError("Flask is not available; MRL Memory API cannot start")

    port = int(os.getenv("PORT", "5105"))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
