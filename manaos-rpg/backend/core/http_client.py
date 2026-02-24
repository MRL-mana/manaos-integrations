from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


def _http_json_get(url: str, timeout_s: float = 5.0, headers: dict[str, str] | None = None) -> dict[str, Any]:
    h = {"User-Agent": "manaos-rpg/0.1"}
    if isinstance(headers, dict):
        for k, v in headers.items():
            if k and v:
                h[str(k)] = str(v)

    req = urllib.request.Request(url, method="GET", headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read(2 * 1024 * 1024)
            data = json.loads(body.decode("utf-8", errors="replace"))
            return {"ok": 200 <= int(resp.status) < 400, "status": int(resp.status), "data": data}
    except urllib.error.HTTPError as e:
        try:
            body = e.read(64 * 1024)
            text = body.decode("utf-8", errors="replace")
        except Exception:
            text = ""
        return {"ok": False, "status": int(getattr(e, "code", 0) or 0), "error": text[:2000]}
    except Exception as e:
        return {"ok": False, "status": 0, "error": str(e)}


def _http_json_post(
    url: str,
    payload: dict[str, Any],
    timeout_s: float = 30.0,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    h = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "manaos-rpg/0.1",
    }
    if isinstance(headers, dict):
        for k, v in headers.items():
            if k and v:
                h[str(k)] = str(v)

    req = urllib.request.Request(url, method="POST", data=raw, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read(8 * 1024 * 1024)
            data = json.loads(body.decode("utf-8", errors="replace"))
            return {"ok": 200 <= int(resp.status) < 400, "status": int(resp.status), "data": data}
    except urllib.error.HTTPError as e:
        try:
            body = e.read(128 * 1024)
            text = body.decode("utf-8", errors="replace")
        except Exception:
            text = ""
        return {"ok": False, "status": int(getattr(e, "code", 0) or 0), "error": text[:4000]}
    except Exception as e:
        return {"ok": False, "status": 0, "error": str(e)}


def _http_status(method: str, url: str, timeout_s: float = 6.0, headers: dict[str, str] | None = None) -> dict[str, Any]:
    m = str(method or "GET").strip().upper() or "GET"
    h = {"User-Agent": "manaos-rpg/0.1"}
    if isinstance(headers, dict):
        for k, v in headers.items():
            if k and v:
                h[str(k)] = str(v)

    req = urllib.request.Request(url, method=m, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return {"ok": 200 <= int(resp.status) < 400, "status": int(resp.status)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": int(getattr(e, "code", 0) or 0)}
    except Exception as e:
        return {"ok": False, "status": 0, "error": str(e)}


def _http_status_post_json(url: str, timeout_s: float = 6.0, headers: dict[str, str] | None = None) -> dict[str, Any]:
    raw = json.dumps({}, ensure_ascii=False).encode("utf-8")
    h = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "manaos-rpg/0.1",
    }
    if isinstance(headers, dict):
        for k, v in headers.items():
            if k and v:
                h[str(k)] = str(v)

    req = urllib.request.Request(url, method="POST", headers=h, data=raw)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            _ = resp.read(1024)
            return {"ok": 200 <= int(resp.status) < 400, "status": int(resp.status)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": int(getattr(e, "code", 0) or 0)}
    except Exception as e:
        return {"ok": False, "status": 0, "error": str(e)}
