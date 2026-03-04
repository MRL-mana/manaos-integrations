#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP APIサーバー統合の pytest スモークテスト。"""

import os

import pytest
import requests

try:
    from manaos_integrations._paths import MCP_API_SERVER_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import MCP_API_SERVER_PORT  # type: ignore
    except Exception:  # pragma: no cover
        MCP_API_SERVER_PORT = int(os.getenv("MCP_API_SERVER_PORT", "5105"))

MCP_API_URL = os.getenv("MCP_API_SERVER_URL", f"http://127.0.0.1:{MCP_API_SERVER_PORT}")
OPS_EXEC_BEARER_TOKEN = os.getenv("OPS_EXEC_BEARER_TOKEN", "").strip()


def _ops_headers():
    if not OPS_EXEC_BEARER_TOKEN:
        return {}
    return {"Authorization": f"Bearer {OPS_EXEC_BEARER_TOKEN}"}


@pytest.fixture(scope="module", autouse=True)
def _require_server():
    try:
        response = requests.get(f"{MCP_API_URL}/health", timeout=5)
    except Exception as error:
        pytest.xfail(f"mcp api server unavailable: {error}")
    if response.status_code != 200:
        pytest.xfail(f"mcp api server unhealthy: {response.status_code}")


def test_health():
    response = requests.get(f"{MCP_API_URL}/health", timeout=5)
    assert response.status_code == 200


def test_list_tools():
    response = requests.get(f"{MCP_API_URL}/api/mcp/tools", timeout=5)
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data.get("tools", []), list)


def test_openapi_spec():
    response = requests.get(f"{MCP_API_URL}/openapi.json", timeout=5)
    assert response.status_code == 200
    spec = response.json()
    assert isinstance(spec.get("paths", {}), dict)


def test_blueprint_endpoints():
    write_payload = {
        "content": "integration-test-memory-entry",
        "source": "integration-test",
        "metadata": {"suite": "test_mcp_api_integration"},
    }
    r_write = requests.post(f"{MCP_API_URL}/memory/write", json=write_payload, timeout=5)
    assert r_write.status_code in {200, 400, 401, 403, 404, 503}

    r_search = requests.post(
        f"{MCP_API_URL}/api/memory/search",
        json={"query": "integration-test-memory-entry", "limit": 3},
        timeout=5,
    )
    assert r_search.status_code in {200, 400, 401, 403, 404, 503}

    r_plan = requests.post(
        f"{MCP_API_URL}/api/ops/plan",
        json={"goal": "integration test plan"},
        timeout=5,
    )
    assert r_plan.status_code in {200, 400, 401, 403, 404, 503}
    plan_id = ""
    if r_plan.status_code == 200:
        try:
            plan_id = (r_plan.json().get("plan") or {}).get("plan_id", "")
        except ValueError:
            plan_id = ""

    r_exec = requests.post(
        f"{MCP_API_URL}/ops/exec",
        headers=_ops_headers(),
        json={
            "plan_id": plan_id,
            "command": "echo integration-test",
            "approved": True,
            "dry_run": True,
        },
        timeout=10,
    )
    assert r_exec.status_code in {200, 400, 401, 403, 404, 503}

    if r_exec.status_code == 200:
        try:
            job_id = r_exec.json().get("job_id", "")
        except ValueError:
            job_id = ""
        if job_id:
            r_job = requests.get(f"{MCP_API_URL}/api/ops/job/{job_id}", timeout=5)
            assert r_job.status_code == 200

    r_patch = requests.post(
        f"{MCP_API_URL}/api/dev/patch",
        json={"reason": "integration test"},
        timeout=5,
    )
    assert r_patch.status_code in {200, 400, 401, 403, 404, 503}

    r_test = requests.post(
        f"{MCP_API_URL}/api/dev/test",
        json={"scope": "smoke"},
        timeout=5,
    )
    assert r_test.status_code in {200, 400, 401, 403, 404, 503}

    r_notify = requests.post(
        f"{MCP_API_URL}/api/ops/notify",
        json={"level": "info", "message": "integration notify check"},
        timeout=5,
    )
    assert r_notify.status_code in {200, 400, 401, 403, 404, 503}
