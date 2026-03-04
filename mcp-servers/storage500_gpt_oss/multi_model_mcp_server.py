#!/usr/bin/env python3
"""
Multi-Model MCP Server
複数のAIモデルを管理・切り替えするMCPサーバー
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
    ImageContent,
)

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiModelMCPServer:
    def __init__(self):
        self.server = Server("multi-model-ai")
        self.models = {}
        self.current_model = None
        self.model_configs = {
            "gpt-oss-20b": {
                "path": "/mnt/storage500/gpt-oss-models/gpt-oss-20b-quantized",
                "type": "transformers",
                "max_length": 2048,
                "description": "GPT-OSS-20B (20B parameters, highest performance)"
            },
            "gemma-3-12b": {
                "path": "/mnt/storage500/gpt-oss-models/gemma-3-12b-it",
                "type": "transformers",
                "max_length": 2048,
                "description": "Gemma-3-12b-it (12B parameters, high performance)"
            },
            "gemma-3-4b": {
                "path": "/mnt/storage500/gpt-oss-models/gemma-3-4b-it",
                "type": "transformers",
                "max_length": 2048,
                "description": "Gemma-3-4b-it (4B parameters, lightweight)"
            },
            "qwen2.5-3b": {
                "path": "qwen2.5:3b",
                "type": "ollama",
                "max_length": 1024,
                "description": "Qwen2.5-3b (3B parameters, current default)"
            }
        }
        self.setup_handlers()

    def setup_handlers(self):
        """MCPハンドラーを設定"""
        
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """利用可能なツール一覧を返す"""
            tools = [
                Tool(
                    name="list_models",
                    description="利用可能なAIモデル一覧を取得",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="switch_model",
                    description="AIモデルを切り替え",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "model_name": {
                                "type": "string",
                                "description": "切り替え先のモデル名"
                            }
                        },
                        "required": ["model_name"]
                    }
                ),
                Tool(
                    name="generate_text",
                    description="テキスト生成",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "生成するテキストのプロンプト"
                            },
                            "max_length": {
                                "type": "integer",
                                "description": "最大生成長",
                                "default": 512
                            },
                            "temperature": {
                                "type": "number",
                                "description": "生成のランダム性",
                                "default": 0.7
                            }
                        },
                        "required": ["prompt"]
                    }
                ),
                Tool(
                    name="get_model_info",
                    description="現在のモデル情報を取得",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="health_check",
                    description="システムヘルスチェック",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                )
            ]
            return ListToolsResult(tools=tools)

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """ツール呼び出しを処理"""
            try:
                if name == "list_models":
                    return await self.list_models()
                elif name == "switch_model":
                    return await self.switch_model(arguments.get("model_name"))
                elif name == "generate_text":
                    return await self.generate_text(
                        arguments.get("prompt", ""),
                        arguments.get("max_length", 512),
                        arguments.get("temperature", 0.7)
                    )
                elif name == "get_model_info":
                    return await self.get_model_info()
                elif name == "health_check":
                    return await self.health_check()
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Unknown tool: {name}")]
                    )
            except Exception as e:
                logger.error(f"Tool call error: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )

    async def list_models(self) -> CallToolResult:
        """利用可能なモデル一覧を返す"""
        models_info = []
        for name, config in self.model_configs.items():
            status = "✅ Loaded" if name in self.models else "⏳ Available"
            models_info.append(f"- {name}: {config['description']} ({status})")
        
        current = f"Current: {self.current_model}" if self.current_model else "No model loaded"
        
        content = f"""🤖 Available AI Models:
{chr(10).join(models_info)}

{current}"""
        
        return CallToolResult(
            content=[TextContent(type="text", text=content)]
        )

    async def switch_model(self, model_name: str) -> CallToolResult:
        """モデルを切り替え"""
        if model_name not in self.model_configs:
            return CallToolResult(
                content=[TextContent(type="text", text=f"❌ Unknown model: {model_name}")]
            )
        
        try:
            # 既存のモデルをアンロード
            if self.current_model and self.current_model in self.models:
                del self.models[self.current_model]
            
            # 新しいモデルをロード
            config = self.model_configs[model_name]
            
            if config["type"] == "ollama":
                # Ollamaモデルの場合
                self.current_model = model_name
                self.models[model_name] = {"type": "ollama", "config": config}
            else:
                # Transformersモデルの場合
                logger.info(f"Loading model: {model_name}")
                tokenizer = AutoTokenizer.from_pretrained(config["path"])
                model = AutoModelForCausalLM.from_pretrained(
                    config["path"],
                    torch_dtype=torch.float16,
                    device_map="auto"
                )
                
                self.models[model_name] = {
                    "tokenizer": tokenizer,
                    "model": model,
                    "config": config
                }
                self.current_model = model_name
            
            return CallToolResult(
                content=[TextContent(type="text", text=f"✅ Switched to {model_name}")]
            )
            
        except Exception as e:
            logger.error(f"Model switch error: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"❌ Failed to switch model: {str(e)}")]
            )

    async def generate_text(self, prompt: str, max_length: int = 512, temperature: float = 0.7) -> CallToolResult:
        """テキスト生成"""
        if not self.current_model or self.current_model not in self.models:
            return CallToolResult(
                content=[TextContent(type="text", text="❌ No model loaded")]
            )
        
        try:
            model_data = self.models[self.current_model]
            
            if model_data["type"] == "ollama":
                # Ollama APIを使用
                import requests
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": model_data["config"]["path"],
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_length
                        }
                    }
                )
                result = response.json()
                generated_text = result.get("response", "")
            else:
                # Transformersモデルを使用
                tokenizer = model_data["tokenizer"]
                model = model_data["model"]
                
                inputs = tokenizer.encode(prompt, return_tensors="pt")
                with torch.no_grad():
                    outputs = model.generate(
                        inputs,
                        max_length=max_length,
                        temperature=temperature,
                        do_sample=True,
                        pad_token_id=tokenizer.eos_token_id
                    )
                
                generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
                # プロンプト部分を除去
                generated_text = generated_text[len(prompt):].strip()
            
            return CallToolResult(
                content=[TextContent(type="text", text=generated_text)]
            )
            
        except Exception as e:
            logger.error(f"Text generation error: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"❌ Generation failed: {str(e)}")]
            )

    async def get_model_info(self) -> CallToolResult:
        """現在のモデル情報を取得"""
        if not self.current_model:
            return CallToolResult(
                content=[TextContent(type="text", text="❌ No model loaded")]
            )
        
        config = self.model_configs[self.current_model]
        info = f"""🤖 Current Model: {self.current_model}
📝 Description: {config['description']}
📁 Path: {config['path']}
🔧 Type: {config['type']}
📏 Max Length: {config['max_length']}"""
        
        return CallToolResult(
            content=[TextContent(type="text", text=info)]
        )

    async def health_check(self) -> CallToolResult:
        """ヘルスチェック"""
        status = {
            "server": "✅ Running",
            "models_loaded": len(self.models),
            "current_model": self.current_model or "None",
            "available_models": list(self.model_configs.keys())
        }
        
        content = f"""🏥 System Health Check:
{chr(10).join([f"- {k}: {v}" for k, v in status.items()])}"""
        
        return CallToolResult(
            content=[TextContent(type="text", text=content)]
        )

    async def run(self):
        """MCPサーバーを実行"""
        logger.info("🚀 Starting Multi-Model MCP Server...")
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="multi-model-ai",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities={}
                    )
                )
            )

if __name__ == "__main__":
    server = MultiModelMCPServer()
    asyncio.run(server.run())
