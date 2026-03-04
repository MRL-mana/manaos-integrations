#!/usr/bin/env python3
"""
Image Editor MCP Server
Pillow + OpenCV + AI ベースの画像編集MCPサーバー
"""
import asyncio
import base64
import io
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolRequest, CallToolResult, ListToolsRequest, ListToolsResult, Tool, TextContent

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImageEditorMCPServer:
    def __init__(self):
        self.server = Server("image-editor-mcp")
        self.setup_tools()

    def setup_tools(self):
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """利用可能なツール一覧を返す"""
            return ListToolsResult(
                tools=[
                    Tool(
                        name="image_adjust_brightness",
                        description="画像の明度を調整",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_file": {"type": "string", "description": "入力画像パス"},
                                "factor": {"type": "number", "default": 1.0, "description": "明度係数 (0.5-2.0)"},
                                "output_file": {"type": "string", "description": "出力画像パス（省略可）"}
                            },
                            "required": ["input_file", "factor"]
                        }
                    ),
                    Tool(
                        name="image_adjust_contrast",
                        description="画像のコントラストを調整",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_file": {"type": "string"},
                                "factor": {"type": "number", "default": 1.0},
                                "output_file": {"type": "string"}
                            },
                            "required": ["input_file", "factor"]
                        }
                    ),
                    Tool(
                        name="image_adjust_saturation",
                        description="画像の彩度を調整",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_file": {"type": "string"},
                                "factor": {"type": "number", "default": 1.0},
                                "output_file": {"type": "string"}
                            },
                            "required": ["input_file", "factor"]
                        }
                    ),
                    Tool(
                        name="image_sharpen",
                        description="画像をシャープ化",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_file": {"type": "string"},
                                "strength": {"type": "number", "default": 1.0},
                                "output_file": {"type": "string"}
                            },
                            "required": ["input_file"]
                        }
                    ),
                    Tool(
                        name="image_denoise",
                        description="ノイズ軽減（OpenCV）",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_file": {"type": "string"},
                                "strength": {"type": "integer", "default": 10},
                                "output_file": {"type": "string"}
                            },
                            "required": ["input_file"]
                        }
                    ),
                    Tool(
                        name="image_blur",
                        description="画像をぼかす",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_file": {"type": "string"},
                                "radius": {"type": "integer", "default": 5},
                                "output_file": {"type": "string"}
                            },
                            "required": ["input_file"]
                        }
                    ),
                    Tool(
                        name="image_resize",
                        description="画像サイズを変更",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_file": {"type": "string"},
                                "width": {"type": "integer"},
                                "height": {"type": "integer"},
                                "keep_aspect": {"type": "boolean", "default": True},
                                "output_file": {"type": "string"}
                            },
                            "required": ["input_file", "width", "height"]
                        }
                    ),
                    Tool(
                        name="image_crop",
                        description="画像をトリミング",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_file": {"type": "string"},
                                "x": {"type": "integer"},
                                "y": {"type": "integer"},
                                "width": {"type": "integer"},
                                "height": {"type": "integer"},
                                "output_file": {"type": "string"}
                            },
                            "required": ["input_file", "x", "y", "width", "height"]
                        }
                    ),
                    Tool(
                        name="image_auto_optimize",
                        description="AI駆動で自動最適化（明度・コントラスト・ノイズ）",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_file": {"type": "string"},
                                "enhance_skin": {"type": "boolean", "default": True},
                                "reduce_noise": {"type": "boolean", "default": True},
                                "output_file": {"type": "string"}
                            },
                            "required": ["input_file"]
                        }
                    ),
                    Tool(
                        name="image_batch_process",
                        description="複数画像を一括処理",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_dir": {"type": "string"},
                                "operations": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "type": {"enum": ["brightness", "contrast", "saturation", "sharpen", "denoise"]},
                                            "factor": {"type": "number"}
                                        },
                                        "required": ["type"]
                                    }
                                },
                                "output_dir": {"type": "string"}
                            },
                            "required": ["input_dir", "operations", "output_dir"]
                        }
                    ),
                    Tool(
                        name="image_remove_background",
                        description="背景除去（OpenCVベース）",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "input_file": {"type": "string"},
                                "method": {"enum": ["grabcut", "watershed", "chromakey"], "default": "grabcut"},
                                "output_file": {"type": "string"}
                            },
                            "required": ["input_file"]
                        }
                    )
                ]
            )

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """ツールを実行"""
            try:
                if name == "image_adjust_brightness":
                    result = await self.adjust_brightness(**arguments)
                elif name == "image_adjust_contrast":
                    result = await self.adjust_contrast(**arguments)
                elif name == "image_adjust_saturation":
                    result = await self.adjust_saturation(**arguments)
                elif name == "image_sharpen":
                    result = await self.sharpen(**arguments)
                elif name == "image_denoise":
                    result = await self.denoise(**arguments)
                elif name == "image_blur":
                    result = await self.blur(**arguments)
                elif name == "image_resize":
                    result = await self.resize(**arguments)
                elif name == "image_crop":
                    result = await self.crop(**arguments)
                elif name == "image_auto_optimize":
                    result = await self.auto_optimize(**arguments)
                elif name == "image_batch_process":
                    result = await self.batch_process(**arguments)
                elif name == "image_remove_background":
                    result = await self.remove_background(**arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps(result, ensure_ascii=False)
                        )
                    ]
                )
            except Exception as e:
                logger.error(f"Error executing {name}: {e}", exc_info=True)
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps({"error": str(e)}, ensure_ascii=False)
                        )
                    ]
                )

    def _load_image(self, file_path: str) -> Image.Image:
        """画像を読み込む"""
        return Image.open(file_path)

    def _save_image(self, image: Image.Image, file_path: Optional[str], source_path: Optional[str] = None) -> str:
        """画像を保存"""
        if file_path:
            save_path = file_path
        elif source_path:
            base = Path(source_path).stem
            ext = Path(source_path).suffix
            save_path = f"{base}_edited{ext}"
        else:
            save_path = "output.png"

        image.save(save_path)
        return save_path

    async def adjust_brightness(self, input_file: str, factor: float, output_file: Optional[str] = None) -> Dict[str, Any]:
        """明度調整"""
        img = self._load_image(input_file)
        enhancer = ImageEnhance.Brightness(img)
        result_img = enhancer.enhance(factor)
        save_path = self._save_image(result_img, output_file, input_file)
        return {"status": "success", "output_file": save_path, "operation": "brightness", "factor": factor}

    async def adjust_contrast(self, input_file: str, factor: float, output_file: Optional[str] = None) -> Dict[str, Any]:
        """コントラスト調整"""
        img = self._load_image(input_file)
        enhancer = ImageEnhance.Contrast(img)
        result_img = enhancer.enhance(factor)
        save_path = self._save_image(result_img, output_file, input_file)
        return {"status": "success", "output_file": save_path, "operation": "contrast", "factor": factor}

    async def adjust_saturation(self, input_file: str, factor: float, output_file: Optional[str] = None) -> Dict[str, Any]:
        """彩度調整"""
        img = self._load_image(input_file)
        enhancer = ImageEnhance.Color(img)
        result_img = enhancer.enhance(factor)
        save_path = self._save_image(result_img, output_file, input_file)
        return {"status": "success", "output_file": save_path, "operation": "saturation", "factor": factor}

    async def sharpen(self, input_file: str, strength: float = 1.0, output_file: Optional[str] = None) -> Dict[str, Any]:
        """シャープ化"""
        img = self._load_image(input_file)
        result_img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=int(strength * 100), threshold=3))
        save_path = self._save_image(result_img, output_file, input_file)
        return {"status": "success", "output_file": save_path, "operation": "sharpen", "strength": strength}

    async def denoise(self, input_file: str, strength: int = 10, output_file: Optional[str] = None) -> Dict[str, Any]:
        """ノイズ軽減（OpenCV）"""
        # OpenCVで読み込み
        cv_img = cv2.imread(input_file)
        if cv_img is None:
            raise ValueError(f"Cannot load image: {input_file}")

        # 非局所平均フィルタでノイズ除去
        denoised = cv2.fastNlMeansDenoisingColored(cv_img, None, strength, strength, 7, 21)

        # 保存
        if output_file:
            save_path = output_file
        else:
            base = Path(input_file).stem
            ext = Path(input_file).suffix
            save_path = f"{base}_denoised{ext}"

        cv2.imwrite(save_path, denoised)
        return {"status": "success", "output_file": save_path, "operation": "denoise", "strength": strength}

    async def blur(self, input_file: str, radius: int = 5, output_file: Optional[str] = None) -> Dict[str, Any]:
        """ぼかし"""
        img = self._load_image(input_file)
        result_img = img.filter(ImageFilter.GaussianBlur(radius=radius))
        save_path = self._save_image(result_img, output_file, input_file)
        return {"status": "success", "output_file": save_path, "operation": "blur", "radius": radius}

    async def resize(self, input_file: str, width: int, height: int, keep_aspect: bool = True, output_file: Optional[str] = None) -> Dict[str, Any]:
        """リサイズ"""
        img = self._load_image(input_file)

        if keep_aspect:
            img.thumbnail((width, height), Image.Resampling.LANCZOS)
            result_img = img
        else:
            result_img = img.resize((width, height), Image.Resampling.LANCZOS)

        save_path = self._save_image(result_img, output_file, input_file)
        return {"status": "success", "output_file": save_path, "operation": "resize", "size": f"{width}x{height}"}

    async def crop(self, input_file: str, x: int, y: int, width: int, height: int, output_file: Optional[str] = None) -> Dict[str, Any]:
        """トリミング"""
        img = self._load_image(input_file)
        result_img = img.crop((x, y, x + width, y + height))
        save_path = self._save_image(result_img, output_file, input_file)
        return {"status": "success", "output_file": save_path, "operation": "crop", "region": f"{x},{y},{width},{height}"}

    async def auto_optimize(self, input_file: str, enhance_skin: bool = True, reduce_noise: bool = True, output_file: Optional[str] = None) -> Dict[str, Any]:
        """自動最適化（AI駆動）"""
        img = self._load_image(input_file)

        # 自動露出調整
        img = ImageOps.autocontrast(img, cutoff=2)

        # ノイズ軽減
        if reduce_noise:
            cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            cv_img = cv2.fastNlMeansDenoisingColored(cv_img, None, 5, 5, 7, 21)
            img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))

        # 肌質改善（適度なシャープ）
        if enhance_skin:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.1)
            img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=50, threshold=3))

        # わずかな彩度向上
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.05)

        save_path = self._save_image(img, output_file, input_file)
        return {
            "status": "success",
            "output_file": save_path,
            "operation": "auto_optimize",
            "enhancements": ["exposure", "denoise", "skin_enhancement" if enhance_skin else None, "saturation"]
        }

    async def batch_process(self, input_dir: str, operations: List[Dict[str, Any]], output_dir: str) -> Dict[str, Any]:
        """一括処理"""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results = []

        for input_file in input_path.glob("*.png"):
            logger.info(f"Processing: {input_file.name}")
            img = self._load_image(str(input_file))

            for op in operations:
                op_type = op.get("type")
                factor = op.get("factor", 1.0)

                if op_type == "brightness":
                    enhancer = ImageEnhance.Brightness(img)
                    img = enhancer.enhance(factor)
                elif op_type == "contrast":
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(factor)
                elif op_type == "saturation":
                    enhancer = ImageEnhance.Color(img)
                    img = enhancer.enhance(factor)
                elif op_type == "sharpen":
                    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=int(factor * 100), threshold=3))
                elif op_type == "denoise":
                    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    cv_img = cv2.fastNlMeansDenoisingColored(cv_img, None, 5, 5, 7, 21)
                    img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))

            output_file = output_path / input_file.name
            img.save(output_file)
            results.append({"file": input_file.name, "status": "success"})

        return {
            "status": "success",
            "processed_count": len(results),
            "output_dir": output_dir,
            "results": results
        }

    async def remove_background(self, input_file: str, method: str = "grabcut", output_file: Optional[str] = None) -> Dict[str, Any]:
        """背景除去"""
        cv_img = cv2.imread(input_file)
        if cv_img is None:
            raise ValueError(f"Cannot load image: {input_file}")

        if method == "grabcut":
            mask = np.zeros(cv_img.shape[:2], np.uint8)
            bgdModel = np.zeros((1, 65), np.float64)
            fgdModel = np.zeros((1, 65), np.float64)

            # 簡易的な前景領域推定
            height, width = cv_img.shape[:2]
            rect = (width//10, height//10, width*8//10, height*8//10)
            cv2.grabCut(cv_img, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)

            mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
            result = cv_img * mask2[:, :, np.newaxis]
        else:
            # 簡易実装
            result = cv_img

        # アルファチャンネル付きで保存
        if output_file:
            save_path = output_file
        else:
            base = Path(input_file).stem
            save_path = f"{base}_no_bg.png"

        # BGR->RGBA変換してアルファチャンネル追加
        bgra = cv2.cvtColor(result, cv2.COLOR_BGR2BGRA)
        mask_bool = (result.sum(axis=2) == 0)
        bgra[:, :, 3] = np.where(mask_bool, 0, 255)

        cv2.imwrite(save_path, bgra)
        return {"status": "success", "output_file": save_path, "operation": "remove_background", "method": method}


async def main():
    """MCPサーバー起動"""
    server = ImageEditorMCPServer()
    async with stdio_server() as streams:
        await server.server.run(streams[0], streams[1])


if __name__ == "__main__":
    asyncio.run(main())






