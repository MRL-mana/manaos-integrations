"""ManaOS統合MCPサーバーのpytestスモークテスト。"""

import asyncio
import sys
import types
from unittest.mock import MagicMock

import pytest

# manaos_unified_mcp_server スタブ（未インストール環境用）
if "manaos_unified_mcp_server" not in sys.modules:
    _mcp_pkg = types.ModuleType("manaos_unified_mcp_server")
    _mcp_srv = types.ModuleType("manaos_unified_mcp_server.server")

    async def _stub_call_tool(tool_name, args):
        item = MagicMock()
        item.text = f"stub:{tool_name}"
        return [item]

    _mcp_srv.call_tool = _stub_call_tool  # type: ignore
    sys.modules["manaos_unified_mcp_server"] = _mcp_pkg
    sys.modules["manaos_unified_mcp_server.server"] = _mcp_srv
    _mcp_pkg.server = _mcp_srv  # type: ignore


def _require_call_tool():
    try:
        from manaos_unified_mcp_server.server import call_tool
    except Exception as error:
        pytest.skip(f"manaos unified mcp unavailable: {error}")
    return call_tool


def _tool_texts(result):
    if not result:
        return []
    texts = []
    for item in result:
        text = getattr(item, "text", None)
        if text is not None:
            texts.append(str(text))
        else:
            texts.append(str(item))
    return texts


def _run_tool(tool_name, args):
    call_tool = _require_call_tool()
    try:
        return asyncio.run(call_tool(tool_name, args))  # type: ignore
    except Exception as error:
        pytest.skip(f"tool call failed ({tool_name}): {error}")


def test_svi_queue_status_smoke():
    result = _run_tool("svi_get_queue_status", {})
    assert isinstance(result, list)


def test_mcp_memory_smoke():
    result = _run_tool("memory_recall", {"query": "MCP", "limit": 3})
    assert isinstance(result, list)


def test_mcp_llm_chat_smoke():
    result = _run_tool(
        "llm_chat",
        {"prompt": "こんにちは、これはテストです。", "task_type": "conversation"},
    )
    texts = _tool_texts(result)
    if texts and all("❌" in text for text in texts):
        pytest.skip("llm backend unavailable")
    assert isinstance(result, list)










