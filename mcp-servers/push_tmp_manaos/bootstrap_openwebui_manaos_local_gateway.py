#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Open WebUI に manaOS ローカル統合ツールを登録する。

Open WebUI の /api/v1/tools を使い、Tool Server(9503) と Unified API(9502) を
Open WebUI 内蔵ツールとして呼べるようにする（External Tools 画面の手作業を省略）。

前提:
- Open WebUI が起動している（既定 http://127.0.0.1:3001）
- 管理ユーザーの email/password が分かっている（環境変数でも可）

注意:
- このツールは Open WebUI コンテナ内で実行されるため、ホスト側のサービスへは
  既定で host.docker.internal を使う。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
import time

import requests


def request_json(
    base_url: str,
    method: str,
    path: str,
    *,
    token: str | None = None,
    host_header: str | None = None,
    payload: dict | None = None,
    timeout: float = 30,
):
    url = f"{base_url.rstrip('/')}{path}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if host_header:
        headers["Host"] = host_header
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.request(method, url, headers=headers, json=payload, timeout=timeout)
    except requests.RequestException as error:
        return 0, {"error": str(error)}

    body: dict | list | str = {}
    if response.text:
        try:
            body = response.json()
        except Exception:
            body = response.text
    return response.status_code, body


def tool_content() -> str:
    # NOTE: Open WebUI へ登録される「ツール本体のPythonコード」。
    # ネストしたトリプルクォートを避けるため外側は ''' を使う。
    return textwrap.dedent(
        '''
        import os
        import requests


        class Tools:
            def __init__(self):
                self.unified_api_url = os.getenv("MANAOS_UNIFIED_API_URL", "http://host.docker.internal:9502").rstrip("/")
                self.tool_server_url = os.getenv("MANAOS_TOOL_SERVER_URL", "http://host.docker.internal:9503").rstrip("/")

            def _get(self, url: str, *, timeout: float = 10) -> dict:
                r = requests.get(url, timeout=timeout)
                r.raise_for_status()
                return r.json()

            def _post(self, url: str, payload: dict, *, timeout: float = 30) -> dict:
                r = requests.post(url, json=payload, timeout=timeout)
                r.raise_for_status()
                return r.json()

            def unified_health(self) -> dict:
                """ManaOS Unified API のヘルスチェック。"""
                return self._get(f"{self.unified_api_url}/health", timeout=5)

            def tool_server_health(self) -> dict:
                """manaOS Tool Server のヘルスチェック。"""
                return self._get(f"{self.tool_server_url}/health", timeout=5)

            def ltx2_generate(self, prompt: str, workflow_path: str | None = None, image: str | None = None, timeout: float = 600.0) -> dict:
                """LTX-2 動画生成（Unified API 経由）。"""
                payload = {"prompt": prompt, "timeout": timeout}
                if workflow_path:
                    payload["workflow_path"] = workflow_path
                if image:
                    payload["image"] = image
                return self._post(f"{self.unified_api_url}/api/ltx2/generate", payload, timeout=timeout + 30)

            def ltx2_infinity_generate(
                self,
                prompt: str,
                segments: int = 1,
                workflow_path: str | None = None,
                image: str | None = None,
                timeout_per_segment: float = 600.0,
                positive_suffix: str | None = None,
                negative_suffix: str | None = None,
            ) -> dict:
                """LTX-2 Infinity 反復生成（Unified API 経由）。"""
                payload = {
                    "prompt": prompt,
                    "segments": segments,
                    "timeout_per_segment": timeout_per_segment,
                }
                if workflow_path:
                    payload["workflow_path"] = workflow_path
                if image:
                    payload["image"] = image
                if positive_suffix:
                    payload["positive_suffix"] = positive_suffix
                if negative_suffix:
                    payload["negative_suffix"] = negative_suffix

                total_timeout = max(30.0, float(timeout_per_segment) * max(1, int(segments)) + 60.0)
                return self._post(f"{self.unified_api_url}/api/ltx2-infinity/generate", payload, timeout=total_timeout)

            def ltx2_infinity_templates(self) -> dict:
                """LTX-2 Infinity テンプレート一覧。"""
                return self._get(f"{self.unified_api_url}/api/ltx2-infinity/templates", timeout=10)

            def ltx2_infinity_storage(self) -> dict:
                """LTX-2 Infinity ストレージ統計。"""
                return self._get(f"{self.unified_api_url}/api/ltx2-infinity/storage", timeout=10)

            def tool_server_execute_command(self, command: str, cwd: str | None = None, timeout: int = 30) -> dict:
                """Tool Server でコマンド実行（ポリシーによりブロックされる場合あり）。"""
                payload = {"command": command, "timeout": timeout}
                if cwd:
                    payload["cwd"] = cwd
                return self._post(f"{self.tool_server_url}/execute_command", payload, timeout=float(timeout) + 10.0)
        '''
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap Open WebUI tool: manaOS local gateway")
    parser.add_argument("--openwebui-base", default=os.getenv("OPENWEBUI_URL", "http://127.0.0.1:3001"), help="Open WebUI base URL")
    parser.add_argument("--host-header", default=os.getenv("OPENWEBUI_HOST_HEADER", ""), help="Optional Host header")
    parser.add_argument("--email", default=os.getenv("OPENWEBUI_ADMIN_EMAIL", ""), help="Open WebUI admin email")
    parser.add_argument("--password", default=os.getenv("OPENWEBUI_ADMIN_PASSWORD", ""), help="Open WebUI admin password")
    parser.add_argument("--signup", action="store_true", help="Run signup if signin fails")
    parser.add_argument("--tool-id", default=os.getenv("OPENWEBUI_MANAOS_TOOL_ID", "manaos_local_gateway"))
    parser.add_argument("--name", default=os.getenv("OPENWEBUI_MANAOS_TOOL_NAME", "manaOS Local Gateway"))
    parser.add_argument("--description", default=os.getenv("OPENWEBUI_MANAOS_TOOL_DESC", "Bridge Open WebUI to manaOS Unified API + Tool Server"))
    parser.add_argument("--signin-retries", type=int, default=6)
    parser.add_argument("--signin-retry-seconds", type=int, default=5)
    args = parser.parse_args()

    if not args.email or not args.password:
        print(
            json.dumps(
                {
                    "success": False,
                    "step": "args",
                    "error": "OPENWEBUI_ADMIN_EMAIL/OPENWEBUI_ADMIN_PASSWORD (or --email/--password) are required",
                },
                ensure_ascii=False,
            )
        )
        return 2

    host_header = args.host_header.strip() or None

    signin_payload = {"email": args.email, "password": args.password}

    def signin_with_retry():
        last_status = 0
        last_body = {}
        for attempt in range(1, args.signin_retries + 1):
            last_status, last_body = request_json(
                args.openwebui_base,
                "POST",
                "/api/v1/auths/signin",
                host_header=host_header,
                payload=signin_payload,
                timeout=30,
            )
            if last_status == 200:
                return last_status, last_body
            if last_status in (0, 502, 503, 504) and attempt < args.signin_retries:
                time.sleep(args.signin_retry_seconds)
                continue
            break
        return last_status, last_body

    status, signin_body = signin_with_retry()
    if status != 200 and args.signup:
        signup_payload = {"name": "ManaOS Admin", "email": args.email, "password": args.password}
        request_json(args.openwebui_base, "POST", "/api/v1/auths/signup", host_header=host_header, payload=signup_payload)
        status, signin_body = signin_with_retry()

    if status != 200 or not isinstance(signin_body, dict):
        print(json.dumps({"success": False, "step": "signin", "status": status, "body": signin_body}, ensure_ascii=False))
        return 1

    token = signin_body.get("token")
    if not token:
        print(json.dumps({"success": False, "step": "token", "body": signin_body}, ensure_ascii=False))
        return 1

    tool_form = {
        "id": args.tool_id,
        "name": args.name,
        "content": tool_content(),
        "meta": {"description": args.description, "manifest": {}},
    }

    get_status, get_body = request_json(
        args.openwebui_base,
        "GET",
        f"/api/v1/tools/id/{args.tool_id}",
        host_header=host_header,
        token=token,
    )
    if get_status == 200 and get_body:
        up_status, up_body = request_json(
            args.openwebui_base,
            "POST",
            f"/api/v1/tools/id/{args.tool_id}/update",
            host_header=host_header,
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
            "POST",
            "/api/v1/tools/create",
            host_header=host_header,
            token=token,
            payload=tool_form,
        )
        if cr_status != 200:
            print(json.dumps({"success": False, "step": "create", "status": cr_status, "body": cr_body}, ensure_ascii=False))
            return 1
        action = "created"

    list_status, list_body = request_json(args.openwebui_base, "GET", "/api/v1/tools/list", host_header=host_header, token=token)
    count = len(list_body) if isinstance(list_body, list) else 0
    print(json.dumps({"success": True, "action": action, "tool_id": args.tool_id, "tool_count": count}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
