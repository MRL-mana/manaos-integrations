#!/usr/bin/env python3
"""
ALITA-G MCT & ミラーループ対策 MCPサーバー
マナOSから直接使用可能なMCPサーバー
"""

import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent.parent / "systems"))

from mcp.server import Server
from mcp.types import Tool, TextContent
import json
from typing import Any

from alita_mct_enhanced import EnhancedMCTOrchestrator
from mirror_loop_enhanced import EnhancedMirrorLoopDetector


# MCPサーバー初期化
server = Server("alita-mct-system")

# MCT Orchestrator初期化
mct_orchestrator = EnhancedMCTOrchestrator(use_llm=True, use_vector_search=True)
mirror_loop_detector = EnhancedMirrorLoopDetector(use_semantic_similarity=True)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """利用可能なツール一覧"""
    return [
        Tool(
            name="search_mcts",
            description="タスクに関連するMCT（成功パターン）を検索",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "タスクの説明"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返すMCTの最大数",
                        "default": 5
                    }
                },
                "required": ["task_description"]
            }
        ),
        Tool(
            name="learn_from_success",
            description="成功体験からMCTを学習・保存",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "エージェント名（remi/luna/mina/aria）"
                    },
                    "task": {
                        "type": "string",
                        "description": "タスクの説明"
                    },
                    "solution": {
                        "type": "string",
                        "description": "成功した解決策"
                    },
                    "context": {
                        "type": "object",
                        "description": "実行時のコンテキスト"
                    }
                },
                "required": ["agent_name", "task", "solution"]
            }
        ),
        Tool(
            name="apply_mct",
            description="MCTを適用（パラメーターを埋め込む）",
            inputSchema={
                "type": "object",
                "properties": {
                    "mct_id": {
                        "type": "string",
                        "description": "MCT ID"
                    },
                    "params": {
                        "type": "object",
                        "description": "パラメーターの値"
                    }
                },
                "required": ["mct_id", "params"]
            }
        ),
        Tool(
            name="detect_mirror_loop",
            description="ミラーループ（停滞）を検出",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "エージェント名"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "タスクID"
                    }
                },
                "required": ["agent_name", "task_id"]
            }
        ),
        Tool(
            name="track_iteration",
            description="反復処理を追跡（ミラーループ検出用）",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "エージェント名"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "タスクID"
                    },
                    "iteration": {
                        "type": "integer",
                        "description": "反復回数"
                    },
                    "output": {
                        "type": "string",
                        "description": "その反復での出力"
                    }
                },
                "required": ["agent_name", "task_id", "iteration", "output"]
            }
        ),
        Tool(
            name="get_agent_insights",
            description="エージェントの洞察情報を取得",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "エージェント名"
                    }
                },
                "required": ["agent_name"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """ツールの実行"""

    if name == "search_mcts":
        task_description = arguments.get("task_description")
        limit = arguments.get("limit", 5)

        results = mct_orchestrator.get_relevant_mcts(task_description, limit)

        return [TextContent(
            type="text",
            text=json.dumps({
                "count": len(results),
                "mcts": [
                    {
                        "id": mct["id"],
                        "description": mct.get("description", ""),
                        "relevance_score": mct.get("relevance_score", 0),
                        "abstraction_method": mct.get("abstraction_method", "unknown")
                    }
                    for mct in results
                ]
            }, ensure_ascii=False, indent=2)
        )]

    elif name == "learn_from_success":
        agent_name = arguments.get("agent_name")
        task = arguments.get("task")
        solution = arguments.get("solution")
        context = arguments.get("context", {})

        mct_id = mct_orchestrator.learn_from_success(
            agent_name=agent_name,
            task=task,
            solution=solution,
            context=context,
            result=True
        )

        return [TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "mct_id": mct_id,
                "message": f"MCTを学習しました: {mct_id}"
            }, ensure_ascii=False)
        )]

    elif name == "apply_mct":
        mct_id = arguments.get("mct_id")
        params = arguments.get("params", {})

        try:
            applied = mct_orchestrator.apply_mct(mct_id, params)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "applied_procedure": applied
                }, ensure_ascii=False)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e)
                }, ensure_ascii=False)
            )]

    elif name == "detect_mirror_loop":
        agent_name = arguments.get("agent_name")
        task_id = arguments.get("task_id")

        result = mirror_loop_detector.detect_mirror_loop(agent_name, task_id)

        return [TextContent(
            type="text",
            text=json.dumps({
                "detected": result.get("detected", False),
                "warning": result.get("warning", ""),
                "avg_info_change": result.get("avg_info_change", 0),
                "method": result.get("method", "unknown")
            }, ensure_ascii=False, indent=2)
        )]

    elif name == "track_iteration":
        agent_name = arguments.get("agent_name")
        task_id = arguments.get("task_id")
        iteration = arguments.get("iteration")
        output = arguments.get("output")

        mirror_loop_detector.track_iteration(agent_name, task_id, iteration, output)

        return [TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "message": f"反復{iteration}を記録しました"
            }, ensure_ascii=False)
        )]

    elif name == "get_agent_insights":
        agent_name = arguments.get("agent_name")

        from trinity_enhancement import TrinityEnhancement
        enhancement = TrinityEnhancement()
        insights = enhancement.get_agent_insights(agent_name)

        return [TextContent(
            type="text",
            text=json.dumps(insights, ensure_ascii=False, indent=2)
        )]

    else:
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)
        )]


if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(main())









