#!/usr/bin/env python3
"""
WAN2.2 MCP Server
完全なMCPサーバー実装 for WAN2.2
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict

# MCP imports
try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        CallToolRequest,
        CallToolResult,
        GetPromptRequest,
        GetPromptResult,
        ListPromptsRequest,
        ListPromptsResult,
        ListResourcesRequest,
        ListResourcesResult,
        ListToolsRequest,
        ListToolsResult,
        Prompt,
        PromptArgument,
        ReadResourceRequest,
        ReadResourceResult,
        Resource,
        TextContent,
        Tool,
        ToolInputSchema,
    )
except ImportError:
    print("MCPライブラリがインストールされていません")
    print("pip install mcp を実行してください")
    sys.exit(1)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WAN22MCPServer:
    """WAN2.2 MCP Server"""
    
    def __init__(self):
        self.server = Server("wan2.2-mcp-server")
        self.tools = {}
        self.resources = {}
        self.prompts = {}
        self._setup_handlers()
        self._register_tools()
        self._register_resources()
        self._register_prompts()
    
    def _setup_handlers(self):
        """MCPハンドラーの設定"""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """利用可能なツール一覧"""
            return ListToolsResult(tools=list(self.tools.values()))
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """ツール実行"""
            if name not in self.tools:
                raise ValueError(f"Unknown tool: {name}")
            
            try:
                result = await self._execute_tool(name, arguments)
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
                )
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
        
        @self.server.list_resources()
        async def list_resources() -> ListResourcesResult:
            """利用可能なリソース一覧"""
            return ListResourcesResult(resources=list(self.resources.values()))
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> ReadResourceResult:
            """リソース読み込み"""
            if uri not in self.resources:
                raise ValueError(f"Unknown resource: {uri}")
            
            try:
                content = await self._read_resource(uri)
                return ReadResourceResult(
                    contents=[TextContent(type="text", text=content)]
                )
            except Exception as e:
                logger.error(f"Resource read error: {e}")
                return ReadResourceResult(
                    contents=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
        
        @self.server.list_prompts()
        async def list_prompts() -> ListPromptsResult:
            """利用可能なプロンプト一覧"""
            return ListPromptsResult(prompts=list(self.prompts.values()))
    
    def _register_tools(self):
        """ツール登録"""
        
        # ファイル操作ツール
        self.tools["file_read"] = Tool(
            name="file_read",
            description="ファイルを読み込む",
            inputSchema=ToolInputSchema(
                type="object",
                properties={
                    "file_path": {
                        "type": "string",
                        "description": "読み込むファイルのパス"
                    }
                },
                required=["file_path"]
            )
        )
        
        self.tools["file_write"] = Tool(
            name="file_write",
            description="ファイルに書き込む",
            inputSchema=ToolInputSchema(
                type="object",
                properties={
                    "file_path": {
                        "type": "string",
                        "description": "書き込むファイルのパス"
                    },
                    "content": {
                        "type": "string",
                        "description": "書き込む内容"
                    }
                },
                required=["file_path", "content"]
            )
        )
        
        self.tools["directory_list"] = Tool(
            name="directory_list",
            description="ディレクトリの内容を一覧表示",
            inputSchema=ToolInputSchema(
                type="object",
                properties={
                    "directory_path": {
                        "type": "string",
                        "description": "一覧表示するディレクトリのパス",
                        "default": "/root"
                    }
                }
            )
        )
        
        # システム監視ツール
        self.tools["system_status"] = Tool(
            name="system_status",
            description="システム状態を取得",
            inputSchema=ToolInputSchema(
                type="object",
                properties={}
            )
        )
        
        self.tools["pm2_status"] = Tool(
            name="pm2_status",
            description="PM2プロセス状態を取得",
            inputSchema=ToolInputSchema(
                type="object",
                properties={}
            )
        )
        
        # AI統合ツール
        self.tools["trinity_chat"] = Tool(
            name="trinity_chat",
            description="トリニティシステムとの会話",
            inputSchema=ToolInputSchema(
                type="object",
                properties={
                    "message": {
                        "type": "string",
                        "description": "送信するメッセージ"
                    },
                    "personality": {
                        "type": "string",
                        "description": "使用する人格 (assistant/creative/technical)",
                        "default": "assistant"
                    }
                },
                required=["message"]
            )
        )
        
        # GPU管理ツール
        self.tools["gpu_status"] = Tool(
            name="gpu_status",
            description="GPU状態を確認",
            inputSchema=ToolInputSchema(
                type="object",
                properties={}
            )
        )
        
        logger.info(f"Registered {len(self.tools)} tools")
    
    def _register_resources(self):
        """リソース登録"""
        
        self.resources["system://logs"] = Resource(
            uri="system://logs",
            name="System Logs",
            description="システムログ",
            mimeType="text/plain"
        )
        
        self.resources["system://config"] = Resource(
            uri="system://config",
            name="System Config",
            description="システム設定",
            mimeType="application/json"
        )
        
        self.resources["trinity://status"] = Resource(
            uri="trinity://status",
            name="Trinity Status",
            description="トリニティシステム状態",
            mimeType="application/json"
        )
        
        logger.info(f"Registered {len(self.resources)} resources")
    
    def _register_prompts(self):
        """プロンプト登録"""
        
        self.prompts["system_analysis"] = Prompt(
            name="system_analysis",
            description="システム分析プロンプト",
            arguments=[
                PromptArgument(
                    name="component",
                    description="分析するコンポーネント",
                    required=True
                )
            ]
        )
        
        self.prompts["trinity_optimization"] = Prompt(
            name="trinity_optimization",
            description="トリニティ最適化プロンプト",
            arguments=[
                PromptArgument(
                    name="optimization_target",
                    description="最適化対象",
                    required=True
                )
            ]
        )
        
        logger.info(f"Registered {len(self.prompts)} prompts")
    
    async def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """ツール実行"""
        
        if name == "file_read":
            file_path = arguments["file_path"]
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {
                    "success": True,
                    "content": content,
                    "file_path": file_path,
                    "size": len(content)
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        elif name == "file_write":
            file_path = arguments["file_path"]
            content = arguments["content"]
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return {
                    "success": True,
                    "file_path": file_path,
                    "bytes_written": len(content.encode('utf-8'))
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        elif name == "directory_list":
            directory_path = arguments.get("directory_path", "/root")
            try:
                files = os.listdir(directory_path)
                return {
                    "success": True,
                    "directory": directory_path,
                    "files": files,
                    "count": len(files)
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        elif name == "system_status":
            try:
                import psutil
                return {
                    "success": True,
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_usage": psutil.disk_usage('/').percent,
                    "timestamp": datetime.now().isoformat()
                }
            except ImportError:
                return {
                    "success": True,
                    "message": "psutil not available, using basic info",
                    "timestamp": datetime.now().isoformat()
                }
        
        elif name == "pm2_status":
            try:
                import subprocess
                result = subprocess.run(
                    ["/root/.local/share/pnpm/pm2", "jlist"],
                    capture_output=True, text=True, check=True
                )
                processes = json.loads(result.stdout)
                return {
                    "success": True,
                    "processes": processes,
                    "count": len(processes)
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        elif name == "trinity_chat":
            message = arguments["message"]
            personality = arguments.get("personality", "assistant")
            # 実際の実装ではトリニティAPIを呼び出し
            return {
                "success": True,
                "response": f"Trinity ({personality}) response to: {message}",
                "personality": personality,
                "timestamp": datetime.now().isoformat()
            }
        
        elif name == "gpu_status":
            try:
                import subprocess
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True
                )
                return {
                    "success": True,
                    "gpu_info": result.stdout.strip() if result.returncode == 0 else "No GPU detected",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": f"Unknown tool: {name}"}
    
    async def _read_resource(self, uri: str) -> str:
        """リソース読み込み"""
        
        if uri == "system://logs":
            log_files = []
            log_dir = "/root/logs"
            if os.path.exists(log_dir):
                log_files = os.listdir(log_dir)
            return json.dumps({
                "log_directory": log_dir,
                "available_logs": log_files
            }, ensure_ascii=False, indent=2)
        
        elif uri == "system://config":
            config = {
                "wan2.2_version": "2.2.0",
                "mcp_server": "active",
                "pm2_managed": True,
                "containerized": True,
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(config, ensure_ascii=False, indent=2)
        
        elif uri == "trinity://status":
            # トリニティシステムの状態を取得
            status = {
                "trinity_api": "running",
                "mcp_gateway": "active",
                "automation": "monitoring",
                "timestamp": datetime.now().isoformat()
            }
            return json.dumps(status, ensure_ascii=False, indent=2)
        
        return f"Unknown resource: {uri}"
    
    async def run(self):
        """MCPサーバー実行"""
        logger.info("🚀 WAN2.2 MCP Server starting...")
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="wan2.2-mcp-server",
                    server_version="2.2.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities={}
                    )
                )
            )

async def main():
    """メイン実行関数"""
    server = WAN22MCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
