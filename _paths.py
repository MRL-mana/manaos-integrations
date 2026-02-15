"""ManaOS 共通パス定数 ─ ハードコードパスの排除.

すべてのモジュールで ``from _paths import INTEGRATIONS_DIR, OBSIDIAN_VAULT``
のようにインポートして使う。環境変数 > Path.home() フォールバック。
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------- ベースディレクトリ ----------
# このファイル自体が manaos_integrations/ の直下にある前提
INTEGRATIONS_DIR: Path = Path(__file__).resolve().parent

USER_HOME: Path = Path.home()

# ---------- Obsidian ----------
OBSIDIAN_VAULT: Path = Path(
    os.getenv(
        "OBSIDIAN_VAULT_PATH",
        str(USER_HOME / "Documents" / "Obsidian Vault"),
    )
)

# ---------- プロジェクトルート（manaos_integrations の親 = Desktop）----------
PROJECT_ROOT: Path = INTEGRATIONS_DIR.parent

# ---------- ログ ----------
LOGS_DIR: Path = INTEGRATIONS_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# ---------- サービスポート定数 ----------
# 環境変数で上書き可能。ハードコードの代わりにここを参照すること。
MRL_MEMORY_PORT: int = int(os.getenv("MRL_MEMORY_PORT", "5105"))
RAG_MEMORY_PORT: int = int(os.getenv("RAG_MEMORY_PORT", "5103"))
INTENT_ROUTER_PORT: int = int(os.getenv("INTENT_ROUTER_PORT", "5100"))
TASK_PLANNER_PORT: int = int(os.getenv("TASK_PLANNER_PORT", "5101"))
TASK_CRITIC_PORT: int = int(os.getenv("TASK_CRITIC_PORT", "5102"))
TASK_QUEUE_PORT: int = int(os.getenv("TASK_QUEUE_PORT", "5104"))
EXECUTOR_ENHANCED_PORT: int = int(os.getenv("EXECUTOR_ENHANCED_PORT", "5107"))
PORTAL_INTEGRATION_PORT: int = int(os.getenv("PORTAL_INTEGRATION_PORT", "5108"))
CONTENT_GENERATION_PORT: int = int(os.getenv("CONTENT_GENERATION_PORT", "5109"))
LEARNING_SYSTEM_PORT: int = int(os.getenv("LEARNING_SYSTEM_PORT", "5126"))
METRICS_COLLECTOR_PORT: int = int(os.getenv("METRICS_COLLECTOR_PORT", "5127"))
PERFORMANCE_DASHBOARD_PORT: int = int(os.getenv("PERFORMANCE_DASHBOARD_PORT", "5128"))
LLM_ROUTING_PORT: int = int(os.getenv("LLM_ROUTING_PORT", "5111"))
VIDEO_PIPELINE_PORT: int = int(os.getenv("VIDEO_PIPELINE_PORT", "5112"))
WINDOWS_AUTOMATION_PORT: int = int(os.getenv("WINDOWS_AUTOMATION_PORT", "5115"))
PERSONALITY_SYSTEM_PORT: int = int(os.getenv("PERSONALITY_SYSTEM_PORT", "5123"))
AUTONOMY_SYSTEM_PORT: int = int(os.getenv("AUTONOMY_SYSTEM_PORT", "5124"))
SECRETARY_SYSTEM_PORT: int = int(os.getenv("SECRETARY_SYSTEM_PORT", "5125"))
PICO_HID_PORT: int = int(os.getenv("PICO_HID_PORT", "5136"))
UNIFIED_API_PORT: int = int(os.getenv("PORT", os.getenv("UNIFIED_API_PORT", "9510")))
MCP_API_SERVER_PORT: int = int(os.getenv("MCP_API_SERVER_PORT", "9502"))
OLLAMA_PORT: int = int(os.getenv("OLLAMA_PORT", "11434"))
GALLERY_PORT: int = int(os.getenv("GALLERY_PORT", "5559"))
COMFYUI_PORT: int = int(os.getenv("COMFYUI_PORT", "8188"))
N8N_PORT: int = int(os.getenv("N8N_PORT", "5678"))
SEARXNG_PORT: int = int(os.getenv("SEARXNG_PORT", "8080"))
MOLTBOT_GATEWAY_PORT: int = int(os.getenv("MOLTBOT_GATEWAY_PORT", "8088"))
ORCHESTRATOR_PORT: int = int(os.getenv("ORCHESTRATOR_PORT", "5106"))
INTRINSIC_MOTIVATION_PORT: int = int(os.getenv("INTRINSIC_MOTIVATION_PORT", "5130"))
LM_STUDIO_PORT: int = int(os.getenv("LM_STUDIO_PORT", "1234"))
SECRETARY_API_PORT: int = int(os.getenv("SECRETARY_API_PORT", "5003"))
EVALUATION_UI_PORT: int = int(os.getenv("EVALUATION_UI_PORT", "9601"))
SLACK_INTEGRATION_PORT: int = int(os.getenv("SLACK_INTEGRATION_PORT", "5114"))
FILE_SECRETARY_PORT: int = int(os.getenv("FILE_SECRETARY_PORT", "5120"))
LEARNING_PORT: int = LEARNING_SYSTEM_PORT  # エイリアス（後方互換）
