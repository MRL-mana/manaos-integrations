#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RunPod GPU MCP Server
RunPod ServerlessをMCPツールとして提供
Cursor/Claudeから直接GPU機能を利用可能に
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict
from datetime import datetime

# MCPライブラリ
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsResult,
    Tool,
    TextContent,
)

# RunPod Manager
sys.path.insert(0, str(Path(__file__).parent.parent))
from services.runpod_serverless_manager import RunPodServerlessManager

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [RUNPOD-MCP] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RunPodMCPServer:
    """RunPod GPU MCPサーバー"""

    def __init__(self):
        self.server = Server("runpod-gpu")
        self.manager = RunPodServerlessManager()
        self.setup_tools()

    def setup_tools(self):
        """MCPツールをセットアップ"""

        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """利用可能なツール一覧"""
            return ListToolsResult(
                tools=[
                    Tool(
                        name="runpod_generate_image",
                        description="Stable Diffusionで画像を生成します。プロンプトから高品質な画像を作成。",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "prompt": {
                                    "type": "string",
                                    "description": "画像生成プロンプト（英語推奨）"
                                },
                                "width": {
                                    "type": "integer",
                                    "default": 512,
                                    "description": "画像の幅（ピクセル）"
                                },
                                "height": {
                                    "type": "integer",
                                    "default": 512,
                                    "description": "画像の高さ（ピクセル）"
                                },
                                "steps": {
                                    "type": "integer",
                                    "default": 30,
                                    "description": "生成ステップ数（多いほど高品質、時間がかかる）"
                                },
                                "guidance_scale": {
                                    "type": "number",
                                    "default": 7.5,
                                    "description": "ガイダンススケール（プロンプトへの忠実度）"
                                },
                                "model": {
                                    "type": "string",
                                    "default": "runwayml/stable-diffusion-v1-5",
                                    "description": "使用するStable Diffusionモデル"
                                },
                                "save_to_gdrive": {
                                    "type": "boolean",
                                    "default": False,
                                    "description": "Google Driveに自動保存するか"
                                }
                            },
                            "required": ["prompt"]
                        }
                    ),
                    Tool(
                        name="runpod_generate_text",
                        description="LLMでテキストを生成します。コード生成、文章作成、翻訳などに利用可能。",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "prompt": {
                                    "type": "string",
                                    "description": "テキスト生成プロンプト"
                                },
                                "model": {
                                    "type": "string",
                                    "default": "mistralai/Mistral-7B-Instruct-v0.2",
                                    "description": "使用するLLMモデル"
                                },
                                "max_length": {
                                    "type": "integer",
                                    "default": 512,
                                    "description": "最大生成文字数"
                                },
                                "temperature": {
                                    "type": "number",
                                    "default": 0.7,
                                    "description": "温度パラメータ（0.0-1.0、高いほど多様性）"
                                },
                                "top_p": {
                                    "type": "number",
                                    "default": 0.9,
                                    "description": "Nucleus sampling パラメータ"
                                }
                            },
                            "required": ["prompt"]
                        }
                    ),
                    Tool(
                        name="runpod_chat",
                        description="LLMとチャット形式で対話します。コードレビュー、質問回答、アイデア相談など。",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "メッセージ内容"
                                },
                                "system_prompt": {
                                    "type": "string",
                                    "default": "You are a helpful assistant.",
                                    "description": "システムプロンプト（AIの役割設定）"
                                },
                                "model": {
                                    "type": "string",
                                    "default": "mistralai/Mistral-7B-Instruct-v0.2",
                                    "description": "使用するLLMモデル"
                                },
                                "max_length": {
                                    "type": "integer",
                                    "default": 512,
                                    "description": "最大応答文字数"
                                },
                                "temperature": {
                                    "type": "number",
                                    "default": 0.7,
                                    "description": "温度パラメータ"
                                }
                            },
                            "required": ["message"]
                        }
                    ),
                    Tool(
                        name="runpod_get_job_status",
                        description="非同期ジョブのステータスを確認します",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "job_id": {
                                    "type": "string",
                                    "description": "ジョブID"
                                }
                            },
                            "required": ["job_id"]
                        }
                    ),
                    Tool(
                        name="runpod_test_gpu",
                        description="GPUの状態をテストします。RunPod接続とGPUの動作確認に使用。",
                        inputSchema={
                            "type": "object",
                            "properties": {}
                        }
                    ),
                    Tool(
                        name="runpod_batch_generate_images",
                        description="複数の画像を一括生成します",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "prompts": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "プロンプトのリスト"
                                },
                                "options": {
                                    "type": "object",
                                    "description": "共通オプション（width, height, stepsなど）",
                                    "default": {}
                                }
                            },
                            "required": ["prompts"]
                        }
                    )
                ]
            )

        @self.server.call_tool()
        async def call_tool(request: CallToolRequest) -> CallToolResult:
            """ツール実行"""
            tool_name = request.name
            args = request.arguments or {}

            try:
                logger.info(f"🔧 ツール実行: {tool_name}")

                if tool_name == "runpod_generate_image":
                    result = await handle_generate_image(self.manager, args)
                elif tool_name == "runpod_generate_text":
                    result = await handle_generate_text(self.manager, args)
                elif tool_name == "runpod_chat":
                    result = await handle_chat(self.manager, args)
                elif tool_name == "runpod_get_job_status":
                    result = await handle_get_job_status(self.manager, args)
                elif tool_name == "runpod_test_gpu":
                    result = await handle_test_gpu(self.manager)
                elif tool_name == "runpod_batch_generate_images":
                    result = await handle_batch_generate_images(self.manager, args)
                else:
                    raise ValueError(f"Unknown tool: {tool_name}")

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps(result, ensure_ascii=False, indent=2)
                        )
                    ]
                )

            except Exception as e:
                logger.error(f"❌ ツール実行エラー: {e}", exc_info=True)
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps({
                                "error": str(e),
                                "error_type": type(e).__name__
                            }, ensure_ascii=False)
                        )
                    ],
                    isError=True
                )


async def handle_generate_image(manager: RunPodServerlessManager, args: Dict) -> Dict:
    """画像生成処理"""
    prompt = args.get("prompt")
    width = args.get("width", 512)
    height = args.get("height", 512)
    steps = args.get("steps", 30)
    guidance_scale = args.get("guidance_scale", 7.5)
    model = args.get("model", "runwayml/stable-diffusion-v1-5")
    save_to_gdrive = args.get("save_to_gdrive", False)

    logger.info(f"🎨 画像生成開始: {prompt[:50]}...")

    # 同期実行（runsync使用）
    result = manager.client.generate_image(
        prompt=prompt,
        width=width,
        height=height,
        steps=steps,
        guidance_scale=guidance_scale,
        model=model
    )

    if result.get("status") == "completed" and result.get("output"):
        output = result["output"]
        image_base64 = output.get("image_base64", "")

        result_dict = {
            "success": True,
            "prompt": prompt,
            "job_id": result.get("id"),
            "width": width,
            "height": height,
            "image_base64": image_base64[:100] + "..." if len(image_base64) > 100 else image_base64,
            "image_size": len(image_base64),
            "saved_to_network_storage": output.get("saved_to_network_storage", False),
            "saved_path": output.get("saved_path", "")
        }

        # Google Drive保存
        if save_to_gdrive and image_base64:
            filename = f"runpod_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            gdrive_url = manager.save_to_google_drive(image_base64, filename)
            if gdrive_url:
                result_dict["gdrive_url"] = gdrive_url

        return result_dict
    else:
        return {
            "success": False,
            "error": result.get("error", "Unknown error"),
            "output": result.get("output")
        }


async def handle_generate_text(manager: RunPodServerlessManager, args: Dict) -> Dict:
    """テキスト生成処理"""
    prompt = args.get("prompt")
    model = args.get("model", "mistralai/Mistral-7B-Instruct-v0.2")
    max_length = args.get("max_length", 512)
    temperature = args.get("temperature", 0.7)
    top_p = args.get("top_p", 0.9)

    logger.info(f"🧠 テキスト生成開始: {prompt[:50]}...")

    result = manager.client.generate_text(
        prompt=prompt,
        model=model,
        max_length=max_length,
        temperature=temperature,
        top_p=top_p
    )

    if result.get("status") == "completed" and result.get("output"):
        output = result["output"]
        return {
            "success": True,
            "prompt": prompt,
            "generated_text": output.get("generated_text", ""),
            "model": model,
            "length": output.get("length", 0)
        }
    else:
        return {
            "success": False,
            "error": result.get("output", {}).get("error", "Unknown error"),
            "output": result.get("output")
        }


async def handle_chat(manager: RunPodServerlessManager, args: Dict) -> Dict:
    """チャット処理"""
    message = args.get("message")
    system_prompt = args.get("system_prompt", "You are a helpful assistant.")
    model = args.get("model", "mistralai/Mistral-7B-Instruct-v0.2")
    max_length = args.get("max_length", 512)
    temperature = args.get("temperature", 0.7)

    logger.info(f"💬 チャット開始: {message[:50]}...")

    result = manager.client.chat(
        message=message,
        system_prompt=system_prompt,
        model=model,
        max_length=max_length,
        temperature=temperature
    )

    if result.get("status") == "completed" and result.get("output"):
        output = result["output"]
        return {
            "success": True,
            "message": message,
            "response": output.get("response", ""),
            "model": model
        }
    else:
        return {
            "success": False,
            "error": result.get("output", {}).get("error", "Unknown error"),
            "output": result.get("output")
        }


async def handle_get_job_status(manager: RunPodServerlessManager, args: Dict) -> Dict:
    """ジョブステータス確認"""
    job_id = args.get("job_id")

    if not job_id:
        return {"error": "job_id is required"}

    result = manager.client.get_job_status(job_id)
    return {
        "job_id": job_id,
        "status": result.get("status"),
        "output": result.get("output")
    }


async def handle_test_gpu(manager: RunPodServerlessManager) -> Dict:
    """GPUテスト"""
    result = manager.client.test_gpu()

    if result.get("status") == "completed" and result.get("output"):
        return {
            "success": True,
            **result["output"]
        }
    else:
        return {
            "success": False,
            "error": result.get("output", {}).get("error", "Unknown error")
        }


async def handle_batch_generate_images(manager: RunPodServerlessManager, args: Dict) -> Dict:
    """バッチ画像生成"""
    prompts = args.get("prompts", [])
    options = args.get("options", {})

    if not prompts:
        return {"error": "prompts is required"}

    logger.info(f"📦 バッチ画像生成開始: {len(prompts)}件")

    results = manager.batch_generate_images(prompts, **options)

    return {
        "success": True,
        "total": len(prompts),
        "jobs": results
    }


async def main():
    """MCPサーバー起動"""
    server = RunPodMCPServer()

    logger.info("🚀 RunPod GPU MCP Server 起動中...")

    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())









