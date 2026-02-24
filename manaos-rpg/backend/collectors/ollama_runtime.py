from __future__ import annotations

import shutil
import subprocess


def get_ollama_ps_models() -> list[str]:
    if not shutil.which("ollama"):
        return []
    try:
        completed = subprocess.run(
            ["ollama", "ps"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2.0,
        )
        text = (completed.stdout or "").strip()
        if not text:
            return []
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if len(lines) <= 1:
            return []

        # table header: NAME ID SIZE PROCESSOR UNTIL
        names: list[str] = []
        for ln in lines[1:]:
            # take first whitespace-separated token as NAME
            parts = ln.split()
            if parts:
                names.append(parts[0])
        return names
    except Exception:
        return []
