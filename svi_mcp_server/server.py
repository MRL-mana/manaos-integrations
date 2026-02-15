"""
SVI × Wan 2.2 動画生成 MCPサーバー
Cursorから直接SVI動画生成を実行できるMCPサーバー
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Optional
from manaos_logger import get_logger

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import sys

# SVI統合モジュールをインポート
sys_path = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(sys_path))

from svi_wan22_video_integration import SVIWan22VideoIntegration

logger = get_logger(__name__)

# 環境変数から設定を読み込み
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")

# SVI統合インスタンス
svi_integration = None


def get_svi_integration():
    """SVI統合インスタンスを取得"""
    global svi_integration
    if svi_integration is None:
        svi_integration = SVIWan22VideoIntegration(base_url=COMFYUI_URL)
    return svi_integration

# MCPサーバーの作成
server = Server("svi-video-generation")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """利用可能なツール一覧を返す"""
    return [
        Tool(
            name="svi_generate_video",
            description="SVI × Wan 2.2で動画を生成します。開始画像とプロンプトを指定して動画を生成できます。",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_image_path": {
                        "type": "string",
                        "description": "開始画像のパス（必須）"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "プロンプト（日本語可、必須）"
                    },
                    "video_length_seconds": {
                        "type": "integer",
                        "description": "動画の長さ（秒、デフォルト: 5）",
                        "default": 5
                    },
                    "steps": {
                        "type": "integer",
                        "description": "ステップ数（6-12推奨、デフォルト: 6）",
                        "default": 6
                    },
                    "motion_strength": {
                        "type": "number",
                        "description": "モーション強度（1.3-1.5推奨、デフォルト: 1.3）",
                        "default": 1.3
                    },
                    "sage_attention": {
                        "type": "boolean",
                        "description": "Sage Attentionを有効にするか（デフォルト: true）",
                        "default": True
                    }
                },
                "required": ["start_image_path", "prompt"]
            }
        ),
        Tool(
            name="svi_extend_video",
            description="既存の動画を延長します。前の動画の続きを生成できます。",
            inputSchema={
                "type": "object",
                "properties": {
                    "previous_video_path": {
                        "type": "string",
                        "description": "前の動画のパス（必須）"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "延長部分のプロンプト（必須）"
                    },
                    "extend_seconds": {
                        "type": "integer",
                        "description": "延長する秒数（デフォルト: 5）",
                        "default": 5
                    },
                    "steps": {
                        "type": "integer",
                        "description": "ステップ数（デフォルト: 6）",
                        "default": 6
                    },
                    "motion_strength": {
                        "type": "number",
                        "description": "モーション強度（デフォルト: 1.3）",
                        "default": 1.3
                    }
                },
                "required": ["previous_video_path", "prompt"]
            }
        ),
        Tool(
            name="svi_create_story_video",
            description="ストーリー性のある長編動画を作成します。複数のシーンを連続して生成できます。",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_image_path": {
                        "type": "string",
                        "description": "開始画像のパス（必須）"
                    },
                    "story_prompts": {
                        "type": "array",
                        "description": "ストーリープロンプトのリスト（必須）",
                        "items": {
                            "type": "object",
                            "properties": {
                                "timestamp": {
                                    "type": "integer",
                                    "description": "タイムスタンプ（秒）"
                                },
                                "prompt": {
                                    "type": "string",
                                    "description": "プロンプト"
                                }
                            },
                            "required": ["timestamp", "prompt"]
                        }
                    },
                    "segment_length_seconds": {
                        "type": "integer",
                        "description": "各セグメントの長さ（秒、デフォルト: 5）",
                        "default": 5
                    },
                    "steps": {
                        "type": "integer",
                        "description": "ステップ数（デフォルト: 6）",
                        "default": 6
                    },
                    "motion_strength": {
                        "type": "number",
                        "description": "モーション強度（デフォルト: 1.3）",
                        "default": 1.3
                    }
                },
                "required": ["start_image_path", "story_prompts"]
            }
        ),
        Tool(
            name="svi_get_queue_status",
            description="ComfyUIのキュー状態を取得します。実行中・待機中のジョブ数を確認できます。",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="svi_get_history",
            description="実行履歴を取得します。過去に実行した動画生成の履歴を確認できます。",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_items": {
                        "type": "integer",
                        "description": "取得する最大件数（デフォルト: 10）",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="svi_check_connection",
            description="ComfyUIへの接続を確認します。ComfyUIが起動しているかチェックできます。",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """ツールを実行"""
    try:
        svi = get_svi_integration()
        
        if name == "svi_check_connection":
            is_available = svi.is_available()
            if is_available:
                return [TextContent(
                    type="text",
                    text=f"✅ ComfyUIに接続できました\nURL: {COMFYUI_URL}"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"❌ ComfyUIに接続できません\nURL: {COMFYUI_URL}\n\nComfyUIを起動してください:\ncd C:\\ComfyUI\npython main.py --port 8188"
                )]
        
        elif name == "svi_generate_video":
            start_image_path = arguments.get("start_image_path")
            prompt = arguments.get("prompt")
            video_length_seconds = arguments.get("video_length_seconds", 5)
            steps = arguments.get("steps", 6)
            motion_strength = arguments.get("motion_strength", 1.3)
            sage_attention = arguments.get("sage_attention", True)
            
            if not start_image_path or not prompt:
                return [TextContent(
                    type="text",
                    text="❌ エラー: start_image_path と prompt は必須です"
                )]
            
            prompt_id = svi.generate_video(
                start_image_path=start_image_path,
                prompt=prompt,
                video_length_seconds=video_length_seconds,
                steps=steps,
                motion_strength=motion_strength,
                sage_attention=sage_attention
            )
            
            if prompt_id:
                return [TextContent(
                    type="text",
                    text=f"✅ 動画生成が開始されました\n\n実行ID: {prompt_id}\n開始画像: {start_image_path}\nプロンプト: {prompt}\n動画の長さ: {video_length_seconds}秒\nステップ数: {steps}\nモーション強度: {motion_strength}\n\n生成状況を確認:\n- ComfyUIのUI: http://127.0.0.1:8188\n- キュー状態: svi_get_queue_status を使用"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"❌ 動画生成に失敗しました\n\n開始画像: {start_image_path}\nプロンプト: {prompt}\n\nエラーログを確認してください"
                )]
        
        elif name == "svi_extend_video":
            previous_video_path = arguments.get("previous_video_path")
            prompt = arguments.get("prompt")
            extend_seconds = arguments.get("extend_seconds", 5)
            steps = arguments.get("steps", 6)
            motion_strength = arguments.get("motion_strength", 1.3)
            
            if not previous_video_path or not prompt:
                return [TextContent(
                    type="text",
                    text="❌ エラー: previous_video_path と prompt は必須です"
                )]
            
            prompt_id = svi.extend_video(
                previous_video_path=previous_video_path,
                prompt=prompt,
                extend_seconds=extend_seconds,
                steps=steps,
                motion_strength=motion_strength
            )
            
            if prompt_id:
                return [TextContent(
                    type="text",
                    text=f"✅ 動画延長が開始されました\n\n実行ID: {prompt_id}\n前の動画: {previous_video_path}\nプロンプト: {prompt}\n延長秒数: {extend_seconds}秒"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"❌ 動画延長に失敗しました\n\n前の動画: {previous_video_path}\nプロンプト: {prompt}"
                )]
        
        elif name == "svi_create_story_video":
            start_image_path = arguments.get("start_image_path")
            story_prompts = arguments.get("story_prompts")
            segment_length_seconds = arguments.get("segment_length_seconds", 5)
            steps = arguments.get("steps", 6)
            motion_strength = arguments.get("motion_strength", 1.3)
            
            if not start_image_path or not story_prompts:
                return [TextContent(
                    type="text",
                    text="❌ エラー: start_image_path と story_prompts は必須です"
                )]
            
            execution_ids = svi.create_story_video(
                start_image_path=start_image_path,
                story_prompts=story_prompts,
                segment_length_seconds=segment_length_seconds,
                steps=steps,
                motion_strength=motion_strength
            )
            
            return [TextContent(
                type="text",
                text=f"✅ ストーリー動画生成が開始されました\n\n実行ID数: {len(execution_ids)}\n開始画像: {start_image_path}\nセグメント数: {len(story_prompts)}\n各セグメントの長さ: {segment_length_seconds}秒\n\n実行ID: {', '.join(str(eid) for eid in execution_ids if eid)}"
            )]
        
        elif name == "svi_get_queue_status":
            queue_status = svi.get_queue_status()
            return [TextContent(
                type="text",
                text=f"キュー状態:\n{json.dumps(queue_status, indent=2, ensure_ascii=False)}"
            )]
        
        elif name == "svi_get_history":
            max_items = arguments.get("max_items", 10)
            history = svi.get_history(max_items=max_items)
            return [TextContent(
                type="text",
                text=f"実行履歴 ({len(history)}件):\n{json.dumps(history, indent=2, ensure_ascii=False)}"
            )]
        
        else:
            return [TextContent(
                type="text",
                text=f"❌ 未知のツール: {name}"
            )]
    
    except Exception as e:
        logger.error(f"ツール実行エラー: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"❌ エラーが発生しました: {str(e)}"
        )]

async def main():
    """メイン関数"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())

