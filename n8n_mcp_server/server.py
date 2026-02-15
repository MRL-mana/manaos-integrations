"""
n8n MCP Server
n8nワークフローをCursorから直接操作できるMCPサーバー
"""
import os
import json
import requests
from typing import Any, Sequence
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent
from manaos_logger import get_logger

# ロギング設定
logger = get_logger(__name__)

# n8nの設定
DEFAULT_N8N_BASE_URL = f"http://127.0.0.1:{os.getenv('N8N_PORT', '5678')}"
N8N_BASE_URL = os.getenv("N8N_BASE_URL", DEFAULT_N8N_BASE_URL)
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

# MCPサーバーの初期化
server = Server("n8n-mcp")


def get_headers():
    """n8n APIリクエスト用のヘッダーを取得"""
    headers = {"Content-Type": "application/json"}
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY
    return headers


@server.list_tools()
async def list_tools() -> list[Tool]:
    """利用可能なツールの一覧を返す"""
    return [
        Tool(
            name="n8n_list_workflows",
            description="n8nのワークフロー一覧を取得します",
            inputSchema={
                "type": "object",
                "properties": {
                    "active": {
                        "type": "boolean",
                        "description": "有効なワークフローのみ取得するか"
                    }
                }
            }
        ),
        Tool(
            name="n8n_import_workflow",
            description="n8nにワークフローをインポートします",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_file": {
                        "type": "string",
                        "description": "ワークフローファイルのパス（JSON形式）"
                    },
                    "activate": {
                        "type": "boolean",
                        "description": "インポート後に有効化するか（デフォルト: true）"
                    }
                },
                "required": ["workflow_file"]
            }
        ),
        Tool(
            name="n8n_activate_workflow",
            description="n8nのワークフローを有効化します",
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
            name="n8n_deactivate_workflow",
            description="n8nのワークフローを無効化します",
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
            name="n8n_execute_workflow",
            description="n8nのワークフローを実行します",
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
            name="n8n_get_execution",
            description="n8nの実行履歴を取得します",
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
            name="n8n_list_executions",
            description="n8nの実行履歴一覧を取得します",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "ワークフローID（オプション）"
                    },
                    "limit": {
                        "type": "number",
                        "description": "取得件数（デフォルト: 10）"
                    }
                }
            }
        ),
        Tool(
            name="n8n_get_webhook_url",
            description="n8nのWebhook URLを取得します",
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
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> Sequence[TextContent | ImageContent]:
    """ツールを呼び出す"""
    try:
        if name == "n8n_list_workflows":
            return await list_workflows(arguments)
        elif name == "n8n_import_workflow":
            return await import_workflow(arguments)
        elif name == "n8n_activate_workflow":
            return await activate_workflow(arguments)
        elif name == "n8n_deactivate_workflow":
            return await deactivate_workflow(arguments)
        elif name == "n8n_execute_workflow":
            return await execute_workflow(arguments)
        elif name == "n8n_get_execution":
            return await get_execution(arguments)
        elif name == "n8n_list_executions":
            return await list_executions(arguments)
        elif name == "n8n_get_webhook_url":
            return await get_webhook_url(arguments)
        else:
            return [TextContent(
                type="text",
                text=f"不明なツール: {name}"
            )]
    except Exception as e:
        logger.error(f"ツール実行エラー: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"エラーが発生しました: {str(e)}"
        )]

async def list_workflows(args: dict) -> Sequence[TextContent]:
    """ワークフロー一覧を取得"""
    try:
        url = f"{N8N_BASE_URL}/api/v1/workflows"
        response = requests.get(url, headers=get_headers(), timeout=30)
        
        if response.status_code == 200:
            workflows = response.json()
            
            # activeフィルタ
            if args.get("active"):
                workflows = [w for w in workflows if w.get("active", False)]
            
            result = {
                "total": len(workflows),
                "workflows": [
                    {
                        "id": w.get("id"),
                        "name": w.get("name"),
                        "active": w.get("active", False),
                        "createdAt": w.get("createdAt"),
                        "updatedAt": w.get("updatedAt")
                    }
                    for w in workflows
                ]
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        else:
            return [TextContent(
                type="text",
                text=f"エラー: {response.status_code} - {response.text}"
            )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"エラーが発生しました: {str(e)}"
        )]

async def import_workflow(args: dict) -> Sequence[TextContent]:
    """ワークフローをインポート"""
    try:
        workflow_file = args.get("workflow_file")
        activate = args.get("activate", True)
        
        if not workflow_file:
            return [TextContent(
                type="text",
                text="エラー: workflow_fileが指定されていません"
            )]
        
        # ワークフローファイルを読み込む
        if not os.path.exists(workflow_file):
            return [TextContent(
                type="text",
                text=f"エラー: ファイルが見つかりません: {workflow_file}"
            )]
        
        with open(workflow_file, "r", encoding="utf-8") as f:
            workflow_data = json.load(f)
        
        # n8nにインポート
        url = f"{N8N_BASE_URL}/api/v1/workflows"
        response = requests.post(
            url,
            json=workflow_data,
            headers=get_headers(),
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            workflow_id = result.get("id")
            
            # 有効化
            if activate and workflow_id:
                activate_url = f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}/activate"
                activate_response = requests.post(
                    activate_url,
                    headers=get_headers(),
                    timeout=30
                )
                
                if activate_response.status_code == 200:
                    result["activated"] = True
                else:
                    result["activated"] = False
                    result["activate_error"] = activate_response.text
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "message": "ワークフローをインポートしました",
                    "workflow_id": workflow_id,
                    "workflow_name": result.get("name"),
                    "activated": result.get("activated", False),
                    "url": f"{N8N_BASE_URL}/workflow/{workflow_id}"
                }, indent=2, ensure_ascii=False)
            )]
        else:
            return [TextContent(
                type="text",
                text=f"エラー: {response.status_code} - {response.text}"
            )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"エラーが発生しました: {str(e)}"
        )]

async def activate_workflow(args: dict) -> Sequence[TextContent]:
    """ワークフローを有効化"""
    try:
        workflow_id = args.get("workflow_id")
        
        if not workflow_id:
            return [TextContent(
                type="text",
                text="エラー: workflow_idが指定されていません"
            )]
        
        url = f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}/activate"
        response = requests.post(url, headers=get_headers(), timeout=30)
        
        if response.status_code == 200:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "message": "ワークフローを有効化しました",
                    "workflow_id": workflow_id
                }, indent=2, ensure_ascii=False)
            )]
        else:
            return [TextContent(
                type="text",
                text=f"エラー: {response.status_code} - {response.text}"
            )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"エラーが発生しました: {str(e)}"
        )]

async def deactivate_workflow(args: dict) -> Sequence[TextContent]:
    """ワークフローを無効化"""
    try:
        workflow_id = args.get("workflow_id")
        
        if not workflow_id:
            return [TextContent(
                type="text",
                text="エラー: workflow_idが指定されていません"
            )]
        
        url = f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}/activate"
        response = requests.delete(url, headers=get_headers(), timeout=30)
        
        if response.status_code == 200:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "message": "ワークフローを無効化しました",
                    "workflow_id": workflow_id
                }, indent=2, ensure_ascii=False)
            )]
        else:
            return [TextContent(
                type="text",
                text=f"エラー: {response.status_code} - {response.text}"
            )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"エラーが発生しました: {str(e)}"
        )]

async def execute_workflow(args: dict) -> Sequence[TextContent]:
    """ワークフローを実行"""
    try:
        workflow_id = args.get("workflow_id")
        data = args.get("data", {})
        
        if not workflow_id:
            return [TextContent(
                type="text",
                text="エラー: workflow_idが指定されていません"
            )]
        
        url = f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}/execute"
        response = requests.post(
            url,
            json=data,
            headers=get_headers(),
            timeout=60
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "message": "ワークフローを実行しました",
                    "execution_id": result.get("id"),
                    "workflow_id": workflow_id
                }, indent=2, ensure_ascii=False)
            )]
        else:
            return [TextContent(
                type="text",
                text=f"エラー: {response.status_code} - {response.text}"
            )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"エラーが発生しました: {str(e)}"
        )]

async def get_execution(args: dict) -> Sequence[TextContent]:
    """実行履歴を取得"""
    try:
        execution_id = args.get("execution_id")
        
        if not execution_id:
            return [TextContent(
                type="text",
                text="エラー: execution_idが指定されていません"
            )]
        
        url = f"{N8N_BASE_URL}/api/v1/executions/{execution_id}"
        response = requests.get(url, headers=get_headers(), timeout=30)
        
        if response.status_code == 200:
            return [TextContent(
                type="text",
                text=json.dumps(response.json(), indent=2, ensure_ascii=False)
            )]
        else:
            return [TextContent(
                type="text",
                text=f"エラー: {response.status_code} - {response.text}"
            )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"エラーが発生しました: {str(e)}"
        )]

async def list_executions(args: dict) -> Sequence[TextContent]:
    """実行履歴一覧を取得"""
    try:
        workflow_id = args.get("workflow_id")
        limit = args.get("limit", 10)
        
        url = f"{N8N_BASE_URL}/api/v1/executions"
        params = {"limit": limit}
        
        if workflow_id:
            params["workflowId"] = workflow_id
        
        response = requests.get(url, params=params, headers=get_headers(), timeout=30)
        
        if response.status_code == 200:
            return [TextContent(
                type="text",
                text=json.dumps(response.json(), indent=2, ensure_ascii=False)
            )]
        else:
            return [TextContent(
                type="text",
                text=f"エラー: {response.status_code} - {response.text}"
            )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"エラーが発生しました: {str(e)}"
        )]

async def get_webhook_url(args: dict) -> Sequence[TextContent]:
    """Webhook URLを取得"""
    try:
        workflow_id = args.get("workflow_id")
        
        if not workflow_id:
            return [TextContent(
                type="text",
                text="エラー: workflow_idが指定されていません"
            )]
        
        # ワークフロー情報を取得
        url = f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}"
        response = requests.get(url, headers=get_headers(), timeout=30)
        
        if response.status_code == 200:
            workflow = response.json()
            
            # Webhookノードを探す
            webhook_url = None
            nodes = workflow.get("nodes", [])
            
            for node in nodes:
                if node.get("type") == "n8n-nodes-base.webhook":
                    webhook_path = node.get("parameters", {}).get("path", "")
                    if webhook_path:
                        webhook_url = f"{N8N_BASE_URL}/webhook/{webhook_path}"
                        break
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "workflow_id": workflow_id,
                    "workflow_name": workflow.get("name"),
                    "webhook_url": webhook_url or "Webhookノードが見つかりませんでした"
                }, indent=2, ensure_ascii=False)
            )]
        else:
            return [TextContent(
                type="text",
                text=f"エラー: {response.status_code} - {response.text}"
            )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"エラーが発生しました: {str(e)}"
        )]

# MCPサーバーを実行
if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server
    
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import sys
        print(f"MCPサーバーエラー: {e}", file=sys.stderr)
        sys.exit(1)

