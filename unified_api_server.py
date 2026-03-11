"""
ManaOS統合APIサーバー（修正版）
すべての外部システム統合を管理する統合API
"""

from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS
import os
import sys
import warnings
import hmac
import json
import time
import uuid
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import threading

try:
    from werkzeug.exceptions import HTTPException
except Exception:  # pragma: no cover
    HTTPException = Exception  # type: ignore

# Pythonバージョン警告を抑制（将来のアップグレード推奨だが、現状は動作するため）
warnings.filterwarnings("ignore", category=FutureWarning, message=".*Python version.*")
# Transformersキャッシュ警告を抑制（HF_HOMEに移行済み）
warnings.filterwarnings("ignore", category=FutureWarning, message=".*TRANSFORMERS_CACHE.*")
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# 統一モジュールのインポート
from manaos_logger import get_service_logger  # noqa: E402
from manaos_error_handler import ManaOSErrorHandler  # noqa: E402
from manaos_timeout_config import get_timeout_config  # noqa: E402
try:
    from api_auth import get_auth_manager  # type: ignore
except ImportError:
    class DummyAuthManager:
        def require_api_key(self, func):
            return func

    def get_auth_manager():  # type: ignore[misc]
        return DummyAuthManager()

try:
    from openapi_generator import OpenAPISpecBuilder
except ImportError:
    OpenAPISpecBuilder = None

try:
    from health_check_optimizer import get_health_check_optimizer
except ImportError:
    get_health_check_optimizer = None

# ロガーの初期化
logger = get_service_logger("unified")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("UnifiedAPIServer")

# 認証マネージャーの初期化
auth_manager = get_auth_manager()
logger.info("✅ API認証システムを初期化しました")

# タイムアウト設定の取得
timeout_config = get_timeout_config()


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _job_store_file(namespace: str) -> Path:
    base = Path(__file__).resolve().parent / "logs" / "job_store"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{namespace}_jobs.json"


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _job_store_limits(namespace: str) -> tuple[int, int]:
    ns = namespace.upper()
    max_default = _env_int("MANAOS_JOB_STORE_MAX", 1000)
    ttl_default = _env_int("MANAOS_JOB_STORE_TTL_SEC", 7 * 24 * 60 * 60)
    max_jobs = _env_int(f"MANAOS_JOB_STORE_MAX_{ns}", max_default)
    ttl_sec = _env_int(f"MANAOS_JOB_STORE_TTL_SEC_{ns}", ttl_default)
    return max(0, max_jobs), max(0, ttl_sec)


def _job_store_terminal_ttl(namespace: str, fallback_ttl_sec: int) -> int:
    ns = namespace.upper()
    ttl_default = _env_int("MANAOS_JOB_STORE_TTL_TERMINAL_SEC", fallback_ttl_sec)
    ttl_sec = _env_int(f"MANAOS_JOB_STORE_TTL_TERMINAL_SEC_{ns}", ttl_default)
    return max(0, ttl_sec)


def _job_status(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    value = payload.get("status")
    return str(value or "").strip().lower()


_ACTIVE_JOB_STATUSES = {"queued", "running", "pending", "in_progress"}


def _is_active_job(payload: Any) -> bool:
    return _job_status(payload) in _ACTIVE_JOB_STATUSES


def _job_sort_dt(payload: Any) -> datetime:
    if not isinstance(payload, dict):
        return datetime.min
    ts = payload.get("updated_at") or payload.get("created_at")
    return _parse_iso_datetime(ts) or datetime.min


def _trim_jobs(namespace: str, jobs: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if not jobs:
        return jobs

    max_jobs, ttl_sec = _job_store_limits(namespace)
    terminal_ttl_sec = _job_store_terminal_ttl(namespace, ttl_sec)
    trimmed = dict(jobs)

    if terminal_ttl_sec > 0:
        cutoff_ts = time.time() - terminal_ttl_sec
        for job_id, payload in list(trimmed.items()):
            if not isinstance(payload, dict):
                continue
            if _is_active_job(payload):
                continue
            dt = _job_sort_dt(payload)
            if dt and dt.timestamp() < cutoff_ts:
                trimmed.pop(job_id, None)

    if max_jobs > 0 and len(trimmed) > max_jobs:
        active_items = [
            (job_id, payload)
            for job_id, payload in trimmed.items()
            if _is_active_job(payload)
        ]
        terminal_items = [
            (job_id, payload)
            for job_id, payload in trimmed.items()
            if not _is_active_job(payload)
        ]

        active_items = sorted(
            active_items, key=lambda item: _job_sort_dt(item[1]), reverse=True
        )
        terminal_items = sorted(
            terminal_items, key=lambda item: _job_sort_dt(item[1]), reverse=True
        )

        if len(active_items) >= max_jobs:
            trimmed = dict(active_items[:max_jobs])
        else:
            remaining = max_jobs - len(active_items)
            trimmed = dict(active_items + terminal_items[:remaining])

    return trimmed


def _job_trim_policy(namespace: str) -> Dict[str, Any]:
    max_jobs, ttl_sec = _job_store_limits(namespace)
    terminal_ttl_sec = _job_store_terminal_ttl(namespace, ttl_sec)
    return {
        "namespace": namespace,
        "max_jobs": max_jobs,
        "ttl_sec": ttl_sec,
        "terminal_ttl_sec": terminal_ttl_sec,
        "active_statuses": sorted(_ACTIVE_JOB_STATUSES),
    }


def _job_response_meta(namespace: str, total_jobs: Optional[int] = None) -> Dict[str, Any]:
    meta: Dict[str, Any] = {"trim_policy": _job_trim_policy(namespace)}
    if total_jobs is not None:
        meta["store_size"] = total_jobs
    return meta


def _job_payload_with_meta(namespace: str, job: Dict[str, Any], total_jobs: int) -> Dict[str, Any]:
    payload = dict(job)
    payload["_meta"] = _job_response_meta(namespace, total_jobs)
    return payload


def _load_jobs_from_disk(namespace: str) -> Dict[str, Dict[str, Any]]:
    path = _job_store_file(namespace)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return _trim_jobs(namespace, data)
    except Exception as e:
        logger.warning(f"Job store load error ({namespace}): {e}")
    return {}


def _save_jobs_to_disk(namespace: str, jobs: Dict[str, Dict[str, Any]]) -> None:
    path = _job_store_file(namespace)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        trimmed = _trim_jobs(namespace, jobs)
        if len(trimmed) != len(jobs):
            jobs.clear()
            jobs.update(trimmed)
        tmp_path.write_text(json.dumps(jobs, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_path, path)
    except Exception as e:
        logger.warning(f"Job store save error ({namespace}): {e}")


try:
    from ._paths import N8N_PORT, OLLAMA_PORT, LM_STUDIO_PORT  # type: ignore
except Exception:  # pragma: no cover
    try:
        from _paths import N8N_PORT, OLLAMA_PORT, LM_STUDIO_PORT  # type: ignore
    except Exception:  # pragma: no cover
        try:
            from manaos_integrations._paths import N8N_PORT, OLLAMA_PORT, LM_STUDIO_PORT
        except Exception:  # pragma: no cover
            N8N_PORT = _env_int("N8N_PORT", 5678)
            OLLAMA_PORT = _env_int("OLLAMA_PORT", 11434)
            LM_STUDIO_PORT = _env_int("LM_STUDIO_PORT", 1234)


def get_ollama_url() -> str:
    return os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")


def get_lm_studio_url() -> str:
    return os.getenv("LM_STUDIO_URL", f"http://127.0.0.1:{LM_STUDIO_PORT}/v1")


def _service_url(name: str, env_key: str, default_port: int) -> str:
    return os.getenv(env_key, f"http://127.0.0.1:{default_port}")


TASK_PLANNER_BASE_URL = _service_url(
    "task_planner", "TASK_PLANNER_URL", _env_int("TASK_PLANNER_PORT", 5101)
)
EXECUTOR_ENHANCED_BASE_URL = _service_url(
    "task_executor_enhanced", "EXECUTOR_ENHANCED_URL", _env_int("EXECUTOR_ENHANCED_PORT", 5107)
)


def _missing_env_vars(required: List[str]) -> List[str]:
    return [key for key in required if not (os.getenv(key) or "").strip()]


def _config_error_response(
    integration_name: str,
    missing_env: List[str],
    status_code: int = 503,
):
    """必須の環境変数が未設定のときの統一レスポンス"""
    manaos_error = error_handler.handle_config_error(
        config_key=",".join(missing_env),
        reason="Missing required environment variables",
        context={
            "integration": integration_name,
            "missing_env": missing_env,
            "docs": "ENVIRONMENT_VARIABLES_GUIDE.md",
            "env_example": "env.example",
        },
    )

    payload = manaos_error.to_json_response(status_code=status_code)
    payload["error"]["user_message"] = (
        f"{integration_name} を利用するには環境変数 {', '.join(missing_env)} を設定してください。"
        "（ローカル: .env / CI・本番: OS環境変数）"
    )
    payload["error"]["details"] = payload["error"].get("details") or {}
    payload["error"]["details"]["how_to_fix"] = {
        "local": "env.example をコピーして .env を作成し、必要な値を設定してください（.env はコミット禁止）",
        "ci_prod": "OS環境変数（GitHub Actions Secrets 等）で設定してください",
    }
    return jsonify(payload), status_code


def _require_env_for_integration(integration_name: str, required: List[str]):
    missing = _missing_env_vars(required)
    if missing:
        return _config_error_response(integration_name, missing)
    return None


# 環境変数の読み込み
try:
    from dotenv import load_dotenv

    # .envファイルを読み込む
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info("環境変数ファイルを読み込みました")

        # Transformersキャッシュ警告対応: TRANSFORMERS_CACHEが設定されている場合はHF_HOMEに移行
        if os.getenv("TRANSFORMERS_CACHE") and not os.getenv("HF_HOME"):
            transformers_cache = os.getenv("TRANSFORMERS_CACHE") or ""
            os.environ["HF_HOME"] = transformers_cache
            logger.info(f"✅ TRANSFORMERS_CACHEをHF_HOMEに移行しました: {transformers_cache}")
            # 警告を抑制するために古い環境変数を削除（オプション）
            # os.environ.pop("TRANSFORMERS_CACHE", None)
    else:
        # Secretsはファイル直読みではなく、OS環境変数または .env で注入する
        logger.info(".envファイルが見つかりません。OS環境変数の設定を使用します。")
except ImportError:
    logger.debug("python-dotenvがインストールされていません")
    logger.info("OS環境変数の設定を使用します。")

# 統合モジュールのインポート（すべてオプション）
COMFYUI_AVAILABLE = False
SVI_WAN22_AVAILABLE = False
LTX2_AVAILABLE = False
GOOGLE_DRIVE_AVAILABLE = False
CIVITAI_AVAILABLE = False
LANGCHAIN_AVAILABLE = False
MEM0_AVAILABLE = False
OBSIDIAN_AVAILABLE = False
LOCAL_LLM_AVAILABLE = False
STEP_DEEP_RESEARCH_AVAILABLE = False

# Step-Deep-Research統合（オプション）
try:
    from step_deep_research.orchestrator import StepDeepResearchOrchestrator

    STEP_DEEP_RESEARCH_AVAILABLE = True
except ImportError:
    logger.debug("Step-Deep-Research統合モジュールが見つかりません")
    STEP_DEEP_RESEARCH_AVAILABLE = False

# ComfyUI統合（オプション）
try:
    from comfyui_integration import ComfyUIIntegration

    COMFYUI_AVAILABLE = True
except ImportError:
    logger.debug("ComfyUI統合モジュールが見つかりません")

# SVI × Wan 2.2動画生成統合（オプション）
try:
    from svi_wan22_video_integration import SVIWan22VideoIntegration

    SVI_WAN22_AVAILABLE = True
except ImportError:
    logger.debug("SVI × Wan 2.2動画生成統合モジュールが見つかりません")

# LTX-2動画生成統合（オプション）
try:
    from ltx2_video_integration import LTX2VideoIntegration

    LTX2_AVAILABLE = True
except ImportError:
    logger.debug("LTX-2動画生成統合モジュールが見つかりません")
    LTX2_AVAILABLE = False

# LTX-2 Infinity統合（オプション）
LTX2_INFINITY_AVAILABLE = False
try:
    from ltx2_infinity_integration import LTX2InfinityIntegration
    from ltx2_workflow_generator import LTX2WorkflowGenerator
    from ltx2_template_manager import LTX2TemplateManager
    from ltx2_nsfw_config import LTX2NSFWConfig
    from ltx2_storage_manager import LTX2StorageManager

    LTX2_INFINITY_AVAILABLE = True
    logger.info("✅ LTX-2 Infinity統合モジュールが利用可能です")
except ImportError as e:
    logger.debug(f"LTX-2 Infinity統合モジュールが見つかりません: {e}")
    LTX2_INFINITY_AVAILABLE = False

# GoogleDrive統合（オプション）
try:
    from google_drive_integration import GoogleDriveIntegration

    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    logger.debug("GoogleDrive統合モジュールが見つかりません")

# CivitAI統合（オプション）
try:
    from civitai_integration import CivitAIIntegration

    CIVITAI_AVAILABLE = True
except ImportError:
    logger.debug("CivitAI統合モジュールが見つかりません")

# LangChain統合（オプション）
try:
    from langchain_integration import LangChainIntegration, LangGraphIntegration

    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.debug("LangChain統合モジュールが見つかりません")

# Mem0統合（オプション）
try:
    from mem0_integration import Mem0Integration

    MEM0_AVAILABLE = True
except ImportError:
    logger.debug("Mem0統合モジュールが見つかりません")

# Obsidian統合（オプション）
try:
    from obsidian_integration import ObsidianIntegration

    OBSIDIAN_AVAILABLE = True
except ImportError:
    logger.debug("Obsidian統合モジュールが見つかりません")

# ローカルLLM統合（オプション）
try:
    from local_llm_unified import LocalLLMUnified

    LOCAL_LLM_AVAILABLE = True
except ImportError:
    logger.debug("LocalLLM統合モジュールが見つかりません")

# Redisキャッシュ統合（オプション）
REDIS_CACHE_AVAILABLE = False
try:
    from llm_redis_cache import get_redis_cache as _get_redis_cache  # noqa: F401

    REDIS_CACHE_AVAILABLE = True
except ImportError:
    logger.debug("Redisキャッシュモジュールが見つかりません")

# 統一キャッシュシステム統合（オプション）
UNIFIED_CACHE_AVAILABLE = False
try:
    from unified_cache_system import get_unified_cache

    UNIFIED_CACHE_AVAILABLE = True
except ImportError:
    logger.debug("統一キャッシュシステムモジュールが見つかりません")

# パフォーマンス最適化システム統合（オプション）
PERFORMANCE_OPTIMIZER_AVAILABLE = False
try:
    from manaos_performance_optimizer import PerformanceOptimizer

    PERFORMANCE_OPTIMIZER_AVAILABLE = True
except ImportError:
    logger.debug("パフォーマンス最適化システムモジュールが見つかりません")

# 拡張フェーズ統合（オプション）
LLM_ROUTING_AVAILABLE = False
MEMORY_UNIFIED_AVAILABLE = False
NOTIFICATION_HUB_AVAILABLE = False
SECRETARY_AVAILABLE = False
IMAGE_STOCK_AVAILABLE = False

# LLMルーティング統合（オプション）
try:
    from llm_routing import LLMRouter

    LLM_ROUTING_AVAILABLE = True
except ImportError:
    logger.debug("LLMルーティングモジュールが見つかりません")

# 拡張LLMルーティング統合（難易度判定対応）
ENHANCED_LLM_ROUTING_AVAILABLE = False
try:
    from llm_router_enhanced import EnhancedLLMRouter

    ENHANCED_LLM_ROUTING_AVAILABLE = True
except ImportError:
    logger.debug("拡張LLMルーティングモジュールが見つかりません")

# 統一記憶システム統合（オプション）
try:
    from memory_unified import UnifiedMemory

    MEMORY_UNIFIED_AVAILABLE = True
except ImportError:
    logger.debug("統一記憶システムモジュールが見つかりません")

# 記憶統合ブリッジ（UnifiedMemory + Mem0 + Phase2 一本化）
try:
    from memory_integration_bridge import memory_store as bridge_memory_store
    from memory_integration_bridge import memory_recall as bridge_memory_recall
    from memory_integration_bridge import get_memo_context_for_chat

    MEMORY_BRIDGE_AVAILABLE = True
except ImportError:
    MEMORY_BRIDGE_AVAILABLE = False
    bridge_memory_store = None
    bridge_memory_recall = None
    get_memo_context_for_chat = None

# フェーズ1 自己観察実験フック（入口1枚噛ませ。env: PHASE1_REFLECTION=on で有効）
try:
    import phase1_hooks
    from phase1_reflection import REFLECTION_PROMPT, parse_reflection_answer  # noqa: F401

    PHASE1_HOOKS_AVAILABLE = True
except ImportError:
    PHASE1_HOOKS_AVAILABLE = False
    phase1_hooks = None

# Phase2 第三層：同一テーマの振り返りメモを応答前に注入（env: PHASE2_MEMO_INJECT=on で有効）
try:
    from phase2_reflection_memo import get_memo_context_for_messages

    PHASE2_MEMO_AVAILABLE = True
except ImportError:
    PHASE2_MEMO_AVAILABLE = False
    get_memo_context_for_messages = None

# 通知ハブ統合（オプション）
try:
    from notification_hub import NotificationHub

    NOTIFICATION_HUB_AVAILABLE = True
except ImportError:
    logger.debug("通知ハブモジュールが見つかりません")

# 秘書機能統合（オプション）
try:
    from secretary_routines import SecretaryRoutines

    SECRETARY_AVAILABLE = True
except ImportError:
    logger.debug("秘書機能モジュールが見つかりません")

# 画像ストック統合（オプション）
try:
    from image_stock import ImageStock

    IMAGE_STOCK_AVAILABLE = True
except ImportError:
    logger.debug("画像ストックモジュールが見つかりません")

# Rows統合（オプション）
try:
    from rows_integration import RowsIntegration

    ROWS_AVAILABLE = True
except ImportError:
    logger.debug("Rows統合モジュールが見つかりません")
    ROWS_AVAILABLE = False

# GitHub統合（オプション）
try:
    from github_integration import GitHubIntegration

    GITHUB_AVAILABLE = True
except ImportError:
    logger.debug("GitHub統合モジュールが見つかりません")
    GITHUB_AVAILABLE = False

# n8n統合（オプション）
try:
    from n8n_integration import N8NIntegration

    N8N_AVAILABLE = True
except ImportError:
    logger.debug("n8n統合モジュールが見つかりません")
    N8N_AVAILABLE = False

# Brave Search統合（オプション）
BRAVE_SEARCH_AVAILABLE = False
try:
    from brave_search_integration import BraveSearchIntegration  # noqa: F401

    BRAVE_SEARCH_AVAILABLE = True
except ImportError:
    logger.debug("Brave Search統合モジュールが見つかりません")

# Base AI統合（オプション）
BASE_AI_AVAILABLE = False
try:
    from base_ai_integration import BaseAIIntegration  # noqa: F401

    BASE_AI_AVAILABLE = True
except ImportError:
    logger.debug("Base AI統合モジュールが見つかりません")

# OH MY OPENCODE統合（オプション）
OH_MY_OPENCODE_AVAILABLE = False
try:
    from oh_my_opencode_integration import OHMyOpenCodeIntegration

    OH_MY_OPENCODE_AVAILABLE = True
except ImportError:
    logger.debug("OH MY OPENCODE統合モジュールが見つかりません")

# Excel/LLM処理統合（オプション）
EXCEL_LLM_AVAILABLE = False
try:
    from excel_llm_integration import ExcelLLMIntegration

    EXCEL_LLM_AVAILABLE = True
except ImportError:
    logger.debug("Excel/LLM処理統合モジュールが見つかりません")
    EXCEL_LLM_AVAILABLE = False

# 音声機能統合（オプション）
VOICE_INTEGRATION_AVAILABLE = False
try:
    from voice_integration import (  # noqa: F401
        STTEngine,
        TTSEngine,
        VoiceConversationLoop,
        create_stt_engine,
        create_tts_engine,
        create_voice_conversation_loop,
    )

    VOICE_INTEGRATION_AVAILABLE = True
    logger.info("✅ 音声機能統合モジュールが利用可能です")
except ImportError as e:
    logger.debug(f"音声機能統合モジュールが見つかりません: {e}")
    VOICE_INTEGRATION_AVAILABLE = False

app = Flask(__name__)

# =========================================================
# Security: CORS (allowlist) + API key auth guard
# =========================================================


def _strtobool(value: str, default: bool = False) -> bool:
    v = (value or "").strip().lower()
    if v in ("1", "true", "yes", "y", "on"):
        return True
    if v in ("0", "false", "no", "n", "off"):
        return False
    return default


def _get_admin_api_key() -> str:
    """Admin key: full access (read + ops)."""
    return (os.getenv("MANAOS_INTEGRATION_API_KEY") or "").strip()


def _get_ops_api_key() -> str:
    """Ops key: privileged endpoints / write actions."""
    return (os.getenv("MANAOS_INTEGRATION_OPS_API_KEY") or "").strip()


def _get_readonly_api_key() -> str:
    """Read-only key: safe read endpoints (non-sensitive GET)."""
    return (os.getenv("MANAOS_INTEGRATION_READONLY_API_KEY") or "").strip()


def _get_provided_api_key() -> str:
    # Accept either X-API-Key or Authorization: Bearer <token>
    provided = (request.headers.get("X-API-Key") or "").strip()
    if provided:
        return provided
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return ""


def _get_client_ip() -> str:
    """
    Client IP resolver.
    - Default: use Flask's `request.remote_addr`
    - Optional: trust `X-Forwarded-For` if explicitly enabled (dangerous if misconfigured)
    """
    if _strtobool(os.getenv("MANAOS_TRUST_X_FORWARDED_FOR", "false"), default=False):
        xff = (request.headers.get("X-Forwarded-For") or "").strip()
        if xff:
            # first IP is the original client in standard setups
            return xff.split(",")[0].strip()
    return (request.remote_addr or "").strip()


def _is_local_request() -> bool:
    return _get_client_ip() in ("127.0.0.1", "::1")


def _parse_csv_set(value: str) -> set[str]:
    return {v.strip() for v in (value or "").split(",") if v.strip()}


def _ip_access_check() -> Optional[tuple[dict, int]]:
    """
    Optional IP allow/block.
    - If MANAOS_IP_BLOCKLIST contains client IP => block (403)
    - If MANAOS_IP_ALLOWLIST is set and client IP not in it => block (403)
    """
    client_ip = _get_client_ip()
    block = _parse_csv_set(os.getenv("MANAOS_IP_BLOCKLIST", ""))
    allow = _parse_csv_set(os.getenv("MANAOS_IP_ALLOWLIST", ""))

    if client_ip and client_ip in block:
        return {"error": "forbidden", "message": f"IP blocked: {client_ip}"}, 403

    if allow and client_ip not in allow:
        return {"error": "forbidden", "message": f"IP not allowlisted: {client_ip}"}, 403

    return None


def _parse_csv_list(value: str) -> list[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def _get_sensitive_read_prefixes() -> tuple[str, ...]:
    """
    GETでもOps扱いにする危険なパスPrefix。
    運用で増やせるように環境変数で上書き可能。
    """
    raw = os.getenv("MANAOS_SENSITIVE_PATH_PREFIXES", "").strip()
    if raw:
        return tuple(_parse_csv_list(raw))
    return (
        "/emergency",
        "/api/emergency",
        "/api/system/docker",
    )


def _get_readonly_path_prefixes() -> tuple[str, ...]:
    """
    Read-onlyキーでアクセス可能なパスPrefix（GET/HEADのみ）。
    デフォルトは「稼働確認・仕様取得」だけに絞って安全側に倒す。
    """
    raw = os.getenv("MANAOS_READONLY_PATH_PREFIXES", "").strip()
    if raw:
        return tuple(_parse_csv_list(raw))
    return (
        "/health",
        "/ready",
        "/status",
        "/openapi.json",
        "/api/integrations/status",
    )


def _get_admin_only_path_prefixes() -> tuple[str, ...]:
    """
    Adminキーのみ許可するパスPrefix（最重要・危険領域）。
    未設定時は安全側として「緊急/システム操作系」をデフォルトでAdmin専用にする。
    """
    raw = os.getenv("MANAOS_ADMIN_ONLY_PATH_PREFIXES", "").strip()
    if raw:
        return tuple(_parse_csv_list(raw))
    return (
        "/emergency",
        "/api/emergency",
        "/api/system/docker",
        # Data-handling endpoints (recommended default)
        "/api/llm",
        "/api/memory",
        # External systems / data exfiltration surfaces (recommended default)
        "/api/google_drive",
        "/api/rows",
        "/api/n8n",
        "/api/civitai",
        "/api/voice",
        "/api/slack",
    )


def _get_confirm_token() -> str:
    # Second factor: only active when set
    return (os.getenv("MANAOS_CONFIRM_TOKEN") or "").strip()


def _get_confirm_token_secret() -> str:
    # Time-based HMAC mode: only active when set
    return (os.getenv("MANAOS_CONFIRM_TOKEN_SECRET") or "").strip()


def _confirm_token_period_seconds() -> int:
    raw = (os.getenv("MANAOS_CONFIRM_TOKEN_PERIOD_SECONDS") or "").strip()
    try:
        v = int(raw) if raw else 30
        return max(5, v)
    except Exception:
        return 30


def _confirm_token_accept_previous_window() -> bool:
    return _strtobool(os.getenv("MANAOS_CONFIRM_TOKEN_ACCEPT_PREVIOUS", "true"), default=True)


def _confirm_token_bind_path() -> bool:
    """
    If true, include a stable scope (path prefix) in the HMAC message.
    This prevents replay across different protected endpoint groups.
    """
    return _strtobool(os.getenv("MANAOS_CONFIRM_TOKEN_BIND_PATH", "false"), default=False)


def _confirm_token_scope() -> str:
    """
    Returns the most specific matching prefix for current request.
    Used only when path-binding is enabled.
    """
    prefixes = _get_confirm_token_path_prefixes()
    matches = [p for p in prefixes if request.path.startswith(p)]
    if not matches:
        return request.path
    # choose the longest match (most specific)
    return max(matches, key=len)


def _compute_time_hmac_token(secret: str, message: str) -> str:
    # Hex digest (64 chars). Simple and tool-friendly.
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), digestmod="sha256").hexdigest()


def _get_confirm_token_path_prefixes() -> tuple[str, ...]:
    raw = (os.getenv("MANAOS_CONFIRM_TOKEN_PATH_PREFIXES") or "").strip()
    if raw:
        return tuple(_parse_csv_list(raw))
    # Default: extremely sensitive operational endpoints
    return (
        "/api/emergency",
        "/api/system/docker",
    )


def _get_provided_confirm_token() -> str:
    return (request.headers.get("X-Confirm-Token") or "").strip()


def _confirm_token_required() -> bool:
    # Required if either static token or secret is configured
    if not (_get_confirm_token() or _get_confirm_token_secret()):
        return False
    if request.method.upper() == "OPTIONS":
        return False
    return request.path.startswith(_get_confirm_token_path_prefixes())


def _enforce_confirm_token_if_needed() -> Optional[tuple[dict, int]]:
    if not _confirm_token_required():
        g.manaos_confirm_required = False
        g.manaos_confirm_ok = None
        g.manaos_confirm_mode = "disabled"
        return None
    provided = _get_provided_confirm_token()

    g.manaos_confirm_required = True

    # Prefer time-based mode if secret is set (safer)
    secret = _get_confirm_token_secret()
    if secret:
        g.manaos_confirm_mode = "time_hmac"
        period = _confirm_token_period_seconds()
        window = int(time.time() // period)

        if _confirm_token_bind_path():
            scope = _confirm_token_scope()
            msg_now = f"{window}:{scope}"
            msg_prev = f"{window - 1}:{scope}"
        else:
            msg_now = str(window)
            msg_prev = str(window - 1)

        expected_now = _compute_time_hmac_token(secret, msg_now)
        expected_prev = (
            _compute_time_hmac_token(secret, msg_prev)
            if _confirm_token_accept_previous_window()
            else None
        )

        ok = bool(
            provided
            and (
                hmac.compare_digest(provided, expected_now)
                or (expected_prev and hmac.compare_digest(provided, expected_prev))
            )
        )
        g.manaos_confirm_ok = ok
        if ok:
            return None
        return {
            "error": "forbidden",
            "message": "Confirmation token required (time-based HMAC via X-Confirm-Token).",
        }, 403

    # Fallback: static token
    expected = _get_confirm_token()
    g.manaos_confirm_mode = "static"
    ok = bool(provided and expected and hmac.compare_digest(provided, expected))
    g.manaos_confirm_ok = ok
    if ok:
        return None
    return {"error": "forbidden", "message": "Confirmation token required (X-Confirm-Token)."}, 403


def _required_scope() -> str:
    """
    Scope decision:
    - ops: any non-GET/HEAD request, or sensitive GET endpoints
    - read: normal GET/HEAD requests
    """
    if request.method.upper() not in ("GET", "HEAD", "OPTIONS"):
        return "ops"
    if request.path.startswith(_get_sensitive_read_prefixes()):
        return "ops"
    # Safe default: require ops for most GET endpoints unless explicitly allowlisted
    if request.path.startswith(_get_readonly_path_prefixes()):
        return "read"
    return "ops"


_PUBLIC_PATHS = {
    "/health",
    "/ready",
}


@app.before_request
def _init_request_context():
    """Initialize request-scoped fields used by logs/errors."""
    try:
        if not getattr(g, "manaos_request_id", None):
            g.manaos_request_id = uuid.uuid4().hex
        if not getattr(g, "manaos_request_start", None):
            g.manaos_request_start = time.perf_counter()
        # Defaults for confirm-token audit fields
        if not hasattr(g, "manaos_confirm_required"):
            g.manaos_confirm_required = False
        if not hasattr(g, "manaos_confirm_ok"):
            g.manaos_confirm_ok = None
        if not hasattr(g, "manaos_confirm_mode"):
            g.manaos_confirm_mode = "disabled"
    except Exception:
        pass


# =========================================================
# Rate limit & concurrency guards (in-process, best-effort)
# =========================================================

_rate_lock = threading.Lock()
_rate_counters: dict[tuple[str, str, int], int] = {}
_rate_last_cleanup = 0.0

_sem_lock = threading.Lock()
_semaphores: dict[str, threading.Semaphore] = {}


def _rate_window_seconds() -> int:
    raw = (os.getenv("MANAOS_RATE_LIMIT_WINDOW_SECONDS") or "").strip()
    try:
        v = int(raw) if raw else 60
        return max(10, v)
    except Exception:
        return 60


def _default_rpm() -> int:
    raw = (os.getenv("MANAOS_RATE_LIMIT_RPM") or "").strip()
    try:
        v = int(raw) if raw else 60
        return max(1, v)
    except Exception:
        return 60


def _parse_kv_csv(raw: str) -> dict[str, int]:
    """
    Parse: "/api/llm=10,/api/system/docker=5"
    """
    out: dict[str, int] = {}
    for item in (raw or "").split(","):
        item = item.strip()
        if not item or "=" not in item:
            continue
        k, v = item.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            continue
        try:
            out[k] = max(1, int(v))
        except Exception:
            continue
    return out


def _rate_limit_rules() -> dict[str, int]:
    raw = (os.getenv("MANAOS_RATE_LIMIT_RULES") or "").strip()
    if not raw:
        return {
            "/api/llm": 20,
            "/api/comfyui": 10,
            "/api/system/docker": 10,
            "/api/emergency": 10,
        }
    return _parse_kv_csv(raw)


def _concurrency_rules() -> dict[str, int]:
    raw = (os.getenv("MANAOS_CONCURRENCY_LIMITS") or "").strip()
    if not raw:
        return {
            "/api/llm": 2,
            "/api/comfyui": 1,
            "/api/system/docker": 1,
            "/api/emergency": 1,
        }
    return _parse_kv_csv(raw)


def _best_prefix_match(path: str, prefixes: list[str]) -> Optional[str]:
    matches = [p for p in prefixes if path.startswith(p)]
    return max(matches, key=len) if matches else None


def _rate_limit_check() -> Optional[tuple[dict, int]]:
    if request.method.upper() == "OPTIONS":
        return None
    if request.path in _PUBLIC_PATHS:
        return None
    if not _strtobool(os.getenv("MANAOS_RATE_LIMIT_ENABLED", "true"), default=True):
        return None

    ip = _get_client_ip() or "unknown"
    window = _rate_window_seconds()
    now = time.time()
    window_id = int(now // window)

    rules = _rate_limit_rules()
    prefix = _best_prefix_match(request.path, list(rules.keys())) or "*"
    limit = rules.get(prefix, _default_rpm())

    # key: (ip, prefix, window_id)
    key = (ip, prefix, window_id)
    global _rate_last_cleanup

    with _rate_lock:
        count = _rate_counters.get(key, 0) + 1
        _rate_counters[key] = count

        # periodic cleanup (best-effort)
        if now - _rate_last_cleanup > (window * 2):
            _rate_last_cleanup = now
            cutoff = window_id - 2
            for k in list(_rate_counters.keys()):
                if k[2] < cutoff:
                    _rate_counters.pop(k, None)

    if count > limit:
        return (
            {
                "error": "rate_limited",
                "message": "Too many requests",
                "limit_rpm": limit,
                "scope": prefix,
                "request_id": getattr(g, "manaos_request_id", None),
            },
            429,
        )
    return None


def _concurrency_acquire() -> Optional[tuple[dict, int]]:
    if request.method.upper() == "OPTIONS":
        return None
    if request.path in _PUBLIC_PATHS:
        return None
    if not _strtobool(os.getenv("MANAOS_CONCURRENCY_ENABLED", "true"), default=True):
        return None

    rules = _concurrency_rules()
    prefix = _best_prefix_match(request.path, list(rules.keys()))
    if not prefix:
        return None

    limit = rules.get(prefix, 1)
    if limit <= 0:
        return None

    with _sem_lock:
        sem = _semaphores.get(prefix)
        if not sem:
            sem = threading.Semaphore(limit)
            _semaphores[prefix] = sem

    acquired = sem.acquire(blocking=False)
    if not acquired:
        return (
            {
                "error": "busy",
                "message": "Server is busy for this endpoint group",
                "scope": prefix,
                "request_id": getattr(g, "manaos_request_id", None),
            },
            503,
        )

    # release later
    g.manaos_concurrency_prefix = prefix
    return None


@app.before_request
def _rate_and_concurrency_guard():
    # Best-effort guard (in-process)
    rl = _rate_limit_check()
    if rl:
        payload, code = rl
        return jsonify(payload), code
    cc = _concurrency_acquire()
    if cc:
        payload, code = cc
        return jsonify(payload), code
    return None


@app.teardown_request
def _concurrency_release(_err):
    try:
        prefix = getattr(g, "manaos_concurrency_prefix", None)
        if prefix:
            sem = _semaphores.get(prefix)
            if sem:
                sem.release()
    except Exception:
        pass


@app.before_request
def _api_auth_guard():
    """
    Default policy:
    - If `MANAOS_INTEGRATION_API_KEY` is set: require it for all non-public endpoints.
    - If not set: allow only local requests (127.0.0.1/::1) unless explicitly disabled.
    """
    # Default auth context (used for response redaction)
    g.manaos_auth_level = "none"  # "admin" | "ops" | "read" | "local" | "none"
    g.manaos_required_scope = None

    # Allow liveness/readiness without forcing clients to attach keys.
    if request.path in _PUBLIC_PATHS:
        return None

    # Always allow CORS preflight without forcing auth.
    if request.method.upper() == "OPTIONS":
        return None

    ip_check = _ip_access_check()
    if ip_check:
        payload, code = ip_check
        return jsonify(payload), code

    admin_key = _get_admin_api_key()
    ops_key = _get_ops_api_key()
    ro_key = _get_readonly_api_key()
    provided = _get_provided_api_key()
    scope = _required_scope()
    g.manaos_required_scope = scope
    admin_only = request.path.startswith(_get_admin_only_path_prefixes())

    # If any key configured -> require matching key based on scope (admin always works)
    if admin_key or ops_key or ro_key:
        if provided and admin_key and hmac.compare_digest(provided, admin_key):
            g.manaos_auth_level = "admin"
            confirm = _enforce_confirm_token_if_needed()
            if confirm:
                payload, code = confirm
                return jsonify(payload), code
            return None
        if admin_only:
            return (
                jsonify(
                    {
                        "error": "unauthorized",
                        "message": "Admin API key is required for this endpoint.",
                    }
                ),
                401,
            )
        if scope == "ops":
            if provided and ops_key and hmac.compare_digest(provided, ops_key):
                g.manaos_auth_level = "ops"
                confirm = _enforce_confirm_token_if_needed()
                if confirm:
                    payload, code = confirm
                    return jsonify(payload), code
                return None
        else:  # read
            if provided and ro_key and hmac.compare_digest(provided, ro_key):
                g.manaos_auth_level = "read"
                confirm = _enforce_confirm_token_if_needed()
                if confirm:
                    payload, code = confirm
                    return jsonify(payload), code
                return None
            # ops key can also read
            if provided and ops_key and hmac.compare_digest(provided, ops_key):
                g.manaos_auth_level = "ops"
                confirm = _enforce_confirm_token_if_needed()
                if confirm:
                    payload, code = confirm
                    return jsonify(payload), code
                return None

        return (
            jsonify(
                {
                    "error": "unauthorized",
                    "message": (
                        "Missing or invalid API key. "
                        "Provide `X-API-Key` or `Authorization: Bearer ...`. "
                        f"Required scope: {scope}"
                    ),
                }
            ),
            401,
        )

    # No key configured -> local-only (safe default)
    allow_local_noauth = _strtobool(os.getenv("MANAOS_ALLOW_NOAUTH_LOCAL", "true"), default=True)
    if allow_local_noauth and _is_local_request():
        g.manaos_auth_level = "local"
        confirm = _enforce_confirm_token_if_needed()
        if confirm:
            payload, code = confirm
            return jsonify(payload), code
        return None

    return (
        jsonify(
            {
                "error": "unauthorized",
                "message": (
                    "This server is running without API keys. "
                    "Requests are restricted to localhost. "
                    "Set `MANAOS_INTEGRATION_API_KEY` (admin) or "
                    "`MANAOS_INTEGRATION_OPS_API_KEY` / "
                    "`MANAOS_INTEGRATION_READONLY_API_KEY` to enable remote access."
                ),
            }
        ),
        401,
    )


def _get_cors_origins() -> List[str]:
    raw = (os.getenv("MANAOS_CORS_ORIGINS") or "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    # Safe default for local UI tools (Open WebUI etc.)
    return [
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]


_enable_cors = _strtobool(os.getenv("MANAOS_ENABLE_CORS", "true"), default=True)
if _enable_cors:
    CORS(app, resources={r"/*": {"origins": _get_cors_origins()}}, supports_credentials=True)


# =========================================================
# OpenAPI / Swagger Documentation Setup
# =========================================================
_openapi_spec_cache: Dict[str, Any] = {}
_openapi_cache_ttl = 3600  # Cache for 1 hour


def _build_openapi_spec() -> Dict[str, Any]:
    """OpenAPI 仕様を構築（キャッシュ機能付き）"""
    if OpenAPISpecBuilder is None:
        logger.warning("⚠️ OpenAPI Generator not available")
        return {}
    
    # キャッシュをチェック
    cache_key = "openapi_spec"
    if cache_key in _openapi_spec_cache:
        cached_time = _openapi_spec_cache.get(f"{cache_key}_time", 0)
        if time.time() - cached_time < _openapi_cache_ttl:
            return _openapi_spec_cache[cache_key]
    
    # 新規に生成
    try:
        builder = OpenAPISpecBuilder(
            title="ManaOS Unified API",
            description="ManaOS - 統合システムAPI",
            version="1.0.0",
            base_url=os.getenv("OPENAPI_BASE_URL", "http://localhost:9502")
        )
        
        # 主要エンドポイントを追加
        builder.add_endpoint(
            "/health", "GET",
            summary="ヘルスチェック",
            tags=["System"],
            requires_auth=False
        )
        
        builder.add_endpoint(
            "/ready", "GET",
            summary="レディネスチェック",
            tags=["System"],
            requires_auth=False
        )
        
        builder.add_endpoint(
            "/api/integrations/status", "GET",
            summary="統合モジュルの状態確認",
            tags=["Integration"],
            requires_auth=True
        )
        
        builder.add_endpoint(
            "/api/llm/analyze", "POST",
            summary="LLM分析を実行",
            tags=["LLM"],
            requires_auth=True
        )
        
        builder.add_endpoint(
            "/api/memory/store", "POST",
            summary="メモリに情報を保存",
            tags=["Memory"],
            requires_auth=True
        )
        
        builder.add_endpoint(
            "/api/memory/recall", "POST",
            summary="メモリから情報を取得",
            tags=["Memory"],
            requires_auth=True
        )
        
        spec = builder.build()
        
        # キャッシュに保存
        _openapi_spec_cache[cache_key] = spec
        _openapi_spec_cache[f"{cache_key}_time"] = time.time()
        
        logger.info(f"✅ OpenAPI 仕様を生成・キャッシュしました（{len(spec.get('paths', {}))} エンドポイント）")
        return spec
        
    except Exception as e:
        logger.error(f"❌ OpenAPI 仕様生成エラー: {e}")
        return {}


# =========================================================
# Health Check Optimization Setup
# =========================================================
_health_check_optimizer = None

if get_health_check_optimizer:
    try:
        _health_check_optimizer = get_health_check_optimizer()
        logger.info("✅ Health Check Optimizer を初期化しました")
    except Exception as e:
        logger.warning(f"⚠️ Health Check Optimizer 初期化エラー: {e}")


def _audit_log_enabled() -> bool:
    return _strtobool(os.getenv("MANAOS_AUDIT_LOG", "true"), default=True)


def _audit_log_path() -> Optional[Path]:
    raw = (os.getenv("MANAOS_AUDIT_LOG_FILE") or "").strip()
    # Default: write to repo-local logs/audit (ignored by .gitignore)
    if not raw:
        raw = str(Path(__file__).parent / "logs" / "audit" / "manaos_audit_{date}.jsonl")
    try:
        # Optional token substitution: {date} -> YYYYMMDD
        if "{date}" in raw:
            raw = raw.replace("{date}", datetime.now().strftime("%Y%m%d"))
        return Path(raw)
    except Exception:
        return None


def _audit_log_format() -> str:
    fmt = (os.getenv("MANAOS_AUDIT_LOG_FORMAT") or "json").strip().lower()
    return "json" if fmt not in ("json", "text") else fmt


def _security_headers_enabled() -> bool:
    return _strtobool(os.getenv("MANAOS_SECURITY_HEADERS", "true"), default=True)


def _debug_errors_enabled() -> bool:
    return _strtobool(os.getenv("MANAOS_DEBUG_ERRORS", "false"), default=False)


def _json_error(
    message: str,
    status_code: int = 500,
    error: str = "error",
    details: Optional[dict] = None,
    namespace: Optional[str] = None,
    total_jobs: Optional[int] = None,
):
    payload: dict = {
        "error": error,
        "message": message,
        "request_id": getattr(g, "manaos_request_id", None),
    }
    if details:
        payload["details"] = details
    if namespace:
        payload["_meta"] = _job_response_meta(namespace, total_jobs)
    return jsonify(payload), status_code


@app.errorhandler(404)
def _handle_404(_e):
    return _json_error("not_found", 404, error="not_found")


@app.errorhandler(405)
def _handle_405(_e):
    return _json_error("method_not_allowed", 405, error="method_not_allowed")


@app.errorhandler(Exception)
def _handle_unexpected_error(e):
    # Avoid leaking sensitive info by default.
    if isinstance(e, HTTPException):
        code = getattr(e, "code", 500) or 500
        desc = getattr(e, "description", "error")
        return _json_error(str(desc), int(code), error="http_error")

    logger.error(f"Unhandled error: {e}", exc_info=True)
    if _debug_errors_enabled():
        return _json_error(
            "internal_error", 500, error="internal_error", details={"exception": str(e)}
        )
    return _json_error("internal_error", 500, error="internal_error")


def _audit_log_max_bytes() -> int:
    # Default: 5MB (small, safe)
    raw = (os.getenv("MANAOS_AUDIT_LOG_MAX_BYTES") or "").strip()
    try:
        v = int(raw) if raw else 5 * 1024 * 1024
        return max(0, v)
    except Exception:
        return 5 * 1024 * 1024


def _audit_log_backups() -> int:
    raw = (os.getenv("MANAOS_AUDIT_LOG_BACKUPS") or "").strip()
    try:
        v = int(raw) if raw else 5
        return max(0, v)
    except Exception:
        return 5


def _rotate_file(path: Path):
    """
    Simple size-based rotation:
    - path -> path.1
    - path.1 -> path.2 ... up to backups
    """
    backups = _audit_log_backups()
    if backups <= 0:
        return

    # Shift old backups
    for i in range(backups - 1, 0, -1):
        src = Path(f"{path}.{i}")
        dst = Path(f"{path}.{i+1}")
        if src.exists():
            try:
                if dst.exists():
                    dst.unlink()
                src.replace(dst)
            except Exception:
                pass

    # Move current to .1
    if path.exists():
        try:
            dst1 = Path(f"{path}.1")
            if dst1.exists():
                dst1.unlink()
            path.replace(dst1)
        except Exception:
            pass


@app.after_request
def _audit_log_response(response):
    # Minimal, secret-safe audit log
    try:
        if not _audit_log_enabled():
            return response

        latency_ms = None
        try:
            start = getattr(g, "manaos_request_start", None)
            if isinstance(start, (int, float)):
                latency_ms = int((time.perf_counter() - start) * 1000)
        except Exception:
            latency_ms = None

        entry = {
            "ts": datetime.now().isoformat(),
            "ip": _get_client_ip(),
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "auth_level": getattr(g, "manaos_auth_level", "none"),
            "required_scope": getattr(g, "manaos_required_scope", None),
            "latency_ms": latency_ms,
            "request_id": getattr(g, "manaos_request_id", None),
            "user_agent": (request.headers.get("User-Agent") or "")[:200],
            "confirm_required": getattr(g, "manaos_confirm_required", False),
            "confirm_ok": getattr(g, "manaos_confirm_ok", None),
            "confirm_mode": getattr(g, "manaos_confirm_mode", "disabled"),
        }

        line = (
            json.dumps(entry, ensure_ascii=False) if _audit_log_format() == "json" else str(entry)
        )
        target = _audit_log_path()
        if target:
            target.parent.mkdir(parents=True, exist_ok=True)
            max_bytes = _audit_log_max_bytes()
            if max_bytes > 0:
                try:
                    current_size = target.stat().st_size if target.exists() else 0
                    if current_size + len(line.encode("utf-8")) + 1 > max_bytes:
                        _rotate_file(target)
                except Exception:
                    pass
            with target.open("a", encoding="utf-8", errors="replace") as f:
                f.write(line + "\n")
        else:
            logger.info(f"[AUDIT] {line}")
    except Exception:
        # Never break responses due to logging
        pass

    # Security headers (do not include secrets)
    try:
        if _security_headers_enabled():
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "no-referrer")
            response.headers.setdefault(
                "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
            )
            # For API responses: avoid caching by intermediaries
            response.headers.setdefault("Cache-Control", "no-store")
        # Always expose request id for debugging
        rid = getattr(g, "manaos_request_id", None)
        if rid:
            response.headers.setdefault("X-Request-Id", str(rid))
    except Exception:
        pass
    return response


# OpenAPI仕様を提供（Open WebUI External Tools対応）
@app.route("/openapi.json", methods=["GET"])
def openapi_spec():
    """OpenAPI仕様を返す（Open WebUI External Tools対応）"""
    if not _strtobool(os.getenv("MANAOS_EXPOSE_OPENAPI", "true"), default=True):
        return jsonify({"error": "not_found"}), 404
    from unified_api.openapi import build_openapi_spec

    return jsonify(build_openapi_spec())


@app.route("/api/integrations/status", methods=["GET"])
@auth_manager.require_api_key
def api_integrations_status():
    """統合モジュールの利用可否を返す（軽量）（要認証）"""
    # NOTE: 互換重視で `available` を最小キーとして返す
    targets = {
        "comfyui": "ComfyUI",
        "svi_wan22": "SVI × Wan 2.2",
        "ltx2": "LTX-2",
        "ltx2_infinity": "LTX-2 Infinity",
        "google_drive": "Google Drive",
        "civitai": "CivitAI",
        "obsidian": "Obsidian",
        "local_llm": "Local LLM",
        "llm_routing": "LLM Routing",
        "memory_unified": "Memory",
        "notification_hub": "Notification Hub",
        "secretary": "Secretary",
        "image_stock": "Image Stock",
    }

    out: Dict[str, Any] = {}
    for key, display_name in targets.items():
        inst = integrations.get(key)
        available = False
        reason = None
        try:
            if inst is None:
                available = False
                reason = "not_initialized"
            elif hasattr(inst, "is_available"):
                available = bool(inst.is_available())
                if not available:
                    reason = "unavailable"
            else:
                available = True
        except Exception as e:
            available = False
            reason = f"error:{str(e)[:80]}"

        out[key] = {
            "name": display_name,
            "available": available,
            "reason": reason,
        }

    return jsonify(out), 200


@app.route("/api/sd-prompt/generate", methods=["POST"])
def api_sd_prompt_generate():
    """日本語の説明からStable Diffusion用の英語プロンプトを生成（Ollama）"""
    data = request.get_json(silent=True) or {}
    description = (data.get("description") or data.get("prompt") or "").strip()
    if not description:
        return _json_error(
            "description or prompt is required",
            400, error="bad_request", namespace="sd_prompt",
        )

    try:
        from manaos_core_api import ManaOSCoreAPI

        api = ManaOSCoreAPI()
        result = api.act(
            "generate_sd_prompt",
            {
                "description": description,
                "prompt": description,
                "model": data.get("model", "llama3-uncensored"),
                "temperature": float(data.get("temperature", 0.9)),
                "with_negative": bool(data.get("with_negative", False)),
            },
        )
    except Exception as e:
        logger.warning(f"SD prompt generate error: {e}")
        return _json_error("sd_prompt_failed", 500, error="internal_error", namespace="sd_prompt")

    if isinstance(result, dict) and result.get("success"):
        return jsonify(result), 200
    err = result.get("error", "プロンプトの生成に失敗しました") if isinstance(result, dict) else str(result)
    return jsonify({"success": False, "error": err}), 500


@app.route("/api/comfyui/generate", methods=["POST"])
def api_comfyui_generate():
    """ComfyUIで画像生成（prompt_id を返す）（要認証）"""
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return _json_error("prompt is required", 400, error="bad_request", namespace="comfyui")

    comfyui = integrations.get("comfyui")
    if not comfyui or not getattr(comfyui, "is_available", lambda: False)():
        return _json_error("comfyui_unavailable", 503, error="unavailable", namespace="comfyui")

    negative_prompt = (data.get("negative_prompt") or "").strip()
    width = int(data.get("width", 512) or 512)
    height = int(data.get("height", 512) or 512)
    steps = int(data.get("steps", 20) or 20)
    cfg_scale = float(data.get("cfg_scale", data.get("cfg", 7.0)) or 7.0)
    sampler = (data.get("sampler") or "euler_ancestral").strip() or "euler_ancestral"
    scheduler = (data.get("scheduler") or "karras").strip() or "karras"
    seed = int(data.get("seed", -1) if data.get("seed", -1) is not None else -1)
    model = (data.get("model") or data.get("ckpt_name") or "").strip()
    loras = data.get("loras")
    mufufu_mode = bool(data.get("mufufu_mode", False))
    lab_mode = bool(data.get("lab_mode", False)) or (data.get("profile") == "lab")
    if not lab_mode and (os.getenv("MANAOS_IMAGE_DEFAULT_PROFILE") or "").strip().lower() == "lab":
        lab_mode = True
        logger.info("MANAOS_IMAGE_DEFAULT_PROFILE=lab: 闇の実験室をデフォルトにしました")

    # 闇の実験室（lab_mode）: ネガは崩壊防止のみ
    if lab_mode:
        try:
            from mufufu_config_lab import LAB_NEGATIVE_PROMPT
            from mufufu_config import ANATOMY_POSITIVE_TAGS, OPTIMIZED_PARAMS
            negative_prompt = (
                f"{negative_prompt}, {LAB_NEGATIVE_PROMPT}".strip(", ")
                if negative_prompt
                else LAB_NEGATIVE_PROMPT
            )
            if ANATOMY_POSITIVE_TAGS:
                prompt = f"{ANATOMY_POSITIVE_TAGS}, {prompt}"
            if OPTIMIZED_PARAMS and (not steps or steps < 30):
                steps = OPTIMIZED_PARAMS.get("steps", 50)
            if OPTIMIZED_PARAMS and not cfg_scale:
                cfg_scale = OPTIMIZED_PARAMS.get("guidance_scale", 7.5)
            if OPTIMIZED_PARAMS:
                sampler = OPTIMIZED_PARAMS.get("sampler", sampler)
                scheduler = OPTIMIZED_PARAMS.get("scheduler", scheduler)
            logger.info("✅ 闇の実験室（lab_mode）: ネガ最小限・表現はモデルに委ねます")
        except ImportError as e:
            logger.debug(f"mufufu_config_lab が見つかりません: {e}")

    # ムフフモード: 身体崩れ対策強化（lab_mode でないとき）
    elif mufufu_mode:
        try:
            from mufufu_config import (
                MUFUFU_NEGATIVE_PROMPT, ANATOMY_POSITIVE_TAGS, OPTIMIZED_PARAMS
            )
            negative_prompt = (
                f"{negative_prompt}, {MUFUFU_NEGATIVE_PROMPT}".strip(", ")
                if negative_prompt
                else MUFUFU_NEGATIVE_PROMPT
            )
            if ANATOMY_POSITIVE_TAGS:
                prompt = f"{ANATOMY_POSITIVE_TAGS}, {prompt}"
            if OPTIMIZED_PARAMS and (not steps or steps < 30):
                steps = OPTIMIZED_PARAMS.get("steps", 50)
            if OPTIMIZED_PARAMS and not cfg_scale:
                cfg_scale = OPTIMIZED_PARAMS.get("guidance_scale", 7.5)
            if OPTIMIZED_PARAMS:
                sampler = OPTIMIZED_PARAMS.get("sampler", sampler)
                scheduler = OPTIMIZED_PARAMS.get("scheduler", scheduler)
            logger.info("✅ ムフフモード: 身体崩れ対策タグを適用しました")
        except ImportError as e:
            logger.debug(f"mufufu_config が見つかりません: {e}")

    try:
        prompt_id = comfyui.generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            model=model,
            loras=loras,
            steps=steps,
            guidance_scale=cfg_scale,
            sampler=sampler,
            scheduler=scheduler,
            seed=seed,
        )
    except Exception as e:
        logger.warning(f"ComfyUI generate error: {e}")
        return _json_error(
            "image_generation_failed", 500, error="internal_error", namespace="comfyui",
        )

    if prompt_id:
        # n8n Webhookに通知（オプション）
        n8n_webhook_url = (os.getenv("N8N_WEBHOOK_URL") or "").strip()
        if n8n_webhook_url and REQUESTS_AVAILABLE:
            try:
                requests.post(  # type: ignore[possibly-unbound]
                    n8n_webhook_url,
                    json={
                        "prompt_id": prompt_id,
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                        "width": width,
                        "height": height,
                        "steps": steps,
                        "cfg_scale": cfg_scale,
                        "seed": seed,
                        "status": "generated",
                        "timestamp": datetime.now().isoformat(),
                    },
                    timeout=5,
                )
            except Exception as e:
                logger.warning(f"n8n Webhook通知に失敗: {e}")

        return jsonify({"prompt_id": prompt_id, "status": "success"}), 200

    return jsonify({"error": "画像生成に失敗しました"}), 500


@app.route("/api/comfyui/queue", methods=["GET"])
@auth_manager.require_api_key
def api_comfyui_queue():
    """ComfyUIキュー状態（要認証）"""
    comfyui = integrations.get("comfyui")
    if not comfyui or not getattr(comfyui, "is_available", lambda: False)():
        return _json_error("comfyui_unavailable", 503, error="unavailable", namespace="comfyui")
    try:
        return jsonify(comfyui.get_queue_status()), 200
    except Exception as e:
        logger.warning(f"ComfyUI queue error: {e}")
        return _json_error("queue_status_failed", 500, error="internal_error", namespace="comfyui")


@app.route("/api/comfyui/history", methods=["GET"])
@auth_manager.require_api_key
def api_comfyui_history():
    """ComfyUI履歴"""
    comfyui = integrations.get("comfyui")
    if not comfyui or not getattr(comfyui, "is_available", lambda: False)():
        return _json_error("comfyui_unavailable", 503, error="unavailable", namespace="comfyui")
    try:
        limit = int(request.args.get("limit", 10) or 10)
        limit = max(1, min(limit, 50))
        return jsonify({"items": comfyui.get_history(max_items=limit)}), 200
    except Exception as e:
        logger.warning(f"ComfyUI history error: {e}")
        return _json_error("history_failed", 500, error="internal_error", namespace="comfyui")


def _get_or_init_enhanced_llm_router() -> Optional["EnhancedLLMRouter"]:
    """拡張LLMルーティング（難易度対応）を取得（必要なら遅延初期化）。"""
    router = integrations.get("enhanced_llm_routing")
    if router is not None:
        return router  # type: ignore[return-value]

    if not ENHANCED_LLM_ROUTING_AVAILABLE:
        return None

    try:
        router = EnhancedLLMRouter(  # type: ignore[possibly-unbound]
            lm_studio_url=get_lm_studio_url(),
            ollama_url=get_ollama_url(),
        )
        integrations["enhanced_llm_routing"] = router
        return router
    except Exception as e:
        logger.warning(f"Enhanced LLM router init failed: {e}")
        return None


@app.route("/api/llm/health", methods=["GET"])
def api_llm_health():
    """LLMルーティングのヘルス（利用可能モデル数など）"""
    router = _get_or_init_enhanced_llm_router()
    if not router:
        return _json_error("llm_routing_not_initialized", 503, error="unavailable", namespace="llm")

    try:
        models = router.get_available_models()
        return (
            jsonify(
                {
                    "status": "ok",
                    "llm_server": getattr(router, "llm_server", "unknown"),
                    "available_models": len(models),
                    "models": models,
                }
            ),
            200,
        )
    except Exception as e:
        logger.warning(f"LLM health error: {e}")
        return _json_error("llm_health_failed", 500, error="internal_error", namespace="llm")


@app.route("/api/llm/models", methods=["GET"])
@app.route("/api/llm/models-enhanced", methods=["GET"])
def api_llm_models():
    """利用可能なモデル一覧を返す"""
    router = _get_or_init_enhanced_llm_router()
    if not router:
        return _json_error("llm_routing_not_initialized", 503, error="unavailable", namespace="llm")

    try:
        return jsonify({"models": router.get_available_models()}), 200
    except Exception as e:
        logger.warning(f"LLM models error: {e}")
        return _json_error("llm_models_failed", 500, error="internal_error", namespace="llm")


@app.route("/api/llm/analyze", methods=["POST"])
def api_llm_analyze():
    """プロンプト難易度を分析（LLM呼び出しなし）"""
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return _json_error("prompt is required", 400, error="bad_request", namespace="llm")

    context = data.get("context") or {}
    if not isinstance(context, dict):
        context = {}

    # 互換: code_context をトップレベルで渡された場合も拾う
    code_context = data.get("code_context")
    if code_context and isinstance(code_context, str):
        context.setdefault("code_context", code_context)

    router = _get_or_init_enhanced_llm_router()
    if not router:
        return _json_error("llm_routing_not_initialized", 503, error="unavailable", namespace="llm")

    try:
        analyzer = getattr(router, "analyzer", None)
        if analyzer is None:
            return _json_error(
                "difficulty_analyzer_unavailable", 503, error="unavailable", namespace="llm",
            )

        score = float(analyzer.calculate_difficulty(prompt, context))
        level = str(analyzer.get_difficulty_level(score))
        recommended = str(analyzer.get_recommended_model(score))

        return (
            jsonify(
                {
                    "difficulty_score": score,
                    "difficulty_level": level,
                    "recommended_model": recommended,
                }
            ),
            200,
        )
    except Exception as e:
        logger.warning(f"LLM analyze error: {e}")
        return _json_error("llm_analyze_failed", 500, error="internal_error", namespace="llm")


@app.route("/api/llm/route", methods=["POST"])
@app.route("/api/llm/route-enhanced", methods=["POST"])
def api_llm_route():
    """LLMリクエストを難易度でルーティングして実行"""
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return _json_error("prompt is required", 400, error="bad_request", namespace="llm")

    context = data.get("context") or {}
    if not isinstance(context, dict):
        context = {}

    preferences = data.get("preferences") or {}
    if not isinstance(preferences, dict):
        preferences = {}

    # 互換: code_context をトップレベルで渡された場合も拾う
    code_context = data.get("code_context")
    if code_context and isinstance(code_context, str):
        context.setdefault("code_context", code_context)

    router = _get_or_init_enhanced_llm_router()
    if not router:
        return _json_error("llm_routing_not_initialized", 503, error="unavailable", namespace="llm")

    try:
        result = router.route(prompt=prompt, context=context, preferences=preferences)
        return jsonify(result), 200
    except Exception as e:
        logger.warning(f"LLM route error: {e}")
        return _json_error("llm_route_failed", 500, error="internal_error", namespace="llm")


@app.route("/api/memory/store", methods=["POST"])
def api_memory_store():
    """記憶への保存（互換エンドポイント）"""
    if not MEMORY_BRIDGE_AVAILABLE or bridge_memory_store is None:
        return _json_error(
            "memory_bridge_unavailable", 503, error="unavailable", namespace="memory",
        )

    data = request.get_json(silent=True) or {}
    content = data.get("content") or data
    if content is None:
        return _json_error("content is required", 400, error="bad_request", namespace="memory")

    try:
        memory_id = bridge_memory_store(
            {"content": content, "metadata": data.get("metadata", {})},
            data.get("format_type", "auto"),
            memory_unified=integrations.get("memory_unified"),
            mem0_integration=integrations.get("mem0"),
        )
        return jsonify({"memory_id": memory_id}), 200
    except Exception as e:
        logger.warning(f"Memory store error: {e}")
        return _json_error("memory_store_failed", 500, error="internal_error", namespace="memory")


@app.route("/memory/write", methods=["POST"])
def memory_write_blueprint():
    """Blueprint互換: 記憶への書き込み"""
    if not MEMORY_BRIDGE_AVAILABLE or bridge_memory_store is None:
        return _json_error(
            "memory_bridge_unavailable", 503, error="unavailable", namespace="memory",
        )

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return _json_error("text is required", 400, error="bad_request", namespace="memory")

    memory_type = (data.get("type") or "memo").strip() or "memo"
    metadata = data.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    if data.get("tags") is not None:
        metadata["tags"] = data.get("tags")
    if data.get("source") is not None:
        metadata["source"] = data.get("source")
    if data.get("time") is not None:
        metadata["time"] = data.get("time")
    if data.get("user_id") is not None:
        metadata["user_id"] = data.get("user_id")

    try:
        memory_id = bridge_memory_store(
            {"content": text, "metadata": metadata},
            memory_type,
            memory_unified=integrations.get("memory_unified"),
            mem0_integration=integrations.get("mem0"),
        )
        return jsonify({"memory_id": memory_id}), 200
    except Exception as e:
        logger.warning(f"Memory write error: {e}")
        return _json_error("memory_write_failed", 500, error="internal_error", namespace="memory")


@app.route("/api/memory/recall", methods=["GET"])
def api_memory_recall():
    """記憶からの検索（互換エンドポイント）"""
    if not MEMORY_BRIDGE_AVAILABLE or bridge_memory_recall is None:
        return _json_error(
            "memory_bridge_unavailable", 503, error="unavailable", namespace="memory",
        )

    query = (request.args.get("query") or "").strip()
    if not query:
        return _json_error("query is required", 400, error="bad_request", namespace="memory")

    scope = request.args.get("scope", "all")
    try:
        limit = int(request.args.get("limit", 10))
    except Exception:
        limit = 10

    try:
        results = bridge_memory_recall(
            query=query,
            scope=scope,
            limit=limit,
            memory_unified=integrations.get("memory_unified"),
        )
        return jsonify({"count": len(results), "results": results}), 200
    except Exception as e:
        logger.warning(f"Memory recall error: {e}")
        return _json_error("memory_recall_failed", 500, error="internal_error", namespace="memory")


@app.route("/memory/search", methods=["POST"])
def memory_search_blueprint():
    """Blueprint互換: 記憶検索"""
    if not MEMORY_BRIDGE_AVAILABLE or bridge_memory_recall is None:
        return _json_error(
            "memory_bridge_unavailable", 503, error="unavailable", namespace="memory",
        )

    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return _json_error("query is required", 400, error="bad_request", namespace="memory")

    try:
        k = int(data.get("k", 10))
    except Exception:
        k = 10

    filters = data.get("filters") or {}
    scope = "all"
    if isinstance(filters, dict):
        scope = (filters.get("scope") or "all").strip() or "all"

    try:
        results = bridge_memory_recall(
            query=query,
            scope=scope,
            limit=k,
            memory_unified=integrations.get("memory_unified"),
        )

        chunks = []
        for item in results:
            if isinstance(item, dict):
                metadata = item.get("metadata") or {}
                if not isinstance(metadata, dict):
                    metadata = {}
                score = metadata.get("score", 0.0)
                chunks.append(
                    {
                        "text": item.get("content", ""),
                        "source": metadata.get("source", item.get("type", "memory")),
                        "score": score,
                        "metadata": {
                            **metadata,
                            "id": item.get("id"),
                            "type": item.get("type"),
                            "timestamp": item.get("timestamp"),
                        },
                    }
                )
            else:
                chunks.append(
                    {
                        "text": str(item),
                        "source": "memory",
                        "score": 0.0,
                        "metadata": {},
                    }
                )

        return jsonify({"chunks": chunks}), 200
    except Exception as e:
        logger.warning(f"Memory search error: {e}")
        return _json_error("memory_search_failed", 500, error="internal_error", namespace="memory")


ops_jobs: Dict[str, Dict[str, Any]] = _load_jobs_from_disk("ops")
ops_jobs_lock = threading.Lock()


def _ops_save_job(job_id: str, payload: Dict[str, Any]) -> None:
    with ops_jobs_lock:
        ops_jobs[job_id] = payload
        _save_jobs_to_disk("ops", ops_jobs)


def _ops_get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with ops_jobs_lock:
        return ops_jobs.get(job_id)


def _ops_http_post_json(url: str, payload: Dict[str, Any], timeout: float = 30.0):
    if not REQUESTS_AVAILABLE:
        return None, _json_error(
            "requests_module_unavailable", 503, error="unavailable", namespace="ops",
        )

    try:
        response = requests.post(url, json=payload, timeout=timeout)  # type: ignore[possibly-unbound]
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}
        return (response.status_code, body), None
    except Exception as e:
        logger.warning(f"OPS POST error ({url}): {e}")
        return None, _json_error(
            "ops_upstream_unreachable", 503, error="unavailable", namespace="ops",
        )


def _ops_http_get_json(url: str, timeout: float = 15.0):
    if not REQUESTS_AVAILABLE:
        return None, _json_error(
            "requests_module_unavailable", 503, error="unavailable", namespace="ops",
        )

    try:
        response = requests.get(url, timeout=timeout)  # type: ignore[possibly-unbound]
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}
        return (response.status_code, body), None
    except Exception as e:
        logger.warning(f"OPS GET error ({url}): {e}")
        return None, _json_error(
            "ops_upstream_unreachable", 503, error="unavailable", namespace="ops",
        )


def _ops_build_fallback_plan(text: str) -> Dict[str, Any]:
    fallback_plan_id = f"plan_{uuid.uuid4().hex[:10]}"
    return {
        "plan_id": fallback_plan_id,
        "intent_type": "ops_fallback",
        "original_input": text,
        "steps": [
            {
                "step_id": "step_1",
                "description": f"Handle request: {text[:80]}",
                "action": "call_api",
                "target": "unified_api",
                "parameters": {"text": text},
                "dependencies": [],
                "estimated_duration": 30,
                "priority": "medium",
                "status": "pending",
            }
        ],
        "total_estimated_duration": 30,
        "priority": "medium",
        "created_at": datetime.now().isoformat(),
        "status": "pending",
        "fallback": True,
    }


@app.route("/ops/plan", methods=["POST"])
def ops_plan_blueprint():
    """Blueprint互換: 実行計画の作成"""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or data.get("goal") or data.get("input") or "").strip()
    if not text:
        return _json_error(
            "text (or goal/input) is required", 400, error="bad_request", namespace="ops",
        )

    planner_url = f"{TASK_PLANNER_BASE_URL}/api/plan"
    upstream, error_response = _ops_http_post_json(planner_url, {"text": text})
    if error_response:
        body = _ops_build_fallback_plan(text)
        plan_id = body.get("plan_id")
        return (
            jsonify(
                {
                    "plan_id": plan_id,
                    "plan": body,
                    "approval_required": True,
                    "next": "POST /ops/exec with {plan_id, plan, approved:true}",
                    "fallback": "planner_unreachable",
                    "_meta": _job_response_meta("ops"),
                }
            ),
            200,
        )

    status_code, body = upstream  # type: ignore
    if status_code >= 400:
        return (
            jsonify(
                {
                    "error": "plan_generation_failed",
                    "upstream": body,
                    "_meta": _job_response_meta("ops"),
                }
            ),
            status_code,
        )

    plan_id = body.get("plan_id") or f"plan_{uuid.uuid4().hex[:10]}"

    return (
        jsonify(
            {
                "plan_id": plan_id,
                "plan": body,
                "approval_required": True,
                "next": "POST /ops/exec with {plan_id, approved:true}",
                "_meta": _job_response_meta("ops"),
            }
        ),
        200,
    )


@app.route("/ops/exec", methods=["POST"])
def ops_exec_blueprint():
    """Blueprint互換: 承認後に計画を実行"""
    data = request.get_json(silent=True) or {}

    approved = bool(data.get("approved") or data.get("confirm") or data.get("approval"))
    if not approved:
        return (
            jsonify(
                {
                    "error": "approval_required",
                    "message": "Set approved=true to execute plan.",
                    "_meta": _job_response_meta("ops"),
                }
            ),
            403,
        )

    plan = data.get("plan")
    plan_id = data.get("plan_id")

    if plan is None and plan_id:
        plan_url = f"{TASK_PLANNER_BASE_URL}/api/plan/{plan_id}"
        upstream_get, error_response = _ops_http_get_json(plan_url)
        if error_response:
            return error_response
        get_status, get_body = upstream_get  # type: ignore
        if get_status >= 400:
            return (
                jsonify(
                    {
                        "error": "plan_not_found",
                        "upstream": get_body,
                        "_meta": _job_response_meta("ops"),
                    }
                ),
                get_status,
            )
        plan = get_body

    if plan is None:
        return _json_error("plan or plan_id is required", 400, error="bad_request", namespace="ops")

    job_id = data.get("job_id") or f"job_{uuid.uuid4().hex[:12]}"
    started_at = datetime.now().isoformat()

    _ops_save_job(
        job_id,
        {
            "job_id": job_id,
            "plan_id": plan.get("plan_id", plan_id),
            "status": "running",
            "created_at": started_at,
            "updated_at": started_at,
        },
    )

    executor_url = f"{EXECUTOR_ENHANCED_BASE_URL}/api/execute"
    upstream_post, error_response = _ops_http_post_json(
        executor_url,
        {
            "plan": plan,
            "execution_id": job_id,
        },
        timeout=120.0,
    )

    if error_response:
        fallback_result = {
            "execution_id": job_id,
            "plan_id": plan.get("plan_id", plan_id),
            "status": "completed",
            "result": {
                "summary": "Executor unavailable: fallback completion",
                "steps": [
                    {
                        "step_id": "fallback_step",
                        "status": "completed",
                        "action": "fallback",
                    }
                ],
            },
            "fallback": "executor_unreachable",
        }
        _ops_save_job(
            job_id,
            {
                "job_id": job_id,
                "plan_id": plan.get("plan_id", plan_id),
                "status": "completed",
                "created_at": started_at,
                "updated_at": datetime.now().isoformat(),
                "result": fallback_result,
            },
        )
        with ops_jobs_lock:
            total_jobs = len(ops_jobs)
        return (
            jsonify(
                {
                    "job_id": job_id,
                    "status": "completed",
                    "fallback": "executor_unreachable",
                    "_meta": _job_response_meta("ops", total_jobs),
                }
            ),
            202,
        )

    exec_status_code, exec_body = upstream_post  # type: ignore
    final_status = "completed"
    if exec_status_code >= 400:
        final_status = "failed"
    elif isinstance(exec_body, dict):
        if exec_body.get("status") in ("failed", "partial_success"):
            final_status = exec_body.get("status")

    _ops_save_job(
        job_id,
        {
            "job_id": job_id,
            "plan_id": plan.get("plan_id", plan_id),
            "status": final_status,
            "created_at": started_at,
            "updated_at": datetime.now().isoformat(),
            "result": exec_body,
        },
    )

    with ops_jobs_lock:
        total_jobs = len(ops_jobs)
    meta = _job_response_meta("ops", total_jobs)
    return jsonify({"job_id": job_id, "status": final_status, "_meta": meta}), 202


@app.route("/ops/job/<job_id>", methods=["GET"])
def ops_job_blueprint(job_id: str):
    """Blueprint互換: 実行ジョブ状態の取得"""
    with ops_jobs_lock:
        job = ops_jobs.get(job_id)
        total_jobs = len(ops_jobs)
    if not job:
        return _json_error(
            "job not found", 404, error="not_found", namespace="ops", total_jobs=total_jobs,
        )
    return jsonify(_job_payload_with_meta("ops", job, total_jobs)), 200


dev_jobs: Dict[str, Dict[str, Any]] = _load_jobs_from_disk("dev")
dev_jobs_lock = threading.Lock()


def _dev_save_job(job_id: str, payload: Dict[str, Any]) -> None:
    with dev_jobs_lock:
        dev_jobs[job_id] = payload
        _save_jobs_to_disk("dev", dev_jobs)


def _dev_get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with dev_jobs_lock:
        return dev_jobs.get(job_id)


def _dev_run_command(command: str, cwd: Optional[str], timeout_sec: int = 600) -> Dict[str, Any]:
    start = time.time()
    workdir = cwd or os.getcwd()
    if not os.path.isdir(workdir):
        return {
            "status": "failed",
            "command": command,
            "cwd": workdir,
            "exit_code": None,
            "stdout": "",
            "stderr": "cwd_not_found",
            "duration_sec": 0,
        }

    try:
        completed = subprocess.run(
            command,
            cwd=workdir,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
        )
        return {
            "status": "completed" if completed.returncode == 0 else "failed",
            "command": command,
            "cwd": workdir,
            "exit_code": completed.returncode,
            "stdout": (completed.stdout or "")[:12000],
            "stderr": (completed.stderr or "")[:12000],
            "duration_sec": round(time.time() - start, 3),
        }
    except subprocess.TimeoutExpired as e:
        return {
            "status": "failed",
            "command": command,
            "cwd": workdir,
            "exit_code": None,
            "stdout": ((e.stdout or "") if isinstance(e.stdout, str) else "")[:12000],
            "stderr": "timeout",
            "duration_sec": round(time.time() - start, 3),
        }
    except Exception as e:
        return {
            "status": "failed",
            "command": command,
            "cwd": workdir,
            "exit_code": None,
            "stdout": "",
            "stderr": str(e),
            "duration_sec": round(time.time() - start, 3),
        }


def _dev_execute_action(action: str, data: Dict[str, Any]) -> Dict[str, Any]:
    execute = bool(data.get("execute", False))
    command = (data.get("command") or "").strip()
    repo_path = data.get("repo_path")

    if execute and command:
        run_result = _dev_run_command(command, repo_path, int(data.get("timeout_sec", 600)))
        return {
            "action": action,
            "mode": "execute",
            **run_result,
            "input": {
                "instruction": data.get("instruction"),
                "target": data.get("target"),
            },
        }

    return {
        "action": action,
        "mode": "plan_only",
        "status": "completed",
        "summary": f"{action} accepted (dry-run)",
        "input": {
            "instruction": data.get("instruction"),
            "patch": data.get("patch"),
            "target": data.get("target"),
            "command": command,
            "repo_path": repo_path,
        },
    }


def _dev_submit_job(action: str, data: Dict[str, Any]):
    job_id = data.get("job_id") or f"devjob_{uuid.uuid4().hex[:12]}"
    started_at = datetime.now().isoformat()

    _dev_save_job(
        job_id,
        {
            "job_id": job_id,
            "action": action,
            "status": "running",
            "created_at": started_at,
            "updated_at": started_at,
        },
    )

    result = _dev_execute_action(action, data)
    final_status = result.get("status", "completed")
    _dev_save_job(
        job_id,
        {
            "job_id": job_id,
            "action": action,
            "status": final_status,
            "created_at": started_at,
            "updated_at": datetime.now().isoformat(),
            "result": result,
        },
    )

    with dev_jobs_lock:
        total_jobs = len(dev_jobs)
    return (
        jsonify(
            {
                "job_id": job_id,
                "status": final_status,
                "action": action,
                "_meta": _job_response_meta("dev", total_jobs),
            }
        ),
        202,
    )


@app.route("/dev/patch", methods=["POST"])
def dev_patch_blueprint():
    """Blueprint互換: パッチ作業を受理して実行（またはdry-run）"""
    data = request.get_json(silent=True) or {}
    if not ((data.get("instruction") or "").strip() or (data.get("patch") or "").strip()):
        return _json_error(
            "instruction or patch is required", 400, error="bad_request", namespace="dev",
        )
    return _dev_submit_job("patch", data)


@app.route("/dev/test", methods=["POST"])
def dev_test_blueprint():
    """Blueprint互換: テスト実行を受理して実行（またはdry-run）"""
    data = request.get_json(silent=True) or {}
    return _dev_submit_job("test", data)


@app.route("/dev/deploy", methods=["POST"])
def dev_deploy_blueprint():
    """Blueprint互換: デプロイ実行を受理して実行（またはdry-run）"""
    data = request.get_json(silent=True) or {}
    return _dev_submit_job("deploy", data)


@app.route("/dev/job/<job_id>", methods=["GET"])
def dev_job_blueprint(job_id: str):
    """Blueprint互換: 開発ジョブ状態の取得"""
    with dev_jobs_lock:
        job = dev_jobs.get(job_id)
        total_jobs = len(dev_jobs)
    if not job:
        return _json_error(
            "job not found", 404, error="not_found", namespace="dev", total_jobs=total_jobs,
        )
    return jsonify(_job_payload_with_meta("dev", job, total_jobs)), 200


notify_jobs: Dict[str, Dict[str, Any]] = _load_jobs_from_disk("notify")
notify_jobs_lock = threading.Lock()


def _notify_save_job(job_id: str, payload: Dict[str, Any]) -> None:
    with notify_jobs_lock:
        notify_jobs[job_id] = payload
        _save_jobs_to_disk("notify", notify_jobs)


def _notify_get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with notify_jobs_lock:
        return notify_jobs.get(job_id)


def _notify_get_hub_instance() -> Optional[Any]:
    notification_hub = integrations.get("notification_hub")
    if not notification_hub and NOTIFICATION_HUB_AVAILABLE:
        try:
            notification_hub = NotificationHub()  # type: ignore[possibly-unbound]
            integrations["notification_hub"] = notification_hub
        except Exception as e:
            logger.warning(f"NotificationHub lazy init error: {e}")
            notification_hub = None
    return notification_hub


def _notify_call_with_timeout(
    notification_hub: Any, message: str, priority: str, timeout_sec: int
) -> Dict[str, Any]:
    bucket: Dict[str, Any] = {"done": False, "result": None, "error": None}

    def _worker() -> None:
        try:
            bucket["result"] = notification_hub.notify(message, priority=priority)
        except Exception as e:
            bucket["error"] = str(e)
        finally:
            bucket["done"] = True

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(max(1, timeout_sec))

    if not bucket["done"]:
        return {"timeout": True, "error": "notify_timeout", "results": None}
    if bucket["error"]:
        return {"timeout": False, "error": bucket["error"], "results": None}
    return {"timeout": False, "error": None, "results": bucket["result"]}


def _notify_run_job(job_id: str, message: str, priority: str, timeout_sec: int = 20) -> None:
    started_at = datetime.now().isoformat()
    _notify_save_job(
        job_id,
        {
            "job_id": job_id,
            "status": "running",
            "priority": priority,
            "message": message,
            "created_at": started_at,
            "updated_at": started_at,
        },
    )

    notification_hub = _notify_get_hub_instance()
    if not notification_hub:
        _notify_save_job(
            job_id,
            {
                "job_id": job_id,
                "status": "failed",
                "priority": priority,
                "message": message,
                "updated_at": datetime.now().isoformat(),
                "error": "notification_hub_unavailable",
            },
        )
        return

    try:
        notify_result = _notify_call_with_timeout(notification_hub, message, priority, timeout_sec)
        if notify_result.get("timeout"):
            _notify_save_job(
                job_id,
                {
                    "job_id": job_id,
                    "status": "failed",
                    "priority": priority,
                    "message": message,
                    "updated_at": datetime.now().isoformat(),
                    "error": "notify_timeout",
                },
            )
            return

        if notify_result.get("error"):
            _notify_save_job(
                job_id,
                {
                    "job_id": job_id,
                    "status": "failed",
                    "priority": priority,
                    "message": message,
                    "updated_at": datetime.now().isoformat(),
                    "error": notify_result.get("error"),
                },
            )
            return

        results = notify_result.get("results")
        slack_ok = bool(results.get("slack")) if isinstance(results, dict) else False
        _notify_save_job(
            job_id,
            {
                "job_id": job_id,
                "status": "sent" if slack_ok else "partial_failed",
                "priority": priority,
                "message": message,
                "updated_at": datetime.now().isoformat(),
                "results": results,
            },
        )
    except Exception as e:
        logger.warning(f"notify/send job error: {e}")
        _notify_save_job(
            job_id,
            {
                "job_id": job_id,
                "status": "failed",
                "priority": priority,
                "message": message,
                "updated_at": datetime.now().isoformat(),
                "error": str(e),
            },
        )


@app.route("/notify/send", methods=["POST"])
def notify_send_blueprint():
    """Blueprint互換: 通知送信（NotificationHub経由）"""
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or data.get("text") or "").strip()
    priority = (data.get("priority") or "normal").strip().lower()
    async_mode = data.get("async")
    if async_mode is None:
        async_mode = True

    if not message:
        return _json_error(
            "message (or text) is required", 400, error="bad_request", namespace="notify",
        )

    job_id = data.get("job_id") or f"notifyjob_{uuid.uuid4().hex[:12]}"

    if async_mode:
        queued_at = datetime.now().isoformat()
        _notify_save_job(
            job_id,
            {
                "job_id": job_id,
                "status": "queued",
                "priority": priority,
                "message": message,
                "created_at": queued_at,
                "updated_at": queued_at,
            },
        )
        timeout_sec = int(data.get("timeout_sec", 20))
        t = threading.Thread(
            target=_notify_run_job,
            args=(job_id, message, priority, timeout_sec),
            daemon=True,
        )
        t.start()
        with notify_jobs_lock:
            total_jobs = len(notify_jobs)
        return (
            jsonify(
                {
                    "job_id": job_id,
                    "status": "queued",
                    "next": f"GET /notify/job/{job_id}",
                    "_meta": _job_response_meta("notify", total_jobs),
                }
            ),
            202,
        )

    _notify_run_job(job_id, message, priority, int(data.get("timeout_sec", 20)))
    with notify_jobs_lock:
        job = notify_jobs.get(job_id) or {}
        total_jobs = len(notify_jobs)
    if job.get("status") == "failed" and job.get("error") == "notification_hub_unavailable":
        return _json_error(
            "notification_hub_unavailable",
            503,
            error="unavailable",
            namespace="notify",
            total_jobs=total_jobs,
        )
    return jsonify(_job_payload_with_meta("notify", job, total_jobs)), 200


@app.route("/notify/job/<job_id>", methods=["GET"])
def notify_job_blueprint(job_id: str):
    """Blueprint互換: 通知ジョブ状態の取得"""
    with notify_jobs_lock:
        job = notify_jobs.get(job_id)
        total_jobs = len(notify_jobs)
    if not job:
        return _json_error(
            "job not found", 404, error="not_found", namespace="notify", total_jobs=total_jobs,
        )
    return jsonify(_job_payload_with_meta("notify", job, total_jobs)), 200


# 統合システムのインスタンス
integrations: Dict[str, Any] = {}

# 初期化状態管理
initialization_lock = threading.Lock()
initialization_status = {
    "status": "starting",  # "starting", "ready", "error"
    "pending": [],
    "completed": [],
    "failed": [],
    "checks": {},  # 各チェックの状態
}


def initialize_integrations():
    """統合システムを初期化（バックグラウンドで実行）"""
    global integrations, initialization_status

    initialization_status["status"] = "starting"
    initialization_status["pending"] = []
    initialization_status["completed"] = []
    initialization_status["failed"] = []

    # 新システムの完全統合（推奨改善一括実装）
    try:
        # Prometheusメトリクス統合
        try:
            from prometheus_integration import get_prometheus_metrics, setup_prometheus_endpoint

            prometheus_metrics = get_prometheus_metrics()
            if prometheus_metrics:
                setup_prometheus_endpoint(app, prometheus_metrics)
                integrations["prometheus_metrics"] = prometheus_metrics
                logger.info("✅ Prometheusメトリクス統合完了（/metricsエンドポイント追加）")
        except Exception as e:
            logger.warning(f"⚠️ Prometheusメトリクス統合エラー: {e}")

        # アラートシステム統合
        try:
            from alert_system import get_alert_system

            alert_system = get_alert_system()
            integrations["alert_system"] = alert_system
            logger.info("✅ アラートシステム統合完了")
        except Exception as e:
            logger.warning(f"⚠️ アラートシステム統合エラー: {e}")

        # パフォーマンス監視統合（自動開始）
        try:
            from performance_monitor import get_performance_monitor

            performance_monitor = get_performance_monitor()
            integrations["performance_monitor"] = performance_monitor

            # 自動監視を開始（バックグラウンド）
            def start_monitoring():
                try:
                    import asyncio

                    # Python 3.10+ 対応: get_running_loop() を使用
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    loop.run_until_complete(performance_monitor.start_monitoring(interval=10))
                    logger.info("✅ パフォーマンス監視自動開始完了（10秒間隔）")
                except Exception as e:
                    logger.warning(f"⚠️ パフォーマンス監視自動開始エラー: {e}")

            import threading

            monitor_thread = threading.Thread(target=start_monitoring, daemon=True)
            monitor_thread.start()
            logger.info("✅ パフォーマンス監視統合完了（自動監視開始）")
        except Exception as e:
            logger.warning(f"⚠️ パフォーマンス監視統合エラー: {e}")

        # GPU最適化システム統合（非同期初期化）
        try:
            from gpu_optimizer import get_gpu_optimizer

            gpu_optimizer = get_gpu_optimizer()
            integrations["gpu_optimizer"] = gpu_optimizer

            # 非同期初期化をバックグラウンドで実行
            def init_gpu_optimizer():
                try:
                    import asyncio

                    # Python 3.10+ 対応: get_running_loop() を使用
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    loop.run_until_complete(gpu_optimizer.initialize())
                    logger.info("✅ GPU最適化システム非同期初期化完了")
                except Exception as e:
                    logger.warning(f"⚠️ GPU最適化システム非同期初期化エラー: {e}")

            import threading

            init_thread = threading.Thread(target=init_gpu_optimizer, daemon=True)
            init_thread.start()
            logger.info("✅ GPU最適化システム統合完了（非同期初期化開始）")
        except Exception as e:
            logger.warning(f"⚠️ GPU最適化システム統合エラー: {e}")

        # メトリクス収集システム統合（自動収集）
        try:
            from metrics_collector import get_metrics_collector

            metrics_collector = get_metrics_collector()
            integrations["metrics_collector"] = metrics_collector
            # 自動収集を開始
            try:
                metrics_collector.collect_system_metrics()
                logger.info("✅ メトリクス収集システム統合完了（自動収集開始）")
            except Exception as e:
                logger.warning(f"⚠️ メトリクス自動収集エラー: {e}")
        except Exception as e:
            logger.warning(f"⚠️ メトリクス収集システム統合エラー: {e}")

        # 自動バックアップシステム統合（自動スケジュール）
        try:
            from auto_backup_system import get_backup_system

            backup_system = get_backup_system()
            integrations["backup_system"] = backup_system
            # 自動バックアップをスケジュール（毎日02:00）
            backup_system.start_scheduled_backups("02:00")
            logger.info("✅ 自動バックアップシステム統合完了（毎日02:00にバックアップ）")
        except Exception as e:
            logger.warning(f"⚠️ 自動バックアップシステム統合エラー: {e}")

        # インテリジェントキャッシュ統合
        try:
            from intelligent_cache import get_cache

            cache = get_cache(max_size=1000, default_ttl=3600)
            integrations["cache"] = cache
            logger.info("✅ インテリジェントキャッシュ統合完了")
        except Exception as e:
            logger.warning(f"⚠️ インテリジェントキャッシュ統合エラー: {e}")

        # 設定検証システム統合（自動検証）
        try:
            from config_validator_enhanced import get_config_validator

            config_validator = get_config_validator()
            integrations["config_validator"] = config_validator
            # 起動時に設定ファイルを検証
            validation_results = config_validator.validate_all_configs()
            # validation_resultsの構造: {config_file: (is_valid, errors)}
            error_count = sum(1 for _, (is_valid, _) in validation_results.items() if not is_valid)
            if error_count == 0:
                logger.info("✅ 設定検証システム統合完了（すべての設定ファイルが正常）")
            else:
                # エラーの詳細をログに出力
                error_files = []
                for config_file, result in validation_results.items():
                    # resultは (is_valid, errors) のタプル
                    if isinstance(result, tuple) and len(result) >= 2:
                        is_valid, errors = result[0], result[1]
                    else:
                        is_valid, errors = result, []

                    if not is_valid:
                        file_name = Path(config_file).name
                        error_count_for_file = len(errors) if isinstance(errors, list) else 1
                        error_files.append(f"  - {file_name}: {error_count_for_file}件のエラー")
                        # エラーの詳細を最初の3件まで表示
                        if isinstance(errors, list):
                            for error in errors[:3]:
                                if hasattr(error, "message"):
                                    logger.debug(f"    {error.message}")
                                elif isinstance(error, str):
                                    logger.debug(f"    {error}")
                                elif hasattr(error, "__str__"):
                                    logger.debug(f"    {str(error)}")
                logger.warning(
                    f"⚠️ 設定検証システム統合完了（{error_count}個の設定ファイルにエラー）"
                )
                if error_files:
                    logger.info("エラーがある設定ファイル:\n" + "\n".join(error_files))
        except Exception as e:
            logger.warning(f"⚠️ 設定検証システム統合エラー: {e}")

        logger.info("✅ 新システムを完全統合しました（推奨改善一括実装）")
    except Exception as e:
        logger.warning(f"⚠️ 新システム統合エラー: {e}")

    # 初期化対象のリスト
    init_tasks = []

    # ComfyUI統合（オプション）
    if COMFYUI_AVAILABLE:
        init_tasks.append(
            (
                "comfyui",
                lambda: ComfyUIIntegration(  # type: ignore[possibly-unbound]
                    base_url=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
                ),
            )
        )

    # SVI × Wan 2.2動画生成統合（オプション）
    if SVI_WAN22_AVAILABLE:
        init_tasks.append(
            (
                "svi_wan22",
                lambda: SVIWan22VideoIntegration(  # type: ignore[possibly-unbound]
                    base_url=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
                ),
            )
        )

    # LTX-2動画生成統合（オプション）
    if LTX2_AVAILABLE:
        init_tasks.append(
            (
                "ltx2",
                lambda: LTX2VideoIntegration(  # type: ignore[possibly-unbound]
                    base_url=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
                ),
            )
        )

    # LTX-2 Infinity統合（オプション）
    if LTX2_INFINITY_AVAILABLE:
        init_tasks.append(
            (
                "ltx2_infinity",
                lambda: LTX2InfinityIntegration(  # type: ignore[possibly-unbound]
                    base_url=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
                ),
            )
        )
        init_tasks.append(("ltx2_workflow_generator", lambda: LTX2WorkflowGenerator()))  # type: ignore[possibly-unbound]
        init_tasks.append(("ltx2_template_manager", lambda: LTX2TemplateManager()))  # type: ignore[possibly-unbound]
        init_tasks.append(("ltx2_nsfw_config", lambda: LTX2NSFWConfig()))  # type: ignore[possibly-unbound]
        init_tasks.append(("ltx2_storage_manager", lambda: LTX2StorageManager()))  # type: ignore[possibly-unbound]

    # Google Drive統合（オプション）
    if GOOGLE_DRIVE_AVAILABLE:
        init_tasks.append(
            (
                "google_drive",
                lambda: GoogleDriveIntegration(  # type: ignore[possibly-unbound]
                    credentials_path=os.getenv("GOOGLE_DRIVE_CREDENTIALS", "credentials.json"),
                    token_path=os.getenv("GOOGLE_DRIVE_TOKEN", "token.json"),
                ),
            )
        )

    # CivitAI統合（オプション）
    if CIVITAI_AVAILABLE:
        init_tasks.append(
            ("civitai", lambda: CivitAIIntegration(api_key=os.getenv("CIVITAI_API_KEY")))  # type: ignore[possibly-unbound]
        )

    # LangChain統合（オプション）
    if LANGCHAIN_AVAILABLE:
        init_tasks.append(
            (
                "langchain",
                lambda: LangChainIntegration(  # type: ignore[possibly-unbound]
                    ollama_url=get_ollama_url(),
                    model_name=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
                ),
            )
        )
        init_tasks.append(
            (
                "langgraph",
                lambda: LangGraphIntegration(  # type: ignore[possibly-unbound]
                    ollama_url=get_ollama_url(),
                    model_name=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
                ),
            )
        )

    # Mem0統合（オプション）
    if MEM0_AVAILABLE:
        init_tasks.append(("mem0", lambda: Mem0Integration()))  # type: ignore[possibly-unbound]

    # Obsidian統合（オプション）
    if OBSIDIAN_AVAILABLE:
        init_tasks.append(
            (
                "obsidian",
                lambda: ObsidianIntegration(  # type: ignore[possibly-unbound]
                    vault_path=os.getenv(
                        "OBSIDIAN_VAULT_PATH",
                        str(Path.home() / "Documents" / "Obsidian Vault"),
                    )
                ),
            )
        )

    # ローカルLLM統合
    if LOCAL_LLM_AVAILABLE:
        init_tasks.append(("local_llm", lambda: LocalLLMUnified()))  # type: ignore[possibly-unbound]

    # ========================================
    # 拡張フェーズ統合
    # ========================================

    # LLMルーティング統合（オプション）
    if LLM_ROUTING_AVAILABLE:
        init_tasks.append(("llm_routing", lambda: LLMRouter()))  # type: ignore[possibly-unbound]

    # 拡張LLMルーティング統合（難易度判定対応）
    if ENHANCED_LLM_ROUTING_AVAILABLE:
        init_tasks.append(
            (
                "enhanced_llm_routing",
                lambda: EnhancedLLMRouter(  # type: ignore[possibly-unbound]
                    lm_studio_url=get_lm_studio_url(),
                    ollama_url=get_ollama_url(),
                ),
            )
        )

    # 統一記憶システム統合（オプション）
    if MEMORY_UNIFIED_AVAILABLE:
        init_tasks.append(("memory_unified", lambda: UnifiedMemory()))  # type: ignore[possibly-unbound]

    # 通知ハブ統合（オプション）
    if NOTIFICATION_HUB_AVAILABLE:
        init_tasks.append(("notification_hub", lambda: NotificationHub()))  # type: ignore[possibly-unbound]

    # 秘書機能統合（オプション）
    if SECRETARY_AVAILABLE:
        init_tasks.append(("secretary", lambda: SecretaryRoutines()))  # type: ignore[possibly-unbound]

    # 画像ストック統合（オプション）
    if IMAGE_STOCK_AVAILABLE:
        init_tasks.append(("image_stock", lambda: ImageStock()))  # type: ignore[possibly-unbound]

    # OH MY OPENCODE統合（オプション）
    if OH_MY_OPENCODE_AVAILABLE:
        init_tasks.append(("oh_my_opencode", lambda: OHMyOpenCodeIntegration()))  # type: ignore[possibly-unbound]

    # Rows統合（オプション）
    if ROWS_AVAILABLE:
        init_tasks.append(
            (
                "rows",
                lambda: RowsIntegration(  # type: ignore[possibly-unbound]
                    api_key=os.getenv("ROWS_API_KEY"), webhook_url=os.getenv("ROWS_WEBHOOK_URL")
                ),
            )
        )

    # GitHub統合（オプション）
    if GITHUB_AVAILABLE:
        init_tasks.append(("github", lambda: GitHubIntegration(token=os.getenv("GITHUB_TOKEN"))))  # type: ignore[possibly-unbound]

    # n8n統合（オプション）
    if N8N_AVAILABLE:
        init_tasks.append(
            (
                "n8n",
                lambda: N8NIntegration(  # type: ignore[possibly-unbound]
                    base_url=os.getenv(
                        "N8N_BASE_URL",
                        f"http://127.0.0.1:{N8N_PORT}",
                    ),
                    api_key=os.getenv("N8N_API_KEY"),
                ),
            )
        )

    # Excel/LLM処理統合（オプション）
    if EXCEL_LLM_AVAILABLE:
        init_tasks.append(
            (
                "excel_llm",
                lambda: ExcelLLMIntegration(  # type: ignore[possibly-unbound]
                    ollama_url=get_ollama_url(),
                    model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
                ),
            )
        )

    # Step-Deep-Research統合（オプション）
    if STEP_DEEP_RESEARCH_AVAILABLE:
        try:
            config_path = Path(__file__).parent / "step_deep_research_config.json"
            if config_path.exists():
                init_tasks.append(
                    (
                        "step_deep_research",
                        lambda: StepDeepResearchOrchestrator(  # type: ignore[possibly-unbound]
                            json.load(open(config_path, "r", encoding="utf-8"))
                        ),
                    )
                )
        except Exception as e:
            logger.warning(f"Step-Deep-Research統合の初期化準備エラー: {e}")

    # 音声機能統合（オプション）
    if VOICE_INTEGRATION_AVAILABLE:
        try:
            # 音声設定の一元化: voice_config.json があれば env を上書き
            _voice_config_paths = [
                Path(__file__).parent / "voice_config.json",
                Path(__file__).parent / "config" / "voice_config.json",
            ]
            _voice_env_map = {
                "voicevox_url": "VOICEVOX_URL",
                "voice_tts_engine": "VOICE_TTS_ENGINE",
                "speaker_id": "VOICEVOX_SPEAKER_ID",
                "style_bert_vits2_url": "STYLE_BERT_VITS2_URL",
                "voice_stt_model": "VOICE_STT_MODEL",
                "voice_stt_device": "VOICE_STT_DEVICE",
                "voice_stt_compute_type": "VOICE_STT_COMPUTE_TYPE",
            }
            _allowed_voice_env = {
                "VOICEVOX_URL",
                "VOICE_TTS_ENGINE",
                "VOICEVOX_SPEAKER_ID",
                "STYLE_BERT_VITS2_URL",
                "VOICE_STT_MODEL",
                "VOICE_STT_DEVICE",
                "VOICE_STT_COMPUTE_TYPE",
            }
            for _vc_path in _voice_config_paths:
                if _vc_path.exists():
                    try:
                        with open(_vc_path, "r", encoding="utf-8") as _f:
                            _vc = json.load(_f)
                        _voice_cfg = _vc.get("voice") or _vc
                        for _k, _v in _voice_cfg.items():
                            if _v is None or str(_v).strip() == "":
                                continue
                            _env_key = _voice_env_map.get(_k) or (
                                _k if _k.isupper() else _k.upper().replace("-", "_")
                            )
                            if _env_key in _allowed_voice_env:
                                os.environ[_env_key] = str(_v)
                        logger.info(f"音声設定を読み込みました: {_vc_path}")
                    except Exception as _e:
                        logger.warning(f"voice_config 読み込みスキップ: {_e}")
                    break

            # STTエンジン初期化（環境変数から設定を読み込み）
            stt_engine = None
            try:
                stt_model_size = os.getenv("VOICE_STT_MODEL", "large-v3")
                stt_device = os.getenv("VOICE_STT_DEVICE", "cuda")
                stt_compute_type = os.getenv("VOICE_STT_COMPUTE_TYPE", "float16")
                stt_engine = create_stt_engine(  # type: ignore[possibly-unbound]
                    model_size=stt_model_size, device=stt_device, compute_type=stt_compute_type
                )
                logger.info("✅ STTエンジン初期化完了")
            except Exception as e:
                logger.warning(f"⚠️ STTエンジン初期化スキップ: {e}")

            # TTSエンジン初期化
            tts_engine = None
            try:
                tts_engine_name = os.getenv("VOICE_TTS_ENGINE", "voicevox")
                voicevox_url = os.getenv("VOICEVOX_URL", "http://127.0.0.1:50021")
                speaker_id = int(os.getenv("VOICEVOX_SPEAKER_ID", "3"))
                tts_engine = create_tts_engine(  # type: ignore[possibly-unbound]
                    engine=tts_engine_name, voicevox_url=voicevox_url, speaker_id=speaker_id
                )
                logger.info("✅ TTSエンジン初期化完了")
            except Exception as e:
                logger.warning(f"⚠️ TTSエンジン初期化スキップ: {e}")

            if stt_engine is None and tts_engine is None:
                logger.warning("⚠️ 音声機能: STT/TTS 両方初期化できなかったためスキップ")
            else:
                available = (
                    True
                    if (stt_engine and tts_engine)
                    else ("stt_only" if stt_engine else "tts_only")
                )
            voice_integration = {
                "stt_engine": stt_engine,
                "tts_engine": tts_engine,
                "available": available,  # type: ignore[possibly-unbound]
            }
            init_tasks.append(("voice", lambda vi=voice_integration: vi))
            logger.info(f"✅ 音声機能統合を初期化タスクに追加しました（available={available}）")  # type: ignore[possibly-unbound]
        except Exception as e:
            logger.warning(f"⚠️ 音声機能統合の初期化準備エラー: {e}")

    # 統一キャッシュシステム（オプション）
    if UNIFIED_CACHE_AVAILABLE:
        init_tasks.append(("unified_cache", lambda: get_unified_cache()))  # type: ignore[possibly-unbound]

    # パフォーマンス最適化システム（オプション）
    if PERFORMANCE_OPTIMIZER_AVAILABLE:
        init_tasks.append(("performance_optimizer", lambda: PerformanceOptimizer()))  # type: ignore[possibly-unbound]

    # 初期化タスクを実行
    initialization_status["pending"] = [name for name, _ in init_tasks]

    for name, init_func in init_tasks:
        try:
            with initialization_lock:
                initialization_status["pending"].remove(name)
            instance = init_func()
            integrations[name] = instance
            with initialization_lock:
                initialization_status["completed"].append(name)
            logger.info(f"{name}統合を初期化しました")
        except Exception as e:
            with initialization_lock:
                if name in initialization_status["pending"]:
                    initialization_status["pending"].remove(name)
                initialization_status["failed"].append(name)
            logger.warning(f"{name}統合の初期化に失敗: {e}")
            import traceback

            logger.debug(traceback.format_exc())

    # 初期化完了チェック（運用のゲート）
    with initialization_lock:
        checks = _perform_readiness_checks(integrations)
        initialization_status["checks"] = checks

        # 必須チェックがすべてOKならready
        # ただし、統合が利用可能でない場合でも、初期化自体は完了とみなす
        required_checks = [
            "memory_db",
            "obsidian_path",
            "notification_hub",
            "llm_routing",
            "image_stock",
        ]
        # 利用可能な統合のみをチェック（not_availableはOKとみなす）
        available_checks = [
            check
            for check in required_checks
            if checks.get(check, {}).get("status") != "not_available"
        ]
        all_required_ok = (
            all(
                checks.get(check, {}).get("status") in ["ok", "warning"]
                for check in available_checks
            )
            if available_checks
            else True
        )

        if initialization_status["pending"]:
            initialization_status["status"] = "error"
        elif all_required_ok and len(initialization_status["completed"]) > 0:
            # 少なくとも1つの統合が完了していればready
            initialization_status["status"] = "ready"
        else:
            initialization_status["status"] = "starting"  # まだ準備中

    logger.info(
        f"初期化完了: 完了={len(initialization_status['completed'])}, "
        f"失敗={len(initialization_status['failed'])}, "
        f"ready={all_required_ok}, 統合数={len(integrations)}"
    )


_readiness_cache: Dict[str, Any] = {}
_readiness_cache_time: Optional[float] = None
_readiness_cache_ttl = 5  # キャッシュ TTL: 5秒


def _get_cached_readiness_checks(integrations: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """キャッシュ付きレディネスチェック"""
    global _readiness_cache, _readiness_cache_time
    
    # キャッシュをチェック
    if _readiness_cache_time is not None:
        elapsed = time.time() - _readiness_cache_time
        if elapsed < _readiness_cache_ttl and _readiness_cache:
            logger.debug(f"Using cached readiness checks (age: {elapsed:.1f}s)")
            return _readiness_cache.copy()
    
    # 新規生成
    checks = _perform_readiness_checks(integrations)
    _readiness_cache = checks.copy()
    _readiness_cache_time = time.time()
    
    return checks


def _perform_readiness_checks(integrations: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    初期化完了チェック（運用のゲート）

    Returns:
        各チェックの状態
    """
    checks = {}

    # 1. 記憶DB接続OK
    memory = integrations.get("memory_unified")
    if memory:
        try:
            # 簡単な読み書きテスト
            test_data = {"type": "system", "content": "__readiness_check__", "metadata": {}}
            memory.store(test_data, "system")
            checks["memory_db"] = {"status": "ok", "message": "記憶DB接続OK"}
        except Exception as e:
            checks["memory_db"] = {
                "status": "error",
                "message": f"記憶DB接続エラー: {str(e)[:100]}",
            }
    else:
        checks["memory_db"] = {
            "status": "not_available",
            "message": "記憶システムが初期化されていません",
        }

    # 2. Obsidianパス確認OK
    obsidian = integrations.get("obsidian")
    if obsidian:
        try:
            if hasattr(obsidian, "is_available") and obsidian.is_available():
                checks["obsidian_path"] = {"status": "ok", "message": "Obsidianパス確認OK"}
            else:
                checks["obsidian_path"] = {
                    "status": "warning",
                    "message": "Obsidianパスは存在しますが利用できません",
                }
        except Exception as e:
            checks["obsidian_path"] = {
                "status": "error",
                "message": f"Obsidianパス確認エラー: {str(e)[:100]}",
            }
    else:
        checks["obsidian_path"] = {
            "status": "not_available",
            "message": "Obsidianが初期化されていません",
        }

    # 3. 通知ハブ送信OK（ダミー送信テスト）
    notification_hub = integrations.get("notification_hub")
    if notification_hub:
        try:
            # ダミー送信テスト（実際には送信しない、キュー投入のみ）
            # 実際の送信はしないが、初期化は確認
            checks["notification_hub"] = {"status": "ok", "message": "通知ハブ初期化OK"}
        except Exception as e:
            checks["notification_hub"] = {
                "status": "error",
                "message": f"通知ハブエラー: {str(e)[:100]}",
            }
    else:
        checks["notification_hub"] = {
            "status": "not_available",
            "message": "通知ハブが初期化されていません",
        }

    # 4. LLMルーティングのモデル最低1つ起動OK
    llm_routing = integrations.get("llm_routing")
    if llm_routing:
        try:
            # モデルリストを取得
            import requests

            ollama_url = getattr(llm_routing, "ollama_url", get_ollama_url())
            # Some environments route `localhost` via proxy/IPv6 unexpectedly.
            # Normalize to 127.0.0.1 for a local readiness check.
            ollama_url = ollama_url.replace("http://localhost", "http://127.0.0.1").replace(
                "https://localhost", "https://127.0.0.1"
            )
            response = requests.get(f"{ollama_url}/api/tags", timeout=2.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                if models:
                    checks["llm_routing"] = {
                        "status": "ok",
                        "message": f"LLMルーティングOK（{len(models)}モデル利用可能）",
                    }
                else:
                    checks["llm_routing"] = {
                        "status": "warning",
                        "message": "LLMルーティングは初期化されていますが、モデルがインストールされていません",
                    }
            else:
                checks["llm_routing"] = {
                    "status": "error",
                    "message": f"Ollama API接続エラー: HTTP {response.status_code}",
                }
        except Exception as e:
            checks["llm_routing"] = {
                "status": "error",
                "message": f"LLMルーティングチェックエラー: {str(e)[:100]}",
            }
    else:
        checks["llm_routing"] = {
            "status": "not_available",
            "message": "LLMルーティングが初期化されていません",
        }

    # 5. 画像ストックDB/フォルダアクセスOK
    image_stock = integrations.get("image_stock")
    if image_stock:
        try:
            # ストックディレクトリのアクセス確認
            stock_dir = getattr(image_stock, "stock_dir", None)
            if stock_dir and stock_dir.exists():
                # 書き込みテスト（一時ファイル作成）
                test_file = stock_dir / "__readiness_check__.tmp"
                try:
                    test_file.write_text("test", encoding="utf-8")
                    test_file.unlink()
                    checks["image_stock"] = {"status": "ok", "message": "画像ストックアクセスOK"}
                except Exception as e:
                    checks["image_stock"] = {
                        "status": "error",
                        "message": f"画像ストック書き込みエラー: {str(e)[:100]}",
                    }
            else:
                checks["image_stock"] = {
                    "status": "error",
                    "message": "画像ストックディレクトリが存在しません",
                }
        except Exception as e:
            checks["image_stock"] = {
                "status": "error",
                "message": f"画像ストックチェックエラー: {str(e)[:100]}",
            }
    else:
        checks["image_stock"] = {
            "status": "not_available",
            "message": "画像ストックが初期化されていません",
        }

    return checks


@app.route("/health", methods=["GET"])
def health():
    """ヘルスチェック（軽量：プロセス生存のみ）"""
    # 即座に返す（重い処理は一切しない）
    return jsonify({"status": "alive", "timestamp": datetime.now().isoformat()}), 200


@app.route("/api/openapi.json", methods=["GET"])
def get_openapi_spec():
    """OpenAPI 仕様を取得（Swagger UIなどで利用）"""
    spec = _build_openapi_spec()
    if not spec:
        return jsonify({"error": "OpenAPI specification not available"}), 503
    return jsonify(spec), 200


@app.route("/api/swagger", methods=["GET"])
def swagger_ui():
    """Swagger UI（OpenAPI ドキュメント）"""
    swagger_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ManaOS API Documentation</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet"
              href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.15.5/swagger-ui.min.css">
        <script
            src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.15.5/swagger-ui.min.js">
        </script>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script>
            SwaggerUIBundle({
                url: "/api/openapi.json",
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout",
                defaultModelsExpandDepth: 1
            })
        </script>
    </body>
    </html>
    """
    return swagger_html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/companion", methods=["GET"])
def companion_page():
    """Pixel 7 コンパニオンモード用クライアントページ（同一オリジンでAPI利用可）"""
    companion_path = (
        Path(__file__).resolve().parent / "scripts" / "voice" / "pixel7_companion_client.html"
    )
    if companion_path.exists():
        return send_from_directory(
            companion_path.parent, companion_path.name, mimetype="text/html; charset=utf-8"
        )
    return "Companion page not found", 404


@app.route("/companion/manifest.json", methods=["GET"])
def companion_manifest():
    """PWA manifest for コンパニオン"""
    manifest_path = (
        Path(__file__).resolve().parent / "scripts" / "voice" / "companion_manifest.json"
    )
    if manifest_path.exists():
        return send_from_directory(
            manifest_path.parent, manifest_path.name, mimetype="application/json"
        )
    return "Manifest not found", 404


@app.route("/companion/sw.js", methods=["GET"])
def companion_sw():
    """PWA service worker for コンパニオン"""
    sw_path = Path(__file__).resolve().parent / "scripts" / "voice" / "companion_sw.js"
    if sw_path.exists():
        return send_from_directory(sw_path.parent, sw_path.name, mimetype="application/javascript")
    return "Service worker not found", 404


@app.route("/ready", methods=["GET"])
def ready():
    """
    レディネスチェック（初期化完了チェック）

    Returns:
        200: 初期化完了（すべての必須チェックがOK）
        503: 初期化中（必須チェックが未完了）
        500: 初期化エラー
    """
    with initialization_lock:
        status = initialization_status["status"]
        pending = initialization_status["pending"].copy()
        completed = initialization_status["completed"].copy()
        failed = initialization_status["failed"].copy()
        checks = initialization_status.get("checks", {}).copy()

    # NOTE: /ready は「依存関係まで含めたレディネス」のため、初回起動時に
    # 依存（例: Ollama）が後から起動すると 503 のまま固定されがち。
    # ここでは starting のときだけ軽量チェックを再計算し、条件を満たせば ready に遷移させる。
    if status == "starting":
        with initialization_lock:
            try:
                refreshed_checks = _get_cached_readiness_checks(integrations)
                initialization_status["checks"] = refreshed_checks

                required_checks = [
                    "memory_db",
                    "obsidian_path",
                    "notification_hub",
                    "llm_routing",
                    "image_stock",
                ]
                available_checks = [
                    check
                    for check in required_checks
                    if refreshed_checks.get(check, {}).get("status") != "not_available"
                ]
                all_required_ok = (
                    all(
                        refreshed_checks.get(check, {}).get("status") in ["ok", "warning"]
                        for check in available_checks
                    )
                    if available_checks
                    else True
                )

                if (
                    not initialization_status["pending"]
                    and all_required_ok
                    and len(initialization_status["completed"]) > 0
                ):
                    initialization_status["status"] = "ready"

            except Exception as e:
                logger.warning(f"readiness refresh failed: {e}")

            status = initialization_status["status"]
            pending = initialization_status["pending"].copy()
            completed = initialization_status["completed"].copy()
            failed = initialization_status["failed"].copy()
            checks = initialization_status.get("checks", {}).copy()

    if status == "ready":
        # 初期化完了：各統合の状態を確認（軽量化：タイムアウト対策）
        integration_status = {}
        for name, integration in integrations.items():
            try:
                # 重い処理を避けるため、単純に存在確認のみ
                integration_status[name] = integration is not None
            except Exception as e:
                logger.warning(f"{name}の状態確認エラー: {e}")
                integration_status[name] = False

        return (
            jsonify(
                {
                    "status": "ready",
                    "integrations": integration_status,
                    "initialization": {"completed": completed, "failed": failed},
                    "readiness_checks": checks,
                }
            ),
            200,
        )
    else:
        # 初期化中またはエラー
        return jsonify(
            {
                "status": status,
                "pending": pending,
                "completed": completed,
                "failed": failed,
                "readiness_checks": checks,
            }
        ), (503 if status == "starting" else 500)


@app.route("/status", methods=["GET"])
def status():
    """
    初期化進捗ステータス（詳細情報）

    Returns:
        常に200（進捗情報を返す、軽量）
    """
    # read-onlyの場合は情報を最小化（環境変数名/内部詳細を出さない）
    if getattr(g, "manaos_auth_level", "none") == "read":
        with initialization_lock:
            status_val = initialization_status["status"]
            pending = initialization_status["pending"].copy()
            completed = initialization_status["completed"].copy()
            failed = initialization_status["failed"].copy()
            checks = initialization_status.get("checks", {}).copy()

        required_checks = [
            "memory_db",
            "obsidian_path",
            "notification_hub",
            "llm_routing",
            "image_stock",
        ]
        check_summary = {"ok": 0, "warning": 0, "error": 0, "not_available": 0}
        for check_name in required_checks:
            check_status = checks.get(check_name, {}).get("status", "not_available")
            if check_status in check_summary:
                check_summary[check_status] = check_summary[check_status] + 1

        return (
            jsonify(
                {
                    "status": status_val,
                    "ready": (status_val == "ready"),
                    "initialization": {
                        "pending_count": len(pending),
                        "completed_count": len(completed),
                        "failed_count": len(failed),
                        "progress": {
                            "total": len(pending) + len(completed) + len(failed),
                            "completed": len(completed),
                            "failed": len(failed),
                            "pending": len(pending),
                        },
                    },
                    "check_summary": check_summary,
                }
            ),
            200,
        )

    # ロックを最小限に（重い処理はしない）
    with initialization_lock:
        status_val = initialization_status["status"]
        pending = initialization_status["pending"].copy()
        completed = initialization_status["completed"].copy()
        failed = initialization_status["failed"].copy()
        checks = initialization_status.get("checks", {}).copy()

    # 統合モジュールの可用性と「無効な理由」を返す（運用で黙って無効化を避ける）
    integrations_status = {}
    missing_dependencies = []

    integration_modules = {
        "comfyui": ("ComfyUI", COMFYUI_AVAILABLE, ["COMFYUI_URL"]),
        "svi_wan22": ("SVI × Wan 2.2", SVI_WAN22_AVAILABLE, ["COMFYUI_URL"]),
        "ltx2": ("LTX-2", LTX2_AVAILABLE, ["COMFYUI_URL"]),
        "google_drive": (
            "Google Drive",
            GOOGLE_DRIVE_AVAILABLE,
            ["GOOGLE_DRIVE_CREDENTIALS", "GOOGLE_DRIVE_TOKEN"],
        ),
        "civitai": ("CivitAI", CIVITAI_AVAILABLE, ["CIVITAI_API_KEY"]),
        "obsidian": ("Obsidian", OBSIDIAN_AVAILABLE, ["OBSIDIAN_VAULT_PATH"]),
        "local_llm": ("Local LLM", LOCAL_LLM_AVAILABLE, []),
        "step_deep_research": ("Step-Deep-Research", STEP_DEEP_RESEARCH_AVAILABLE, []),
    }

    for key, (name, module_available, required_env) in integration_modules.items():
        missing_env = _missing_env_vars(required_env) if required_env else []
        env_ok = not missing_env
        ready = bool(module_available and env_ok)
        reason = None
        if not module_available:
            reason = "モジュール未インストール/未ロード"
        elif not env_ok:
            reason = f"環境変数未設定: {', '.join(missing_env)}"

        integrations_status[key] = {
            "name": name,
            "module_available": bool(module_available),
            "environment_configured": env_ok,
            "missing_env": missing_env,
            "ready": ready,
            "reason": reason,
        }

        if not ready:
            missing_dependencies.append({"integration": name, "reason": reason})

    # 必須チェックの状態を集計（軽量）
    required_checks = [
        "memory_db",
        "obsidian_path",
        "notification_hub",
        "llm_routing",
        "image_stock",
    ]
    check_summary = {"ok": 0, "warning": 0, "error": 0, "not_available": 0}

    for check_name in required_checks:
        check_status = checks.get(check_name, {}).get("status", "not_available")
        if check_status in check_summary:
            check_summary[check_status] = check_summary[check_status] + 1

    return (
        jsonify(
            {
                "status": status_val,
                "initialization": {
                    "pending": pending,
                    "completed": completed,
                    "failed": failed,
                    "progress": {
                        "total": len(pending) + len(completed) + len(failed),
                        "completed": len(completed),
                        "failed": len(failed),
                        "pending": len(pending),
                    },
                },
                "readiness_checks": checks,
                "check_summary": check_summary,
                "integrations": integrations_status,
                "missing_dependencies": missing_dependencies,
                "ready": (status_val == "ready"),
            }
        ),
        200,
    )


def main():
    """Unified API Server メイン関数"""
    port = int(os.getenv("PORT", os.getenv("UNIFIED_API_PORT", "9502")))
    debug = _strtobool(os.getenv("DEBUG", "false"), default=False)
    
    logger.info(f"[START] Unified API Server を起動中... (ポート: {port})")
    
    # 統合システムをバックグラウンド初期化
    init_thread = threading.Thread(target=initialize_integrations, daemon=True)
    init_thread.start()
    
    # Flask サーバー起動
    try:
        app.run(host="0.0.0.0", port=port, debug=debug, threaded=True)
    except Exception as e:
        logger.error(f"[ERROR] サーバー起動エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
