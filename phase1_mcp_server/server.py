"""
Phase1 自己観察実験 専用 MCP サーバー
phase1_run_off, phase1_run_on, phase1_save_run, phase1_aggregate, phase1_compare_on_off
"""

import asyncio
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

if sys.platform == "win32":
    import io

    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

ROOT = Path(__file__).resolve().parent.parent
server = Server("phase1")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="phase1_run_off_3rounds",
            description="Phase1 OFF 3往復テスト。API が PHASE1_REFLECTION=off で起動している必要あり。",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="phase1_run_on_rounds",
            description="Phase1 ON N往復テスト。デフォルト15往復。PHASE1_REFLECTION=on で起動していること。",
            inputSchema={
                "type": "object",
                "properties": {"rounds": {"type": "integer", "default": 15}},
            },
        ),
        Tool(
            name="phase1_save_run",
            description="phase1 ログを phase1_runs/ にスナップショット保存。",
            inputSchema={
                "type": "object",
                "properties": {
                    "condition": {"type": "string", "enum": ["on", "off"]},
                    "tag": {"type": "string"},
                },
                "required": ["condition"],
            },
        ),
        Tool(
            name="phase1_aggregate",
            description="phase1 ログを集計（継続率・テーマ再訪・満足度）。",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="phase1_compare_on_off",
            description="phase1_runs/ 内の ON/OFF スナップショットを比較。",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


def _is_windows() -> bool:
    return sys.platform == "win32"


async def _run_ps1(script: str, *args) -> tuple[str, str, int]:
    """Windows: PowerShell で実行。Linux/Mac: 未使用。"""
    proc = await asyncio.create_subprocess_exec(
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ROOT / script),
        *args,
        cwd=str(ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=900)
    out = (stdout or b"").decode("utf-8", errors="replace")
    err = (stderr or b"").decode("utf-8", errors="replace")
    return out, err, proc.returncode or 0


async def _run_python(script: str, *args, timeout: int = 30) -> tuple[str, str, int]:
    cmd = [sys.executable, str(ROOT / script)] + list(args)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    out = (stdout or b"").decode("utf-8", errors="replace")
    err = (stderr or b"").decode("utf-8", errors="replace")
    return out, err, proc.returncode or 0


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "phase1_run_off_3rounds":
            if _is_windows():
                out, err, code = await _run_ps1("phase1_run_off_3rounds.ps1")
            else:
                out, err, code = await _run_python("phase1_run_off_3rounds.py")
            if code != 0:
                return [
                    TextContent(
                        type="text", text=f"❌ Phase1 OFF エラー (exit={code})\n{err}\n{out}"
                    )
                ]
            return [TextContent(type="text", text=f"✅ Phase1 OFF 3往復完了\n\n{out}")]

        elif name == "phase1_run_on_rounds":
            rounds = int(arguments.get("rounds", 15))
            if _is_windows():
                out, err, code = await _run_ps1(
                    "phase1_run_on_15rounds.ps1", "-Rounds", str(rounds)
                )
            else:
                out, err, code = await _run_python(
                    "phase1_run_on_rounds.py",
                    "--rounds",
                    str(rounds),
                    timeout=900,
                )
            if code != 0:
                msg = f"❌ Phase1 ON {rounds}往復エラー (exit={code})\n{err}\n{out}"
                return [TextContent(type="text", text=msg)]
            return [TextContent(type="text", text=f"✅ Phase1 ON {rounds}往復完了\n\n{out}")]

        elif name == "phase1_save_run":
            condition = arguments.get("condition", "").lower()
            tag = arguments.get("tag") or ""
            if condition not in ("on", "off"):
                return [
                    TextContent(
                        type="text", text="❌ condition は on または off を指定してください"
                    )
                ]
            cmd_args = ["--condition", condition]
            if tag:
                cmd_args.extend(["--tag", tag])
            out, err, code = await _run_python("phase1_save_run.py", *cmd_args)
            if code != 0:
                return [TextContent(type="text", text=f"❌ phase1_save_run エラー\n{err}\n{out}")]
            return [TextContent(type="text", text=f"✅ {out}")]

        elif name == "phase1_aggregate":
            out, err, _ = await _run_python("phase1_aggregate.py")
            txt = f"=== Phase1 集計 ===\n\n{out}" + (f"\n{err}" if err else "")
            return [TextContent(type="text", text=txt)]

        elif name == "phase1_compare_on_off":
            out, err, code = await _run_python("phase1_compare_on_off.py")
            if code != 0:
                msg = f"❌ phase1_compare_on_off エラー\n{err}\n{out}"
                return [TextContent(type="text", text=msg)]
            return [TextContent(type="text", text=f"✅ Phase1 ON/OFF 比較\n\n{out}")]

        return [TextContent(type="text", text=f"❌ 未知のツール: {name}")]
    except asyncio.TimeoutError:
        return [TextContent(type="text", text="❌ タイムアウトしました")]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ エラー: {e}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
