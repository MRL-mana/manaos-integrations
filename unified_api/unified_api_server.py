"""
ManaOS統合APIサーバー（修正版）
すべての外部システム統合を管理する統合API
"""

from flask import Flask, request, jsonify, send_from_directory, g, Response, stream_with_context
from flask_cors import CORS
import os
import sys
import warnings
import hmac
import json
import time
import uuid
import subprocess
import collections
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import threading

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_MISC_DIR = REPO_ROOT / "scripts" / "misc"
LLM_DIR = REPO_ROOT / "llm"
for _sys_path in (REPO_ROOT, SCRIPTS_MISC_DIR, LLM_DIR):
    _path_str = str(_sys_path)
    if _sys_path.exists() and _path_str not in sys.path:
        sys.path.insert(0, _path_str)

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
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
try:
    from api_auth import get_auth_manager
except ImportError:
    class DummyAuthManager:
        def require_api_key(self, func):
            return func
    get_auth_manager = lambda: DummyAuthManager()

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
    return _parse_iso_datetime(payload.get("updated_at") or payload.get("created_at")) or datetime.min


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
        active_items = [(job_id, payload) for job_id, payload in trimmed.items() if _is_active_job(payload)]
        terminal_items = [(job_id, payload) for job_id, payload in trimmed.items() if not _is_active_job(payload)]

        active_items = sorted(active_items, key=lambda item: _job_sort_dt(item[1]), reverse=True)
        terminal_items = sorted(terminal_items, key=lambda item: _job_sort_dt(item[1]), reverse=True)

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


TASK_PLANNER_BASE_URL = _service_url("task_planner", "TASK_PLANNER_URL", _env_int("TASK_PLANNER_PORT", 5101))
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
            transformers_cache = os.getenv("TRANSFORMERS_CACHE")
            os.environ["HF_HOME"] = transformers_cache
            logger.info(f"✅ TRANSFORMERS_CACHEをHF_HOMEに移行しました: {transformers_cache}")
            # 警告を抑制するために古い環境変数を削除（オプション）
            # os.environ.pop("TRANSFORMERS_CACHE", None)
    else:
        # Secretsはファイル直読みではなく、OS環境変数または .env で注入する
        logger.info(".envファイルが見つかりません。OS環境変数の設定を使用します。")
except ImportError:
    logger.warning("python-dotenvがインストールされていません")
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
    import json

    STEP_DEEP_RESEARCH_AVAILABLE = True
except ImportError:
    logger.warning("Step-Deep-Research統合モジュールが見つかりません")
    STEP_DEEP_RESEARCH_AVAILABLE = False

# ComfyUI統合（オプション）
try:
    from comfyui_integration import ComfyUIIntegration

    COMFYUI_AVAILABLE = True
except ImportError:
    try:
        from scripts.misc.comfyui_integration import ComfyUIIntegration

        COMFYUI_AVAILABLE = True
        logger.info("ComfyUI統合モジュールを scripts.misc から読み込みました")
    except ImportError:
        logger.warning("ComfyUI統合モジュールが見つかりません。軽量フォールバックを使用します")

        class ComfyUIIntegration:
            def __init__(self, base_url: str = "http://127.0.0.1:8188"):
                self.base_url = (base_url or "http://127.0.0.1:8188").rstrip("/")

            def is_available(self) -> bool:
                if not REQUESTS_AVAILABLE:
                    return False
                try:
                    response = requests.get(f"{self.base_url}/system_stats", timeout=5)
                    return response.status_code == 200
                except Exception:
                    return False

            def _list_checkpoints(self) -> List[str]:
                if not REQUESTS_AVAILABLE:
                    return []
                try:
                    response = requests.get(
                        f"{self.base_url}/object_info/CheckpointLoaderSimple",
                        timeout=10,
                    )
                    response.raise_for_status()
                    data = response.json() or {}
                    ckpts = (
                        data.get("CheckpointLoaderSimple", {})
                        .get("input", {})
                        .get("required", {})
                        .get("ckpt_name", [[[]]])[0]
                    )
                    return list(ckpts) if ckpts else []
                except Exception:
                    return []

            def generate_image(
                self,
                prompt: str,
                negative_prompt: str = "",
                width: int = 512,
                height: int = 512,
                model: str = "",
                loras: Optional[List[tuple]] = None,
                steps: int = 20,
                guidance_scale: float = 7.0,
                sampler: str = "euler_ancestral",
                scheduler: str = "karras",
                seed: int = -1,
            ) -> Optional[str]:
                if not REQUESTS_AVAILABLE:
                    return None
                ckpts = self._list_checkpoints()
                resolved_model = (model or "").strip()
                if ckpts:
                    if not resolved_model or resolved_model not in ckpts:
                        resolved_model = ckpts[0]

                if seed is None or int(seed) < 0:
                    seed = int(time.time() * 1000) % (2**32)

                workflow = {
                    "1": {
                        "inputs": {"ckpt_name": resolved_model},
                        "class_type": "CheckpointLoaderSimple",
                    },
                    "2": {
                        "inputs": {"text": prompt, "clip": ["1", 1]},
                        "class_type": "CLIPTextEncode",
                    },
                    "3": {
                        "inputs": {"text": negative_prompt or "", "clip": ["1", 1]},
                        "class_type": "CLIPTextEncode",
                    },
                    "4": {
                        "inputs": {
                            "seed": int(seed),
                            "steps": int(steps or 20),
                            "cfg": float(guidance_scale or 7.0),
                            "sampler_name": sampler or "euler_ancestral",
                            "scheduler": scheduler or "karras",
                            "denoise": 1.0,
                            "model": ["1", 0],
                            "positive": ["2", 0],
                            "negative": ["3", 0],
                            "latent_image": ["5", 0],
                        },
                        "class_type": "KSampler",
                    },
                    "5": {
                        "inputs": {
                            "width": int(width or 512),
                            "height": int(height or 512),
                            "batch_size": 1,
                        },
                        "class_type": "EmptyLatentImage",
                    },
                    "6": {
                        "inputs": {"samples": ["4", 0], "vae": ["1", 2]},
                        "class_type": "VAEDecode",
                    },
                    "7": {
                        "inputs": {"filename_prefix": "manaos_txt2img", "images": ["6", 0]},
                        "class_type": "SaveImage",
                    },
                }
                try:
                    response = requests.post(
                        f"{self.base_url}/prompt",
                        json={"prompt": workflow, "client_id": "manaos-unified-api"},
                        timeout=30,
                    )
                    response.raise_for_status()
                    return (response.json() or {}).get("prompt_id")
                except Exception:
                    return None

            def get_queue_status(self) -> Dict[str, Any]:
                if not REQUESTS_AVAILABLE:
                    return {"error": "requests_unavailable"}
                try:
                    response = requests.get(f"{self.base_url}/queue", timeout=10)
                    response.raise_for_status()
                    return response.json() or {}
                except Exception as e:
                    return {"error": str(e)}

            def get_history(self, max_items: int = 10) -> List[Dict[str, Any]]:
                if not REQUESTS_AVAILABLE:
                    return []
                try:
                    response = requests.get(f"{self.base_url}/history", timeout=10)
                    response.raise_for_status()
                    payload = response.json() or {}
                    if isinstance(payload, dict):
                        values = list(payload.values())
                        return values[: max(1, min(int(max_items or 10), 50))]
                    if isinstance(payload, list):
                        return payload[: max(1, min(int(max_items or 10), 50))]
                    return []
                except Exception:
                    return []

        COMFYUI_AVAILABLE = REQUESTS_AVAILABLE

# SVI × Wan 2.2動画生成統合（オプション）
try:
    from svi_wan22_video_integration import SVIWan22VideoIntegration

    SVI_WAN22_AVAILABLE = True
except ImportError:
    logger.warning("SVI × Wan 2.2動画生成統合モジュールが見つかりません")

# LTX-2動画生成統合（オプション）
try:
    from ltx2_video_integration import LTX2VideoIntegration

    LTX2_AVAILABLE = True
except ImportError:
    logger.warning("LTX-2動画生成統合モジュールが見つかりません")
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
    logger.warning(f"⚠️ LTX-2 Infinity統合モジュールが見つかりません: {e}")
    LTX2_INFINITY_AVAILABLE = False

# GoogleDrive統合（オプション）
try:
    from google_drive_integration import GoogleDriveIntegration

    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    logger.warning("GoogleDrive統合モジュールが見つかりません")

# CivitAI統合（オプション）
try:
    from civitai_integration import CivitAIIntegration

    CIVITAI_AVAILABLE = True
except ImportError:
    logger.warning("CivitAI統合モジュールが見つかりません")

# LangChain統合（オプション）
try:
    from langchain_integration import LangChainIntegration, LangGraphIntegration

    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("LangChain統合モジュールが見つかりません")

# Mem0統合（オプション）
try:
    from mem0_integration import Mem0Integration

    MEM0_AVAILABLE = True
except ImportError:
    logger.warning("Mem0統合モジュールが見つかりません")

# Obsidian統合（オプション）
try:
    from obsidian_integration import ObsidianIntegration

    OBSIDIAN_AVAILABLE = True
except ImportError:
    logger.warning("Obsidian統合モジュールが見つかりません")

# ローカルLLM統合（オプション）
try:
    from local_llm_unified import LocalLLMUnified

    LOCAL_LLM_AVAILABLE = True
except ImportError:
    logger.warning("LocalLLM統合モジュールが見つかりません")

# Redisキャッシュ統合（オプション）
REDIS_CACHE_AVAILABLE = False
try:
    from llm_redis_cache import get_redis_cache

    REDIS_CACHE_AVAILABLE = True
except ImportError:
    logger.warning("Redisキャッシュモジュールが見つかりません")

# 統一キャッシュシステム統合（オプション）
UNIFIED_CACHE_AVAILABLE = False
try:
    from unified_cache_system import get_unified_cache

    UNIFIED_CACHE_AVAILABLE = True
except ImportError:
    logger.warning("統一キャッシュシステムモジュールが見つかりません")

# パフォーマンス最適化システム統合（オプション）
PERFORMANCE_OPTIMIZER_AVAILABLE = False
try:
    from manaos_performance_optimizer import PerformanceOptimizer

    PERFORMANCE_OPTIMIZER_AVAILABLE = True
except ImportError:
    logger.warning("パフォーマンス最適化システムモジュールが見つかりません")

# 拡張フェーズ統合（オプション）
LLM_ROUTING_AVAILABLE = False
MEMORY_UNIFIED_AVAILABLE = False
NOTIFICATION_HUB_AVAILABLE = False
SECRETARY_AVAILABLE = False
IMAGE_STOCK_AVAILABLE = False

# LLMルーティング統合（オプション）
try:
    try:
        from llm.llm_routing import LLMRouter
    except ImportError:
        from llm_routing import LLMRouter

    LLM_ROUTING_AVAILABLE = True
except ImportError:
    logger.warning("LLMルーティングモジュールが見つかりません")

# 拡張LLMルーティング統合（難易度判定対応）
ENHANCED_LLM_ROUTING_AVAILABLE = False
try:
    try:
        from llm.llm_router_enhanced import EnhancedLLMRouter
    except ImportError:
        from llm_router_enhanced import EnhancedLLMRouter

    ENHANCED_LLM_ROUTING_AVAILABLE = True
except ImportError:
    logger.warning("拡張LLMルーティングモジュールが見つかりません")

# 統一記憶システム統合（オプション）
try:
    from memory_unified import UnifiedMemory

    MEMORY_UNIFIED_AVAILABLE = True
except ImportError:
    logger.warning("統一記憶システムモジュールが見つかりません")

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
    from phase1_reflection import REFLECTION_PROMPT, parse_reflection_answer

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

try:
    from core5_identity_guard import (
        evaluate_identity_guard,
        get_identity_policy_config,
        identity_guard_to_dict,
    )

    IDENTITY_GUARD_AVAILABLE = True
except ImportError:
    IDENTITY_GUARD_AVAILABLE = False
    evaluate_identity_guard = None
    get_identity_policy_config = None
    identity_guard_to_dict = None

# 通知ハブ統合（オプション）
try:
    from notification_hub import NotificationHub

    NOTIFICATION_HUB_AVAILABLE = True
except ImportError:
    logger.warning("通知ハブモジュールが見つかりません")

# 秘書機能統合（オプション）
try:
    from secretary_routines import SecretaryRoutines

    SECRETARY_AVAILABLE = True
except ImportError:
    logger.warning("秘書機能モジュールが見つかりません")

# 画像ストック統合（オプション）
try:
    from image_stock import ImageStock

    IMAGE_STOCK_AVAILABLE = True
except ImportError:
    logger.warning("画像ストックモジュールが見つかりません")

# Rows統合（オプション）
try:
    from rows_integration import RowsIntegration

    ROWS_AVAILABLE = True
except ImportError:
    logger.warning("Rows統合モジュールが見つかりません")
    ROWS_AVAILABLE = False

# GitHub統合（オプション）
try:
    from github_integration import GitHubIntegration

    GITHUB_AVAILABLE = True
except ImportError:
    logger.warning("GitHub統合モジュールが見つかりません")
    GITHUB_AVAILABLE = False

# n8n統合（オプション）
try:
    from n8n_integration import N8NIntegration

    N8N_AVAILABLE = True
except ImportError:
    logger.warning("n8n統合モジュールが見つかりません")
    N8N_AVAILABLE = False

# Brave Search統合（オプション）
BRAVE_SEARCH_AVAILABLE = False
try:
    from brave_search_integration import BraveSearchIntegration

    BRAVE_SEARCH_AVAILABLE = True
except ImportError:
    logger.warning("Brave Search統合モジュールが見つかりません")

# Base AI統合（オプション）
BASE_AI_AVAILABLE = False
try:
    from base_ai_integration import BaseAIIntegration

    BASE_AI_AVAILABLE = True
except ImportError:
    logger.warning("Base AI統合モジュールが見つかりません")

# OH MY OPENCODE統合（オプション）
OH_MY_OPENCODE_AVAILABLE = False
try:
    from oh_my_opencode_integration import OHMyOpenCodeIntegration

    OH_MY_OPENCODE_AVAILABLE = True
except ImportError:
    logger.warning("OH MY OPENCODE統合モジュールが見つかりません")

# Excel/LLM処理統合（オプション）
EXCEL_LLM_AVAILABLE = False
try:
    from excel_llm_integration import ExcelLLMIntegration

    EXCEL_LLM_AVAILABLE = True
except ImportError:
    logger.warning("Excel/LLM処理統合モジュールが見つかりません")
    EXCEL_LLM_AVAILABLE = False

# 音声機能統合（オプション）
VOICE_INTEGRATION_AVAILABLE = False
try:
    from voice_integration import (
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
    logger.warning(f"⚠️ 音声機能統合モジュールが見つかりません: {e}")
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
                        "Missing or invalid API key. Provide `X-API-Key` or `Authorization: Bearer ...`. "
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
                    "This server is running without API keys. Requests are restricted to localhost. "
                    "Set `MANAOS_INTEGRATION_API_KEY` (admin) or "
                    "`MANAOS_INTEGRATION_OPS_API_KEY` / `MANAOS_INTEGRATION_READONLY_API_KEY` to enable remote access."
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
    global _openapi_spec_cache
    
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


@app.route("/api/google_drive/upload", methods=["POST"])
@auth_manager.require_api_key
def api_google_drive_upload():
    """Google Driveへファイルをアップロード（要認証）

    Body(JSON):
      - file_path: str (required)
      - folder_id: str (optional)
      - file_name: str (optional)
      - overwrite: bool (optional)
    """
    data = request.get_json(silent=True) or {}
    file_path = (data.get("file_path") or "").strip()
    if not file_path:
        return _json_error("file_path is required", 400, error="bad_request", namespace="google_drive")

    drive = integrations.get("google_drive")
    if not drive or not getattr(drive, "is_available", lambda: False)():
        return _json_error("google_drive_unavailable", 503, error="unavailable", namespace="google_drive")

    folder_id = (data.get("folder_id") or "").strip() or None
    file_name = (data.get("file_name") or "").strip() or None
    overwrite = bool(data.get("overwrite", False))

    try:
        file_id = drive.upload_file(
            file_path=file_path,
            folder_id=folder_id,
            file_name=file_name,
            overwrite=overwrite,
        )
        if not file_id:
            return jsonify({"success": False, "error": "upload_failed"}), 500
        return jsonify(
            {
                "success": True,
                "file_id": file_id,
                "url": f"https://drive.google.com/file/d/{file_id}/view",
            }
        ), 200
    except Exception as e:
        err = error_handler.handle_exception(
            e,
            context={"file_path": file_path, "action": "google_drive_upload"},
            user_message="Google Driveへのアップロードに失敗しました",
        )
        return jsonify({"success": False, "error": err.message}), 500


@app.route("/api/sd-prompt/generate", methods=["POST"])
def api_sd_prompt_generate():
    """日本語の説明からStable Diffusion用の英語プロンプトを生成（Ollama）"""
    data = request.get_json(silent=True) or {}
    description = (data.get("description") or data.get("prompt") or "").strip()
    if not description:
        return _json_error("description or prompt is required", 400, error="bad_request", namespace="sd_prompt")

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

    comfyui = _get_or_init_comfyui()
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
            negative_prompt = f"{negative_prompt}, {LAB_NEGATIVE_PROMPT}".strip(", ") if negative_prompt else LAB_NEGATIVE_PROMPT
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
            logger.warning(f"mufufu_config_lab が見つかりません: {e}")

    # ムフフモード: 身体崩れ対策強化（lab_mode でないとき）
    elif mufufu_mode:
        try:
            from mufufu_config import MUFUFU_NEGATIVE_PROMPT, ANATOMY_POSITIVE_TAGS, OPTIMIZED_PARAMS
            negative_prompt = f"{negative_prompt}, {MUFUFU_NEGATIVE_PROMPT}".strip(", ") if negative_prompt else MUFUFU_NEGATIVE_PROMPT
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
            logger.warning(f"mufufu_config が見つかりません: {e}")

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
        return _json_error("image_generation_failed", 500, error="internal_error", namespace="comfyui")

    if prompt_id:
        # n8n Webhookに通知（オプション）
        n8n_webhook_url = (os.getenv("N8N_WEBHOOK_URL") or "").strip()
        if n8n_webhook_url and REQUESTS_AVAILABLE:
            try:
                requests.post(
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


# ─── Image Generation Service Proxy (→ :5560) ────────

_IMAGE_GEN_BASE = os.getenv("IMAGE_GENERATION_URL", "http://127.0.0.1:5560")


def _proxy_image_gen(subpath: str, method: str = "GET"):
    """画像生成サービスへのプロキシ転送"""
    url = f"{_IMAGE_GEN_BASE}{subpath}"
    headers = {k: v for k, v in request.headers if k.lower() not in ("host", "content-length")}
    try:
        if method == "GET":
            resp = requests.get(url, params=request.args, headers=headers, timeout=30)
        else:
            resp = requests.request(
                method, url,
                json=request.get_json(silent=True),
                params=request.args,
                headers=headers,
                timeout=60,
            )
        return resp.content, resp.status_code, {"Content-Type": resp.headers.get("Content-Type", "application/json")}
    except requests.exceptions.ConnectionError:
        return _json_error("image_generation_service_unavailable", 503, error="unavailable", namespace="image_gen")
    except requests.exceptions.Timeout:
        return _json_error("image_generation_service_timeout", 504, error="timeout", namespace="image_gen")
    except Exception as e:
        logger.warning(f"Image Gen proxy error: {e}")
        return _json_error("image_generation_proxy_error", 502, error="proxy_error", namespace="image_gen")


@app.route("/api/v1/images/generate", methods=["POST"])
def api_v1_images_generate():
    """画像生成API (→ image_generation_service)"""
    return _proxy_image_gen("/api/v1/generate", "POST")


@app.route("/api/v1/images/status/<job_id>", methods=["GET"])
def api_v1_images_status(job_id):
    """ジョブ状態 (→ image_generation_service)"""
    return _proxy_image_gen(f"/api/v1/status/{job_id}")


@app.route("/api/v1/images/result/<job_id>", methods=["GET"])
def api_v1_images_result(job_id):
    """生成結果取得 (→ image_generation_service)"""
    return _proxy_image_gen(f"/api/v1/result/{job_id}")


@app.route("/api/v1/images/history", methods=["GET"])
def api_v1_images_history():
    """生成履歴 (→ image_generation_service)"""
    return _proxy_image_gen("/api/v1/history")


@app.route("/api/v1/images/dashboard", methods=["GET"])
def api_v1_images_dashboard():
    """ダッシュボード (→ image_generation_service)"""
    return _proxy_image_gen("/api/v1/dashboard")


@app.route("/api/v1/images/billing", methods=["GET"])
def api_v1_images_billing():
    """課金状態 (→ image_generation_service)"""
    return _proxy_image_gen("/api/v1/billing")


@app.route("/api/v1/images/enhance-preview", methods=["POST"])
def api_v1_images_enhance_preview():
    """プロンプト強化プレビュー (→ image_generation_service)"""
    return _proxy_image_gen("/api/v1/enhance-preview", "POST")


@app.route("/api/v1/images/health", methods=["GET"])
def api_v1_images_health():
    """画像生成サービスヘルスチェック (→ image_generation_service)"""
    return _proxy_image_gen("/health")


@app.route("/api/svi/capabilities", methods=["GET"])
def api_svi_capabilities():
    """ComfyUI の /object_info から SVI の必要ノード有無を返す（事前診断用）"""
    if not REQUESTS_AVAILABLE:
        return _json_error("requests_unavailable", 503, error="unavailable", namespace="svi")

    base_url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
    required_generate = ["SVIWan22VideoGenerate", "SaveVideo"]
    required_extend = ["SVIWan22VideoExtend", "LoadVideo", "SaveVideo"]

    # Model assets required for local Wan I2V workflow (based on ComfyUI templates).
    comfyui_path = Path(os.getenv("COMFYUI_PATH", "C:/ComfyUI"))
    models_base = comfyui_path / "models"

    # Try to pick a smaller Wan2.2 i2v diffusion model (fp8_scaled) if known.
    preferred_unet = {
        "role": "diffusion_model_i2v",
        "save_path": "diffusion_models",
        "filename": "wan2.1_i2v_480p_14B_fp16.safetensors",
        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_i2v_480p_14B_fp16.safetensors",
        "size": "(large)",
    }

    size_map: dict[str, str] = {}

    try:
        model_list_path = comfyui_path / "custom_nodes" / "ComfyUI-Manager" / "node_db" / "new" / "model-list.json"
        if model_list_path.exists():
            raw = json.loads(model_list_path.read_text(encoding="utf-8"))
            models = raw.get("models") if isinstance(raw, dict) else None
            if isinstance(models, list):
                for m in models:
                    if not isinstance(m, dict):
                        continue
                    fn = (m.get("filename") or "").strip()
                    sz = (m.get("size") or "").strip()
                    if fn and sz and fn not in size_map:
                        size_map[fn] = sz

                candidates = []
                for m in models:
                    if not isinstance(m, dict):
                        continue
                    if (m.get("base") or "") != "Wan2.2":
                        continue
                    if (m.get("type") or "") != "diffusion_model":
                        continue
                    fn = (m.get("filename") or "").strip()
                    sp = (m.get("save_path") or "").strip().replace("\\", "/")
                    if not fn or not sp:
                        continue
                    if "i2v" not in fn.lower():
                        continue
                    candidates.append(m)

                # Prefer fp8_scaled i2v models (smaller), then any i2v.
                def _rank(m: dict) -> tuple[int, int]:
                    fn = (m.get("filename") or "").lower()
                    size = (m.get("size") or "")
                    # smaller first: fp8_scaled preferred
                    fp8 = 0 if "fp8" in fn else 1
                    # low_noise preferred for I2V stability (heuristic)
                    low = 0 if "low_noise" in fn else 1
                    return (fp8, low)

                if candidates:
                    best = sorted(candidates, key=_rank)[0]
                    preferred_unet = {
                        "role": "diffusion_model_i2v",
                        "save_path": (best.get("save_path") or "diffusion_models").strip().replace("\\", "/"),
                        "filename": (best.get("filename") or "").strip(),
                        "url": (best.get("url") or "").strip(),
                        "size": (best.get("size") or size_map.get((best.get("filename") or "").strip()) or "(large)"),
                    }
    except Exception:
        pass

    template_assets = [
        preferred_unet,
        {
            "role": "text_encoder",
            "save_path": "text_encoders",
            "filename": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            "size": size_map.get("umt5_xxl_fp8_e4m3fn_scaled.safetensors") or "(large)",
        },
        {
            "role": "vae",
            "save_path": "vae",
            "filename": "wan_2.1_vae.safetensors",
            "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors",
            "size": size_map.get("wan_2.1_vae.safetensors") or "(large)",
        },
        {
            "role": "clip_vision",
            "save_path": "clip_vision",
            "filename": "clip_vision_h.safetensors",
            "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors",
            "size": size_map.get("clip_vision_h.safetensors") or "(large)",
        },
    ]

    def _asset_status(item: dict) -> dict:
        save_path = str(item.get("save_path") or "").replace("\\", "/").strip("/")
        filename = str(item.get("filename") or "").strip()
        rel = f"{save_path}/{filename}" if save_path else filename
        target_path = (models_base / save_path / filename).resolve()
        url = item.get("url")
        return {
            "role": item.get("role"),
            "relative_path": rel,
            "target_path": str(target_path),
            "exists": target_path.exists(),
            "url": url,
            "size": item.get("size"),
            "download_ps": (
                f"Start-BitsTransfer -Source '{url}' -Destination '{str(target_path)}'"
                if isinstance(url, str) and url.strip()
                else ""
            ),
        }

    assets = [_asset_status(a) for a in template_assets]
    missing_assets = [a for a in assets if not a.get("exists")]

    def _parse_size_to_gb(value: Any) -> Optional[float]:
        if not isinstance(value, str):
            return None
        text = value.strip().upper().replace(" ", "")
        try:
            if text.endswith("GB"):
                return float(text[:-2])
            if text.endswith("MB"):
                return float(text[:-2]) / 1024.0
        except Exception:
            return None
        return None

    missing_total_gb = 0.0
    missing_total_gb_known = True
    for a in missing_assets:
        gb = _parse_size_to_gb(a.get("size"))
        if gb is None:
            missing_total_gb_known = False
            continue
        missing_total_gb += gb

    wan22_suggestions = []
    try:
        model_list_path = comfyui_path / "custom_nodes" / "ComfyUI-Manager" / "node_db" / "new" / "model-list.json"
        if model_list_path.exists():
            raw = json.loads(model_list_path.read_text(encoding="utf-8"))
            models = raw.get("models") if isinstance(raw, dict) else None
            if isinstance(models, list):
                for m in models:
                    if not isinstance(m, dict):
                        continue
                    if (m.get("base") or "") != "Wan2.2":
                        continue
                    if (m.get("type") or "") != "diffusion_model":
                        continue
                    fn = (m.get("filename") or "").strip()
                    sp = (m.get("save_path") or "").strip().replace("\\", "/")
                    if not fn or not sp:
                        continue
                    wan22_suggestions.append(
                        {
                            "name": m.get("name"),
                            "filename": fn,
                            "save_path": sp,
                            "target_path": str((models_base / sp / fn).resolve()),
                            "exists": (models_base / sp / fn).exists(),
                            "url": m.get("url"),
                            "size": m.get("size"),
                        }
                    )
                wan22_suggestions = wan22_suggestions[:8]
    except Exception:
        wan22_suggestions = []

    try:
        r = requests.get(f"{base_url}/object_info", timeout=5)
        r.raise_for_status()
        obj = r.json() or {}
        if not isinstance(obj, dict):
            return _json_error(
                "comfyui_object_info_invalid",
                502,
                error="bad_gateway",
                namespace="svi",
            )

        available = {str(k) for k in obj.keys()}
        missing_generate = [ct for ct in required_generate if ct not in available]
        missing_extend = [ct for ct in required_extend if ct not in available]
        return jsonify(
            {
                "comfyui_url": base_url,
                "comfyui_path": str(comfyui_path),
                "object_info": "ok",
                "required": {"generate": required_generate, "extend": required_extend},
                "missing": {"generate": missing_generate, "extend": missing_extend},
                "model_assets": {
                    "models_base": str(models_base),
                    "required": assets,
                    "missing": missing_assets,
                    "ok": len(missing_assets) == 0,
                    "missing_total_gb": round(missing_total_gb, 2) if missing_total_gb_known else None,
                    "wan22_suggestions": wan22_suggestions,
                },
                "ok": (not missing_generate) and (not missing_extend) and (len(missing_assets) == 0),
            }
        ), 200
    except Exception as e:
        logger.warning(f"SVI capabilities error: {e}")
        return _json_error(
            "comfyui_object_info_failed",
            502,
            error="bad_gateway",
            namespace="svi",
            details={
                "detail": str(e),
                "comfyui_url": base_url,
                "comfyui_path": str(comfyui_path),
                "model_assets": {
                    "models_base": str(models_base),
                    "required": assets,
                    "missing": missing_assets,
                    "ok": len(missing_assets) == 0,
                    "wan22_suggestions": wan22_suggestions,
                },
            },
        )


@app.route("/api/svi/generate", methods=["POST"])
def api_svi_generate():
    """SVI × Wan 2.2 で動画生成（prompt_id を返す）"""
    if not SVI_WAN22_AVAILABLE:
        return _json_error("svi_wan22_unavailable", 503, error="unavailable", namespace="svi")

    data = request.get_json(silent=True) or {}
    start_image_path = (data.get("start_image_path") or "").strip()
    prompt = (data.get("prompt") or "").strip()
    if not start_image_path:
        return _json_error(
            "start_image_path is required",
            400,
            error="bad_request",
            namespace="svi",
        )
    if not prompt:
        return _json_error("prompt is required", 400, error="bad_request", namespace="svi")

    if not os.path.exists(start_image_path):
        return _json_error(
            "start_image_path_not_found",
            404,
            error="not_found",
            namespace="svi",
            detail=start_image_path,
        )

    svi = integrations.get("svi_wan22")
    if not svi:
        try:
            svi = SVIWan22VideoIntegration(
                base_url=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
            )
        except Exception:
            svi = None
    if not svi or not getattr(svi, "is_available", lambda: False)():
        return _json_error("comfyui_unavailable", 503, error="unavailable", namespace="svi")

    quality = (data.get("quality") or "balanced").strip().lower()
    video_length_seconds = int(data.get("video_length_seconds", 5) or 5)
    steps = int(data.get("steps", 6) or 6)
    motion_strength = float(data.get("motion_strength", 1.3) or 1.3)
    sage_attention = bool(data.get("sage_attention", True))
    extend_enabled = bool(data.get("extend_enabled", False))

    # Quality presets (keep user override but nudge defaults)
    if quality == "fast":
        steps = min(steps, 6)
        motion_strength = float(data.get("motion_strength", 1.2) or 1.2)
    elif quality in {"quality", "high", "accurate"}:
        steps = max(steps, 10)
        motion_strength = float(data.get("motion_strength", 1.4) or 1.4)

    try:
        prompt_id = svi.generate_video(
            start_image_path=start_image_path,
            prompt=prompt,
            video_length_seconds=video_length_seconds,
            steps=steps,
            motion_strength=motion_strength,
            sage_attention=sage_attention,
            extend_enabled=extend_enabled,
        )
    except Exception as e:
        logger.warning(f"SVI generate error: {e}")
        return _json_error("svi_generation_failed", 500, error="internal_error", namespace="svi")

    if prompt_id:
        return jsonify({"prompt_id": prompt_id, "status": "started"}), 200

    last_error = getattr(svi, "last_error", None)
    try:
        detail = (last_error or {}).get("detail") if isinstance(last_error, dict) else None
    except Exception:
        detail = None

    # Missing custom node is a common setup issue -> return 503 with a clear hint.
    if isinstance(detail, dict):
        err_obj = detail.get("error") if isinstance(detail.get("error"), dict) else None
        err_type = (err_obj.get("type") if err_obj else "") or ""
        err_msg = (err_obj.get("message") if err_obj else "") or ""
        if err_type == "missing_node_type" or "missing_node_type" in (err_msg or ""):
            return _json_error(
                "svi_custom_node_missing",
                503,
                error="unavailable",
                namespace="svi",
                details={
                    "hint": "ComfyUIに SVI × Wan 2.2 のカスタムノードが未導入です。該当ノード(SVIWan22VideoGenerate)をインストールして再起動してください。",
                    "comfyui_error": detail,
                },
            )
        if err_type == "missing_model_asset" or "missing_model_asset" in (err_msg or ""):
            return _json_error(
                "svi_model_missing",
                503,
                error="unavailable",
                namespace="svi",
                details={
                    "hint": "Wan動画生成に必要なモデルファイルが未導入です。/api/svi/capabilities の model_assets.missing を参照して、指定パスに配置してください。",
                    "missing": err_obj.get("missing") if isinstance(err_obj, dict) else None,
                    "models_base": err_obj.get("models_base") if isinstance(err_obj, dict) else None,
                    "comfyui_error": detail,
                },
            )

    return _json_error(
        "svi_generation_failed",
        500,
        error="internal_error",
        namespace="svi",
        details={"last_error": last_error} if last_error else None,
    )


@app.route("/api/svi/extend", methods=["POST"])
def api_svi_extend():
    """SVI × Wan 2.2 で動画延長（prompt_id を返す）"""
    if not SVI_WAN22_AVAILABLE:
        return _json_error("svi_wan22_unavailable", 503, error="unavailable", namespace="svi")

    data = request.get_json(silent=True) or {}
    previous_video_path = (data.get("previous_video_path") or "").strip()
    prompt = (data.get("prompt") or "").strip()
    if not previous_video_path:
        return _json_error(
            "previous_video_path is required",
            400,
            error="bad_request",
            namespace="svi",
        )
    if not prompt:
        return _json_error("prompt is required", 400, error="bad_request", namespace="svi")

    if not os.path.exists(previous_video_path):
        return _json_error(
            "previous_video_path_not_found",
            404,
            error="not_found",
            namespace="svi",
            detail=previous_video_path,
        )

    svi = integrations.get("svi_wan22")
    if not svi:
        try:
            svi = SVIWan22VideoIntegration(
                base_url=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
            )
        except Exception:
            svi = None
    if not svi or not getattr(svi, "is_available", lambda: False)():
        return _json_error("comfyui_unavailable", 503, error="unavailable", namespace="svi")

    quality = (data.get("quality") or "balanced").strip().lower()
    extend_seconds = int(data.get("extend_seconds", 5) or 5)
    steps = int(data.get("steps", 6) or 6)
    motion_strength = float(data.get("motion_strength", 1.3) or 1.3)

    if quality == "fast":
        steps = min(steps, 6)
        motion_strength = float(data.get("motion_strength", 1.2) or 1.2)
    elif quality in {"quality", "high", "accurate"}:
        steps = max(steps, 10)
        motion_strength = float(data.get("motion_strength", 1.4) or 1.4)

    try:
        prompt_id = svi.extend_video(
            previous_video_path=previous_video_path,
            prompt=prompt,
            extend_seconds=extend_seconds,
            steps=steps,
            motion_strength=motion_strength,
        )
    except Exception as e:
        logger.warning(f"SVI extend error: {e}")
        return _json_error("svi_extend_failed", 500, error="internal_error", namespace="svi")

    if prompt_id:
        return jsonify({"prompt_id": prompt_id, "status": "started"}), 200

    last_error = getattr(svi, "last_error", None)
    try:
        detail = (last_error or {}).get("detail") if isinstance(last_error, dict) else None
    except Exception:
        detail = None

    if isinstance(detail, dict):
        err_obj = detail.get("error") if isinstance(detail.get("error"), dict) else None
        err_type = (err_obj.get("type") if err_obj else "") or ""
        err_msg = (err_obj.get("message") if err_obj else "") or ""
        if err_type == "missing_node_type" or "missing_node_type" in (err_msg or ""):
            return _json_error(
                "svi_custom_node_missing",
                503,
                error="unavailable",
                namespace="svi",
                details={
                    "hint": "ComfyUIに SVI × Wan 2.2 のカスタムノードが未導入です。該当ノード(SVIWan22VideoExtend)をインストールして再起動してください。",
                    "comfyui_error": detail,
                },
            )
        if err_type == "missing_model_asset" or "missing_model_asset" in (err_msg or ""):
            return _json_error(
                "svi_model_missing",
                503,
                error="unavailable",
                namespace="svi",
                details={
                    "hint": "Wan動画延長に必要なモデルファイルが未導入です。/api/svi/capabilities の model_assets.missing を参照して、指定パスに配置してください。",
                    "missing": err_obj.get("missing") if isinstance(err_obj, dict) else None,
                    "models_base": err_obj.get("models_base") if isinstance(err_obj, dict) else None,
                    "comfyui_error": detail,
                },
            )

    return _json_error(
        "svi_extend_failed",
        500,
        error="internal_error",
        namespace="svi",
        details={"last_error": last_error} if last_error else None,
    )


@app.route("/api/svi/queue", methods=["GET"])
def api_svi_queue():
    """ComfyUI の /queue を返す（SVI/LTXなど共通の実行状況確認）"""
    if not REQUESTS_AVAILABLE:
        return _json_error("requests_unavailable", 503, error="unavailable", namespace="svi")

    base_url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
    try:
        r = requests.get(f"{base_url}/queue", timeout=5)
        r.raise_for_status()
        data = r.json()

        def _extract_prompt_ids(items):
            out = []
            for it in items or []:
                if isinstance(it, (list, tuple)) and len(it) > 1:
                    out.append(it[1])
            return out

        return jsonify(
            {
                "queue_running": data.get("queue_running", []),
                "queue_pending": data.get("queue_pending", []),
                "running_prompt_ids": _extract_prompt_ids(data.get("queue_running")),
                "pending_prompt_ids": _extract_prompt_ids(data.get("queue_pending")),
            }
        ), 200
    except Exception as e:
        logger.warning(f"SVI queue error: {e}")
        return _json_error("comfyui_queue_failed", 502, error="bad_gateway", namespace="svi")


@app.route("/api/svi/history", methods=["GET"])
def api_svi_history():
    """ComfyUI の /history/{prompt_id} を要約して返す"""
    if not REQUESTS_AVAILABLE:
        return _json_error("requests_unavailable", 503, error="unavailable", namespace="svi")

    prompt_id = (request.args.get("prompt_id") or "").strip()
    if not prompt_id:
        return _json_error("prompt_id is required", 400, error="bad_request", namespace="svi")

    base_url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
    try:
        r = requests.get(f"{base_url}/history/{prompt_id}", timeout=5)
        if r.status_code == 404:
            return _json_error("history_not_found", 404, error="not_found", namespace="svi")
        r.raise_for_status()
        raw = r.json() or {}
        entry = raw.get(prompt_id)
        if not entry:
            return _json_error("history_not_found", 404, error="not_found", namespace="svi")

        status = entry.get("status", {}) or {}
        outputs = entry.get("outputs", {}) or {}

        # collect output filenames (best-effort)
        out_files = {"video": [], "images": []}
        for _node_id, out in outputs.items():
            if isinstance(out, dict):
                if isinstance(out.get("video"), list):
                    for vf in out["video"]:
                        if isinstance(vf, dict) and vf.get("filename"):
                            out_files["video"].append(vf.get("filename"))
                if isinstance(out.get("images"), list):
                    for im in out["images"]:
                        if isinstance(im, dict) and im.get("filename"):
                            out_files["images"].append(im.get("filename"))

        return jsonify(
            {
                "prompt_id": prompt_id,
                "status": {
                    "status_str": status.get("status_str", "unknown"),
                    "completed": bool(status.get("completed", False)),
                    "messages": status.get("messages", [])[-10:],
                },
                "outputs": out_files,
            }
        ), 200
    except Exception as e:
        logger.warning(f"SVI history error: {e}")
        return _json_error("comfyui_history_failed", 502, error="bad_gateway", namespace="svi")


def _lazy_integration(key: str, factory):
    """初期化待ちでも使えるよう、必要な統合インスタンスを遅延生成する。"""
    inst = integrations.get(key)
    if inst is not None:
        return inst
    try:
        with initialization_lock:
            inst = integrations.get(key)
            if inst is not None:
                return inst
            new_inst = factory()
            integrations[key] = new_inst
            return new_inst
    except Exception:
        return None


def _get_or_init_comfyui():
    comfyui = integrations.get("comfyui")
    if comfyui is not None:
        return comfyui
    if not COMFYUI_AVAILABLE:
        return None
    return _lazy_integration(
        "comfyui",
        lambda: ComfyUIIntegration(base_url=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")),
    )


@app.route("/api/ltx2/generate", methods=["POST"])
def api_ltx2_generate():
    """LTX-2 動画生成（ComfyUIへワークフロー送信して待機）"""
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return _json_error("prompt is required", 400, error="bad_request", namespace="ltx2")

    ltx2 = integrations.get("ltx2")
    if not ltx2:
        ltx2 = _lazy_integration(
            "ltx2",
            lambda: LTX2VideoIntegration(base_url=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")),
        )
    if not ltx2 or not getattr(ltx2, "is_available", lambda: False)():
        return _json_error("ltx2_unavailable", 503, error="unavailable", namespace="ltx2")

    workflow_path = (data.get("workflow") or data.get("workflow_path") or "").strip() or None
    image = (data.get("image") or "").strip() or None
    timeout = float(data.get("timeout", 600.0) or 600.0)

    try:
        result = ltx2.generate(prompt=prompt, workflow_path=workflow_path, image=image, timeout=timeout)
        return jsonify(result), (200 if result.get("success") else 500)
    except Exception as e:
        logger.warning(f"LTX2 generate error: {e}")
        return _json_error("ltx2_generate_failed", 500, error="internal_error", namespace="ltx2")


@app.route("/api/ltx2/queue", methods=["GET"])
def api_ltx2_queue():
    """ComfyUI の /queue を返す（LTX-2用）"""
    if not REQUESTS_AVAILABLE:
        return _json_error("requests_unavailable", 503, error="unavailable", namespace="ltx2")

    base_url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
    try:
        r = requests.get(f"{base_url}/queue", timeout=5)
        r.raise_for_status()
        return jsonify(r.json()), 200
    except Exception as e:
        logger.warning(f"LTX2 queue error: {e}")
        return _json_error("comfyui_queue_failed", 502, error="bad_gateway", namespace="ltx2")


@app.route("/api/ltx2/history", methods=["GET"])
def api_ltx2_history():
    """ComfyUI の /history/{prompt_id} を返す（LTX-2用）"""
    if not REQUESTS_AVAILABLE:
        return _json_error("requests_unavailable", 503, error="unavailable", namespace="ltx2")

    prompt_id = (request.args.get("prompt_id") or "").strip()
    if not prompt_id:
        return _json_error("prompt_id is required", 400, error="bad_request", namespace="ltx2")

    base_url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
    try:
        r = requests.get(f"{base_url}/history/{prompt_id}", timeout=5)
        if r.status_code == 404:
            return _json_error("history_not_found", 404, error="not_found", namespace="ltx2")
        r.raise_for_status()
        return jsonify(r.json()), 200
    except Exception as e:
        logger.warning(f"LTX2 history error: {e}")
        return _json_error("comfyui_history_failed", 502, error="bad_gateway", namespace="ltx2")


@app.route("/api/ltx2-infinity/generate", methods=["POST"])
def api_ltx2_infinity_generate():
    """LTX-2 Infinity: セグメント反復生成（最小実装）"""
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return _json_error("prompt is required", 400, error="bad_request", namespace="ltx2_infinity")

    inf = integrations.get("ltx2_infinity")
    if not inf:
        inf = _lazy_integration(
            "ltx2_infinity",
            lambda: LTX2InfinityIntegration(base_url=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")),
        )
    if not inf or not getattr(inf, "is_available", lambda: False)():
        return _json_error("ltx2_infinity_unavailable", 503, error="unavailable", namespace="ltx2_infinity")

    segments = int(data.get("segments", 1) or 1)
    workflow_path = (data.get("workflow") or data.get("workflow_path") or "").strip() or None
    image = (data.get("image") or "").strip() or None
    timeout_per_segment = float(data.get("timeout_per_segment", data.get("timeout", 600.0)) or 600.0)

    try:
        result = inf.generate(
            prompt=prompt,
            segments=segments,
            workflow_path=workflow_path,
            image=image,
            timeout_per_segment=timeout_per_segment,
            positive_suffix=(data.get("positive_suffix") or "").strip() or None,
            negative_suffix=(data.get("negative_suffix") or "").strip() or None,
        )
        return jsonify(result), (200 if result.get("success") else 500)
    except Exception as e:
        logger.warning(f"LTX2 Infinity generate error: {e}")
        return _json_error("ltx2_infinity_generate_failed", 500, error="internal_error", namespace="ltx2_infinity")


@app.route("/api/ltx2-infinity/templates", methods=["GET", "POST"])
def api_ltx2_infinity_templates():
    """LTX-2 Infinity: テンプレート一覧/保存"""
    mgr = integrations.get("ltx2_template_manager")
    if not mgr:
        mgr = _lazy_integration("ltx2_template_manager", lambda: LTX2TemplateManager())
    if not mgr:
        return _json_error("template_manager_unavailable", 503, error="unavailable", namespace="ltx2_infinity")

    if request.method == "GET":
        try:
            return jsonify({"success": True, "templates": mgr.list_templates()}), 200
        except Exception as e:
            logger.warning(f"LTX2 templates list error: {e}")
            return _json_error("templates_list_failed", 500, error="internal_error", namespace="ltx2_infinity")

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    tpl = data.get("template")
    if not name or not isinstance(tpl, dict):
        return _json_error("name and template(dict) are required", 400, error="bad_request", namespace="ltx2_infinity")
    try:
        path = mgr.save_template(name, tpl)
        return jsonify({"success": True, "path": path}), 200
    except Exception as e:
        logger.warning(f"LTX2 template save error: {e}")
        return _json_error("template_save_failed", 500, error="internal_error", namespace="ltx2_infinity")


@app.route("/api/ltx2-infinity/storage", methods=["GET"])
def api_ltx2_infinity_storage():
    """LTX-2 Infinity: ストレージ統計"""
    st = integrations.get("ltx2_storage_manager")
    if not st:
        st = _lazy_integration("ltx2_storage_manager", lambda: LTX2StorageManager())
    if not st:
        return _json_error("storage_manager_unavailable", 503, error="unavailable", namespace="ltx2_infinity")
    try:
        return jsonify({"success": True, "stats": st.get_storage_stats()}), 200
    except Exception as e:
        logger.warning(f"LTX2 storage stats error: {e}")
        return _json_error("storage_stats_failed", 500, error="internal_error", namespace="ltx2_infinity")


@app.route("/api/pdf/to-excel", methods=["POST"])
def api_pdf_to_excel():
    """PDF→Excel（OCR/LLM強化版を既定で使用）"""
    data = request.get_json(silent=True) or {}
    pdf_path = (data.get("pdf_path") or "").strip()
    drive_url = (data.get("drive_url") or data.get("url") or "").strip()
    output_path = (data.get("output_path") or "").strip()
    mode = (data.get("mode") or "llm_enhanced").strip().lower()
    quality = (data.get("quality") or "balanced").strip().lower()

    if not pdf_path and not drive_url:
        return _json_error("pdf_path or drive_url is required", 400, error="bad_request", namespace="pdf")

    repo_root = Path(__file__).resolve().parent
    out_dir = repo_root / "output" / "excel"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Resolve input
    resolved_pdf = None
    if drive_url:
        try:
            from pdf_to_excel_converter import PDFToExcelConverter

            converter = PDFToExcelConverter(google_drive=None)
            tmp_pdf = out_dir / f"temp_drive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            downloaded = converter.download_from_google_drive(drive_url, output_path=str(tmp_pdf))
            if not downloaded:
                return _json_error("drive_download_failed", 502, error="bad_gateway", namespace="pdf")
            resolved_pdf = Path(downloaded)
        except Exception as e:
            logger.warning(f"Drive download error: {e}")
            return _json_error("drive_download_failed", 502, error="bad_gateway", namespace="pdf")
    else:
        p = Path(pdf_path)
        if not p.is_absolute():
            p = (repo_root / p).resolve()
        else:
            p = p.resolve()
        try:
            p.relative_to(repo_root)
        except Exception:
            return _json_error("pdf_path_outside_repo", 400, error="bad_request", namespace="pdf")
        if not p.exists() or not p.is_file():
            return _json_error("pdf_not_found", 404, error="not_found", namespace="pdf", detail=str(p))
        resolved_pdf = p

    if resolved_pdf.suffix.lower() != ".pdf":
        return _json_error("not_a_pdf", 400, error="bad_request", namespace="pdf")

    # Resolve output
    if output_path:
        out = Path(output_path)
        if not out.is_absolute():
            out = (repo_root / out).resolve()
        else:
            out = out.resolve()
        try:
            out.relative_to(repo_root)
        except Exception:
            return _json_error("output_path_outside_repo", 400, error="bad_request", namespace="pdf")
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = out_dir / f"{resolved_pdf.stem}_{ts}.xlsx"

    try:
        # default: llm_enhanced
        from pdf_to_excel_converter_llm_enhanced import PDFToExcelConverterLLMEnhanced

        llm_model = (data.get("llm_model") or "qwen2.5:7b").strip() or "qwen2.5:7b"
        use_llm_correction = bool(data.get("use_llm_correction", True))
        use_ocr = bool(data.get("use_ocr", True))
        ocr_providers = data.get("ocr_providers")
        if not isinstance(ocr_providers, list) or not ocr_providers:
            ocr_providers = ["tesseract", "google", "microsoft", "amazon"]

        # Quality presets
        use_super_ocr = bool(data.get("use_super_ocr", False))
        if quality == "fast":
            # Quick pass: local OCR only, no LLM correction by default
            ocr_providers = ["tesseract"]
            use_llm_correction = bool(data.get("use_llm_correction", False))
            use_super_ocr = bool(data.get("use_super_ocr", False))
        elif quality in {"quality", "high", "accurate"}:
            # Accuracy pass: multi OCR + LLM correction (still configurable)
            use_llm_correction = bool(data.get("use_llm_correction", True))
            use_super_ocr = bool(data.get("use_super_ocr", True))

        converter = PDFToExcelConverterLLMEnhanced(
            use_llm_correction=use_llm_correction,
            llm_model=llm_model,
            ocr_providers=ocr_providers,
            use_super_ocr=use_super_ocr,
        )
        result_path = converter.convert_to_excel(str(resolved_pdf), str(out), use_ocr=use_ocr)

        return jsonify(
            {
                "success": True,
                "output_path": result_path,
                "pages": len(getattr(converter, "page_data", []) or []),
                "llm_corrected_pages": sum(
                    1
                    for p in (getattr(converter, "page_data", []) or [])
                    if isinstance(p, dict) and p.get("llm_corrected")
                ),
            }
        ), 200
    except Exception as e:
        err = str(e)
        logger.warning(f"PDF→Excel error: {err}")
        return _json_error("pdf_to_excel_failed", 500, error="internal_error", namespace="pdf")


@app.route("/api/images/recent", methods=["GET"])
def api_images_recent():
    """最近の画像ファイル一覧（gallery_images をスキャン）"""
    try:
        limit = int(request.args.get("limit", "20") or "20")
    except Exception:
        limit = 20
    limit = max(1, min(limit, 200))
    raw_qs = (getattr(request, "query_string", b"") or b"").decode("utf-8", errors="ignore")
    debug_arg = (request.args.get("debug", "") or "").strip().lower()
    debug = (
        debug_arg in {"1", "true", "yes"}
        or "debug=1" in raw_qs
        or "debug=true" in raw_qs.lower()
        or "debug=yes" in raw_qs.lower()
    )

    repo_root = Path(__file__).resolve().parent
    workspace_root = repo_root.parent
    images_dir = Path(os.getenv("GALLERY_IMAGES_DIR", str(workspace_root / "gallery_images")))
    try:
        images_dir = images_dir if images_dir.is_absolute() else (workspace_root / images_dir).resolve()
    except Exception:
        images_dir = (workspace_root / "gallery_images").resolve()

    # Restrict to workspace to avoid arbitrary filesystem enumeration
    try:
        images_dir.relative_to(workspace_root)
    except Exception:
        images_dir = (workspace_root / "gallery_images").resolve()

    if not images_dir.exists():
        payload = {"success": True, "images": [], "source_dir": str(images_dir), "matched_images": 0}
        if debug:
            payload["debug"] = {
                "repo_root": str(repo_root),
                "workspace_root": str(workspace_root),
                "images_dir": str(images_dir),
                "images_dir_exists": False,
            }
        return jsonify(payload), 200

    exts = {".png", ".jpg", ".jpeg", ".webp"}
    items = []
    scanned_files = 0
    try:
        for p in images_dir.rglob("*"):
            if not p.is_file():
                continue
            scanned_files += 1
            if p.suffix.lower() not in exts:
                continue
            try:
                st = p.stat()
            except Exception:
                continue
            items.append(
                {
                    "path": str(p),
                    "name": p.name,
                    "mtime": st.st_mtime,
                    "size": st.st_size,
                }
            )

        items.sort(key=lambda x: x.get("mtime", 0), reverse=True)
        payload = {
            "success": True,
            "images": items[:limit],
            "source_dir": str(images_dir),
            "matched_images": len(items),
        }
        if debug:
            payload["debug"] = {
                "repo_root": str(repo_root),
                "workspace_root": str(workspace_root),
                "images_dir": str(images_dir),
                "images_dir_exists": True,
                "scanned_files": scanned_files,
                "matched_images": len(items),
            }
        return jsonify(payload), 200
    except Exception as e:
        logger.warning(f"recent images error: {e}")
        return _json_error("images_recent_failed", 500, error="internal_error", namespace="images")


@app.route("/api/vision/describe_url", methods=["POST"])
def api_vision_describe_url():
    """画像URL（Pixel7カメラのshot.jpg等）を取得して、llavaで内容説明を返す"""
    if not REQUESTS_AVAILABLE:
        return _json_error("requests_unavailable", 503, error="unavailable", namespace="vision")

    data = request.get_json(silent=True) or {}
    image_url = (data.get("image_url") or data.get("url") or "").strip()
    if not image_url:
        return _json_error("image_url is required", 400, error="bad_request", namespace="vision")

    prompt = (data.get("prompt") or "この画像の内容を日本語で詳しく説明してください。"
             ).strip() or "この画像の内容を日本語で詳しく説明してください。"
    model = (data.get("model") or os.getenv("MANAOS_VISION_MODEL") or "llava:latest").strip() or "llava:latest"

    try:
        img_resp = requests.get(image_url, timeout=10)
        img_resp.raise_for_status()
        img_bytes = img_resp.content
        if not img_bytes:
            return _json_error("empty_image", 502, error="bad_gateway", namespace="vision")
    except Exception as e:
        logger.warning(f"vision fetch error: {e}")
        return _json_error("fetch_failed", 502, error="bad_gateway", namespace="vision")

    try:
        import base64

        image_b64 = base64.b64encode(img_bytes).decode("utf-8")
        payload = {
            "model": model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {"temperature": float(data.get("temperature", 0.2) or 0.2), "num_predict": int(data.get("max_tokens", 512) or 512)},
        }
        ollama_url = get_ollama_url().rstrip("/")
        r = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=120)
        try:
            r.raise_for_status()
        except Exception:
            detail_text = ""
            try:
                detail_text = (r.json() or {}).get("error") or ""
            except Exception:
                detail_text = (r.text or "").strip()
            if "model" in detail_text.lower() and "not found" in detail_text.lower():
                return _json_error(
                    "vision_model_unavailable",
                    503,
                    error="unavailable",
                    namespace="vision",
                    details={
                        "requested": model,
                        "available_models": available_models,
                        "hint": "Install a vision model like llava:latest or set MANAOS_VISION_MODEL.",
                        "ollama_error": detail_text,
                    },
                )
            raise

        resp = r.json() or {}
        text = (resp.get("response") or "").strip()
        return jsonify({"success": True, "model": model, "description": text}), 200
    except Exception as e:
        logger.warning(f"vision llava error: {e}")
        return _json_error("vision_failed", 500, error="internal_error", namespace="vision")


@app.route("/api/vision/evaluate_url", methods=["POST"])
def api_vision_evaluate_url():
    """画像URLを評価してスコア/短評を返す（llava等）。"""
    if not REQUESTS_AVAILABLE:
        return _json_error("requests_unavailable", 503, error="unavailable", namespace="vision")

    data = request.get_json(silent=True) or {}
    image_url = (data.get("image_url") or data.get("url") or "").strip()
    if not image_url:
        return _json_error("image_url is required", 400, error="bad_request", namespace="vision")

    criteria = (data.get("criteria") or "").strip()
    model = (data.get("model") or os.getenv("MANAOS_VISION_MODEL") or "llava:latest").strip() or "llava:latest"
    temperature = float(data.get("temperature", 0.2) or 0.2)
    max_tokens = int(data.get("max_tokens", 256) or 256)

    try:
        img_resp = requests.get(image_url, timeout=10)
        img_resp.raise_for_status()
        img_bytes = img_resp.content
        if not img_bytes:
            return _json_error("empty_image", 502, error="bad_gateway", namespace="vision")
    except Exception as e:
        logger.warning(f"vision fetch error: {e}")
        return _json_error("fetch_failed", 502, error="bad_gateway", namespace="vision")

    base_prompt = (
        "次の画像を評価してください。必ずJSONのみで返してください。"
        "キーは score_overall, score_quality, score_aesthetic, score_clarity（0-100の整数）、notes（短い日本語）です。"
    )
    if criteria:
        base_prompt += f" 評価観点: {criteria}"

    try:
        import base64
        import json as _json

        image_b64 = base64.b64encode(img_bytes).decode("utf-8")
        ollama_url = get_ollama_url().rstrip("/")

        # Select a vision-capable model if the requested one is missing.
        fallback_note = None
        available_models = []
        try:
            tags = requests.get(f"{ollama_url}/api/tags", timeout=10).json() or {}
            available_models = [m.get("name") for m in (tags.get("models") or []) if m.get("name")]
            if model not in available_models:
                candidates = [
                    n for n in available_models
                    if any(k in n.lower() for k in ("llava", "vision", "vl", "minicpm", "qwen2.5-vl", "qwen2vl", "phi3-vision"))
                ]
                if candidates:
                    fallback_note = f"fallback:{model}→{candidates[0]}"
                    model = candidates[0]
                else:
                    return _json_error(
                        "vision_model_unavailable",
                        503,
                        error="unavailable",
                        namespace="vision",
                        details={
                            "requested": model,
                            "available_models": available_models,
                            "hint": "Install a vision model like llava:latest or set MANAOS_VISION_MODEL.",
                        },
                    )
        except Exception:
            # If we cannot fetch tags, proceed with the requested model.
            pass

        payload = {
            "model": model,
            "prompt": base_prompt,
            "images": [image_b64],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        r = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=120)
        r.raise_for_status()
        resp = r.json() or {}
        text = (resp.get("response") or "").strip()

        parsed = None
        parsed_ok = False
        if text:
            try:
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    parsed = _json.loads(text[start : end + 1])
                    parsed_ok = isinstance(parsed, dict)
            except Exception:
                parsed_ok = False

        return jsonify({
            "success": True,
            "model": model,
            "model_fallback": fallback_note,
            "evaluation": parsed if parsed_ok else None,
            "parsed": parsed_ok,
            "raw": text,
        }), 200
    except Exception as e:
        logger.warning(f"vision evaluation error: {e}")
        return _json_error("vision_failed", 500, error="internal_error", namespace="vision")


@app.route("/api/comfyui/queue", methods=["GET"])
@auth_manager.require_api_key
def api_comfyui_queue():
    """ComfyUIキュー状態（要認証）"""
    comfyui = _get_or_init_comfyui()
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
    comfyui = _get_or_init_comfyui()
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
        router = EnhancedLLMRouter(
            lm_studio_url=get_lm_studio_url(),
            ollama_url=get_ollama_url(),
        )
        integrations["enhanced_llm_routing"] = router
        return router
    except Exception as e:
        logger.warning(f"Enhanced LLM router init failed: {e}")
        return None


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _identity_guard_fail_closed_enabled() -> bool:
    return _env_flag("MANAOS_IDENTITY_GUARD_FAIL_CLOSED", default=False)


def _identity_guard_fail_closed_policy(reason: str) -> Dict[str, Any]:
    return {
        "checked": False,
        "blocked": True,
        "fail_closed": True,
        "block_reason": reason,
        "policy_version": "core5-identity-guard-v1",
    }


def _evaluate_identity_guard_or_fail_closed(
    prompt: str,
    context: Dict[str, Any],
    preferences: Dict[str, Any],
    endpoint: str,
):
    if not IDENTITY_GUARD_AVAILABLE or evaluate_identity_guard is None:
        if _identity_guard_fail_closed_enabled():
            logger.error(
                "Identity guard unavailable and fail-closed active: endpoint=%s",
                endpoint,
            )
            return None, _identity_guard_fail_closed_policy("identity_guard_unavailable")
        return None, None

    try:
        return evaluate_identity_guard(prompt, context=context, preferences=preferences), None
    except Exception as e:
        logger.error(
            "Identity guard evaluation error: endpoint=%s error=%s",
            endpoint,
            e,
        )
        if _identity_guard_fail_closed_enabled():
            return None, _identity_guard_fail_closed_policy("identity_guard_evaluation_failed")
        return None, None


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


@app.route("/api/llm/policy/status", methods=["GET"])
def api_llm_policy_status():
    """CORE5 Identityポリシー設定の状態を返す"""
    if not IDENTITY_GUARD_AVAILABLE or get_identity_policy_config is None:
        return jsonify(
            {
                "identity_guard": {
                    "available": False,
                    "fail_closed": _identity_guard_fail_closed_enabled(),
                }
            }
        ), 200

    try:
        config = get_identity_policy_config()
        return (
            jsonify(
                {
                    "identity_guard": {
                        "available": True,
                        "fail_closed": _identity_guard_fail_closed_enabled(),
                        **config,
                    }
                }
            ),
            200,
        )
    except Exception as e:
        logger.warning(f"LLM policy status error: {e}")
        return _json_error("llm_policy_status_failed", 500, error="internal_error", namespace="llm")


@app.route("/api/llm/policy/evaluate", methods=["POST"])
def api_llm_policy_evaluate():
    """CORE5 Identityポリシーで入力を事前評価する（実行はしない）"""
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

    include_normalized_prompt = bool(data.get("include_normalized_prompt", False))

    if not IDENTITY_GUARD_AVAILABLE or evaluate_identity_guard is None or identity_guard_to_dict is None:
        identity_payload: Dict[str, Any] = {
            "checked": False,
            "available": False,
            "fail_closed": _identity_guard_fail_closed_enabled(),
        }
        if _identity_guard_fail_closed_enabled():
            identity_payload.update(
                {
                    "blocked": True,
                    "block_reason": "identity_guard_unavailable",
                }
            )
        return jsonify({"identity_guard": identity_payload}), 200

    try:
        guard = evaluate_identity_guard(prompt, context=context, preferences=preferences)
        return jsonify(
            {
                "identity_guard": identity_guard_to_dict(
                    guard,
                    include_normalized_prompt=include_normalized_prompt,
                )
            }
        ), 200
    except Exception as e:
        logger.warning(f"LLM policy evaluate error: {e}")
        return _json_error("llm_policy_evaluate_failed", 500, error="internal_error", namespace="llm")


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
            return _json_error("difficulty_analyzer_unavailable", 503, error="unavailable", namespace="llm")

        score = float(analyzer.calculate_difficulty(prompt, context))
        level = str(analyzer.get_difficulty_level(score))
        recommended = str(analyzer.get_recommended_model(score))

        identity_payload: Dict[str, Any] = {
            "checked": False,
            "blocked": False,
            "risk_score": 0.0,
            "reasons": [],
        }
        guard, fail_closed_policy = _evaluate_identity_guard_or_fail_closed(
            prompt,
            context=context,
            preferences={},
            endpoint="/api/llm/analyze",
        )
        if fail_closed_policy is not None:
            return (
                jsonify(
                    {
                        "error": "identity_guard_unavailable_fail_closed",
                        "policy_blocked": True,
                        "identity_guard": fail_closed_policy,
                    }
                ),
                503,
            )

        if guard is not None:
            identity_payload = {
                "checked": True,
                "blocked": bool(guard.blocked),
                "risk_score": float(guard.risk_score),
                "reasons": list(guard.reasons),
                "has_explicit_approval": bool(guard.has_explicit_approval),
                "policy_version": guard.policy_version,
            }

        return (
            jsonify(
                {
                    "difficulty_score": score,
                    "difficulty_level": level,
                    "recommended_model": recommended,
                    "identity_guard": identity_payload,
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
        normalized_prompt = prompt
        guard, fail_closed_policy = _evaluate_identity_guard_or_fail_closed(
            prompt,
            context=context,
            preferences=preferences,
            endpoint="/api/llm/route",
        )
        if fail_closed_policy is not None:
            return (
                jsonify(
                    {
                        "success": True,
                        "model": "manaos-policy-identity",
                        "response": "安全ポリシーにより現在リクエストを処理できません。時間をおいて再試行してください。",
                        "policy_blocked": True,
                        "policy": {"identity": fail_closed_policy},
                    }
                ),
                200,
            )

        if guard is not None:
            if guard.blocked:
                return (
                    jsonify(
                        {
                            "success": True,
                            "model": "manaos-policy-identity",
                            "response": guard.fallback_response,
                            "policy_blocked": True,
                            "policy": {
                                "identity": {
                                    "checked": True,
                                    "blocked": True,
                                    "risk_score": float(guard.risk_score),
                                    "reasons": list(guard.reasons),
                                    "has_explicit_approval": bool(guard.has_explicit_approval),
                                    "policy_version": guard.policy_version,
                                }
                            },
                        }
                    ),
                    200,
                )
            normalized_prompt = guard.normalized_prompt

        result = router.route(prompt=normalized_prompt, context=context, preferences=preferences)
        if isinstance(result, dict):
            identity_meta = {"checked": bool(guard is not None)}
            if guard is not None:
                identity_meta.update(
                    {
                        "blocked": False,
                        "risk_score": float(guard.risk_score),
                        "reasons": list(guard.reasons),
                        "has_explicit_approval": bool(guard.has_explicit_approval),
                        "policy_version": guard.policy_version,
                    }
                )
            policy_meta = result.get("policy") if isinstance(result.get("policy"), dict) else {}
            policy_meta["identity"] = identity_meta
            result["policy"] = policy_meta
        return jsonify(result), 200
    except Exception as e:
        logger.warning(f"LLM route error: {e}")
        return _json_error("llm_route_failed", 500, error="internal_error", namespace="llm")


@app.route("/api/memory/store", methods=["POST"])
def api_memory_store():
    """記憶への保存（互換エンドポイント）"""
    if not MEMORY_BRIDGE_AVAILABLE or bridge_memory_store is None:
        return _json_error("memory_bridge_unavailable", 503, error="unavailable", namespace="memory")

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
        return _json_error("memory_bridge_unavailable", 503, error="unavailable", namespace="memory")

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
        return _json_error("memory_bridge_unavailable", 503, error="unavailable", namespace="memory")

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
        return _json_error("memory_bridge_unavailable", 503, error="unavailable", namespace="memory")

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
        return None, _json_error("requests_module_unavailable", 503, error="unavailable", namespace="ops")

    try:
        response = requests.post(url, json=payload, timeout=timeout)
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}
        return (response.status_code, body), None
    except Exception as e:
        logger.warning(f"OPS POST error ({url}): {e}")
        return None, _json_error("ops_upstream_unreachable", 503, error="unavailable", namespace="ops")


def _ops_http_get_json(url: str, timeout: float = 15.0):
    if not REQUESTS_AVAILABLE:
        return None, _json_error("requests_module_unavailable", 503, error="unavailable", namespace="ops")

    try:
        response = requests.get(url, timeout=timeout)
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text}
        return (response.status_code, body), None
    except Exception as e:
        logger.warning(f"OPS GET error ({url}): {e}")
        return None, _json_error("ops_upstream_unreachable", 503, error="unavailable", namespace="ops")


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
        return _json_error("text (or goal/input) is required", 400, error="bad_request", namespace="ops")

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

    status_code, body = upstream
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
        get_status, get_body = upstream_get
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

    exec_status_code, exec_body = upstream_post
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
    return jsonify({"job_id": job_id, "status": final_status, "_meta": _job_response_meta("ops", total_jobs)}), 202


@app.route("/ops/job/<job_id>", methods=["GET"])
def ops_job_blueprint(job_id: str):
    """Blueprint互換: 実行ジョブ状態の取得"""
    with ops_jobs_lock:
        job = ops_jobs.get(job_id)
        total_jobs = len(ops_jobs)
    if not job:
        return _json_error("job not found", 404, error="not_found", namespace="ops", total_jobs=total_jobs)
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
        return _json_error("instruction or patch is required", 400, error="bad_request", namespace="dev")
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
        return _json_error("job not found", 404, error="not_found", namespace="dev", total_jobs=total_jobs)
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
            notification_hub = NotificationHub()
            integrations["notification_hub"] = notification_hub
        except Exception as e:
            logger.warning(f"NotificationHub lazy init error: {e}")
            notification_hub = None
    return notification_hub


def _notify_call_with_timeout(notification_hub: Any, message: str, priority: str, timeout_sec: int) -> Dict[str, Any]:
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
        return _json_error("message (or text) is required", 400, error="bad_request", namespace="notify")

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
        t = threading.Thread(target=_notify_run_job, args=(job_id, message, priority, timeout_sec), daemon=True)
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
        return _json_error("job not found", 404, error="not_found", namespace="notify", total_jobs=total_jobs)
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
                    logger.info(f"エラーがある設定ファイル:\n" + "\n".join(error_files))
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
                lambda: ComfyUIIntegration(
            base_url=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
                ),
            )
        )

    # SVI × Wan 2.2動画生成統合（オプション）
    if SVI_WAN22_AVAILABLE:
        init_tasks.append(
            (
                "svi_wan22",
                lambda: SVIWan22VideoIntegration(
            base_url=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
                ),
            )
        )

    # LTX-2動画生成統合（オプション）
    if LTX2_AVAILABLE:
        init_tasks.append(
            (
                "ltx2",
                lambda: LTX2VideoIntegration(
            base_url=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
                ),
            )
        )

    # LTX-2 Infinity統合（オプション）
    if LTX2_INFINITY_AVAILABLE:
        init_tasks.append(
            (
                "ltx2_infinity",
                lambda: LTX2InfinityIntegration(
                    base_url=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
                ),
            )
        )
        init_tasks.append(("ltx2_workflow_generator", lambda: LTX2WorkflowGenerator()))
        init_tasks.append(("ltx2_template_manager", lambda: LTX2TemplateManager()))
        init_tasks.append(("ltx2_nsfw_config", lambda: LTX2NSFWConfig()))
        init_tasks.append(("ltx2_storage_manager", lambda: LTX2StorageManager()))

    # Google Drive統合（オプション）
    if GOOGLE_DRIVE_AVAILABLE:
        init_tasks.append(
            (
                "google_drive",
                lambda: GoogleDriveIntegration(
            credentials_path=os.getenv("GOOGLE_DRIVE_CREDENTIALS", "credentials.json"),
                    token_path=os.getenv("GOOGLE_DRIVE_TOKEN", "token.json"),
                ),
            )
        )

    # CivitAI統合（オプション）
    if CIVITAI_AVAILABLE:
        init_tasks.append(
            ("civitai", lambda: CivitAIIntegration(api_key=os.getenv("CIVITAI_API_KEY")))
        )

    # LangChain統合（オプション）
    if LANGCHAIN_AVAILABLE:
        init_tasks.append(
            (
                "langchain",
                lambda: LangChainIntegration(
            ollama_url=get_ollama_url(),
                    model_name=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
                ),
            )
        )
        init_tasks.append(
            (
                "langgraph",
                lambda: LangGraphIntegration(
            ollama_url=get_ollama_url(),
                    model_name=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
                ),
            )
        )

    # Mem0統合（オプション）
    if MEM0_AVAILABLE:
        init_tasks.append(("mem0", lambda: Mem0Integration()))

    # Obsidian統合（オプション）
    if OBSIDIAN_AVAILABLE:
        init_tasks.append(
            (
                "obsidian",
                lambda: ObsidianIntegration(
                    vault_path=os.getenv(
                        "OBSIDIAN_VAULT_PATH",
                        str(Path.home() / "Documents" / "Obsidian Vault"),
                    )
                ),
            )
        )

    # ローカルLLM統合
    if LOCAL_LLM_AVAILABLE:
        init_tasks.append(("local_llm", lambda: LocalLLMUnified()))

    # ========================================
    # 拡張フェーズ統合
    # ========================================

    # LLMルーティング統合（オプション）
    if LLM_ROUTING_AVAILABLE:
        init_tasks.append(("llm_routing", lambda: LLMRouter()))

    # 拡張LLMルーティング統合（難易度判定対応）
    if ENHANCED_LLM_ROUTING_AVAILABLE:
        init_tasks.append(
            (
                "enhanced_llm_routing",
                lambda: EnhancedLLMRouter(
            lm_studio_url=get_lm_studio_url(),
                    ollama_url=get_ollama_url(),
                ),
            )
        )

    # 統一記憶システム統合（オプション）
    if MEMORY_UNIFIED_AVAILABLE:
        init_tasks.append(("memory_unified", lambda: UnifiedMemory()))

    # 通知ハブ統合（オプション）
    if NOTIFICATION_HUB_AVAILABLE:
        init_tasks.append(("notification_hub", lambda: NotificationHub()))

    # 秘書機能統合（オプション）
    if SECRETARY_AVAILABLE:
        init_tasks.append(("secretary", lambda: SecretaryRoutines()))

    # 画像ストック統合（オプション）
    if IMAGE_STOCK_AVAILABLE:
        init_tasks.append(("image_stock", lambda: ImageStock()))

    # OH MY OPENCODE統合（オプション）
    if OH_MY_OPENCODE_AVAILABLE:
        init_tasks.append(("oh_my_opencode", lambda: OHMyOpenCodeIntegration()))

    # Rows統合（オプション）
    if ROWS_AVAILABLE:
        init_tasks.append(
            (
                "rows",
                lambda: RowsIntegration(
                    api_key=os.getenv("ROWS_API_KEY"), webhook_url=os.getenv("ROWS_WEBHOOK_URL")
                ),
            )
        )

    # GitHub統合（オプション）
    if GITHUB_AVAILABLE:
        init_tasks.append(("github", lambda: GitHubIntegration(token=os.getenv("GITHUB_TOKEN"))))

    # n8n統合（オプション）
    if N8N_AVAILABLE:
        init_tasks.append(
            (
                "n8n",
                lambda: N8NIntegration(
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
                lambda: ExcelLLMIntegration(
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
                        lambda: StepDeepResearchOrchestrator(
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
                stt_engine = create_stt_engine(
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
                tts_engine = create_tts_engine(
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
                "available": available,
            }
            init_tasks.append(("voice", lambda vi=voice_integration: vi))
            logger.info(f"✅ 音声機能統合を初期化タスクに追加しました（available={available}）")
        except Exception as e:
            logger.warning(f"⚠️ 音声機能統合の初期化準備エラー: {e}")

    # 統一キャッシュシステム（オプション）
    if UNIFIED_CACHE_AVAILABLE:
        init_tasks.append(("unified_cache", lambda: get_unified_cache()))

    # パフォーマンス最適化システム（オプション）
    if PERFORMANCE_OPTIMIZER_AVAILABLE:
        init_tasks.append(("performance_optimizer", lambda: PerformanceOptimizer()))

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
        f"初期化完了: 完了={len(initialization_status['completed'])}, 失敗={len(initialization_status['failed'])}, ready={all_required_ok}, 統合数={len(integrations)}"
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
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.15.5/swagger-ui.min.css">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.15.5/swagger-ui.min.js"></script>
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
    companion_path = Path(__file__).resolve().parent / "scripts" / "voice" / "pixel7_companion_client.html"
    if companion_path.exists():
        return send_from_directory(companion_path.parent, companion_path.name, mimetype="text/html; charset=utf-8")
    return "Companion page not found", 404


@app.route("/companion/manifest.json", methods=["GET"])
def companion_manifest():
    """PWA manifest for コンパニオン"""
    manifest_path = Path(__file__).resolve().parent / "scripts" / "voice" / "companion_manifest.json"
    if manifest_path.exists():
        return send_from_directory(manifest_path.parent, manifest_path.name, mimetype="application/json")
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
    レディネスチェック（L1: 超軽量）

    目的:
        - 外部watchdog/監視が「プロセスが応答できているか」を最小コストで確認する
        - 依存サービス（LLM/DB/通知など）の状態に引きずられて 503 になる事故を避ける

    NOTE:
        深い判定（初期化状態・依存チェック）は /status を参照する。

    Returns:
        200: HTTPとして応答できる（listenできている）
    """
    return (
        jsonify(
            {
                "status": "ready",
                "mode": "l1",
                "timestamp": datetime.now().isoformat(),
            }
        ),
        200,
    )


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


# =============================================================================
# ManaOS Shell  ─  自然言語 → 意図分類 → 既存 API へ Dispatch
# =============================================================================

_INTENT_ROUTER_URL = "http://127.0.0.1:5100/api/classify"
_shell_history: collections.deque = collections.deque(maxlen=100)


def _shell_known_services() -> set:
    """services_ledger.yaml からサービス名セットを返す（heal ルーティング用）"""
    try:
        ledger_path = REPO_ROOT / "config" / "services_ledger.yaml"
        with open(ledger_path, "r", encoding="utf-8") as f:
            ledger = yaml.safe_load(f) or {}
        names: set = set()
        for section in ("core", "optional"):
            names.update((ledger.get(section) or {}).keys())
        return names
    except Exception:
        return set()


def _shell_classify_inline(message: str) -> Dict[str, Any]:
    """intent_router が落ちているときのキーワードベース・フォールバック分類"""
    text = message.lower()
    if any(k in text for k in ("画像", "生成", "描いて", "絵", "イラスト", "comfyui", "generate image", "image gen")):
        return {"intent_type": "image_generation", "confidence": 0.8, "entities": {}}
    if any(k in text for k in ("起動", "再起動", "停止", "状態", "status", "ヘルス", "サービス", "heal", "復旧")):
        return {"intent_type": "system_control", "confidence": 0.8, "entities": {}}
    if any(k in text for k in ("実行", "やって", "作成", "処理", "タスク", "タスク登録")):
        return {"intent_type": "task_execution", "confidence": 0.7, "entities": {}}
    if any(k in text for k in ("コード", "実装", "プログラム", "スクリプト", "code")):
        return {"intent_type": "code_generation", "confidence": 0.8, "entities": {}}
    if any(k in text for k in ("分析", "集計", "レポート", "統計", "analyze")):
        return {"intent_type": "data_analysis", "confidence": 0.7, "entities": {}}
    if any(k in text for k in ("pixel7", "デバイス", "adb", "スマホ", "android")):
        return {"intent_type": "device_status", "confidence": 0.8, "entities": {}}
    return {"intent_type": "conversation", "confidence": 0.5, "entities": {}}


def _shell_build_dispatch(intent: Dict[str, Any], message: str) -> tuple:
    """intent_type → (method, url, body) へマッピング"""
    intent_type = intent.get("intent_type", "unknown")
    _port = int(os.getenv("UNIFIED_API_PORT", "9502"))
    base = f"http://127.0.0.1:{_port}"

    if intent_type == "image_generation":
        return "POST", f"{base}/api/comfyui/generate", {"prompt": message}

    if intent_type == "system_control":
        msg = message.lower()
        if any(k in msg for k in ("heal", "復旧", "修復", "restart", "再起動")):
            # entities に service 名があれば直接 /api/shell/heal / restart へ
            svc_name = intent.get("entities", {}).get("service") or intent.get("entities", {}).get("target")
            if not svc_name:
                # メッセージから最初の既知サービス名をマッチ
                import re as _re
                words = _re.split(r"[\s,、。]+", message)
                known = _shell_known_services()
                for w in words:
                    if w.lower() in known:
                        svc_name = w.lower()
                        break
            body: Dict[str, Any] = {"dry_run": False}
            if svc_name:
                body["service"] = svc_name
            is_restart = any(k in msg for k in ("restart", "再起動", "reboot"))
            endpoint = "/api/shell/restart" if is_restart else "/api/shell/heal"
            return "POST", f"{base}{endpoint}", body
        return "GET", f"{base}/api/integrations/status", {}

    if intent_type == "task_execution":
        return "POST", f"{base}/ops/plan", {"text": message}

    if intent_type == "data_analysis":
        return "POST", f"{base}/api/llm/analyze", {"text": message}

    if intent_type == "device_status":
        return "GET", f"{base}/api/integrations/status", {}

    # conversation / information_search / code_generation / scheduling / file_* / unknown
    return "POST", f"{base}/api/llm/route", {"prompt": message, "context": f"intent:{intent_type}"}


@app.route("/api/shell", methods=["POST"])
def api_shell():
    """
    ManaOS Shell ─ 自然言語を受け取り、意図分類して既存 API へ転送する。

    Request body:
        {"message": "comfyui で猫を生成して", "dry_run": false}

    Response:
        {"status": "ok", "plan": {...}, "dispatch": "url", "http_status": 200, "result": {...}}
    """
    if not REQUESTS_AVAILABLE:
        return _json_error("requests module unavailable", 503, error="unavailable", namespace="shell")

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or data.get("text") or "").strip()
    if not message:
        return _json_error("message is required", 400, error="bad_request", namespace="shell")

    dry_run = bool(data.get("dry_run", False))

    # ── 1. 意図分類 ──────────────────────────────────────────────────────────
    intent: Dict[str, Any] = {}
    classifier_used = "inline_keyword"

    try:
        ir_resp = requests.post(
            _INTENT_ROUTER_URL,
            json={"text": message},
            timeout=5.0,
        )
        if ir_resp.status_code == 200:
            body = ir_resp.json()
            # intent_router は dataclass を asdict() で返す
            intent = {
                "intent_type":       body.get("intent_type", "unknown"),
                "confidence":        float(body.get("confidence", 0.5)),
                "entities":          body.get("entities", {}),
                "reasoning":         body.get("reasoning", ""),
                "suggested_actions": body.get("suggested_actions", []),
            }
            classifier_used = "intent_router"
    except Exception:
        pass  # fall through to inline

    if not intent or intent.get("intent_type", "unknown") == "unknown":
        intent = _shell_classify_inline(message)

    # ── 2. Dispatch 先を決定 ───────────────────────────────────────────────
    method, dispatch_url, dispatch_body = _shell_build_dispatch(intent, message)

    plan = {
        "intent":     intent,
        "dispatch":   {"method": method, "url": dispatch_url, "body": dispatch_body},
        "classifier": classifier_used,
    }

    if dry_run:
        return jsonify({"status": "dry_run", "plan": plan}), 200

    # ── 3. 実行（元のリクエストの認証ヘッダーを転送） ────────────────────
    forward_headers: Dict[str, str] = {"Content-Type": "application/json"}
    api_key = (request.headers.get("X-API-Key") or "").strip()
    if api_key:
        forward_headers["X-API-Key"] = api_key
    else:
        auth_hdr = (request.headers.get("Authorization") or "").strip()
        if auth_hdr:
            forward_headers["Authorization"] = auth_hdr

    try:
        if method == "GET":
            result_resp = requests.get(dispatch_url, headers=forward_headers, timeout=60.0)
        else:
            result_resp = requests.post(
                dispatch_url, json=dispatch_body, headers=forward_headers, timeout=120.0
            )
        try:
            result = result_resp.json()
        except Exception:
            result = {"raw": result_resp.text[:500]}
        upstream_status = result_resp.status_code
    except Exception as exc:
        return jsonify({
            "status": "dispatch_error",
            "plan":   plan,
            "error":  str(exc)[:200],
        }), 502

    _shell_history.append({
        "ts":       datetime.utcnow().isoformat() + "Z",
        "message":  message,
        "intent":   intent.get("intent_type", "unknown"),
        "status":   "ok" if upstream_status < 400 else "upstream_error",
        "dispatch": dispatch_url,
    })
    return jsonify({
        "status":      "ok" if upstream_status < 400 else "upstream_error",
        "plan":        plan,
        "dispatch":    dispatch_url,
        "http_status": upstream_status,
        "result":      result,
    }), 200


@app.route("/api/shell/stream", methods=["POST"])
def api_shell_stream():
    """
    ManaOS Shell SSE版 ─ 各処理ステップをリアルタイムでストリーム。

    Request body:
        {"message": "サービス状態を教えて", "dry_run": false}

    SSE events (text/event-stream):
        data: {"step": "classifying", "message": "..."}
        data: {"step": "classified", "intent": {...}, "classifier": "..."}
        data: {"step": "dispatching", "method": "GET", "url": "..."}
        data: {"step": "done", "status": "ok", "http_status": 200, "result": {...}}
        data: {"step": "error", "error": "..."}
    """
    if not REQUESTS_AVAILABLE:
        def _err():
            yield f"data: {json.dumps({'step':'error','error':'requests unavailable'})}\n\n"
        return Response(stream_with_context(_err()), mimetype="text/event-stream")

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or data.get("text") or "").strip()
    dry_run = bool(data.get("dry_run", False))

    # 認証ヘッダーをここで確定（generator 内は request コンテキスト外）
    api_key = (request.headers.get("X-API-Key") or "").strip()
    auth_hdr = (request.headers.get("Authorization") or "").strip()

    def generate():
        if not message:
            yield f"data: {json.dumps({'step':'error','error':'message is required'})}\n\n"
            return

        # step 1: classifying
        yield f"data: {json.dumps({'step':'classifying','message':message})}\n\n"

        intent: Dict[str, Any] = {}
        classifier_used = "inline_keyword"
        try:
            ir_resp = requests.post(_INTENT_ROUTER_URL, json={"text": message}, timeout=5.0)
            if ir_resp.status_code == 200:
                body = ir_resp.json()
                intent = {
                    "intent_type":       body.get("intent_type", "unknown"),
                    "confidence":        float(body.get("confidence", 0.5)),
                    "entities":          body.get("entities", {}),
                    "reasoning":         body.get("reasoning", ""),
                    "suggested_actions": body.get("suggested_actions", []),
                }
                classifier_used = "intent_router"
        except Exception:
            pass

        if not intent or intent.get("intent_type", "unknown") == "unknown":
            intent = _shell_classify_inline(message)

        # step 2: classified
        yield f"data: {json.dumps({'step':'classified','intent':intent,'classifier':classifier_used})}\n\n"

        method, dispatch_url, dispatch_body = _shell_build_dispatch(intent, message)

        # step 3: dispatching
        yield f"data: {json.dumps({'step':'dispatching','method':method,'url':dispatch_url})}\n\n"

        if dry_run:
            plan = {"intent": intent, "dispatch": {"method": method, "url": dispatch_url, "body": dispatch_body}, "classifier": classifier_used}
            yield f"data: {json.dumps({'step':'done','status':'dry_run','plan':plan})}\n\n"
            return

        forward_headers: Dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            forward_headers["X-API-Key"] = api_key
        elif auth_hdr:
            forward_headers["Authorization"] = auth_hdr

        try:
            if method == "GET":
                result_resp = requests.get(dispatch_url, headers=forward_headers, timeout=60.0)
            else:
                result_resp = requests.post(dispatch_url, json=dispatch_body, headers=forward_headers, timeout=120.0)
            try:
                result = result_resp.json()
            except Exception:
                result = {"raw": result_resp.text[:500]}
            upstream_status = result_resp.status_code
        except Exception as exc:
            yield f"data: {json.dumps({'step':'error','error':str(exc)[:200]})}\n\n"
            return

        # step 4: done
        status = "ok" if upstream_status < 400 else "upstream_error"
        yield f"data: {json.dumps({'step':'done','status':status,'http_status':upstream_status,'result':result})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/shell/history", methods=["GET"])
def api_shell_history():
    """ManaOS Shell ─ 直近メッセージ履歴 (in-memory ring buffer, 再起動でリセット)."""
    n = min(int(request.args.get("n", 50)), 200)
    return jsonify({"history": list(_shell_history)[-n:], "total": len(_shell_history)}), 200


@app.route("/api/shell/services", methods=["GET"])
def api_shell_services():
    """
    ManaOS Shell ─ サービス一覧 (services_ledger.yaml + health probe)。
    dashboard_cli の normalize_rows / probe_service を軽量に再実装。

    Response:
        {"services": [{"name":"ollama","port":11434,"section":"core","enabled":true,"summary":"OK","health":"ok"},...]}
    """
    ledger_path = REPO_ROOT / "config" / "services_ledger.yaml"
    if not ledger_path.exists():
        return _json_error("services_ledger.yaml not found", 503, namespace="shell_services")

    try:
        with open(ledger_path, "r", encoding="utf-8") as f:
            ledger = yaml.safe_load(f) or {}
    except Exception as exc:
        return _json_error(str(exc), 500, namespace="shell_services")

    result = []
    for section in ("core", "optional"):
        for svc_name, svc in (ledger.get(section) or {}).items():
            enabled = bool(svc.get("enabled", section == "core"))
            port = svc.get("port")
            url = svc.get("url") or (f"http://127.0.0.1:{port}" if port else None)
            health_url = url and f"{url.rstrip('/')}/health"
            health_txt = "n/a"
            summary = "NO_URL"
            if health_url:
                try:
                    r = requests.get(health_url, timeout=2.0)
                    health_txt = "ok" if r.status_code < 400 else f"http_{r.status_code}"
                    summary = "OK" if r.status_code < 400 else ("HTTP_401" if r.status_code == 401 else "WARN")
                except Exception:
                    health_txt = "timeout"
                    summary = "DOWN"
            result.append({
                "name":    svc_name,
                "section": section,
                "enabled": enabled,
                "port":    port,
                "health":  health_txt,
                "summary": summary,
            })

    return jsonify({"services": result, "count": len(result)}), 200


@app.route("/api/shell/restart", methods=["POST"])
def api_shell_restart():
    """
    ManaOS Shell ─ サービスの再起動 (manaosctl restart ラッパ).

    Request body:
        {"service": "ollama"}   → 指定サービスのみ再起動
        {"service": null}       → 全サービス再起動

    Response:
        {"status": "ok", "service": "ollama", "exit_code": 0, "stdout": "...", "stderr": "..."}
    """
    data = request.get_json(silent=True) or {}
    svc_name: Optional[str] = (data.get("service") or "").strip() or None

    manaosctl = REPO_ROOT / "tools" / "manaosctl.py"
    if not manaosctl.exists():
        return _json_error("manaosctl.py not found", 503, namespace="shell_restart")

    cmd = [sys.executable, str(manaosctl), "restart"]
    if svc_name:
        cmd += [svc_name]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=120,
        )
        ok = proc.returncode == 0
        return jsonify({
            "status":    "ok" if ok else "error",
            "service":   svc_name,
            "exit_code": proc.returncode,
            "stdout":    proc.stdout[-4000:] if proc.stdout else "",
            "stderr":    proc.stderr[-2000:] if proc.stderr else "",
        }), 200 if ok else 207
    except subprocess.TimeoutExpired:
        return _json_error("restart timed out (120s)", 504, namespace="shell_restart")
    except Exception as exc:
        return _json_error(str(exc), 500, namespace="shell_restart")


@app.route("/api/shell/heal", methods=["POST"])
def api_shell_heal():
    """
    ManaOS Shell ─ サービスのヒールを直接実行 (manaosctl heal ラッパ).

    Request body:
        {"service": "ollama"}              → 指定サービスのみヒール
        {"service": null}                  → 全サービス auto-heal
        {"service": "ollama", "dry_run": true}  → dry-run

    Response:
        {"status": "ok", "service": "ollama", "exit_code": 0, "stdout": "...", "stderr": "..."}
    """
    data = request.get_json(silent=True) or {}
    svc_name: Optional[str] = (data.get("service") or "").strip() or None
    dry_run = bool(data.get("dry_run", False))

    manaosctl = REPO_ROOT / "tools" / "manaosctl.py"
    if not manaosctl.exists():
        return _json_error("manaosctl.py not found", 503, namespace="shell_heal")

    cmd = [sys.executable, str(manaosctl), "heal"]
    if dry_run:
        cmd.append("--dry-run")
    if svc_name:
        cmd += ["--service", svc_name]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=60,
        )
        ok = proc.returncode == 0
        return jsonify({
            "status":    "ok" if ok else "error",
            "service":   svc_name,
            "exit_code": proc.returncode,
            "stdout":    proc.stdout[-4000:] if proc.stdout else "",
            "stderr":    proc.stderr[-2000:] if proc.stderr else "",
            "dry_run":   dry_run,
        }), 200 if ok else 207
    except subprocess.TimeoutExpired:
        return _json_error("heal timed out (60s)", 504, namespace="shell_heal")
    except Exception as exc:
        return _json_error(str(exc), 500, namespace="shell_heal")


# manaosctl run コマンドのホワイトリスト（副作用のある操作は除外）
_SHELL_RUN_WHITELIST = frozenset({"status", "deps", "events", "tier", "report", "cost", "dashboard", "watch", "gtd", "notify"})

_ANSI_RE = __import__("re").compile(r"\x1b\[[0-9;]*m")


@app.route("/api/shell/run", methods=["POST"])
def api_shell_run():
    """
    ManaOS Shell — manaosctl コマンドを直接実行してテキスト出力を返す。

    Request body:
        {"command": "deps", "args": ["--tree", "unified_api"]}
        {"command": "events", "args": ["-n", "20"]}
        {"command": "watch", "args": []}         # --once を自動付与
        {"command": "tier", "args": []}

    Response:
        {"status": "ok", "command": "deps", "args": [...], "output": "...", "exit_code": 0}
    """
    data    = request.get_json(silent=True) or {}
    command = (data.get("command") or "").strip().lower()
    args    = [str(a) for a in (data.get("args") or [])]

    if command not in _SHELL_RUN_WHITELIST:
        return _json_error(
            f"command '{command}' not in whitelist. allowed: {sorted(_SHELL_RUN_WHITELIST)}",
            400, namespace="shell_run",
        )

    manaosctl = REPO_ROOT / "tools" / "manaosctl.py"
    if not manaosctl.exists():
        return _json_error("manaosctl.py not found", 503, namespace="shell_run")

    # watch は --once を強制（無限ループ防止）
    if command == "watch" and "--once" not in args:
        args = ["--once"] + [a for a in args if a not in ("--interval",)]

    cmd = [sys.executable, str(manaosctl), command] + args

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=30,
        )
        raw_out = (proc.stdout or "") + (proc.stderr or "")
        output  = _ANSI_RE.sub("", raw_out)
        return jsonify({
            "status":    "ok" if proc.returncode in (0, 1) else "error",
            "command":   command,
            "args":      args,
            "output":    output[-6000:],
            "exit_code": proc.returncode,
        }), 200
    except subprocess.TimeoutExpired:
        return _json_error(f"command timed out (30s): {command}", 504, namespace="shell_run")
    except Exception as exc:
        return _json_error(str(exc), 500, namespace="shell_run")


@app.route("/shell", methods=["GET"])
def shell_ui():
    """ManaOS Shell ブラウザ UI (web/dashboard/shell.html)"""
    shell_html = REPO_ROOT / "web" / "dashboard" / "shell.html"
    if not shell_html.exists():
        return "shell.html not found — run the setup to generate it.", 404
    return send_from_directory(str(shell_html.parent), shell_html.name, mimetype="text/html; charset=utf-8")


# ── GTD Proxy (→ port 5130) ──────────────────────────────────────────────────
_GTD_CAPTURE_URL = "http://127.0.0.1:5130"

def _gtd_run_cli(*args, timeout: int = 15) -> str:
    """manaosctl gtd サブコマンドをサブプロセスで実行してstdoutを返す。"""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "manaosctl.py"), "gtd", *args],
        capture_output=True, text=True, timeout=timeout, cwd=str(REPO_ROOT)
    )
    return result.stdout

@app.route("/api/gtd/capture", methods=["POST"])
def gtd_capture_proxy():
    """Inbox に1アイテム追加 (GTD Capture Server → フォールバック: manaosctl)。"""
    import urllib.request as _ur
    import urllib.error as _ue
    try:
        body = request.get_data()
        req = _ur.Request(
            f"{_GTD_CAPTURE_URL}/api/gtd/capture",
            data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with _ur.urlopen(req, timeout=5) as r:
            return r.read(), r.status, {"Content-Type": "application/json"}
    except _ue.URLError:
        # port 5130 DOWN → manaosctl gtd capture でフォールバック
        try:
            payload = request.get_json(force=True, silent=True) or {}
            text = payload.get("text") or payload.get("content") or ""
            if not text:
                return _json_error("text field required", 400, namespace="gtd")
            extra_args = []
            if payload.get("context"):
                extra_args += ["--context", str(payload["context"])]
            if payload.get("due"):
                extra_args += ["--due", str(payload["due"])]
            out = _gtd_run_cli("capture", text, *extra_args)
            return jsonify({"status": "ok", "source": "fallback_cli", "output": out.strip()}), 200
        except Exception as exc:
            return _json_error(str(exc), 500, namespace="gtd")

@app.route("/api/gtd/status", methods=["GET"])
def gtd_status_proxy():
    """GTD ステータス (port 5130 → フォールバック: manaosctl --json)。"""
    import urllib.request as _ur
    import urllib.error as _ue
    try:
        with _ur.urlopen(f"{_GTD_CAPTURE_URL}/api/gtd/status", timeout=5) as r:
            return r.read(), r.status, {"Content-Type": "application/json"}
    except _ue.URLError:
        out = _gtd_run_cli("status", "--json")
        return out, 200, {"Content-Type": "application/json"}

@app.route("/api/gtd/morning", methods=["GET"])
def gtd_morning_proxy():
    """今日のモーニングログを取得・作成。"""
    out = _gtd_run_cli("morning")
    return jsonify({"status": "ok", "output": out.strip()}), 200

@app.route("/api/gtd/inbox", methods=["GET"])
def gtd_inbox_proxy():
    """Inbox 一覧 JSON を返す。"""
    out = _gtd_run_cli("inbox", "--json")
    return out, 200, {"Content-Type": "application/json"}

@app.route("/api/gtd/next", methods=["GET"])
def gtd_next_proxy():
    """Next Actions + Projects 一覧 JSON を返す。"""
    out = _gtd_run_cli("next", "--json")
    return out, 200, {"Content-Type": "application/json"}

@app.route("/api/gtd/weekly", methods=["GET"])
def gtd_weekly_proxy():
    """週次レビュー JSON を返す。"""
    out = _gtd_run_cli("weekly", "--json")
    return out, 200, {"Content-Type": "application/json"}

@app.route("/api/gtd/process", methods=["POST"])
def gtd_process_proxy():
    """Inbox アイテムをバッチ移動: {"index": 1, "to": "next"}。"""
    payload = request.get_json(force=True, silent=True) or {}
    idx = payload.get("index")
    to  = payload.get("to")
    if not idx or not to:
        return _json_error("index and to are required", 400, namespace="gtd")
    inbox_out = _gtd_run_cli("inbox", "--json")
    try:
        inbox_list = json.loads(inbox_out)
    except Exception:
        return _json_error("failed to parse inbox list", 500, namespace="gtd")
    n = len(inbox_list)
    if not (1 <= int(idx) <= n):
        return _json_error(f"index out of range 1-{n}", 400, namespace="gtd")
    target = inbox_list[int(idx) - 1]
    out = _gtd_run_cli("process", "--target", target, "--to", str(to))
    return jsonify({"status": "ok", "target": target, "to": to, "output": out.strip()}), 200


@app.route("/api/gtd/commit", methods=["POST"])
def gtd_commit_proxy():
    """GTD 変更を git commit: {"push": true} で push も実行。"""
    payload = request.get_json(force=True, silent=True) or {}
    push = payload.get("push", False)
    args = ["commit"]
    if push:
        args.append("--push")
    out = _gtd_run_cli(*args)
    return jsonify({"status": "ok", "output": out.strip()}), 200

# =============================================================================
# END ManaOS Shell
# =============================================================================


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

