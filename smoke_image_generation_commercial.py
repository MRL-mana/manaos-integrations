"""商用画像生成APIのスモークテスト。

対象:
- POST /api/v1/images/signup
- POST /api/v1/images/payment/stripe
- POST /api/v1/images/payment/komoju
- GET  /api/v1/images/dashboard
"""

from __future__ import annotations

import json
import os
from typing import Any

import requests
from requests import Response
from requests.exceptions import RequestException

BASE_URL = os.getenv("IMAGE_GEN_BASE_URL", "http://127.0.0.1:5560")
TIMEOUT = float(os.getenv("SMOKE_TIMEOUT", "8"))


def _print(name: str, ok: bool, detail: Any) -> None:
    status = "OK" if ok else "NG"
    print(f"[{status}] {name}: {detail}")


def _post(path: str, **kwargs):
    return requests.post(f"{BASE_URL}{path}", timeout=TIMEOUT, **kwargs)


def _get(path: str, **kwargs):
    return requests.get(f"{BASE_URL}{path}", timeout=TIMEOUT, **kwargs)


def _safe_post(path: str, **kwargs) -> tuple[bool, Response | None, str]:
    try:
        response = _post(path, **kwargs)
        return True, response, ""
    except RequestException as exc:
        return False, None, str(exc)


def _safe_get(path: str, **kwargs) -> tuple[bool, Response | None, str]:
    try:
        response = _get(path, **kwargs)
        return True, response, ""
    except RequestException as exc:
        return False, None, str(exc)


def main() -> int:
    print(f"Smoke target: {BASE_URL}")

    ok_all = True

    signup_req_ok, signup_resp, signup_err = _safe_post(
        "/api/v1/images/signup",
        json={
            "email": "smoke-user@example.com",
            "plan": "free",
            "label": "smoke",
        },
    )
    if not signup_req_ok or signup_resp is None:
        _print("signup", False, signup_err)
        print(json.dumps({"base_url": BASE_URL, "ok": False}, ensure_ascii=False))
        return 1

    signup_ok = signup_resp.status_code == 200
    ok_all = ok_all and signup_ok
    signup_json = signup_resp.json() if signup_resp.headers.get("content-type", "").startswith("application/json") else {"text": signup_resp.text}
    _print("signup", signup_ok, f"status={signup_resp.status_code}")

    stripe_req_ok, stripe_resp, stripe_err = _safe_post(
        "/api/v1/images/payment/stripe",
        params={"plan": "pro", "user_id": "smoke-user"},
    )
    if not stripe_req_ok or stripe_resp is None:
        _print("payment/stripe", False, stripe_err)
        print(json.dumps({"base_url": BASE_URL, "ok": False}, ensure_ascii=False))
        return 1

    stripe_ok = stripe_resp.status_code == 200
    ok_all = ok_all and stripe_ok
    _print("payment/stripe", stripe_ok, f"status={stripe_resp.status_code}")

    komoju_req_ok, komoju_resp, komoju_err = _safe_post(
        "/api/v1/images/payment/komoju",
        params={"plan": "enterprise", "user_id": "smoke-user"},
    )
    if not komoju_req_ok or komoju_resp is None:
        _print("payment/komoju", False, komoju_err)
        print(json.dumps({"base_url": BASE_URL, "ok": False}, ensure_ascii=False))
        return 1

    komoju_ok = komoju_resp.status_code == 200
    ok_all = ok_all and komoju_ok
    _print("payment/komoju", komoju_ok, f"status={komoju_resp.status_code}")

    api_key = signup_json.get("api_key") if isinstance(signup_json, dict) else None
    if not api_key:
        ok_all = False
        _print("dashboard", False, "signup response has no api_key")
    else:
        dashboard_req_ok, dashboard_resp, dashboard_err = _safe_get(
            "/api/v1/images/dashboard",
            headers={"X-API-Key": api_key},
        )
        if not dashboard_req_ok or dashboard_resp is None:
            _print("dashboard", False, dashboard_err)
            print(json.dumps({"base_url": BASE_URL, "ok": False}, ensure_ascii=False))
            return 1

        dashboard_ok = dashboard_resp.status_code == 200
        ok_all = ok_all and dashboard_ok
        metrics_ok = False
        if dashboard_ok:
            data = dashboard_resp.json()
            metrics_ok = all(
                key in data
                for key in ("mrr_yen", "daily_sales_yen", "active_users_30d")
            )
            ok_all = ok_all and metrics_ok
        _print(
            "dashboard",
            dashboard_ok and metrics_ok,
            f"status={dashboard_resp.status_code}",
        )

    print(json.dumps({"base_url": BASE_URL, "ok": ok_all}, ensure_ascii=False))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
