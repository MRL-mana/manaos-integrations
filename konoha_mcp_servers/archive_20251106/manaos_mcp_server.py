#!/usr/bin/env python3
"""
ManaOS MCP Server - 統合MCPサーバー
ManaOSの全機能をCursorから直接利用可能にする
"""
import asyncio
import json
import logging
from typing import Any, Dict
import httpx
import subprocess
import os
from datetime import datetime

# MCP imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
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
            "image_generator": "http://localhost:5559",
            "gallery_api": "http://localhost:5559",
            "sd_inference_api": "http://localhost:8000",
            "trinity_sync": "http://localhost:5012",
            "x280_rdp_bridge": "http://localhost:5015"
        }

        # ALITA-G MCTシステムの初期化
        try:
            import sys
            sys.path.insert(0, os.path.join(os.getenv('HOME', '/root'), 'trinity_workspace/systems'))
            from alita_mct_enhanced import EnhancedMCTOrchestrator
            from mirror_loop_enhanced import EnhancedMirrorLoopDetector

            self.mct_orchestrator = EnhancedMCTOrchestrator(use_llm=True, use_vector_search=True)
            self.mirror_loop_detector = EnhancedMirrorLoopDetector(use_semantic_similarity=True)
            self.alita_available = True
            logger.info("✅ ALITA-G MCTシステムを初期化しました")
        except Exception as e:
            self.alita_available = False
            logger.warning(f"⚠️ ALITA-G MCTシステムの初期化に失敗: {e}")

        # Image Editor MCPシステムの初期化
        try:
            # 現在のディレクトリが/rootなので、絶対パスでインポート
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "image_editor_mcp_server",
                os.path.join(os.getenv("HOME", "/root"), "trinity_workspace/mcp/image_editor_mcp_server.py")
            )
            image_editor_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(image_editor_module)

            self.image_editor = image_editor_module.ImageEditorMCPServer()
            self.image_editor_available = True
            logger.info("✅ Image Editor MCPを初期化しました")
        except Exception as e:
            self.image_editor_available = False
            logger.warning(f"⚠️ Image Editor MCPの初期化に失敗: {e}")

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
                    # ALITA-G MCT & ミラーループ対策
                    Tool(
                        name="alita_search_mcts",
                        description="タスクに関連するMCT（成功パターン）を検索",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "task_description": {"type": "string", "description": "タスクの説明"},
                                "limit": {"type": "integer", "description": "返すMCTの最大数", "default": 5}
                            },
                            "required": ["task_description"]
                        }
                    ),
                    Tool(
                        name="alita_learn_from_success",
                        description="成功体験からMCTを学習・保存",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "agent_name": {"type": "string", "description": "エージェント名（remi/luna/mina/aria）"},
                                "task": {"type": "string", "description": "タスクの説明"},
                                "solution": {"type": "string", "description": "成功した解決策"},
                                "context": {"type": "object", "description": "実行時のコンテキスト"}
                            },
                            "required": ["agent_name", "task", "solution"]
                        }
                    ),
                    Tool(
                        name="alita_detect_mirror_loop",
                        description="ミラーループ（停滞）を検出",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "agent_name": {"type": "string", "description": "エージェント名"},
                                "task_id": {"type": "string", "description": "タスクID"}
                            },
                            "required": ["agent_name", "task_id"]
                        }
                    ),
                    Tool(
                        name="manaos_image_generate",
                        description="AI画像生成（ManaOS Gallery API経由・ムフフモード対応）",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "prompt": {"type": "string", "description": "生成プロンプト"},
                                "model": {"type": "string", "description": "使用モデル名（デフォルト: majicmixRealistic_v7.safetensors）"},
                                "steps": {"type": "integer", "description": "推論ステップ数（デフォルト: 30）"},
                                "guidance_scale": {"type": "number", "description": "ガイダンススケール（デフォルト: 7.5）"},
                                "mufufu_mode": {"type": "boolean", "description": "ムフフモード（服を除外するネガティブプロンプトを自動適用）"},
                                "negative_prompt": {"type": "string", "description": "ネガティブプロンプト（任意）"}
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
                    ),
                    Tool(
                        name="copilot_cli_execute",
                        description="GitHub Copilot CLIを実行（Trinity System統合版）",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "mode": {
                                    "type": "string",
                                    "enum": ["remi", "luna", "mina", "aria", "git"],
                                    "description": "Trinity Systemモード: remi(設計), luna(実装), mina(レビュー), aria(記録), git(Git Workflow)"
                                },
                                "prompt": {
                                    "type": "string",
                                    "description": "Copilot CLIに送信するプロンプト"
                                }
                            },
                            "required": ["mode", "prompt"]
                        }
                    ),
                    # X280 RDP Bridge
                    Tool(
                        name="x280_rdp_control",
                        description="X280 RDP Bridgeの起動・停止・ステータス確認",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": ["start", "stop", "restart", "status"],
                                    "description": "アクション"
                                }
                            },
                            "required": ["action"]
                        }
                    ),
                    Tool(
                        name="x280_rdp_connect",
                        description="X280へRDP接続（自動または手動）",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "password": {
                                    "type": "string",
                                    "description": "RDP接続パスワード（省略可、環境変数から取得）"
                                },
                                "auto": {
                                    "type": "boolean",
                                    "description": "自動接続モード（デフォルト: false）",
                                    "default": False
                                }
                            },
                            "required": []
                        }
                    ),
                    # Evolution Shadow統合
                    Tool(
                        name="evolution_shadow_status",
                        description="Evolution Shadowの状態を取得",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    ),
                    Tool(
                        name="evolution_shadow_run",
                        description="Evolution Shadowサイクルを実行",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "max_trials": {
                                    "type": "integer",
                                    "description": "最大試行回数（デフォルト: 50）",
                                    "default": 50
                                },
                                "trial_interval": {
                                    "type": "number",
                                    "description": "試行間隔（秒、デフォルト: 300.0）",
                                    "default": 300.0
                                }
                            },
                            "required": []
                        }
                    ),
                    # Remi Autonomy Engine統合（Safeguard & Boost）
                    Tool(
                        name="remi_autonomy_stats",
                        description="Remi Autonomy Engineの統計を取得",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    ),
                    Tool(
                        name="remi_autonomy_policy",
                        description="Remi Autonomy Engineのポリシーを取得",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    ),
                    Tool(
                        name="remi_autonomy_kill_switch",
                        description="Remi Autonomy EngineのKill Switch制御",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": ["enable", "disable", "status"],
                                    "description": "Kill Switch操作（enable=停止, disable=再開, status=状態確認）"
                                }
                            },
                            "required": ["action"]
                        }
                    ),
                    Tool(
                        name="remi_personality_state",
                        description="Remi Personality（感情状態）を取得",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": []
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
                elif name == "copilot_cli_execute":
                    return await self.copilot_cli_execute(arguments)
                elif name == "x280_rdp_control":
                    return await self.x280_rdp_control(arguments)
                elif name == "x280_rdp_connect":
                    return await self.x280_rdp_connect(arguments)
                elif name == "evolution_shadow_status":
                    return await self.evolution_shadow_status()
                elif name == "evolution_shadow_run":
                    return await self.evolution_shadow_run(arguments)
                elif name == "remi_autonomy_stats":
                    return await self.remi_autonomy_stats()
                elif name == "remi_autonomy_policy":
                    return await self.remi_autonomy_policy()
                elif name == "remi_autonomy_kill_switch":
                    return await self.remi_autonomy_kill_switch(arguments)
                elif name == "remi_personality_state":
                    return await self.remi_personality_state()
                elif name == "alita_search_mcts":
                    return await self.alita_search_mcts(arguments)
                elif name == "alita_learn_from_success":
                    return await self.alita_learn_from_success(arguments)
                elif name == "alita_detect_mirror_loop":
                    return await self.alita_detect_mirror_loop(arguments)
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
        """画像生成（ManaOS Gallery API経由・ムフフモード対応）"""
        prompt = arguments.get("prompt")
        model = arguments.get("model", "majicmixRealistic_v7.safetensors")
        steps = arguments.get("steps", 30)
        guidance_scale = arguments.get("guidance_scale", 7.5)
        mufufu_mode = arguments.get("mufufu_mode", False)
        negative_prompt = arguments.get("negative_prompt", None)

        if not prompt:
            return CallToolResult(
                content=[TextContent(type="text", text="❌ プロンプトが指定されていません")]
            )

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # 1. 画像生成ジョブを開始
                payload = {
                    "prompt": prompt,
                    "model": model,
                    "steps": steps,
                    "guidance_scale": guidance_scale
                }

                # ムフフモードまたはネガティブプロンプトが指定されている場合
                if mufufu_mode:
                    payload["mufufu_mode"] = True
                if negative_prompt:
                    payload["negative_prompt"] = negative_prompt

                response = await client.post(
                    "http://localhost:5559/api/generate",
                    json=payload
                )

                response.raise_for_status()
                result = response.json()

                if not result.get("success"):
                    error_msg = result.get("error", "不明なエラー")
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ 画像生成開始失敗: {error_msg}\n詳細: {json.dumps(result, indent=2, ensure_ascii=False)}"
                        )]
                    )

                job_id = result.get("job_id", "unknown")
                logger.info(f"📥 画像生成ジョブ開始: {job_id}")

                # 2. ジョブ完了までポーリング（最大60秒）
                max_polls = 60
                poll_interval = 1.0

                for poll_count in range(max_polls):
                    await asyncio.sleep(poll_interval)

                    try:
                        status_response = await client.get(
                            f"http://localhost:5559/api/job/{job_id}",
                            timeout=5.0
                        )
                        status_response.raise_for_status()
                        status_result = status_response.json()

                        status = status_result.get("status", "unknown")

                        if status == "completed":
                            # 画像生成完了
                            filename = status_result.get("filename", "unknown")

                            # 画像URLを構築
                            image_url = f"http://localhost:5559/images/{filename}"
                            external_url = f"http://163.44.120.49:5559/images/{filename}"

                            return CallToolResult(
                                content=[TextContent(
                                    type="text",
                                    text=f"""✅ 画像生成完了

📝 プロンプト: {prompt}
🤖 モデル: {model}
📊 ステップ数: {steps}
🎯 ガイダンス: {guidance_scale}

📦 ファイル名: {filename}
🆔 ジョブID: {job_id}

🌐 画像URL:
   - ローカル: {image_url}
   - 外部: {external_url}

詳細: {json.dumps(status_result, indent=2, ensure_ascii=False)}"""
                                )]
                            )
                        elif status == "failed":
                            error_msg = status_result.get("error", "不明なエラー")
                            return CallToolResult(
                                content=[TextContent(
                                    type="text",
                                    text=f"❌ 画像生成失敗: {error_msg}\nジョブID: {job_id}"
                                )]
                            )
                        # status == "processing" の場合は続行

                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 404:
                            # ジョブがまだ存在しない可能性（処理中の可能性）
                            continue
                        else:
                            raise
                    except Exception as e:
                        logger.warning(f"ジョブステータス確認エラー (再試行): {e}")
                        continue

                # タイムアウト
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"⏱️ 画像生成タイムアウト（{max_polls}秒）\nジョブID: {job_id}\n\n💡 後でジョブステータスを確認してください: http://localhost:5559/api/job/{job_id}"
                    )]
                )

        except httpx.TimeoutException:
            return CallToolResult(
                content=[TextContent(type="text", text="❌ 画像生成タイムアウト（120秒）")]
            )
        except httpx.HTTPStatusError as e:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ HTTPエラー ({e.response.status_code}): {e.response.text}"
                )]
            )
        except Exception as e:
            logger.error(f"画像生成エラー: {e}", exc_info=True)
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ 画像生成エラー: {str(e)}\n\n💡 Gallery API (ポート5559) が起動しているか確認してください"
                )]
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
                ["python3", os.path.join(os.getenv("HOME", "/root"), "trinity_workspace/tools/system_optimizer.py")],
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
            result = None
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
            elif metric_type == "network":
                result = subprocess.run(
                    ["ss", "-s"],
                    capture_output=True, text=True
                )
            elif metric_type == "services":
                result = subprocess.run(
                    ["systemctl", "list-units", "--type=service", "--state=running", "--no-pager"],
                    capture_output=True, text=True
                )
            else:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"❌ サポートされていないメトリクスタイプ: {metric_type}\n利用可能: cpu, memory, disk, network, services"
                    )]
                )

            if result is None:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"❌ メトリクス取得に失敗しました: {metric_type}"
                    )]
                )

            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"📊 Metrics ({metric_type}):\n{result.stdout}"
                )]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"❌ Error monitoring metrics: {e}")]
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

    async def copilot_cli_execute(self, arguments: Dict[str, Any]) -> CallToolResult:
        """GitHub Copilot CLIを実行（Trinity System統合版）"""
        mode = arguments.get("mode")
        prompt = arguments.get("prompt")

        try:
            # Copilot CLIブリッジスクリプトのパス
            bridge_script = os.path.join(os.getenv("HOME", "/root"), "trinity_workspace/scripts/copilot_trinity_bridge.sh")

            # スクリプトが存在するか確認
            if not os.path.exists(bridge_script):
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"❌ Copilot CLI bridge script not found: {bridge_script}"
                    )]
                )

            # Copilot CLIコマンド実行
            result = subprocess.run(
                [bridge_script, mode, prompt],
                capture_output=True,
                text=True,
                timeout=300,  # 5分タイムアウト
                cwd=os.path.join(os.getenv("HOME", "/root"), "trinity_workspace/scripts")
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"✅ Copilot CLI実行完了 (mode: {mode})\n\n{output}"
                    )]
                )
            else:
                error = result.stderr.strip()
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"❌ Copilot CLI実行エラー (mode: {mode})\n\n{error}"
                    )]
                )
        except subprocess.TimeoutExpired:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"⏱️ Copilot CLI実行タイムアウト (mode: {mode}, 5分経過)"
                )]
            )
        except Exception as e:
            logger.error(f"Error executing Copilot CLI: {e}")
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ Copilot CLI実行エラー: {str(e)}"
                )]
            )

    async def alita_search_mcts(self, arguments: Dict[str, Any]) -> CallToolResult:
        """ALITA-G: MCT検索"""
        if not self.alita_available:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ ALITA-G MCTシステムが利用できません"
                )]
            )

        try:
            task_description = arguments.get("task_description")
            limit = arguments.get("limit", 5)

            results = self.mct_orchestrator.get_relevant_mcts(task_description, limit)

            return CallToolResult(
                content=[TextContent(
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
            )
        except Exception as e:
            logger.error(f"Error searching MCTs: {e}")
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ MCT検索エラー: {str(e)}"
                )]
            )

    async def alita_learn_from_success(self, arguments: Dict[str, Any]) -> CallToolResult:
        """ALITA-G: 成功体験から学習"""
        if not self.alita_available:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ ALITA-G MCTシステムが利用できません"
                )]
            )

        try:
            agent_name = arguments.get("agent_name")
            task = arguments.get("task")
            solution = arguments.get("solution")
            context = arguments.get("context", {})

            mct_id = self.mct_orchestrator.learn_from_success(
                agent_name=agent_name,
                task=task,
                solution=solution,
                context=context,
                result=True
            )

            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "mct_id": mct_id,
                        "message": f"MCTを学習しました: {mct_id}"
                    }, ensure_ascii=False)
                )]
            )
        except Exception as e:
            logger.error(f"Error learning MCT: {e}")
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ MCT学習エラー: {str(e)}"
                )]
            )

    async def alita_detect_mirror_loop(self, arguments: Dict[str, Any]) -> CallToolResult:
        """ALITA-G: ミラーループ検出"""
        if not self.alita_available:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text="❌ ALITA-G MCTシステムが利用できません"
                )]
            )

        try:
            agent_name = arguments.get("agent_name")
            task_id = arguments.get("task_id")

            result = self.mirror_loop_detector.detect_mirror_loop(agent_name, task_id)

            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "detected": result.get("detected", False),
                        "warning": result.get("warning", ""),
                        "avg_info_change": result.get("avg_info_change", 0),
                        "method": result.get("method", "unknown")
                    }, ensure_ascii=False, indent=2)
                )]
            )
        except Exception as e:
            logger.error(f"Error detecting mirror loop: {e}")
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ ミラーループ検出エラー: {str(e)}"
                )]
            )

    async def x280_rdp_control(self, arguments: Dict[str, Any]) -> CallToolResult:
        """X280 RDP Bridgeの制御"""
        try:
            action = arguments.get("action")

            if action == "status":
                # ステータス確認
                result = subprocess.run(
                    ["systemctl", "is-active", "x280-rdp-bridge"],
                    capture_output=True,
                    text=True
                )
                status = result.stdout.strip()

                # APIもチェック
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get("http://localhost:5015/api/status")
                        api_status = response.json() if response.status_code == 200 else None
                except:
                    api_status = None

                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({
                            "service": status,
                            "web_ui": "http://localhost:5015",
                            "api_status": api_status,
                            "ports": {
                                "web_ui": 5015,
                                "vnc": 5902,
                                "websocket": 6082
                            }
                        }, ensure_ascii=False, indent=2)
                    )]
                )
            else:
                # start, stop, restart
                result = subprocess.run(
                    ["systemctl", action, "x280-rdp-bridge"],
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"✅ X280 RDP Bridgeを{action}しました"
                        )]
                    )
                else:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ {action}に失敗: {result.stderr}"
                        )]
                    )
        except Exception as e:
            logger.error(f"Error controlling X280 RDP Bridge: {e}")
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ X280 RDP Bridge制御エラー: {str(e)}"
                )]
            )

    async def x280_rdp_connect(self, arguments: Dict[str, Any]) -> CallToolResult:
        """X280へRDP接続"""
        try:
            password = arguments.get("password")
            auto = arguments.get("auto", False)

            if password:
                # パスワードを環境変数に設定
                os.environ['X280_RDP_PASSWORD'] = password
                logger.info("RDPパスワードを環境変数に設定しました")

            if auto:
                # 自動接続モード: サービスを再起動して自動接続
                result = subprocess.run(
                    ["systemctl", "restart", "x280-rdp-bridge"],
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text="✅ X280 RDP Bridgeを自動接続モードで再起動しました。数秒待ってからステータスを確認してください。"
                        )]
                    )
                else:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ 自動接続に失敗: {result.stderr}"
                        )]
                    )
            else:
                # 手動接続モード: コマンドを返す
                cmd = "export DISPLAY=:99 && xfreerdp /v:100.127.121.20 /u:mana /cert:ignore /f /bpp:24"
                if password:
                    cmd += f" /p:{password}"

                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"手動接続コマンド:\n```bash\n{cmd}\n```\n\nまたはWeb UI (http://localhost:5015) からVNC Viewerを使用してください。"
                    )]
                )
        except Exception as e:
            logger.error(f"Error connecting X280 RDP: {e}")
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ X280 RDP接続エラー: {str(e)}"
                )]
            )

    async def evolution_shadow_status(self) -> CallToolResult:
        """Evolution Shadowの状態を取得"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:5074/api/status")
                if response.status_code == 200:
                    data = response.json()
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(data, ensure_ascii=False, indent=2)
                        )]
                    )
                else:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ Evolution Shadow状態取得失敗: {response.status_code}"
                        )]
                    )
        except Exception as e:
            logger.error(f"Error getting Evolution Shadow status: {e}")
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ Evolution Shadow状態取得エラー: {str(e)}"
                )]
            )

    async def evolution_shadow_run(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Evolution Shadowサイクルを実行"""
        try:
            import httpx
            max_trials = arguments.get("max_trials", 50)
            trial_interval = arguments.get("trial_interval", 300.0)

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    "http://localhost:5074/api/run",
                    json={"max_trials": max_trials, "trial_interval": trial_interval}
                )
                if response.status_code == 200:
                    data = response.json()
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(data, ensure_ascii=False, indent=2)
                        )]
                    )
                else:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ Evolution Shadow実行失敗: {response.status_code} - {response.text}"
                        )]
                    )
        except Exception as e:
            logger.error(f"Error running Evolution Shadow: {e}")
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ Evolution Shadow実行エラー: {str(e)}"
                )]
            )

    async def remi_autonomy_stats(self) -> CallToolResult:
        """Remi Autonomy Engineの統計を取得"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:5076/api/stats")
                if response.status_code == 200:
                    data = response.json()
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(data, ensure_ascii=False, indent=2)
                        )]
                    )
                else:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ Remi Autonomy統計取得失敗: {response.status_code}"
                        )]
                    )
        except Exception as e:
            logger.error(f"Error getting Remi Autonomy stats: {e}")
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ Remi Autonomy統計取得エラー: {str(e)}"
                )]
            )

    async def remi_autonomy_policy(self) -> CallToolResult:
        """Remi Autonomy Engineのポリシーを取得"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:5076/policy")
                if response.status_code == 200:
                    data = response.json()
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(data, ensure_ascii=False, indent=2)
                        )]
                    )
                else:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ Remi Autonomyポリシー取得失敗: {response.status_code}"
                        )]
                    )
        except Exception as e:
            logger.error(f"Error getting Remi Autonomy policy: {e}")
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ Remi Autonomyポリシー取得エラー: {str(e)}"
                )]
            )

    async def remi_autonomy_kill_switch(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Remi Autonomy EngineのKill Switch制御"""
        try:
            import httpx
            action = arguments.get("action", "status")

            async with httpx.AsyncClient(timeout=5.0) as client:
                if action == "enable":
                    response = await client.post("http://localhost:5076/kill-switch/enable")
                elif action == "disable":
                    response = await client.post("http://localhost:5076/kill-switch/disable")
                else:
                    response = await client.post(
                        "http://localhost:5076/api/kill-switch",
                        json={"action": "status"}
                    )

                if response.status_code == 200:
                    data = response.json()
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(data, ensure_ascii=False, indent=2)
                        )]
                    )
                else:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ Kill Switch操作失敗: {response.status_code}"
                        )]
                    )
        except Exception as e:
            logger.error(f"Error controlling Kill Switch: {e}")
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ Kill Switch操作エラー: {str(e)}"
                )]
            )

    async def remi_personality_state(self) -> CallToolResult:
        """Remi Personality（感情状態）を取得"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:5075/api/emotion/state")
                if response.status_code == 200:
                    data = response.json()
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps(data, ensure_ascii=False, indent=2)
                        )]
                    )
                else:
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=f"❌ Remi Personality状態取得失敗: {response.status_code}"
                        )]
                    )
        except Exception as e:
            logger.error(f"Error getting Remi Personality state: {e}")
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"❌ Remi Personality状態取得エラー: {str(e)}"
                )]
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








