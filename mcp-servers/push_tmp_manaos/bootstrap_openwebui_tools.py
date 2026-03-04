#!/usr/bin/env python3
import argparse
import json
import sys
import textwrap
import time

import requests


TOOL_ID = "manaos_blueprint_gateway"


def request_json(base_url: str, host: str, method: str, path: str, token: str | None = None, payload: dict | None = None):
    url = f"{base_url.rstrip('/')}{path}"
    headers = {"Host": host, "Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.request(method, url, headers=headers, json=payload, timeout=30)
    except requests.RequestException as error:
        return 0, {"error": str(error)}
    body = {}
    if response.text:
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}
    return response.status_code, body


def tool_content() -> str:
    return textwrap.dedent(
        """
        import os
        import requests


        class Tools:
            def __init__(self):
                self.base_url = os.getenv("MANAOS_BLUEPRINT_API_URL", "http://manaos-bp-api:9502").rstrip("/")
                self.ops_token = os.getenv("OPS_EXEC_BEARER_TOKEN", "")

            def _headers(self, with_ops_token: bool = False):
                headers = {"Content-Type": "application/json"}
                if with_ops_token and self.ops_token:
                    headers["Authorization"] = f"Bearer {self.ops_token}"
                return headers

            def memory_write(self, content: str, source: str = "openwebui", metadata: dict | None = None) -> dict:
                "Write a memory entry into ManaOS blueprint memory store."
                payload = {"content": content, "source": source, "metadata": metadata or {}}
                response = requests.post(f"{self.base_url}/memory/write", headers=self._headers(), json=payload, timeout=20)
                response.raise_for_status()
                return response.json()

            def memory_search(self, query: str, limit: int = 10) -> dict:
                "Search memory entries in ManaOS blueprint memory store."
                payload = {"query": query, "limit": limit}
                response = requests.post(f"{self.base_url}/memory/search", headers=self._headers(), json=payload, timeout=20)
                response.raise_for_status()
                return response.json()

            def ops_plan(self, goal: str) -> dict:
                "Create an operation plan for approval flow."
                response = requests.post(
                    f"{self.base_url}/ops/plan",
                    headers=self._headers(),
                    json={"goal": goal},
                    timeout=20,
                )
                response.raise_for_status()
                return response.json()

            def ops_exec(self, command: str, approved: bool = True, dry_run: bool = True) -> dict:
                "Execute approved operation command (dry-run by default)."
                payload = {"command": command, "approved": approved, "dry_run": dry_run}
                response = requests.post(
                    f"{self.base_url}/ops/exec",
                    headers=self._headers(with_ops_token=True),
                    json=payload,
                    timeout=30,
                )
                response.raise_for_status()
                return response.json()

            def dev_patch(self) -> dict:
                "Queue patch task in ManaOS blueprint."
                response = requests.post(f"{self.base_url}/dev/patch", headers=self._headers(), json={}, timeout=20)
                response.raise_for_status()
                return response.json()

            def dev_test(self) -> dict:
                "Queue test task in ManaOS blueprint."
                response = requests.post(f"{self.base_url}/dev/test", headers=self._headers(), json={}, timeout=20)
                response.raise_for_status()
                return response.json()

            def dev_deploy(self) -> dict:
                "Queue deploy task in ManaOS blueprint."
                response = requests.post(
                    f"{self.base_url}/dev/deploy",
                    headers=self._headers(with_ops_token=True),
                    json={},
                    timeout=20,
                )
                response.raise_for_status()
                return response.json()
        """
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap Open WebUI tool for ManaOS blueprint API")
    parser.add_argument("--openwebui-base", default="http://localhost", help="Open WebUI base URL")
    parser.add_argument("--base-domain", default="mrl-mana.com", help="BASE_DOMAIN for Host header")
    parser.add_argument("--email", default="mana-blueprint-admin@example.local")
    parser.add_argument("--password", default="ManaOS!2026")
    parser.add_argument("--signup", action="store_true", help="Run signup if signin fails")
    parser.add_argument("--signin-retries", type=int, default=6, help="Retry count for signin on transient errors")
    parser.add_argument("--signin-retry-seconds", type=int, default=5, help="Delay between signin retries")
    args = parser.parse_args()

    host = f"chat.{args.base_domain}"

    signin_payload = {"email": args.email, "password": args.password}

    def signin_with_retry():
        status = 0
        body = {}
        for attempt in range(1, args.signin_retries + 1):
            status, body = request_json(args.openwebui_base, host, "POST", "/api/v1/auths/signin", payload=signin_payload)
            if status == 200:
                return status, body

            if status in (0, 502, 503, 504) and attempt < args.signin_retries:
                time.sleep(args.signin_retry_seconds)
                continue

            break
        return status, body

    status, signin_body = signin_with_retry()

    if status != 200 and args.signup:
        signup_payload = {"name": "Mana Blueprint Admin", "email": args.email, "password": args.password}
        request_json(args.openwebui_base, host, "POST", "/api/v1/auths/signup", payload=signup_payload)
        status, signin_body = signin_with_retry()

    if status != 200:
        print(json.dumps({"success": False, "step": "signin", "status": status, "body": signin_body}, ensure_ascii=False))
        return 1

    token = signin_body.get("token")
    if not token:
        print(json.dumps({"success": False, "step": "token", "body": signin_body}, ensure_ascii=False))
        return 1

    tool_form = {
        "id": TOOL_ID,
        "name": "ManaOS Blueprint Gateway",
        "content": tool_content(),
        "meta": {"description": "Bridge Open WebUI to ManaOS blueprint memory/ops/dev API", "manifest": {}},
    }

    get_status, get_body = request_json(args.openwebui_base, host, "GET", f"/api/v1/tools/id/{TOOL_ID}", token=token)
    if get_status == 200 and get_body:
        up_status, up_body = request_json(
            args.openwebui_base,
            host,
            "POST",
            f"/api/v1/tools/id/{TOOL_ID}/update",
            token=token,
            payload=tool_form,
        )
        if up_status != 200:
            print(json.dumps({"success": False, "step": "update", "status": up_status, "body": up_body}, ensure_ascii=False))
            return 1
        action = "updated"
    else:
        cr_status, cr_body = request_json(
            args.openwebui_base,
            host,
            "POST",
            "/api/v1/tools/create",
            token=token,
            payload=tool_form,
        )
        if cr_status != 200:
            print(json.dumps({"success": False, "step": "create", "status": cr_status, "body": cr_body}, ensure_ascii=False))
            return 1
        action = "created"

    list_status, list_body = request_json(args.openwebui_base, host, "GET", "/api/v1/tools/list", token=token)
    count = len(list_body) if isinstance(list_body, list) else 0
    print(json.dumps({"success": True, "action": action, "tool_id": TOOL_ID, "tool_count": count}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
