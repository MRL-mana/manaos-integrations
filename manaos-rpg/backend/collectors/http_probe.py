from __future__ import annotations

import json
import urllib.error
import urllib.request


def http_probe(url: str, timeout_s: float = 0.8) -> dict:
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": "manaos-rpg/0.1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read(64 * 1024)
            ct = (resp.headers.get("content-type") or "").lower()
            data = None
            if "application/json" in ct:
                try:
                    data = json.loads(body.decode("utf-8", errors="replace"))
                except Exception:
                    data = None
            return {
                "ok": 200 <= int(resp.status) < 400,
                "status": int(resp.status),
                "content_type": ct,
                "json": data,
            }
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": int(getattr(e, "code", 0) or 0), "content_type": None, "json": None}
    except Exception:
        return {"ok": False, "status": 0, "content_type": None, "json": None}
