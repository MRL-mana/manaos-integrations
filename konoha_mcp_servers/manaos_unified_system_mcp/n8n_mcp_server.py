#!/usr/bin/env python3
"""n8n MCP Server
n8nをMCPサーバーとして統合し、Cursorから直接操作可能にする
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from mcp.server import Server
from mcp.types import Tool, TextContent

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

N8N_BASE = os.getenv("N8N_BASE", "http://127.0.0.1:5678")
N8N_USER = os.getenv("N8N_USER", "mana")
N8N_PASSWORD = os.getenv("N8N_PASSWORD", "trinity2025")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

server = Server("n8n-mcp-server")


def get_n8n_headers() -> dict:
    """n8n認証ヘッダーを取得（APIキー優先）"""
    headers = {"Content-Type": "application/json"}
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY
        return headers
    return headers


def get_n8n_auth() -> tuple:
    """n8n認証情報を取得（Basic認証用、後方互換性のため）"""
    return (N8N_USER, N8N_PASSWORD)


@server.list_tools()
async def list_tools() -> List[Tool]:
    """利用可能なツール一覧を返す"""
    return [
        Tool(
            name="n8n_list_workflows",
            description="n8nのワークフロー一覧を取得",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="n8n_execute_workflow",
            description="n8nワークフローを実行",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "ワークフローID"
                    },
                    "data": {
                        "type": "object",
                        "description": "ワークフローに渡すデータ"
                    }
                },
                "required": ["workflow_id"]
            }
        ),
        Tool(
            name="n8n_trigger_webhook",
            description="n8n Webhookをトリガー",
            inputSchema={
                "type": "object",
                "properties": {
                    "webhook_path": {
                        "type": "string",
                        "description": "Webhookパス（例: manaos-slack）"
                    },
                    "data": {
                        "type": "object",
                        "description": "Webhookに渡すデータ"
                    }
                },
                "required": ["webhook_path"]
            }
        ),
        Tool(
            name="n8n_get_workflow_status",
            description="ワークフローの実行ステータスを取得",
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_id": {
                        "type": "string",
                        "description": "実行ID"
                    }
                },
                "required": ["execution_id"]
            }
        ),
        Tool(
            name="n8n_export_workflow",
            description="ワークフローをエクスポート（JSON形式）",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "ワークフローID"
                    }
                },
                "required": ["workflow_id"]
            }
        ),
        Tool(
            name="n8n_import_workflow",
            description="ワークフローをインポート",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_data": {
                        "type": "object",
                        "description": "ワークフローデータ（JSON形式）"
                    }
                },
                "required": ["workflow_data"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """ツールを実行"""
    try:
        if name == "n8n_list_workflows":
            headers = get_n8n_headers()
            if N8N_API_KEY:
                response = requests.get(
                    f"{N8N_BASE}/api/v1/workflows",
                    headers=headers,
                    timeout=5
                )
            else:
                response = requests.get(
                    f"{N8N_BASE}/api/v1/workflows",
                    auth=get_n8n_auth(),
                    headers=headers,
                    timeout=5
                )
            if response.status_code == 200:
                workflows = response.json().get("data", [])
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "workflows": [
                            {
                                "id": w.get("id"),
                                "name": w.get("name"),
                                "active": w.get("active")
                            }
                            for w in workflows
                        ]
                    }, indent=2, ensure_ascii=False)
                )]
            return [TextContent(
                type="text",
                text=json.dumps({"success": False, "error": f"Status {response.status_code}"})
            )]

        elif name == "n8n_execute_workflow":
            workflow_id = arguments.get("workflow_id")
            data = arguments.get("data", {})

            headers = get_n8n_headers()
            if N8N_API_KEY:
                response = requests.post(
                    f"{N8N_BASE}/api/v1/workflows/{workflow_id}/execute",
                    json=data,
                    headers=headers,
                    timeout=30
                )
            else:
                response = requests.post(
                    f"{N8N_BASE}/api/v1/workflows/{workflow_id}/execute",
                    json=data,
                    auth=get_n8n_auth(),
                    headers=headers,
                    timeout=30
                )

            if response.status_code == 200:
                try:
                    result = response.json()
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "execution_id": result.get("id"),
                            "data": result
                        }, indent=2, ensure_ascii=False)
                    )]
                except json.JSONDecodeError:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "execution_id": None,
                            "data": response.text
                        }, indent=2, ensure_ascii=False)
                    )]
            try:
                error_text = response.text[:200] if response.text else "No error message"
            except Exception:
                error_text = "Unknown error"
            return [TextContent(
                type="text",
                text=json.dumps({"success": False, "error": f"Status {response.status_code}: {error_text}"})
            )]

        elif name == "n8n_trigger_webhook":
            webhook_path = arguments.get("webhook_path")
            data = arguments.get("data", {})

            # Webhookは通常認証不要だが、一貫性のためヘッダーを設定
            headers = get_n8n_headers()
            # Webhookの場合はContent-Typeのみ必要
            headers.pop("X-N8N-API-KEY", None)  # Webhookは認証不要

            response = requests.post(
                f"{N8N_BASE}/webhook/{webhook_path}",
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if response.status_code == 200:
                try:
                    result = response.json() if response.text else {}
                except json.JSONDecodeError:
                    result = {"raw_response": response.text[:500]} if response.text else {}
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "data": result
                    }, indent=2, ensure_ascii=False)
                )]
            try:
                error_text = response.text[:200] if response.text else "No error message"
            except Exception:
                error_text = "Unknown error"
            return [TextContent(
                type="text",
                text=json.dumps({"success": False, "error": f"Status {response.status_code}: {error_text}"})
            )]

        elif name == "n8n_get_workflow_status":
            execution_id = arguments.get("execution_id")

            headers = get_n8n_headers()
            if N8N_API_KEY:
                response = requests.get(
                    f"{N8N_BASE}/api/v1/executions/{execution_id}",
                    headers=headers,
                    timeout=5
                )
            else:
                response = requests.get(
                    f"{N8N_BASE}/api/v1/executions/{execution_id}",
                    auth=get_n8n_auth(),
                    headers=headers,
                    timeout=5
                )

            if response.status_code == 200:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "status": response.json().get("finished"),
                        "data": response.json()
                    }, indent=2, ensure_ascii=False)
                )]
            return [TextContent(
                type="text",
                text=json.dumps({"success": False, "error": f"Status {response.status_code}"})
            )]

        elif name == "n8n_export_workflow":
            workflow_id = arguments.get("workflow_id")

            headers = get_n8n_headers()
            if N8N_API_KEY:
                response = requests.get(
                    f"{N8N_BASE}/api/v1/workflows/{workflow_id}",
                    headers=headers,
                    timeout=5
                )
            else:
                response = requests.get(
                    f"{N8N_BASE}/api/v1/workflows/{workflow_id}",
                    auth=get_n8n_auth(),
                    headers=headers,
                    timeout=5
                )

            if response.status_code == 200:
                try:
                    workflow = response.json()
                except json.JSONDecodeError:
                    return [TextContent(
                        type="text",
                        text=json.dumps({"success": False, "error": "Invalid JSON response"})
                    )]
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "workflow": workflow
                    }, indent=2, ensure_ascii=False)
                )]
            try:
                error_text = response.text[:200] if response.text else "No error message"
            except Exception:
                error_text = "Unknown error"
            return [TextContent(
                type="text",
                text=json.dumps({"success": False, "error": f"Status {response.status_code}: {error_text}"})
            )]

        elif name == "n8n_import_workflow":
            workflow_data = arguments.get("workflow_data")

            headers = get_n8n_headers()
            if N8N_API_KEY:
                response = requests.post(
                    f"{N8N_BASE}/api/v1/workflows",
                    json=workflow_data,
                    headers=headers,
                    timeout=10
                )
            else:
                response = requests.post(
                    f"{N8N_BASE}/api/v1/workflows",
                    json=workflow_data,
                    auth=get_n8n_auth(),
                    headers=headers,
                    timeout=10
                )

            if response.status_code in [200, 201]:
                try:
                    result = response.json()
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "workflow_id": result.get("id"),
                            "data": result
                        }, indent=2, ensure_ascii=False)
                    )]
                except json.JSONDecodeError:
                    return [TextContent(
                        type="text",
                        text=json.dumps({"success": False, "error": "Invalid JSON response"})
                    )]
            try:
                error_text = response.text[:200] if response.text else "No error message"
            except Exception:
                error_text = "Unknown error"
            return [TextContent(
                type="text",
                text=json.dumps({"success": False, "error": f"Status {response.status_code}: {error_text}"})
            )]

        else:
            return [TextContent(
                type="text",
                text=json.dumps({"success": False, "error": f"Unknown tool: {name}"})
            )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)})
        )]


async def main():
    """MCPサーバーを起動"""
    import asyncio
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())







