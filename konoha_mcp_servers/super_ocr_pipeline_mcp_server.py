#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Super OCR Pipeline MCP Server
超解像→OCRパイプラインをMCP経由で利用可能に
"""

import asyncio
import logging
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsResult,
    Tool,
    TextContent
)

# ローカルモジュール
import sys
sys.path.insert(0, str(Path(__file__).parent))

from pipeline import SuperOCRPipeline
from upscale import upscale_image
from preprocess import preprocess_image
from ocr_to_excel import ocr_to_excel
from pdf_ocr import pdf_ocr

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class SuperOCRPipelineMCPServer:
    """超解像→OCRパイプラインMCPサーバー"""

    def __init__(self):
        self.server = Server("super-ocr-pipeline")
        self.pipeline = SuperOCRPipeline()
        self.setup_tools()

    def setup_tools(self):
        """MCPツールをセットアップ"""

        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """利用可能なツール一覧"""
            return ListToolsResult(
                tools=[
                    Tool(
                        name="ocr_pipeline_process",
                        description="超解像→前処理→OCRの完全パイプラインを実行。画像をExcel/CSV/JSONに変換",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_path": {
                                    "type": "string",
                                    "description": "入力画像パス"
                                },
                                "output_format": {
                                    "type": "string",
                                    "enum": ["excel", "csv", "json", "txt"],
                                    "default": "excel",
                                    "description": "出力形式"
                                },
                                "skip_upscale": {
                                    "type": "boolean",
                                    "default": False,
                                    "description": "超解像をスキップ（既に高解像度の場合）"
                                }
                            },
                            "required": ["input_path"]
                        }
                    ),
                    Tool(
                        name="ocr_pipeline_batch",
                        description="scanフォルダ内の全ファイルを一括処理",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "output_format": {
                                    "type": "string",
                                    "enum": ["excel", "csv", "json", "txt"],
                                    "default": "excel",
                                    "description": "出力形式"
                                }
                            }
                        }
                    ),
                    Tool(
                        name="ocr_upscale",
                        description="Real-ESRGANで画像を超解像",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_path": {"type": "string"},
                                "output_path": {"type": "string"},
                                "model": {
                                    "type": "string",
                                    "default": "realesrgan-x4plus",
                                    "description": "モデル名"
                                },
                                "scale": {
                                    "type": "integer",
                                    "default": 4,
                                    "description": "スケール倍率"
                                }
                            },
                            "required": ["input_path"]
                        }
                    ),
                    Tool(
                        name="ocr_preprocess",
                        description="画像前処理（ノイズ除去・シャープ化・傾き補正）",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_path": {"type": "string"},
                                "output_path": {"type": "string"},
                                "mode": {
                                    "type": "string",
                                    "enum": ["full", "minimal", "denoise_only"],
                                    "default": "full",
                                    "description": "処理モード"
                                }
                            },
                            "required": ["input_path"]
                        }
                    ),
                    Tool(
                        name="ocr_extract",
                        description="OCR実行（PaddleOCR）してExcel/CSV/JSONに変換",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_path": {"type": "string"},
                                "output_path": {"type": "string"},
                                "format": {
                                    "type": "string",
                                    "enum": ["excel", "csv", "json", "txt"],
                                    "default": "excel"
                                },
                                "lang": {
                                    "type": "string",
                                    "default": "japan",
                                    "description": "OCR言語"
                                }
                            },
                            "required": ["input_path"]
                        }
                    ),
                    Tool(
                        name="ocr_pdf",
                        description="PDFにOCRを実行して検索可能PDFに変換",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_path": {"type": "string"},
                                "output_path": {"type": "string"},
                                "lang": {
                                    "type": "string",
                                    "default": "jpn",
                                    "description": "OCR言語"
                                },
                                "deskew": {
                                    "type": "boolean",
                                    "default": True,
                                    "description": "傾き補正を有効化"
                                }
                            },
                            "required": ["input_path"]
                        }
                    ),
                    Tool(
                        name="ocr_status",
                        description="パイプラインのステータス確認",
                        inputSchema={
                            "type": "object",
                            "properties": {}
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
                if tool_name == "ocr_pipeline_process":
                    result = self.pipeline.process_image(
                        args["input_path"],
                        args.get("output_format", "excel"),
                        args.get("skip_upscale", False)
                    )
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=f"✅ パイプライン処理完了\n出力: {result}"
                            )
                        ]
                    )

                elif tool_name == "ocr_pipeline_batch":
                    results = self.pipeline.process_scan_folder(
                        args.get("output_format", "excel")
                    )
                    success_count = len([r for r in results if r.get("status") == "success"])
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=f"✅ バッチ処理完了\n成功: {success_count}/{len(results)}ファイル"
                            )
                        ]
                    )

                elif tool_name == "ocr_upscale":
                    upscale_image(
                        args["input_path"],
                        args.get("output_path") or Path(args["input_path"]).parent / f"{Path(args['input_path']).stem}_upscaled{Path(args['input_path']).suffix}",
                        args.get("model", "realesrgan-x4plus"),
                        args.get("scale", 4)
                    )
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text="✅ 超解像完了"
                            )
                        ]
                    )

                elif tool_name == "ocr_preprocess":
                    preprocess_image(
                        args["input_path"],
                        args.get("output_path") or Path(args["input_path"]).parent / f"{Path(args['input_path']).stem}_preprocessed{Path(args['input_path']).suffix}",
                        args.get("mode", "full")
                    )
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text="✅ 前処理完了"
                            )
                        ]
                    )

                elif tool_name == "ocr_extract":
                    result = ocr_to_excel(
                        args["input_path"],
                        args.get("output_path") or Path(args["input_path"]).parent / f"{Path(args['input_path']).stem}_ocr.xlsx",
                        args.get("format", "excel"),
                        args.get("lang", "japan")
                    )
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=f"✅ OCR完了\n出力: {result}"
                            )
                        ]
                    )

                elif tool_name == "ocr_pdf":
                    pdf_ocr(
                        args["input_path"],
                        args.get("output_path") or Path(args["input_path"]).parent / f"{Path(args['input_path']).stem}_ocr.pdf",
                        args.get("lang", "jpn"),
                        args.get("deskew", True)
                    )
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text="✅ PDF OCR完了"
                            )
                        ]
                    )

                elif tool_name == "ocr_status":
                    scan_count = len(list(Path(self.pipeline.scan_dir).glob("*")))
                    output_count = len(list(Path(self.pipeline.output_dir).glob("*")))
                    processed_count = len(list(Path(self.pipeline.processed_dir).glob("*")))

                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=f"📊 パイプラインステータス\n"
                                     f"scanフォルダ: {scan_count}ファイル\n"
                                     f"outputフォルダ: {output_count}ファイル\n"
                                     f"processedフォルダ: {processed_count}ファイル"
                            )
                        ]
                    )

                else:
                    raise ValueError(f"未知のツール: {tool_name}")

            except Exception as e:
                logger.error(f"ツール実行エラー: {e}", exc_info=True)
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"❌ エラー: {str(e)}"
                        )
                    ],
                    isError=True
                )


async def main():
    """MCPサーバー起動"""
    server_instance = SuperOCRPipelineMCPServer()

    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            server_instance.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())




