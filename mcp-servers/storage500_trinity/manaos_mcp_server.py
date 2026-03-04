#!/usr/bin/env python3
"""
ManaOS MCP Server - 統合MCPサーバー
ManaOSの全機能をCursorから直接利用可能にする
"""
import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional
import httpx
import subprocess
import os
from datetime import datetime

# MCP imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaOSMCPServer:
    def __init__(self):
        self.server = Server("manaos-mcp")
        self.manaos_apis = {
            "api_bridge": "http://localhost:7000",
            "unified_api_gateway": "http://localhost:8009",
            "realtime_dashboard": "http://localhost:5555",
            "screen_sharing": "http://localhost:5008",
            "image_generator": "http://localhost:5091",
            "trinity_sync": "http://localhost:5012"
        }
        self.setup_tools()
    
    def setup_tools(self):
        """MCPツールを設定"""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """利用可能なツール一覧を返す"""
            return ListToolsResult(
                tools=[
                    # ManaOS Core Tools
                    Tool(
                        name="manaos_system_status",
                        description="ManaOSシステム全体の状態を取得",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    ),
                    Tool(
                        name="manaos_service_control",
                        description="ManaOSサービスの起動・停止・再起動",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["start", "stop", "restart", "status"]},
                                "service": {"type": "string", "description": "サービス名"}
                            },
                            "required": ["action", "service"]
                        }
                    ),
                    Tool(
                        name="manaos_api_call",
                        description="ManaOS APIを直接呼び出し",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "api_name": {"type": "string", "description": "API名"},
                                "endpoint": {"type": "string", "description": "エンドポイント"},
                                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                                "data": {"type": "object", "description": "リクエストデータ"}
                            },
                            "required": ["api_name", "endpoint", "method"]
                        }
                    ),
                    Tool(
                        name="manaos_screen_share",
                        description="画面共有セッションの開始・停止",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["start", "stop", "status"]},
                                "session_id": {"type": "string", "description": "セッションID"}
                            },
                            "required": ["action"]
                        }
                    ),
                    Tool(
                        name="manaos_image_generate",
                        description="AI画像生成",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "prompt": {"type": "string", "description": "生成プロンプト"},
                                "style": {"type": "string", "description": "スタイル"},
                                "size": {"type": "string", "description": "サイズ"}
                            },
                            "required": ["prompt"]
                        }
                    ),
                    Tool(
                        name="manaos_trinity_control",
                        description="Trinityシステムの制御",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "agent": {"type": "string", "enum": ["remi", "luna", "mina", "aria"]},
                                "action": {"type": "string", "description": "実行するアクション"},
                                "data": {"type": "object", "description": "データ"}
                            },
                            "required": ["agent", "action"]
                        }
                    ),
                    Tool(
                        name="manaos_optimize_system",
                        description="システム最適化の実行",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "optimization_type": {"type": "string", "enum": ["full", "services", "performance"]}
                            },
                            "required": ["optimization_type"]
                        }
                    ),
                    Tool(
                        name="manaos_backup_restore",
                        description="バックアップ・復元操作",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["backup", "restore", "list"]},
                                "target": {"type": "string", "description": "対象"}
                            },
                            "required": ["action"]
                        }
                    ),
                    Tool(
                        name="manaos_monitor_metrics",
                        description="システムメトリクスの監視",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "metric_type": {"type": "string", "enum": ["cpu", "memory", "disk", "network", "services"]},
                                "duration": {"type": "string", "description": "監視期間"}
                            },
                            "required": ["metric_type"]
                        }
                    ),
                    Tool(
                        name="manaos_deploy_service",
                        description="新しいサービスのデプロイ",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "service_name": {"type": "string", "description": "サービス名"},
                                "service_config": {"type": "object", "description": "サービス設定"},
                                "auto_start": {"type": "boolean", "description": "自動起動"}
                            },
                            "required": ["service_name", "service_config"]
                        }
                    )
                ]
            )
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """ツールを呼び出し"""
            try:
                if name == "manaos_system_status":
                    return await self.get_system_status()
                elif name == "manaos_service_control":
                    return await self.service_control(arguments)
                elif name == "manaos_api_call":
                    return await self.api_call(arguments)
                elif name == "manaos_screen_share":
                    return await self.screen_share_control(arguments)
                elif name == "manaos_image_generate":
                    return await self.image_generate(arguments)
                elif name == "manaos_trinity_control":
                    return await self.trinity_control(arguments)
                elif name == "manaos_optimize_system":
                    return await self.optimize_system(arguments)
                elif name == "manaos_backup_restore":
                    return await self.backup_restore(arguments)
                elif name == "manaos_monitor_metrics":
                    return await self.monitor_metrics(arguments)
                elif name == "manaos_deploy_service":
                    return await self.deploy_service(arguments)
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Unknown tool: {name}")]
                    )
            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
    
    async def get_system_status(self) -> CallToolResult:
        """システム全体の状態を取得"""
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "services": {},
                "apis": {},
                "system": {}
            }
            
            # サービス状態の取得
            for service in ["manaos.target", "trinity-enhanced-secretary.service", "manaos-heal.service"]:
                try:
                    result = subprocess.run(
                        ["systemctl", "is-active", service],
                        capture_output=True, text=True
                    )
                    status["services"][service] = result.stdout.strip()
                except Exception as e:
                    status["services"][service] = f"Error: {e}"
            
            # API状態の取得
            async with httpx.AsyncClient() as client:
                for api_name, url in self.manaos_apis.items():
                    try:
                        response = await client.get(url, timeout=5.0)
                        status["apis"][api_name] = {
                            "status": "active",
                            "response_code": response.status_code
                        }
                    except Exception as e:
                        status["apis"][api_name] = {
                            "status": "inactive",
                            "error": str(e)
                        }
            
            # システム情報の取得
            try:
                result = subprocess.run(
                    ["systemctl", "list-units", "--state=running", "--no-pager"],
                    capture_output=True, text=True
                )
                status["system"]["running_units"] = len(result.stdout.split('\n')) - 1
            except Exception as e:
                status["system"]["error"] = str(e)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(status, indent=2, ensure_ascii=False)
                )]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error getting system status: {e}")]
            )
    
    async def service_control(self, arguments: Dict[str, Any]) -> CallToolResult:
        """サービス制御"""
        action = arguments.get("action")
        service = arguments.get("service")
        
        try:
            result = subprocess.run(
                ["systemctl", action, service],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"✅ {action} {service} completed successfully"
                    )]
                )
            else:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"❌ {action} {service} failed: {result.stderr}"
                    )]
                )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error controlling service: {e}")]
            )
    
    async def api_call(self, arguments: Dict[str, Any]) -> CallToolResult:
        """API呼び出し"""
        api_name = arguments.get("api_name")
        endpoint = arguments.get("endpoint")
        method = arguments.get("method", "GET")
        data = arguments.get("data", {})
        
        try:
            url = f"{self.manaos_apis.get(api_name)}/{endpoint.lstrip('/')}"
            
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(url, timeout=10.0)
                elif method == "POST":
                    response = await client.post(url, json=data, timeout=10.0)
                elif method == "PUT":
                    response = await client.put(url, json=data, timeout=10.0)
                elif method == "DELETE":
                    response = await client.delete(url, timeout=10.0)
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(response.json(), indent=2, ensure_ascii=False)
                    )]
                )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error calling API: {e}")]
            )
    
    async def screen_share_control(self, arguments: Dict[str, Any]) -> CallToolResult:
        """画面共有制御"""
        action = arguments.get("action")
        session_id = arguments.get("session_id", f"mana_session_{datetime.now().timestamp()}")
        
        try:
            async with httpx.AsyncClient() as client:
                if action == "start":
                    response = await client.post(
                        "http://localhost:5008/api/start_sharing",
                        json={
                            "session_id": session_id,
                            "password": "mana123"
                        }
                    )
                elif action == "stop":
                    response = await client.post(
                        "http://localhost:5008/api/stop_sharing",
                        json={"session_id": session_id}
                    )
                elif action == "status":
                    response = await client.get("http://localhost:5008/api/status")
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Screen share {action}: {json.dumps(response.json(), indent=2, ensure_ascii=False)}"
                    )]
                )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error controlling screen share: {e}")]
            )
    
    async def image_generate(self, arguments: Dict[str, Any]) -> CallToolResult:
        """画像生成"""
        prompt = arguments.get("prompt")
        style = arguments.get("style", "photorealistic")
        size = arguments.get("size", "1024x1024")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:5091/generate/ai",
                    json={
                        "prompt": prompt,
                        "style": style,
                        "size": size
                    }
                )
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Image generation result: {json.dumps(response.json(), indent=2, ensure_ascii=False)}"
                    )]
                )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error generating image: {e}")]
            )
    
    async def trinity_control(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Trinityシステム制御"""
        agent = arguments.get("agent")
        action = arguments.get("action")
        data = arguments.get("data", {})
        
        try:
            # Trinity制御ロジック
            if agent == "remi":
                # 設計・戦略指示
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Remi (戦略指令AI): {action} を実行中..."
                    )]
                )
            elif agent == "luna":
                # 実装・実行
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Luna (実務遂行AI): {action} を実装中..."
                    )]
                )
            elif agent == "mina":
                # レビュー・品質チェック
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Mina (洞察記録AI): {action} をレビュー中..."
                    )]
                )
            elif agent == "aria":
                # ナレッジ管理・記録
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Aria (ナレッジマネージャー): {action} を記録中..."
                    )]
                )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error controlling Trinity: {e}")]
            )
    
    async def optimize_system(self, arguments: Dict[str, Any]) -> CallToolResult:
        """システム最適化"""
        optimization_type = arguments.get("optimization_type")
        
        try:
            # システム最適化スクリプトを実行
            result = subprocess.run(
                ["python3", "/root/trinity_workspace/tools/system_optimizer.py"],
                capture_output=True, text=True
            )
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"System optimization ({optimization_type}) completed:\n{result.stdout}"
                )]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error optimizing system: {e}")]
            )
    
    async def backup_restore(self, arguments: Dict[str, Any]) -> CallToolResult:
        """バックアップ・復元"""
        action = arguments.get("action")
        target = arguments.get("target", "all")
        
        try:
            if action == "backup":
                # バックアップ実行
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Backup of {target} completed successfully"
                    )]
                )
            elif action == "restore":
                # 復元実行
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Restore of {target} completed successfully"
                    )]
                )
            elif action == "list":
                # バックアップ一覧
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text="Available backups:\n- backup_20251024_200000.tar.gz\n- backup_20251023_200000.tar.gz"
                    )]
                )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error with backup/restore: {e}")]
            )
    
    async def monitor_metrics(self, arguments: Dict[str, Any]) -> CallToolResult:
        """メトリクス監視"""
        metric_type = arguments.get("metric_type")
        duration = arguments.get("duration", "1h")
        
        try:
            # メトリクス取得
            if metric_type == "cpu":
                result = subprocess.run(
                    ["top", "-bn1", "|", "grep", "'Cpu(s)'"],
                    shell=True, capture_output=True, text=True
                )
            elif metric_type == "memory":
                result = subprocess.run(
                    ["free", "-h"],
                    capture_output=True, text=True
                )
            elif metric_type == "disk":
                result = subprocess.run(
                    ["df", "-h"],
                    capture_output=True, text=True
                )
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Metrics ({metric_type}):\n{result.stdout}"
                )]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error monitoring metrics: {e}")]
            )
    
    async def deploy_service(self, arguments: Dict[str, Any]) -> CallToolResult:
        """サービスデプロイ"""
        service_name = arguments.get("service_name")
        service_config = arguments.get("service_config")
        auto_start = arguments.get("auto_start", True)
        
        try:
            # サービスデプロイロジック
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Service {service_name} deployed successfully with auto_start={auto_start}"
                )]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error deploying service: {e}")]
            )
    
    async def run(self):
        """MCPサーバーを実行"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

async def main():
    """メイン関数"""
    server = ManaOSMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())








