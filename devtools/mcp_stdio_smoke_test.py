#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def run_smoke_test(*, command: str, args: list[str], cwd: str | None, env: dict[str, str]):
    params = StdioServerParameters(
        command=command,
        args=args,
        env=env,
        cwd=cwd,
        encoding="utf-8",
        encoding_error_handler="replace",
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            return tool_names, session


async def call_tool(session: ClientSession, name: str, payload: dict[str, Any]):
    res = await session.call_tool(name, payload)
    text_parts: list[str] = []
    for c in res.content:
        t = getattr(c, "text", None)
        if isinstance(t, str):
            text_parts.append(t)
    return "".join(text_parts)


async def main_async(ns: argparse.Namespace) -> int:
    env = os.environ.copy()

    # Merge extra env entries (KEY=VALUE)
    for kv in ns.env or []:
        if "=" not in kv:
            continue
        k, v = kv.split("=", 1)
        env[k] = v

    tool_name = ns.call
    tool_payload: dict[str, Any] = {}
    if ns.payload:
        tool_payload = json.loads(ns.payload)

    params = StdioServerParameters(
        command=ns.command,
        args=ns.args,
        env=env,
        cwd=ns.cwd,
        encoding="utf-8",
        encoding_error_handler="replace",
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print("TOOLS_COUNT", len(names))
            print("TOOLS", ",".join(names))

            if tool_name:
                if tool_name not in names:
                    print("CALL_SKIPPED tool_not_found", tool_name)
                    return 2
                out = await call_tool(session, tool_name, tool_payload)
                print("CALL_OK", tool_name)
                if out:
                    print("CALL_TEXT_PREVIEW", out[:1000].replace("\r", " ").replace("\n", " "))
                else:
                    print("CALL_TEXT_PREVIEW", "")

    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="MCP stdio smoke test (initialize -> list_tools -> optional call_tool)")
    p.add_argument("--command", default="py", help="server command, e.g. py")
    p.add_argument("--cwd", default=None, help="working directory")
    p.add_argument("--env", action="append", default=[], help="extra env KEY=VALUE (repeatable)")
    p.add_argument("--call", default="", help="tool name to call (optional)")
    p.add_argument("--payload", default="", help="JSON object payload for --call")
    p.add_argument("args", nargs=argparse.REMAINDER, help="command args after --, e.g. -- -3.10 -m module")
    ns = p.parse_args()

    if ns.args and ns.args[0] == "--":
        ns.args = ns.args[1:]

    try:
        return asyncio.run(main_async(ns))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
