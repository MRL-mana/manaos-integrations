"""
ManaOS統合APIサーバー（修正版）
すべての外部システム統合を管理する統合API
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
import warnings
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import subprocess
import threading

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
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("UnifiedAPIServer")

# タイムアウト設定の取得
timeout_config = get_timeout_config()


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
    env_path = Path(__file__).parent / '.env'
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
    logger.warning("ComfyUI統合モジュールが見つかりません")

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
    from llm_routing import LLMRouter
    LLM_ROUTING_AVAILABLE = True
except ImportError:
    logger.warning("LLMルーティングモジュールが見つかりません")

# 拡張LLMルーティング統合（難易度判定対応）
ENHANCED_LLM_ROUTING_AVAILABLE = False
try:
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

app = Flask(__name__)
CORS(app)

# OpenAPI仕様を提供（Open WebUI External Tools対応）
@app.route("/openapi.json", methods=["GET"])
def openapi_spec():
    """OpenAPI仕様を返す（Open WebUI External Tools対応）"""
    return jsonify({
        "openapi": "3.0.0",
        "info": {
            "title": "manaOS統合API",
            "description": "manaOS統合システムへのアクセス（画像生成、ファイル管理、ノート作成など）",
            "version": "1.0.0"
        },
        "servers": [
            {
                "url": "http://host.docker.internal:9500",
                "description": "ローカルサーバー"
            }
        ],
        "paths": {
            "/api/comfyui/generate": {
                "post": {
                    "summary": "ComfyUIで画像を生成",
                    "description": "ComfyUIを使って画像を生成します",
                    "operationId": "generateImageComfyUI",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "prompt": {
                                            "type": "string",
                                            "description": "画像生成のプロンプト"
                                        },
                                        "width": {
                                            "type": "integer",
                                            "description": "画像の幅（デフォルト: 512）",
                                            "default": 512
                                        },
                                        "height": {
                                            "type": "integer",
                                            "description": "画像の高さ（デフォルト: 512）",
                                            "default": 512
                                        },
                                        "steps": {
                                            "type": "integer",
                                            "description": "生成ステップ数（デフォルト: 20）",
                                            "default": 20
                                        }
                                    },
                                    "required": ["prompt"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/google_drive/upload": {
                "post": {
                    "summary": "Google Driveにファイルをアップロード",
                    "description": "ファイルをGoogle Driveにアップロードします",
                    "operationId": "uploadToGoogleDrive",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "file_path": {
                                            "type": "string",
                                            "description": "アップロードするファイルのパス"
                                        },
                                        "folder_id": {
                                            "type": "string",
                                            "description": "アップロード先のフォルダID（オプション）"
                                        }
                                    },
                                    "required": ["file_path"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "成功"
                        }
                    }
                }
            },
            "/api/obsidian/create": {
                "post": {
                    "summary": "Obsidianにノートを作成",
                    "description": "Obsidianにノートを作成します",
                    "operationId": "createObsidianNote",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "title": {
                                            "type": "string",
                                            "description": "ノートのタイトル"
                                        },
                                        "content": {
                                            "type": "string",
                                            "description": "ノートの内容"
                                        },
                                        "tags": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "タグのリスト"
                                        }
                                    },
                                    "required": ["title", "content"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "成功"
                        }
                    }
                }
            },
            "/api/civitai/search": {
                "get": {
                    "summary": "CivitAIでモデルを検索",
                    "description": "CivitAIでモデルを検索します",
                    "operationId": "searchCivitAIModels",
                    "parameters": [
                        {
                            "name": "query",
                            "in": "query",
                            "required": True,
                            "schema": {
                                "type": "string"
                            },
                            "description": "検索クエリ"
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "integer",
                                "default": 10
                            },
                            "description": "結果の最大数"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "成功"
                        }
                    }
                }
            }
        }
    })

# 統合システムのインスタンス
integrations: Dict[str, Any] = {}

# 初期化状態管理
initialization_lock = threading.Lock()
initialization_status = {
    "status": "starting",  # "starting", "ready", "error"
    "pending": [],
    "completed": [],
    "failed": [],
    "checks": {}  # 各チェックの状態
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
                                if hasattr(error, 'message'):
                                    logger.debug(f"    {error.message}")
                                elif isinstance(error, str):
                                    logger.debug(f"    {error}")
                                elif hasattr(error, '__str__'):
                                    logger.debug(f"    {str(error)}")
                logger.warning(f"⚠️ 設定検証システム統合完了（{error_count}個の設定ファイルにエラー）")
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
        init_tasks.append(("comfyui", lambda: ComfyUIIntegration(
            base_url=os.getenv("COMFYUI_URL", "http://localhost:8188")
        )))

    # SVI × Wan 2.2動画生成統合（オプション）
    if SVI_WAN22_AVAILABLE:
        init_tasks.append(("svi_wan22", lambda: SVIWan22VideoIntegration(
            base_url=os.getenv("COMFYUI_URL", "http://localhost:8188")
        )))

    # LTX-2動画生成統合（オプション）
    if LTX2_AVAILABLE:
        init_tasks.append(("ltx2", lambda: LTX2VideoIntegration(
            base_url=os.getenv("COMFYUI_URL", "http://localhost:8188")
        )))

    # Google Drive統合（オプション）
    if GOOGLE_DRIVE_AVAILABLE:
        init_tasks.append(("google_drive", lambda: GoogleDriveIntegration(
            credentials_path=os.getenv("GOOGLE_DRIVE_CREDENTIALS", "credentials.json"),
            token_path=os.getenv("GOOGLE_DRIVE_TOKEN", "token.json")
        )))

    # CivitAI統合（オプション）
    if CIVITAI_AVAILABLE:
        init_tasks.append(("civitai", lambda: CivitAIIntegration(
            api_key=os.getenv("CIVITAI_API_KEY")
        )))

    # LangChain統合（オプション）
    if LANGCHAIN_AVAILABLE:
        init_tasks.append(("langchain", lambda: LangChainIntegration(
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            model_name=os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        )))
        init_tasks.append(("langgraph", lambda: LangGraphIntegration(
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            model_name=os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        )))

    # Mem0統合（オプション）
    if MEM0_AVAILABLE:
        init_tasks.append(("mem0", lambda: Mem0Integration()))

    # Obsidian統合（オプション）
    if OBSIDIAN_AVAILABLE:
        init_tasks.append(("obsidian", lambda: ObsidianIntegration(
            vault_path=os.getenv("OBSIDIAN_VAULT_PATH", "C:/Users/mana4/Documents/Obsidian Vault")
        )))

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
        init_tasks.append(("enhanced_llm_routing", lambda: EnhancedLLMRouter(
            lm_studio_url=os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1"),
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434")
        )))

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
        init_tasks.append(("rows", lambda: RowsIntegration(
            api_key=os.getenv("ROWS_API_KEY"),
            webhook_url=os.getenv("ROWS_WEBHOOK_URL")
        )))

    # GitHub統合（オプション）
    if GITHUB_AVAILABLE:
        init_tasks.append(("github", lambda: GitHubIntegration(
            token=os.getenv("GITHUB_TOKEN")
        )))

    # n8n統合（オプション）
    if N8N_AVAILABLE:
        init_tasks.append(("n8n", lambda: N8NIntegration(
            base_url=os.getenv("N8N_BASE_URL", "http://localhost:5678"),
            api_key=os.getenv("N8N_API_KEY")
        )))

    # Excel/LLM処理統合（オプション）
    if EXCEL_LLM_AVAILABLE:
        init_tasks.append(("excel_llm", lambda: ExcelLLMIntegration(
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        )))

    # Step-Deep-Research統合（オプション）
    if STEP_DEEP_RESEARCH_AVAILABLE:
        try:
            config_path = Path(__file__).parent / "step_deep_research_config.json"
            if config_path.exists():
                init_tasks.append(("step_deep_research", lambda: StepDeepResearchOrchestrator(
                    json.load(open(config_path, "r", encoding="utf-8"))
                )))
        except Exception as e:
            logger.warning(f"Step-Deep-Research統合の初期化準備エラー: {e}")

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
        required_checks = ["memory_db", "obsidian_path", "notification_hub", "llm_routing", "image_stock"]
        # 利用可能な統合のみをチェック（not_availableはOKとみなす）
        available_checks = [check for check in required_checks if checks.get(check, {}).get("status") != "not_available"]
        all_required_ok = all(checks.get(check, {}).get("status") in ["ok", "warning"] for check in available_checks) if available_checks else True

        if initialization_status["pending"]:
            initialization_status["status"] = "error"
        elif all_required_ok and len(initialization_status["completed"]) > 0:
            # 少なくとも1つの統合が完了していればready
            initialization_status["status"] = "ready"
        else:
            initialization_status["status"] = "starting"  # まだ準備中

    logger.info(f"初期化完了: 完了={len(initialization_status['completed'])}, 失敗={len(initialization_status['failed'])}, ready={all_required_ok}, 統合数={len(integrations)}")


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
            checks["memory_db"] = {"status": "error", "message": f"記憶DB接続エラー: {str(e)[:100]}"}
    else:
        checks["memory_db"] = {"status": "not_available", "message": "記憶システムが初期化されていません"}

    # 2. Obsidianパス確認OK
    obsidian = integrations.get("obsidian")
    if obsidian:
        try:
            if hasattr(obsidian, "is_available") and obsidian.is_available():
                checks["obsidian_path"] = {"status": "ok", "message": "Obsidianパス確認OK"}
            else:
                checks["obsidian_path"] = {"status": "warning", "message": "Obsidianパスは存在しますが利用できません"}
        except Exception as e:
            checks["obsidian_path"] = {"status": "error", "message": f"Obsidianパス確認エラー: {str(e)[:100]}"}
    else:
        checks["obsidian_path"] = {"status": "not_available", "message": "Obsidianが初期化されていません"}

    # 3. 通知ハブ送信OK（ダミー送信テスト）
    notification_hub = integrations.get("notification_hub")
    if notification_hub:
        try:
            # ダミー送信テスト（実際には送信しない、キュー投入のみ）
            # 実際の送信はしないが、初期化は確認
            checks["notification_hub"] = {"status": "ok", "message": "通知ハブ初期化OK"}
        except Exception as e:
            checks["notification_hub"] = {"status": "error", "message": f"通知ハブエラー: {str(e)[:100]}"}
    else:
        checks["notification_hub"] = {"status": "not_available", "message": "通知ハブが初期化されていません"}

    # 4. LLMルーティングのモデル最低1つ起動OK
    llm_routing = integrations.get("llm_routing")
    if llm_routing:
        try:
            # モデルリストを取得
            import requests
            ollama_url = getattr(llm_routing, "ollama_url", "http://localhost:11434")
            response = requests.get(f"{ollama_url}/api/tags", timeout=2.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                if models:
                    checks["llm_routing"] = {"status": "ok", "message": f"LLMルーティングOK（{len(models)}モデル利用可能）"}
                else:
                    checks["llm_routing"] = {"status": "warning", "message": "LLMルーティングは初期化されていますが、モデルがインストールされていません"}
            else:
                checks["llm_routing"] = {"status": "error", "message": f"Ollama API接続エラー: HTTP {response.status_code}"}
        except Exception as e:
            checks["llm_routing"] = {"status": "error", "message": f"LLMルーティングチェックエラー: {str(e)[:100]}"}
    else:
        checks["llm_routing"] = {"status": "not_available", "message": "LLMルーティングが初期化されていません"}

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
                    test_file.write_text("test", encoding='utf-8')
                    test_file.unlink()
                    checks["image_stock"] = {"status": "ok", "message": "画像ストックアクセスOK"}
                except Exception as e:
                    checks["image_stock"] = {"status": "error", "message": f"画像ストック書き込みエラー: {str(e)[:100]}"}
            else:
                checks["image_stock"] = {"status": "error", "message": "画像ストックディレクトリが存在しません"}
        except Exception as e:
            checks["image_stock"] = {"status": "error", "message": f"画像ストックチェックエラー: {str(e)[:100]}"}
    else:
        checks["image_stock"] = {"status": "not_available", "message": "画像ストックが初期化されていません"}

    return checks


@app.route("/health", methods=["GET"])
def health():
    """ヘルスチェック（軽量：プロセス生存のみ）"""
    # 即座に返す（重い処理は一切しない）
    return jsonify({
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    }), 200


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

        return jsonify({
            "status": "ready",
            "integrations": integration_status,
            "initialization": {
                "completed": completed,
                "failed": failed
            },
            "readiness_checks": checks
        }), 200
    else:
        # 初期化中またはエラー
        return jsonify({
            "status": status,
            "pending": pending,
            "completed": completed,
            "failed": failed,
            "readiness_checks": checks
        }), 503 if status == "starting" else 500


@app.route("/status", methods=["GET"])
def status():
    """
    初期化進捗ステータス（詳細情報）

    Returns:
        常に200（進捗情報を返す、軽量）
    """
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
        "google_drive": ("Google Drive", GOOGLE_DRIVE_AVAILABLE, ["GOOGLE_DRIVE_CREDENTIALS", "GOOGLE_DRIVE_TOKEN"]),
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
    required_checks = ["memory_db", "obsidian_path", "notification_hub", "llm_routing", "image_stock"]
    check_summary = {
        "ok": 0,
        "warning": 0,
        "error": 0,
        "not_available": 0
    }

    for check_name in required_checks:
        check_status = checks.get(check_name, {}).get("status", "not_available")
        if check_status in check_summary:
            check_summary[check_status] = check_summary[check_status] + 1

    return jsonify({
        "status": status_val,
        "initialization": {
            "pending": pending,
            "completed": completed,
            "failed": failed,
            "progress": {
                "total": len(pending) + len(completed) + len(failed),
                "completed": len(completed),
                "failed": len(failed),
                "pending": len(pending)
            }
        },
        "readiness_checks": checks,
        "check_summary": check_summary,
        "integrations": integrations_status,
        "missing_dependencies": missing_dependencies,
        "ready": (status_val == "ready")
    }), 200


@app.route("/api/comfyui/generate", methods=["POST"])
def comfyui_generate():
    """ComfyUIで画像生成"""
    data = request.json
    prompt = data.get("prompt", "")
    negative_prompt = data.get("negative_prompt", "")
    width = data.get("width", 512)
    height = data.get("height", 512)
    steps = data.get("steps", 20)
    cfg_scale = data.get("cfg_scale", 7.0)
    seed = data.get("seed", -1)

    comfyui = integrations.get("comfyui")
    if not comfyui or not comfyui.is_available():
        return jsonify({"error": "ComfyUIが利用できません"}), 503

    prompt_id = comfyui.generate_image(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        steps=steps,
        cfg_scale=cfg_scale,
        seed=seed
    )

    if prompt_id:
        # n8n Webhookに通知（オプション）
        n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL")
        if n8n_webhook_url and REQUESTS_AVAILABLE:
            try:
                requests.post(n8n_webhook_url, json={
                    "prompt_id": prompt_id,
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": width,
                    "height": height,
                    "steps": steps,
                    "cfg_scale": cfg_scale,
                    "seed": seed,
                    "status": "generated",
                    "timestamp": datetime.now().isoformat()
                }, timeout=5)
                logger.info(f"n8n Webhookに通知を送信しました: {prompt_id}")
            except Exception as e:
                logger.warning(f"n8n Webhook通知に失敗: {e}")

        return jsonify({"prompt_id": prompt_id, "status": "success"})
    else:
        return jsonify({"error": "画像生成に失敗しました"}), 500


@app.route("/api/svi/generate", methods=["POST"])
def svi_generate_video():
    """SVI × Wan 2.2で動画生成"""
    if not SVI_WAN22_AVAILABLE:
        return jsonify({"error": "SVI × Wan 2.2動画生成統合が利用できません"}), 503

    data = request.json
    start_image_path = data.get("start_image_path", "")
    prompt = data.get("prompt", "")
    video_length_seconds = data.get("video_length_seconds", 5)
    steps = data.get("steps", 6)
    motion_strength = data.get("motion_strength", 1.3)
    sage_attention = data.get("sage_attention", True)
    extend_enabled = data.get("extend_enabled", False)
    timestamped_prompts = data.get("timestamped_prompts")

    svi = integrations.get("svi_wan22")
    if not svi or not svi.is_available():
        return jsonify({"error": "SVI × Wan 2.2が利用できません"}), 503

    prompt_id = svi.generate_video(
        start_image_path=start_image_path,
        prompt=prompt,
        video_length_seconds=video_length_seconds,
        steps=steps,
        motion_strength=motion_strength,
        sage_attention=sage_attention,
        extend_enabled=extend_enabled,
        timestamped_prompts=timestamped_prompts
    )

    if prompt_id:
        return jsonify({
            "prompt_id": prompt_id,
            "status": "success",
            "message": "動画生成が開始されました"
        })
    else:
        return jsonify({"error": "動画生成に失敗しました"}), 500


@app.route("/api/svi/extend", methods=["POST"])
def svi_extend_video():
    """既存の動画を延長"""
    if not SVI_WAN22_AVAILABLE:
        return jsonify({"error": "SVI × Wan 2.2動画生成統合が利用できません"}), 503

    data = request.json
    previous_video_path = data.get("previous_video_path", "")
    prompt = data.get("prompt", "")
    extend_seconds = data.get("extend_seconds", 5)
    steps = data.get("steps", 6)
    motion_strength = data.get("motion_strength", 1.3)

    svi = integrations.get("svi_wan22")
    if not svi or not svi.is_available():
        return jsonify({"error": "SVI × Wan 2.2が利用できません"}), 503

    prompt_id = svi.extend_video(
        previous_video_path=previous_video_path,
        prompt=prompt,
        extend_seconds=extend_seconds,
        steps=steps,
        motion_strength=motion_strength
    )

    if prompt_id:
        return jsonify({
            "prompt_id": prompt_id,
            "status": "success",
            "message": "動画延長が開始されました"
        })
    else:
        return jsonify({"error": "動画延長に失敗しました"}), 500


@app.route("/api/svi/story", methods=["POST"])
def svi_create_story_video():
    """ストーリー性のある長編動画を作成"""
    if not SVI_WAN22_AVAILABLE:
        return jsonify({"error": "SVI × Wan 2.2動画生成統合が利用できません"}), 503

    data = request.json
    start_image_path = data.get("start_image_path", "")
    story_prompts = data.get("story_prompts", [])
    segment_length_seconds = data.get("segment_length_seconds", 5)
    steps = data.get("steps", 6)
    motion_strength = data.get("motion_strength", 1.3)

    svi = integrations.get("svi_wan22")
    if not svi or not svi.is_available():
        return jsonify({"error": "SVI × Wan 2.2が利用できません"}), 503

    execution_ids = svi.create_story_video(
        start_image_path=start_image_path,
        story_prompts=story_prompts,
        segment_length_seconds=segment_length_seconds,
        steps=steps,
        motion_strength=motion_strength
    )

    return jsonify({
        "execution_ids": execution_ids,
        "status": "success",
        "message": f"{len(execution_ids)}個のセグメントの生成が開始されました"
    })


@app.route("/api/svi/queue", methods=["GET"])
def svi_get_queue():
    """キュー状態を取得"""
    if not SVI_WAN22_AVAILABLE:
        return jsonify({"error": "SVI × Wan 2.2動画生成統合が利用できません"}), 503

    svi = integrations.get("svi_wan22")
    if not svi or not svi.is_available():
        return jsonify({"error": "SVI × Wan 2.2が利用できません"}), 503

    queue_status = svi.get_queue_status()
    return jsonify(queue_status)


@app.route("/api/svi/history", methods=["GET"])
def svi_get_history():
    """実行履歴を取得"""
    if not SVI_WAN22_AVAILABLE:
        return jsonify({"error": "SVI × Wan 2.2動画生成統合が利用できません"}), 503

    max_items = int(request.args.get("max_items", 10))

    svi = integrations.get("svi_wan22")
    if not svi or not svi.is_available():
        return jsonify({"error": "SVI × Wan 2.2が利用できません"}), 503

    history = svi.get_history(max_items=max_items)
    return jsonify({"history": history})


@app.route("/api/svi/batch/generate", methods=["POST"])
def svi_batch_generate():
    """複数の動画を一括生成"""
    if not SVI_WAN22_AVAILABLE:
        return jsonify({"error": "SVI × Wan 2.2動画生成統合が利用できません"}), 503

    svi = integrations.get("svi_wan22")
    if not svi or not svi.is_available():
        return jsonify({"error": "SVI × Wan 2.2が利用できません"}), 503

    try:
        data = request.json
        batch_items = data.get("batch_items", [])

        if not batch_items:
            return jsonify({"error": "batch_itemsが指定されていません"}), 400

        execution_ids = []
        for item in batch_items:
            prompt_id = svi.generate_video(
                start_image_path=item.get("start_image_path", ""),
                prompt=item.get("prompt", ""),
                video_length_seconds=item.get("video_length_seconds", 5),
                steps=item.get("steps", 6),
                motion_strength=item.get("motion_strength", 1.3),
                sage_attention=item.get("sage_attention", True),
                extend_enabled=item.get("extend_enabled", False),
                timestamped_prompts=item.get("timestamped_prompts")
            )
            if prompt_id:
                execution_ids.append(prompt_id)

        return jsonify({
            "execution_ids": execution_ids,
            "total": len(batch_items),
            "success": len(execution_ids),
            "status": "success"
        })
    except Exception as e:
        logger.error(f"SVIバッチ生成エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/svi/status/<prompt_id>", methods=["GET"])
def svi_get_status(prompt_id):
    """特定の実行IDの状態を取得"""
    if not SVI_WAN22_AVAILABLE:
        return jsonify({"error": "SVI × Wan 2.2動画生成統合が利用できません"}), 503

    svi = integrations.get("svi_wan22")
    if not svi or not svi.is_available():
        return jsonify({"error": "SVI × Wan 2.2が利用できません"}), 503

    try:
        # 履歴から該当する実行IDを検索
        history = svi.get_history(max_items=100)
        for item in history:
            if item.get("prompt_id") == prompt_id:
                return jsonify({
                    "prompt_id": prompt_id,
                    "status": item.get("status", "unknown"),
                    "details": item
                })

        return jsonify({
            "prompt_id": prompt_id,
            "status": "not_found",
            "message": "実行IDが見つかりません"
        }), 404
    except Exception as e:
        logger.error(f"SVI状態取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/ltx2/generate", methods=["POST"])
def ltx2_generate_video():
    """LTX-2で動画生成（Super LTX-2設定）"""
    if not LTX2_AVAILABLE:
        return jsonify({"error": "LTX-2動画生成統合が利用できません"}), 503

    data = request.json
    start_image_path = data.get("start_image_path", "")
    prompt = data.get("prompt", "")
    negative_prompt = data.get("negative_prompt", "")
    video_length_seconds = data.get("video_length_seconds", 5)
    width = data.get("width", 512)
    height = data.get("height", 512)
    use_two_pass = data.get("use_two_pass", True)
    use_nag = data.get("use_nag", True)
    use_res2s_sampler = data.get("use_res2s_sampler", True)
    model_name = data.get("model_name", "ltx2-q8.gguf")

    ltx2 = integrations.get("ltx2")
    if not ltx2 or not ltx2.is_available():
        return jsonify({"error": "LTX-2が利用できません"}), 503

    prompt_id = ltx2.generate_video(
        start_image_path=start_image_path,
        prompt=prompt,
        negative_prompt=negative_prompt,
        video_length_seconds=video_length_seconds,
        width=width,
        height=height,
        use_two_pass=use_two_pass,
        use_nag=use_nag,
        use_res2s_sampler=use_res2s_sampler,
        model_name=model_name
    )

    if prompt_id:
        return jsonify({
            "prompt_id": prompt_id,
            "status": "success",
            "message": "動画生成が開始されました（Super LTX-2設定）"
        })
    else:
        return jsonify({"error": "動画生成に失敗しました"}), 500


@app.route("/api/ltx2/queue", methods=["GET"])
def ltx2_get_queue():
    """LTX-2のキュー状態を取得"""
    if not LTX2_AVAILABLE:
        return jsonify({"error": "LTX-2動画生成統合が利用できません"}), 503

    ltx2 = integrations.get("ltx2")
    if not ltx2 or not ltx2.is_available():
        return jsonify({"error": "LTX-2が利用できません"}), 503

    try:
        queue_status = ltx2.get_queue_status()
        return jsonify(queue_status)
    except Exception as e:
        logger.error(f"LTX-2キュー状態取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/ltx2/history", methods=["GET"])
def ltx2_get_history():
    """LTX-2の実行履歴を取得"""
    if not LTX2_AVAILABLE:
        return jsonify({"error": "LTX-2動画生成統合が利用できません"}), 503

    ltx2 = integrations.get("ltx2")
    if not ltx2 or not ltx2.is_available():
        return jsonify({"error": "LTX-2が利用できません"}), 503

    try:
        max_items = request.args.get("max_items", 10, type=int)
        history = ltx2.get_history(max_items=max_items)
        return jsonify({"history": history})
    except Exception as e:
        logger.error(f"LTX-2履歴取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/ltx2/status/<prompt_id>", methods=["GET"])
def ltx2_get_status(prompt_id):
    """特定の実行IDの状態を取得"""
    if not LTX2_AVAILABLE:
        return jsonify({"error": "LTX-2動画生成統合が利用できません"}), 503

    ltx2 = integrations.get("ltx2")
    if not ltx2 or not ltx2.is_available():
        return jsonify({"error": "LTX-2が利用できません"}), 503

    try:
        # 履歴から該当する実行IDを検索
        history = ltx2.get_history(max_items=100)
        for item in history:
            if item.get("prompt_id") == prompt_id:
                return jsonify({
                    "prompt_id": prompt_id,
                    "status": item.get("status", "unknown"),
                    "details": item
                })

        return jsonify({
            "prompt_id": prompt_id,
            "status": "not_found",
            "message": "実行IDが見つかりません"
        }), 404
    except Exception as e:
        logger.error(f"LTX-2状態取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


# ========================================
# SVI自動化 API エンドポイント
# ========================================

SVI_AUTOMATION_AVAILABLE = False
try:
    from svi_automation import SVIAutomation
    SVI_AUTOMATION_AVAILABLE = True
except ImportError:
    logger.warning("SVI自動化モジュールが見つかりません")


@app.route("/api/svi/automation/watch", methods=["POST"])
def svi_automation_watch():
    """フォルダ監視を開始"""
    if not SVI_AUTOMATION_AVAILABLE:
        return jsonify({"error": "SVI自動化モジュールが利用できません"}), 503

    try:
        data = request.json
        folder_path = data.get("folder_path", "")
        auto_generate = data.get("auto_generate", True)
        default_prompt = data.get("default_prompt")

        automation = SVIAutomation()
        success = automation.watch_folder(
            folder_path=folder_path,
            auto_generate=auto_generate,
            default_prompt=default_prompt
        )

        if success:
            automation.start_scheduler()
            return jsonify({
                "status": "success",
                "message": f"フォルダ監視を開始しました: {folder_path}"
            })
        else:
            return jsonify({"error": "フォルダ監視の開始に失敗しました"}), 500
    except Exception as e:
        logger.error(f"SVI自動化フォルダ監視エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/svi/automation/schedule", methods=["POST"])
def svi_automation_schedule():
    """スケジュールタスクを追加"""
    if not SVI_AUTOMATION_AVAILABLE:
        return jsonify({"error": "SVI自動化モジュールが利用できません"}), 503

    try:
        from datetime import datetime, timedelta

        data = request.json
        task_name = data.get("task_name", f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        schedule_time_str = data.get("schedule_time")
        image_path = data.get("image_path", "")
        prompt = data.get("prompt", "")
        video_length_seconds = data.get("video_length_seconds", 5)
        repeat = data.get("repeat", False)
        repeat_interval_seconds = data.get("repeat_interval_seconds")

        if schedule_time_str:
            schedule_time = datetime.fromisoformat(schedule_time_str)
        else:
            schedule_time = datetime.now() + timedelta(hours=1)

        automation = SVIAutomation()
        automation.schedule_task(
            task_name=task_name,
            schedule_time=schedule_time,
            image_path=image_path,
            prompt=prompt,
            video_length_seconds=video_length_seconds,
            repeat=repeat,
            repeat_interval=timedelta(seconds=repeat_interval_seconds) if repeat_interval_seconds else None
        )

        return jsonify({
            "status": "success",
            "message": f"スケジュールタスクを追加しました: {task_name}",
            "schedule_time": schedule_time.isoformat()
        })
    except Exception as e:
        logger.error(f"SVI自動化スケジュールエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/svi/automation/batch", methods=["POST"])
def svi_automation_batch():
    """フォルダ内の画像を一括処理"""
    if not SVI_AUTOMATION_AVAILABLE:
        return jsonify({"error": "SVI自動化モジュールが利用できません"}), 503

    try:
        data = request.json
        folder_path = data.get("folder_path", "")
        prompt = data.get("prompt")
        max_files = data.get("max_files")

        automation = SVIAutomation()
        execution_ids = automation.batch_process_folder(
            folder_path=folder_path,
            prompt=prompt,
            max_files=max_files
        )

        return jsonify({
            "status": "success",
            "execution_ids": execution_ids,
            "count": len(execution_ids)
        })
    except Exception as e:
        logger.error(f"SVI自動化バッチ処理エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/google_drive/upload", methods=["POST"])
def google_drive_upload():
    """Google Driveにファイルをアップロード"""
    missing_resp = _require_env_for_integration(
        "GoogleDrive",
        ["GOOGLE_DRIVE_CREDENTIALS", "GOOGLE_DRIVE_TOKEN"],
    )
    if missing_resp:
        return missing_resp

    data = request.json
    file_path = data.get("file_path", "")
    folder_id = data.get("folder_id")

    google_drive = integrations.get("google_drive")
    if not google_drive or not google_drive.is_available():
        return jsonify({"error": "GoogleDriveが利用できません"}), 503

    file_id = google_drive.upload_file(file_path, folder_id)

    if file_id:
        return jsonify({"file_id": file_id, "status": "success"})
    else:
        return jsonify({"error": "アップロードに失敗しました"}), 500


@app.route("/api/civitai/search", methods=["GET"])
def civitai_search():
    """CivitAIでモデルを検索"""
    missing_resp = _require_env_for_integration("CivitAI", ["CIVITAI_API_KEY"])
    if missing_resp:
        return missing_resp

    query = request.args.get("query", "")
    limit = int(request.args.get("limit", 20))
    model_type = request.args.get("type")

    civitai = integrations.get("civitai")
    if not civitai:
        return jsonify({"error": "CivitAIが利用できません"}), 503

    models = civitai.search_models(query=query, limit=limit, model_type=model_type)
    return jsonify({"models": models, "count": len(models)})


@app.route("/api/langchain/chat", methods=["POST"])
def langchain_chat():
    """LangChainでチャット"""
    data = request.json
    message = data.get("message", "")
    system_prompt = data.get("system_prompt")

    langchain = integrations.get("langchain")
    if not langchain or not langchain.is_available():
        return jsonify({"error": "LangChainが利用できません"}), 503

    response = langchain.chat(message, system_prompt)
    return jsonify({"response": response, "status": "success"})


@app.route("/api/mem0/add", methods=["POST"])
def mem0_add():
    """Mem0にメモリを追加"""
    data = request.json
    memory_text = data.get("memory_text", "")
    user_id = data.get("user_id")
    metadata = data.get("metadata")

    mem0 = integrations.get("mem0")
    if not mem0 or not mem0.is_available():
        return jsonify({"error": "Mem0が利用できません"}), 503

    memory_id = mem0.add_memory(memory_text, user_id, metadata)

    if memory_id:
        return jsonify({"memory_id": memory_id, "status": "success"})
    else:
        return jsonify({"error": "メモリ追加に失敗しました"}), 500


@app.route("/api/obsidian/create", methods=["POST"])
def obsidian_create():
    """Obsidianにノートを作成"""
    data = request.json
    title = data.get("title", "")
    content = data.get("content", "")
    tags = data.get("tags", [])
    folder = data.get("folder")

    obsidian = integrations.get("obsidian")
    if not obsidian or not obsidian.is_available():
        return jsonify({"error": "Obsidianが利用できません"}), 503

    note_path = obsidian.create_note(title, content, tags, folder)

    if note_path:
        return jsonify({"note_path": str(note_path), "status": "success"})
    else:
        return jsonify({"error": "ノート作成に失敗しました"}), 500


@app.route("/api/searxng/search", methods=["GET", "POST"])
def searxng_search():
    """SearXNGでWeb検索を実行"""
    try:
        from searxng_integration import SearXNGIntegration

        searxng = SearXNGIntegration()

        if request.method == "GET":
            query = request.args.get("query", "")
            max_results = int(request.args.get("max_results", 10))
            language = request.args.get("language", "ja")
        else:
            data = request.json or {}
            query = data.get("query", "")
            max_results = data.get("max_results", 10)
            language = data.get("language", "ja")

        if not query:
            return jsonify({"error": "検索クエリが必要です"}), 400

        result = searxng.search(
            query=query,
            max_results=max_results,
            language=language
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"SearXNG検索エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/brave/search", methods=["GET", "POST"])
def brave_search():
    """Brave Search APIでWeb検索を実行"""
    try:
        if not BRAVE_SEARCH_AVAILABLE:
            return jsonify({"error": "Brave Search統合が利用できません"}), 503

        brave = BraveSearchIntegration()

        if not brave.is_available():
            return jsonify({"error": "Brave Search APIキーが設定されていません"}), 503

        if request.method == "GET":
            query = request.args.get("query", "")
            count = int(request.args.get("count", 10))
            search_lang = request.args.get("search_lang", "jp")  # Brave Search APIは'jp'を使用
            country = request.args.get("country", "JP")
            freshness = request.args.get("freshness")
        else:
            data = request.json or {}
            query = data.get("query", "")
            count = data.get("count", 10)
            search_lang = data.get("search_lang", "jp")  # Brave Search APIは'jp'を使用
            country = data.get("country", "JP")
            freshness = data.get("freshness")

        if not query:
            return jsonify({"error": "検索クエリが必要です"}), 400

        results = brave.search(
            query=query,
            count=min(count, 20),  # 最大20件
            search_lang=search_lang,
            country=country,
            freshness=freshness
        )

        return jsonify({
            "query": query,
            "total_results": len(results),
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "description": r.description,
                    "age": r.age
                }
                for r in results
            ]
        })

    except Exception as e:
        logger.error(f"Brave Search検索エラー: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/base-ai/chat", methods=["POST"])
def base_ai_chat():
    """Base AI APIでチャットを実行"""
    try:
        if not BASE_AI_AVAILABLE:
            return jsonify({"error": "Base AI統合が利用できません"}), 503

        data = request.json or {}
        prompt = data.get("prompt", "")
        system_prompt = data.get("system_prompt")
        use_free = data.get("use_free", False)
        temperature = data.get("temperature", 0.7)
        max_tokens = data.get("max_tokens")

        if not prompt:
            return jsonify({"error": "プロンプトが必要です"}), 400

        base_ai = BaseAIIntegration(use_free=use_free)

        if not base_ai.is_available():
            return jsonify({"error": "Base AI APIキーが設定されていません"}), 503

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = base_ai.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return jsonify({
            "response": response.content,
            "model": response.model,
            "usage": response.usage,
            "use_free": use_free
        })

    except Exception as e:
        logger.error(f"Base AIチャットエラー: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/oh_my_opencode/execute", methods=["POST"])
def oh_my_opencode_execute():
    """OH MY OPENCODEでタスクを実行"""
    try:
        if not OH_MY_OPENCODE_AVAILABLE:
            return jsonify({"error": "OH MY OPENCODE統合が利用できません"}), 503

        oh_my_opencode = integrations.get("oh_my_opencode")
        if not oh_my_opencode:
            return jsonify({"error": "OH MY OPENCODEが初期化されていません"}), 503

        data = request.json or {}
        task_description = data.get("task_description", "")
        mode = data.get("mode", "normal")
        task_type = data.get("task_type", "general")
        use_trinity = data.get("use_trinity", None)

        if not task_description:
            return jsonify({"error": "タスク説明が必要です"}), 400

        import asyncio
        # Python 3.10+ 対応: get_running_loop() を使用
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        from oh_my_opencode_integration import ExecutionMode, TaskType

        result = loop.run_until_complete(
            oh_my_opencode.execute_task(
                task_description=task_description,
                mode=ExecutionMode(mode) if mode else None,
                task_type=TaskType(task_type) if task_type else None,
                use_trinity=use_trinity
            )
        )

        return jsonify({
            "result": {
                "task_id": result.task_id,
                "status": result.status,
                "result": result.result,
                "error": result.error,
                "cost": result.cost,
                "execution_time": result.execution_time
            },
            "status": "success"
        })
    except Exception as e:
        logger.error(f"OH MY OPENCODE実行エラー: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/integrations/status", methods=["GET"])
def integrations_status():
    """すべての統合システムの状態を取得"""
    status = {}

    for name, integration in integrations.items():
        if hasattr(integration, "is_available"):
            status[name] = {
                "available": integration.is_available(),
                "type": type(integration).__name__
            }
        else:
            status[name] = {
                "available": False,
                "type": type(integration).__name__
            }

    # ローカルLLMシステムの状態も追加
    if LOCAL_LLM_AVAILABLE and "local_llm" in integrations:
        try:
            llm_status = integrations["local_llm"].get_status()
            status["local_llm_systems"] = llm_status
        except:
            pass

    return jsonify({"integrations": status})


@app.route("/api/local-llm/systems", methods=["GET"])
def local_llm_systems():
    """ローカルLLMシステム一覧を取得"""
    if not LOCAL_LLM_AVAILABLE:
        return jsonify({"error": "ローカルLLM統合が利用できません"}), 503

    if "local_llm" not in integrations:
        return jsonify({"error": "ローカルLLMが初期化されていません"}), 503

    try:
        status = integrations["local_llm"].get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"ローカルLLMシステム取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


# ========================================
# 拡張フェーズ API エンドポイント
# ========================================

@app.route("/api/llm/route", methods=["POST"])
def llm_route():
    """LLMルーティング（ロール別モデル + fallback）"""
    if not LLM_ROUTING_AVAILABLE:
        return jsonify({"error": "LLMルーティングが利用できません"}), 503

    router = integrations.get("llm_routing")
    if not router:
        return jsonify({"error": "LLMルーティングが初期化されていません"}), 503

    try:
        data = request.json
        task_type = data.get("task_type", "conversation")
        prompt = data.get("prompt", "")
        memory_refs = data.get("memory_refs", [])
        tools_used = data.get("tools_used", [])

        result = router.route(
            task_type=task_type,
            prompt=prompt,
            memory_refs=memory_refs,
            tools_used=tools_used
        )

        return jsonify(result)
    except Exception as e:
        logger.error(f"LLMルーティングエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/llm/chat", methods=["POST"])
def llm_chat():
    """Ollamaチャット（記憶システムと自動連携）"""
    if not LLM_ROUTING_AVAILABLE:
        return jsonify({"error": "LLMルーティングが利用できません"}), 503

    router = integrations.get("llm_routing")
    if not router:
        return jsonify({"error": "LLMルーティングが初期化されていません"}), 503

    try:
        data = request.json
        messages = data.get("messages", [])
        model = data.get("model")  # オプション
        user_id = data.get("user_id", "default")
        load_history = data.get("load_history", True)
        auto_save = data.get("auto_save", True)

        if not messages:
            return jsonify({"error": "messagesが必要です"}), 400

        result = router.chat(
            messages=messages,
            model=model,
            user_id=user_id,
            load_history=load_history,
            auto_save=auto_save
        )

        return jsonify(result)
    except Exception as e:
        logger.error(f"Ollamaチャットエラー: {e}")
        return jsonify({"error": str(e)}), 500


# ========================================
# 拡張LLMルーティング API エンドポイント（難易度判定対応）
# ========================================

@app.route("/api/llm/route-enhanced", methods=["POST"])
def llm_route_enhanced():
    """
    拡張LLMルーティング（難易度判定対応）

    リクエスト例:
    {
        "prompt": "この関数のタイポを修正して",
        "context": {
            "file_path": "path/to/file.py",
            "code_context": "def hello():\n    print('helo')",
            "task_type": "implementation"
        },
        "preferences": {
            "prefer_speed": true,
            "prefer_quality": false,
            "force_model": null
        }
    }
    """
    if not ENHANCED_LLM_ROUTING_AVAILABLE:
        return jsonify({"error": "拡張LLMルーティングが利用できません"}), 503

    router = integrations.get("enhanced_llm_routing")
    if not router:
        return jsonify({"error": "拡張LLMルーティングが初期化されていません"}), 503

    try:
        data = request.json
        prompt = data.get("prompt", "")
        context = data.get("context", {})
        preferences = data.get("preferences", {})

        if not prompt:
            return jsonify({"error": "promptが必要です"}), 400

        result = router.route(
            prompt=prompt,
            context=context,
            preferences=preferences
        )

        return jsonify(result)
    except Exception as e:
        logger.error(f"拡張LLMルーティングエラー: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/llm/analyze", methods=["POST"])
def llm_analyze_difficulty():
    """
    プロンプトの難易度を分析（LLM呼び出しなし）

    リクエスト例:
    {
        "prompt": "このコードをリファクタリングして",
        "context": {
            "code_context": "def hello():\n    print('hello')"
        }
    }
    """
    if not ENHANCED_LLM_ROUTING_AVAILABLE:
        return jsonify({"error": "拡張LLMルーティングが利用できません"}), 503

    router = integrations.get("enhanced_llm_routing")
    if not router:
        return jsonify({"error": "拡張LLMルーティングが初期化されていません"}), 503

    try:
        data = request.json
        prompt = data.get("prompt", "")
        context = data.get("context", {})

        if not prompt:
            return jsonify({"error": "promptが必要です"}), 400

        # 難易度分析
        analyzer = router.analyzer
        score = analyzer.calculate_difficulty(prompt, context)
        level = analyzer.get_difficulty_level(score)
        recommended_model = analyzer.get_recommended_model(score)

        return jsonify({
            "difficulty_score": score,
            "difficulty_level": level,
            "recommended_model": recommended_model
        })
    except Exception as e:
        logger.error(f"難易度分析エラー: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/llm/models-enhanced", methods=["GET"])
def llm_models_enhanced():
    """利用可能なモデル一覧を取得（拡張LLMルーティング）"""
    if not ENHANCED_LLM_ROUTING_AVAILABLE:
        return jsonify({"error": "拡張LLMルーティングが利用できません"}), 503

    router = integrations.get("enhanced_llm_routing")
    if not router:
        return jsonify({"error": "拡張LLMルーティングが初期化されていません"}), 503

    try:
        models = router.get_available_models()
        return jsonify({"models": models})
    except Exception as e:
        logger.error(f"モデル一覧取得エラー: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ========================================
# LFM 2.5専用APIエンドポイント
# ========================================

# LFM 2.5クライアントのインポート
LFM25_AVAILABLE = False
try:
    from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType
    LFM25_AVAILABLE = True
except ImportError:
    logger.warning("LFM 2.5クライアントが利用できません")


@app.route("/api/lfm25/chat", methods=["POST"])
def lfm25_chat():
    """LFM 2.5でチャット（超軽量・超高速）"""
    if not LFM25_AVAILABLE:
        return jsonify({"error": "LFM 2.5クライアントが利用できません"}), 503

    try:
        data = request.json or {}
        message = data.get("message", "")
        task_type = data.get("task_type", "conversation")
        use_cache = data.get("use_cache", True)
        temperature = data.get("temperature", 0.7)
        max_tokens = data.get("max_tokens")

        if not message:
            return jsonify({"error": "messageパラメータが必要です"}), 400

        # タスクタイプの変換
        if task_type == "lightweight_conversation":
            task_type_enum = TaskType.LIGHTWEIGHT_CONVERSATION
        elif task_type == "conversation":
            task_type_enum = TaskType.CONVERSATION
        else:
            task_type_enum = TaskType.CONVERSATION

        # LFM 2.5クライアントでチャット
        client = AlwaysReadyLLMClient()
        response = client.chat(
            message=message,
            model=ModelType.ULTRA_LIGHT,
            task_type=task_type_enum,
            use_cache=use_cache,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return jsonify({
            "success": True,
            "response": response.response,
            "model": response.model,
            "latency_ms": response.latency_ms,
            "cached": response.cached,
            "source": response.source,
            "tokens": response.tokens
        })

    except Exception as e:
        logger.error(f"LFM 2.5チャットエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/lfm25/lightweight", methods=["POST"])
def lfm25_lightweight():
    """LFM 2.5軽量会話（オフライン会話・下書き・整理専用）"""
    if not LFM25_AVAILABLE:
        return jsonify({"error": "LFM 2.5クライアントが利用できません"}), 503

    try:
        data = request.json or {}
        message = data.get("message", "")
        use_cache = data.get("use_cache", True)

        if not message:
            return jsonify({"error": "messageパラメータが必要です"}), 400

        # LFM 2.5クライアントで軽量会話
        client = AlwaysReadyLLMClient()
        response = client.chat(
            message=message,
            model=ModelType.ULTRA_LIGHT,
            task_type=TaskType.LIGHTWEIGHT_CONVERSATION,
            use_cache=use_cache
        )

        return jsonify({
            "success": True,
            "response": response.response,
            "model": response.model,
            "latency_ms": response.latency_ms,
            "cached": response.cached,
            "source": response.source,
            "task_type": "lightweight_conversation"
        })

    except Exception as e:
        logger.error(f"LFM 2.5軽量会話エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/lfm25/batch", methods=["POST"])
def lfm25_batch():
    """LFM 2.5バッチチャット（複数メッセージを順次処理）"""
    if not LFM25_AVAILABLE:
        return jsonify({"error": "LFM 2.5クライアントが利用できません"}), 503

    try:
        data = request.json or {}
        messages = data.get("messages", [])
        task_type = data.get("task_type", "conversation")

        if not messages or not isinstance(messages, list):
            return jsonify({"error": "messagesパラメータ（リスト）が必要です"}), 400

        # タスクタイプの変換
        if task_type == "lightweight_conversation":
            task_type_enum = TaskType.LIGHTWEIGHT_CONVERSATION
        else:
            task_type_enum = TaskType.CONVERSATION

        # LFM 2.5クライアントでバッチチャット
        client = AlwaysReadyLLMClient()
        results = client.batch_chat(
            messages=messages,
            model=ModelType.ULTRA_LIGHT,
            task_type=task_type_enum
        )

        # 結果を整形
        formatted_results = []
        for i, result in enumerate(results):
            formatted_results.append({
                "index": i,
                "message": messages[i] if i < len(messages) else "",
                "response": result.response,
                "model": result.model,
                "latency_ms": result.latency_ms,
                "cached": result.cached,
                "source": result.source
            })

        return jsonify({
            "success": True,
            "results": formatted_results,
            "count": len(formatted_results)
        })

    except Exception as e:
        logger.error(f"LFM 2.5バッチチャットエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/lfm25/status", methods=["GET"])
def lfm25_status():
    """LFM 2.5の状態を取得"""
    if not LFM25_AVAILABLE:
        return jsonify({
            "available": False,
            "error": "LFM 2.5クライアントが利用できません"
        }), 503

    try:
        # 簡単なテストリクエストで状態確認
        client = AlwaysReadyLLMClient()
        test_response = client.chat(
            "test",
            model=ModelType.ULTRA_LIGHT,
            task_type=TaskType.CONVERSATION
        )

        return jsonify({
            "available": True,
            "model": ModelType.ULTRA_LIGHT.value,
            "status": "operational",
            "test_latency_ms": test_response.latency_ms,
            "test_source": test_response.source
        })

    except Exception as e:
        return jsonify({
            "available": False,
            "error": str(e)
        }), 500


@app.route("/api/cache/get", methods=["GET"])
def cache_get():
    """キャッシュから取得（統一キャッシュシステム優先）"""
    # 統一キャッシュシステムを優先
    if UNIFIED_CACHE_AVAILABLE:
        unified_cache = integrations.get("unified_cache")
        if unified_cache:
            try:
                cache_key = request.args.get("key")
                cache_type = request.args.get("type", "api_response")
                if not cache_key:
                    return jsonify({"error": "keyパラメータが必要です"}), 400

                # 統一キャッシュシステムはkeyをkwargsで受け取る
                cached_data = unified_cache.get(cache_type, key=cache_key)
                if cached_data is not None:
                    return jsonify({
                        "found": True,
                        "data": cached_data,
                        "cache_type": "unified"
                    })
                else:
                    return jsonify({
                        "found": False,
                        "data": None
                    })
            except Exception as e:
                logger.warning(f"統一キャッシュ取得エラー: {e}")
                # フォールバック: Redisキャッシュに切り替え

    # Redisキャッシュ（フォールバック）
    if REDIS_CACHE_AVAILABLE:
        try:
            cache_key = request.args.get("key")
            if not cache_key:
                return jsonify({"error": "keyパラメータが必要です"}), 400

            import redis
            redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                decode_responses=True
            )
            cached_data = redis_client.get(cache_key)

            if cached_data:
                import json
                result = json.loads(cached_data)
                return jsonify({
                    "found": True,
                    "data": result,
                    "cache_type": "redis"
                })
            else:
                return jsonify({
                    "found": False,
                    "data": None
                })
        except Exception as e:
            logger.warning(f"キャッシュ取得エラー: {e}")
            return jsonify({
                "found": False,
                "error": str(e)
            })

    return jsonify({"error": "キャッシュシステムが利用できません"}), 503


@app.route("/api/cache/set", methods=["POST"])
def cache_set():
    """キャッシュに保存（統一キャッシュシステム優先）"""
    try:
        data = request.json
        cache_key = data.get("key")
        cache_value = data.get("value")
        cache_type = data.get("type", "api_response")
        ttl_seconds = data.get("ttl_seconds", 86400)  # デフォルト24時間

        if not cache_key or cache_value is None:
            return jsonify({"error": "keyとvalueが必要です"}), 400

        # 統一キャッシュシステムを優先
        if UNIFIED_CACHE_AVAILABLE:
            unified_cache = integrations.get("unified_cache")
            if unified_cache:
                try:
                    # 統一キャッシュシステムはkeyをkwargsで受け取る
                    unified_cache.set(cache_type, cache_value, ttl_seconds=ttl_seconds, key=cache_key)
                    return jsonify({
                        "status": "success",
                        "key": cache_key,
                        "ttl_seconds": ttl_seconds,
                        "cache_type": "unified"
                    })
                except Exception as e:
                    logger.warning(f"統一キャッシュ保存エラー: {e}")
                    # フォールバック: Redisキャッシュに切り替え

        # Redisキャッシュ（フォールバック）
        if REDIS_CACHE_AVAILABLE:
            try:
                import redis
                import json
                redis_client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", 6379)),
                    decode_responses=True
                )

                # 値が文字列でない場合はJSON文字列化
                if isinstance(cache_value, str):
                    value_str = cache_value
                else:
                    value_str = json.dumps(cache_value, ensure_ascii=False)

                redis_client.setex(cache_key, ttl_seconds, value_str)

                return jsonify({
                    "status": "success",
                    "key": cache_key,
                    "ttl_seconds": ttl_seconds,
                    "cache_type": "redis"
                })
            except Exception as e:
                logger.warning(f"キャッシュ保存エラー: {e}")
                return jsonify({"error": str(e)}), 500

        return jsonify({"error": "キャッシュシステムが利用できません"}), 503
    except Exception as e:
        logger.error(f"キャッシュ保存エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/cache/stats", methods=["GET"])
def cache_stats():
    """キャッシュ統計を取得"""
    if UNIFIED_CACHE_AVAILABLE:
        unified_cache = integrations.get("unified_cache")
        if unified_cache:
            try:
                stats = unified_cache.get_stats()
                return jsonify({
                    "status": "success",
                    "stats": stats,
                    "cache_type": "unified"
                })
            except Exception as e:
                logger.warning(f"キャッシュ統計取得エラー: {e}")

    return jsonify({"error": "統一キャッシュシステムが利用できません"}), 503


@app.route("/api/performance/stats", methods=["GET"])
def performance_stats():
    """パフォーマンス統計を取得"""
    if PERFORMANCE_OPTIMIZER_AVAILABLE:
        optimizer = integrations.get("performance_optimizer")
        if optimizer:
            try:
                cache_stats = optimizer.get_cache_stats()
                http_pool_stats = optimizer.get_http_pool_stats()
                config_cache_stats = optimizer.get_config_cache_stats()

                return jsonify({
                    "status": "success",
                    "cache_stats": cache_stats,
                    "http_pool_stats": http_pool_stats,
                    "config_cache_stats": config_cache_stats
                })
            except Exception as e:
                logger.warning(f"パフォーマンス統計取得エラー: {e}")
                return jsonify({"error": str(e)}), 500

    return jsonify({"error": "パフォーマンス最適化システムが利用できません"}), 503


@app.route("/api/memory/store", methods=["POST"])
def memory_store():
    """記憶への保存（統一記憶システム）"""
    if not MEMORY_UNIFIED_AVAILABLE:
        return jsonify({"error": "統一記憶システムが利用できません"}), 503

    memory = integrations.get("memory_unified")
    if not memory:
        return jsonify({"error": "統一記憶システムが初期化されていません"}), 503

    try:
        data = request.json

        # データ形式を統一記憶システムの形式に変換
        if isinstance(data.get("content"), str):
            # contentが文字列の場合、辞書形式に変換
            content = {
                "content": data.get("content", ""),
                "metadata": data.get("metadata", {})
            }
        else:
            # 既に辞書形式の場合
            content = data.get("content", {})
            if not isinstance(content, dict):
                content = {"content": str(content), "metadata": data.get("metadata", {})}

        format_type = data.get("format_type", "auto")

        memory_id = memory.store(content, format_type)

        return jsonify({
            "memory_id": memory_id,
            "status": "success"
        })
    except Exception as e:
        logger.error(f"記憶保存エラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route("/api/memory/recall", methods=["GET"])
def memory_recall():
    """記憶からの検索（統一記憶システム）"""
    if not MEMORY_UNIFIED_AVAILABLE:
        return jsonify({"error": "統一記憶システムが利用できません"}), 503

    memory = integrations.get("memory_unified")
    if not memory:
        return jsonify({"error": "統一記憶システムが初期化されていません"}), 503

    try:
        query = request.args.get("query", "")
        scope = request.args.get("scope", "all")
        limit = int(request.args.get("limit", 10))

        results = memory.recall(query, scope, limit)

        return jsonify({
            "results": results,
            "count": len(results)
        })
    except Exception as e:
        logger.error(f"記憶検索エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/notification/send", methods=["POST"])
def notification_send():
    """通知送信（通知ハブ）"""
    if not NOTIFICATION_HUB_AVAILABLE:
        return jsonify({"error": "通知ハブが利用できません"}), 503

    hub = integrations.get("notification_hub")
    if not hub:
        return jsonify({"error": "通知ハブが初期化されていません"}), 503

    # Slack Webhookが未設定なら、環境変数から設定を試みる（ローカル: .env / CI: env）
    try:
        slack_webhook = (os.getenv("SLACK_WEBHOOK_URL") or "").strip()
        notification_system = getattr(hub, "notification_system", None)
        if notification_system and slack_webhook and not notification_system.slack_webhook_url:
            notification_system.configure_slack(slack_webhook)
    except Exception as e:
        logger.warning(f"通知ハブSlack設定の自動適用に失敗: {e}")

    # まだSlack Webhookが無い場合は、明確な設定エラーを返す
    notification_system = getattr(hub, "notification_system", None)
    if not notification_system or not getattr(notification_system, "slack_webhook_url", None):
        return _config_error_response("NotificationHub(Slack)", ["SLACK_WEBHOOK_URL"])

    try:
        data = request.json
        message = data.get("message", "")
        priority = data.get("priority", "normal")

        results = hub.notify(message, priority)

        return jsonify({
            "results": results,
            "status": "success"
        })
    except Exception as e:
        logger.error(f"通知送信エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/secretary/morning", methods=["POST"])
def secretary_morning():
    """朝のルーチン"""
    if not SECRETARY_AVAILABLE:
        return jsonify({"error": "秘書機能が利用できません"}), 503

    secretary = integrations.get("secretary")
    if not secretary:
        return jsonify({"error": "秘書機能が初期化されていません"}), 503

    try:
        result = secretary.morning_routine()

        return jsonify({
            "schedule": result.get("schedule", []),
            "tasks": result.get("tasks", []),
            "log_diff": result.get("log_diff", {}),
            "report": result.get("report", ""),
            "status": "success"
        })
    except Exception as e:
        logger.error(f"朝のルーチンエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/secretary/noon", methods=["POST"])
def secretary_noon():
    """昼のルーチン"""
    if not SECRETARY_AVAILABLE:
        return jsonify({"error": "秘書機能が利用できません"}), 503

    secretary = integrations.get("secretary")
    if not secretary:
        return jsonify({"error": "秘書機能が初期化されていません"}), 503

    try:
        result = secretary.noon_routine()

        return jsonify({
            "progress": result.get("progress", {}),
            "report": result.get("report", ""),
            "status": "success"
        })
    except Exception as e:
        logger.error(f"昼のルーチンエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/secretary/evening", methods=["POST"])
def secretary_evening():
    """夜のルーチン"""
    if not SECRETARY_AVAILABLE:
        return jsonify({"error": "秘書機能が利用できません"}), 503

    secretary = integrations.get("secretary")
    if not secretary:
        return jsonify({"error": "秘書機能が初期化されていません"}), 503

    try:
        result = secretary.evening_routine()

        return jsonify({
            "daily_report": result.get("daily_report", ""),
            "tomorrow_prep": result.get("tomorrow_prep", {}),
            "report": result.get("report", ""),
            "status": "success"
        })
    except Exception as e:
        logger.error(f"夜のルーチンエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/vscode/open", methods=["POST"])
def vscode_open_file():
    """VS Codeでファイルを開く"""
    try:
        data = request.json or {}
        file_path = data.get("file_path")
        line = data.get("line")
        
        if not file_path:
            return jsonify({"error": "file_pathが必要です"}), 400
        
        import subprocess
        cmd = ["code", file_path]
        if line:
            cmd.extend(["--goto", f"{file_path}:{line}"])
        subprocess.Popen(cmd, shell=True)
        
        return jsonify({
            "status": "success",
            "message": f"VS Codeでファイルを開きました: {file_path}",
            "file_path": file_path,
            "line": line
        })
    except Exception as e:
        logger.error(f"VS Codeファイルオープンエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/vscode/open-folder", methods=["POST"])
def vscode_open_folder():
    """VS Codeでフォルダを開く"""
    try:
        data = request.json or {}
        folder_path = data.get("folder_path")
        
        if not folder_path:
            return jsonify({"error": "folder_pathが必要です"}), 400
        
        import subprocess
        subprocess.Popen(["code", folder_path], shell=True)
        
        return jsonify({
            "status": "success",
            "message": f"VS Codeでフォルダを開きました: {folder_path}",
            "folder_path": folder_path
        })
    except Exception as e:
        logger.error(f"VS Codeフォルダオープンエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/github/repository", methods=["GET"])
def github_repository():
    """GitHubリポジトリ情報を取得"""
    if not GITHUB_AVAILABLE:
        return jsonify({"error": "GitHub統合が利用できません"}), 503

    github = integrations.get("github")
    if not github:
        return jsonify({"error": "GitHub統合が初期化されていません"}), 503

    try:
        owner = request.args.get("owner", "")
        repo = request.args.get("repo", "")

        if not owner or not repo:
            return jsonify({"error": "ownerとrepoパラメータが必要です"}), 400

        repo_info = github.get_repository(owner, repo)

        if repo_info:
            return jsonify({
                "repository": repo_info,
                "status": "success"
            })
        else:
            return jsonify({"error": "リポジトリ情報を取得できませんでした"}), 404
    except Exception as e:
        logger.error(f"GitHubリポジトリ取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/github/commits", methods=["GET"])
def github_commits():
    """GitHubリポジトリの最近のコミットを取得"""
    if not GITHUB_AVAILABLE:
        return jsonify({"error": "GitHub統合が利用できません"}), 503

    github = integrations.get("github")
    if not github:
        return jsonify({"error": "GitHub統合が初期化されていません"}), 503

    try:
        owner = request.args.get("owner", "")
        repo = request.args.get("repo", "")
        branch = request.args.get("branch", "main")
        limit = int(request.args.get("limit", 10))

        if not owner or not repo:
            return jsonify({"error": "ownerとrepoパラメータが必要です"}), 400

        commits = github.get_recent_commits(owner, repo, branch, limit)

        return jsonify({
            "commits": commits,
            "count": len(commits),
            "status": "success"
        })
    except Exception as e:
        logger.error(f"GitHubコミット取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/github/pull_requests", methods=["GET"])
def github_pull_requests():
    """GitHubリポジトリのプルリクエストを取得"""
    if not GITHUB_AVAILABLE:
        return jsonify({"error": "GitHub統合が利用できません"}), 503

    github = integrations.get("github")
    if not github:
        return jsonify({"error": "GitHub統合が初期化されていません"}), 503

    try:
        owner = request.args.get("owner", "")
        repo = request.args.get("repo", "")
        state = request.args.get("state", "open")
        limit = int(request.args.get("limit", 10))

        if not owner or not repo:
            return jsonify({"error": "ownerとrepoパラメータが必要です"}), 400

        prs = github.get_pull_requests(owner, repo, state, limit)

        return jsonify({
            "pull_requests": prs,
            "count": len(prs),
            "status": "success"
        })
    except Exception as e:
        logger.error(f"GitHubプルリクエスト取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/github/search", methods=["GET"])
def github_search():
    """GitHubリポジトリを検索"""
    if not GITHUB_AVAILABLE:
        return jsonify({"error": "GitHub統合が利用できません"}), 503

    github = integrations.get("github")
    if not github:
        return jsonify({"error": "GitHub統合が初期化されていません"}), 503

    try:
        query = request.args.get("query", "")
        limit = int(request.args.get("limit", 10))

        if not query:
            return jsonify({"error": "queryパラメータが必要です"}), 400

        repos = github.search_repositories(query, limit)

        return jsonify({
            "repositories": repos,
            "count": len(repos),
            "status": "success"
        })
    except Exception as e:
        logger.error(f"GitHub検索エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/n8n/workflows", methods=["GET"])
def n8n_workflows():
    """n8nワークフロー一覧を取得"""
    missing_resp = _require_env_for_integration("n8n", ["N8N_BASE_URL", "N8N_API_KEY"])
    if missing_resp:
        return missing_resp

    if not N8N_AVAILABLE:
        return jsonify({"error": "n8n統合が利用できません"}), 503

    n8n = integrations.get("n8n")
    if not n8n or not n8n.is_available():
        return jsonify({"error": "n8n統合が初期化されていません"}), 503

    try:
        workflows = n8n.list_workflows()

        return jsonify({
            "workflows": workflows,
            "count": len(workflows),
            "status": "success"
        })
    except Exception as e:
        logger.error(f"n8nワークフロー一覧取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/n8n/workflow/<workflow_id>", methods=["GET"])
def n8n_workflow(workflow_id):
    """n8nワークフロー情報を取得"""
    missing_resp = _require_env_for_integration("n8n", ["N8N_BASE_URL", "N8N_API_KEY"])
    if missing_resp:
        return missing_resp

    if not N8N_AVAILABLE:
        return jsonify({"error": "n8n統合が利用できません"}), 503

    n8n = integrations.get("n8n")
    if not n8n or not n8n.is_available():
        return jsonify({"error": "n8n統合が初期化されていません"}), 503

    try:
        workflow = n8n.get_workflow(workflow_id)

        if workflow:
            return jsonify({
                "workflow": workflow,
                "status": "success"
            })
        else:
            return jsonify({"error": "ワークフロー情報を取得できませんでした"}), 404
    except Exception as e:
        logger.error(f"n8nワークフロー取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/n8n/workflow/<workflow_id>/execute", methods=["POST"])
def n8n_execute_workflow(workflow_id):
    """n8nワークフローを実行"""
    missing_resp = _require_env_for_integration("n8n", ["N8N_BASE_URL", "N8N_API_KEY"])
    if missing_resp:
        return missing_resp

    if not N8N_AVAILABLE:
        return jsonify({"error": "n8n統合が利用できません"}), 503

    n8n = integrations.get("n8n")
    if not n8n or not n8n.is_available():
        return jsonify({"error": "n8n統合が初期化されていません"}), 503

    try:
        data = request.json or {}
        result = n8n.execute_workflow(workflow_id, data)

        if result:
            return jsonify({
                "result": result,
                "status": "success"
            })
        else:
            return jsonify({"error": "ワークフローの実行に失敗しました"}), 500
    except Exception as e:
        logger.error(f"n8nワークフロー実行エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/n8n/workflow/<workflow_id>/activate", methods=["POST"])
def n8n_activate_workflow(workflow_id):
    """n8nワークフローを有効化"""
    missing_resp = _require_env_for_integration("n8n", ["N8N_BASE_URL", "N8N_API_KEY"])
    if missing_resp:
        return missing_resp

    if not N8N_AVAILABLE:
        return jsonify({"error": "n8n統合が利用できません"}), 503

    n8n = integrations.get("n8n")
    if not n8n or not n8n.is_available():
        return jsonify({"error": "n8n統合が初期化されていません"}), 503

    try:
        success = n8n.activate_workflow(workflow_id)

        if success:
            return jsonify({"status": "success", "message": "ワークフローを有効化しました"})
        else:
            return jsonify({"error": "ワークフローの有効化に失敗しました"}), 500
    except Exception as e:
        logger.error(f"n8nワークフロー有効化エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/n8n/workflow/<workflow_id>/deactivate", methods=["POST"])
def n8n_deactivate_workflow(workflow_id):
    """n8nワークフローを無効化"""
    missing_resp = _require_env_for_integration("n8n", ["N8N_BASE_URL", "N8N_API_KEY"])
    if missing_resp:
        return missing_resp

    if not N8N_AVAILABLE:
        return jsonify({"error": "n8n統合が利用できません"}), 503

    n8n = integrations.get("n8n")
    if not n8n or not n8n.is_available():
        return jsonify({"error": "n8n統合が初期化されていません"}), 503

    try:
        success = n8n.deactivate_workflow(workflow_id)

        if success:
            return jsonify({"status": "success", "message": "ワークフローを無効化しました"})
        else:
            return jsonify({"error": "ワークフローの無効化に失敗しました"}), 500
    except Exception as e:
        logger.error(f"n8nワークフロー無効化エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/image/stock", methods=["POST"])
def image_stock():
    """画像をストック"""
    if not IMAGE_STOCK_AVAILABLE:
        return jsonify({"error": "画像ストックが利用できません"}), 503

    stock = integrations.get("image_stock")
    if not stock:
        return jsonify({"error": "画像ストックが初期化されていません"}), 503

    try:
        from pathlib import Path

        data = request.json
        image_path = Path(data.get("image_path", ""))
        prompt = data.get("prompt")
        negative_prompt = data.get("negative_prompt")
        model = data.get("model")
        parameters = data.get("parameters", {})
        category = data.get("category")

        stock_info = stock.store(
            image_path=image_path,
            prompt=prompt,
            negative_prompt=negative_prompt,
            model=model,
            parameters=parameters,
            category=category
        )

        return jsonify({
            "stock_info": stock_info,
            "status": "success"
        })
    except Exception as e:
        logger.error(f"画像ストックエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/image/search", methods=["GET"])
def image_search():
    """ストックされた画像を検索"""
    if not IMAGE_STOCK_AVAILABLE:
        return jsonify({"error": "画像ストックが利用できません"}), 503

    stock = integrations.get("image_stock")
    if not stock:
        return jsonify({"error": "画像ストックが初期化されていません"}), 503

    try:
        query = request.args.get("query")
        category = request.args.get("category")
        model = request.args.get("model")
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        limit = int(request.args.get("limit", 20))

        results = stock.search(
            query=query,
            category=category,
            model=model,
            date_from=date_from,
            date_to=date_to,
            limit=limit
        )

        return jsonify({
            "results": results,
            "count": len(results)
        })
    except Exception as e:
        logger.error(f"画像検索エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/image/statistics", methods=["GET"])
def image_statistics():
    """画像ストック統計情報"""
    if not IMAGE_STOCK_AVAILABLE:
        return jsonify({"error": "画像ストックが利用できません"}), 503

    stock = integrations.get("image_stock")
    if not stock:
        return jsonify({"error": "画像ストックが初期化されていません"}), 503

    try:
        stats = stock.get_statistics()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"統計情報取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


# ========================================
# Rows統合 API エンドポイント
# ========================================

@app.route("/api/rows/spreadsheets", methods=["GET"])
def rows_list_spreadsheets():
    """Rowsスプレッドシート一覧を取得"""
    missing_resp = _require_env_for_integration("Rows", ["ROWS_API_KEY"])
    if missing_resp:
        return missing_resp

    if not ROWS_AVAILABLE:
        return jsonify({"error": "Rows統合が利用できません"}), 503

    rows = integrations.get("rows")
    if not rows or not rows.is_available():
        return jsonify({"error": "Rowsが初期化されていません"}), 503

    try:
        limit = int(request.args.get("limit", 50))
        spreadsheets = rows.list_spreadsheets(limit=limit)
        return jsonify({"spreadsheets": spreadsheets, "count": len(spreadsheets) if spreadsheets else 0})
    except Exception as e:
        logger.error(f"Rowsスプレッドシート一覧取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/rows/spreadsheets", methods=["POST"])
def rows_create_spreadsheet():
    """Rowsスプレッドシートを作成"""
    missing_resp = _require_env_for_integration("Rows", ["ROWS_API_KEY"])
    if missing_resp:
        return missing_resp

    if not ROWS_AVAILABLE:
        return jsonify({"error": "Rows統合が利用できません"}), 503

    rows = integrations.get("rows")
    if not rows or not rows.is_available():
        return jsonify({"error": "Rowsが初期化されていません"}), 503

    try:
        data = request.json
        title = data.get("title", "")
        description = data.get("description")

        spreadsheet = rows.create_spreadsheet(title=title, description=description)
        return jsonify({"spreadsheet": spreadsheet, "status": "success"})
    except Exception as e:
        logger.error(f"Rowsスプレッドシート作成エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/rows/spreadsheets/<spreadsheet_id>", methods=["GET"])
def rows_get_spreadsheet(spreadsheet_id):
    """Rowsスプレッドシート情報を取得"""
    missing_resp = _require_env_for_integration("Rows", ["ROWS_API_KEY"])
    if missing_resp:
        return missing_resp

    if not ROWS_AVAILABLE:
        return jsonify({"error": "Rows統合が利用できません"}), 503

    rows = integrations.get("rows")
    if not rows or not rows.is_available():
        return jsonify({"error": "Rowsが初期化されていません"}), 503

    try:
        spreadsheet = rows.get_spreadsheet(spreadsheet_id)
        return jsonify({"spreadsheet": spreadsheet})
    except Exception as e:
        logger.error(f"Rowsスプレッドシート取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/rows/ai/query", methods=["POST"])
def rows_ai_query():
    """Rows AIに自然言語でクエリを実行"""
    missing_resp = _require_env_for_integration("Rows", ["ROWS_API_KEY"])
    if missing_resp:
        return missing_resp

    if not ROWS_AVAILABLE:
        return jsonify({"error": "Rows統合が利用できません"}), 503

    rows = integrations.get("rows")
    if not rows or not rows.is_available():
        return jsonify({"error": "Rowsが初期化されていません"}), 503

    try:
        data = request.json
        spreadsheet_id = data.get("spreadsheet_id", "")
        query = data.get("query", "")
        context = data.get("context")

        result = rows.ai_query(spreadsheet_id=spreadsheet_id, query=query, context=context)
        return jsonify({"result": result, "status": "success"})
    except Exception as e:
        logger.error(f"Rows AIクエリエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/rows/ai/analyze", methods=["POST"])
def rows_ai_analyze():
    """Rows AIでデータ分析を実行"""
    missing_resp = _require_env_for_integration("Rows", ["ROWS_API_KEY"])
    if missing_resp:
        return missing_resp

    if not ROWS_AVAILABLE:
        return jsonify({"error": "Rows統合が利用できません"}), 503

    rows = integrations.get("rows")
    if not rows or not rows.is_available():
        return jsonify({"error": "Rowsが初期化されていません"}), 503

    try:
        data = request.json
        spreadsheet_id = data.get("spreadsheet_id", "")
        analysis_type = data.get("analysis_type", "trend")
        target_range = data.get("target_range")

        result = rows.ai_analyze(
            spreadsheet_id=spreadsheet_id,
            analysis_type=analysis_type,
            target_range=target_range
        )
        return jsonify({"result": result, "status": "success"})
    except Exception as e:
        logger.error(f"Rows AI分析エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/rows/data/send", methods=["POST"])
def rows_send_data():
    """ManaOSからRowsにデータを送信"""
    missing_resp = _require_env_for_integration("Rows", ["ROWS_API_KEY"])
    if missing_resp:
        return missing_resp

    if not ROWS_AVAILABLE:
        return jsonify({"error": "Rows統合が利用できません"}), 503

    rows = integrations.get("rows")
    if not rows or not rows.is_available():
        return jsonify({"error": "Rowsが初期化されていません"}), 503

    try:
        data = request.json
        spreadsheet_id = data.get("spreadsheet_id", "")
        send_data = data.get("data", {})
        sheet_name = data.get("sheet_name", "Sheet1")
        append = data.get("append", True)

        result = rows.send_to_rows(
            spreadsheet_id=spreadsheet_id,
            data=send_data,
            sheet_name=sheet_name,
            append=append
        )
        return jsonify({"result": result, "status": "success"})
    except Exception as e:
        logger.error(f"Rowsデータ送信エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/rows/export/slack", methods=["POST"])
def rows_export_to_slack():
    """Rowsのデータを要約してSlackに送信"""
    missing_resp = _require_env_for_integration("Rows", ["ROWS_API_KEY"])
    if missing_resp:
        return missing_resp

    if not ROWS_AVAILABLE:
        return jsonify({"error": "Rows統合が利用できません"}), 503

    rows = integrations.get("rows")
    if not rows or not rows.is_available():
        return jsonify({"error": "Rowsが初期化されていません"}), 503

    try:
        data = request.json
        spreadsheet_id = data.get("spreadsheet_id", "")
        sheet_name = data.get("sheet_name", "Sheet1")
        range_ref = data.get("range")
        channel = data.get("channel")

        result = rows.export_to_slack(
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            range_ref=range_ref,
            channel=channel
        )
        return jsonify({"result": result, "status": "success"})
    except Exception as e:
        logger.error(f"Rows Slack送信エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/rows/webhook", methods=["POST"])
def rows_webhook():
    """RowsからのWebhookを受信"""
    try:
        data = request.json
        event_type = data.get("event_type", "")
        spreadsheet_id = data.get("spreadsheet_id", "")
        payload = data.get("payload", {})

        logger.info(f"Rows Webhook受信: {event_type} - {spreadsheet_id}")

        # n8n Webhookに転送（オプション）
        n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL")
        if n8n_webhook_url and REQUESTS_AVAILABLE:
            try:
                requests.post(n8n_webhook_url, json={
                    "source": "rows",
                    "event_type": event_type,
                    "spreadsheet_id": spreadsheet_id,
                    "payload": payload,
                    "timestamp": datetime.now().isoformat()
                }, timeout=5)
                logger.info(f"n8n Webhookに転送しました: {event_type}")
            except Exception as e:
                logger.warning(f"n8n Webhook転送に失敗: {e}")

        return jsonify({"status": "received", "event_type": event_type})
    except Exception as e:
        logger.error(f"Rows Webhook受信エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/rows/batch/update", methods=["POST"])
def rows_batch_update():
    """Rowsの複数セルを一括更新"""
    missing_resp = _require_env_for_integration("Rows", ["ROWS_API_KEY"])
    if missing_resp:
        return missing_resp

    if not ROWS_AVAILABLE:
        return jsonify({"error": "Rows統合が利用できません"}), 503

    rows = integrations.get("rows")
    if not rows or not rows.is_available():
        return jsonify({"error": "Rowsが初期化されていません"}), 503

    try:
        data = request.json
        spreadsheet_id = data.get("spreadsheet_id", "")
        updates = data.get("updates", [])
        sheet_name = data.get("sheet_name", "Sheet1")

        result = rows.batch_update(
            spreadsheet_id=spreadsheet_id,
            updates=updates,
            sheet_name=sheet_name
        )
        return jsonify({"result": result, "status": "success"})
    except Exception as e:
        logger.error(f"Rowsバッチ更新エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/rows/import/csv", methods=["POST"])
def rows_import_csv():
    """CSVファイルからRowsにインポート"""
    missing_resp = _require_env_for_integration("Rows", ["ROWS_API_KEY"])
    if missing_resp:
        return missing_resp

    if not ROWS_AVAILABLE:
        return jsonify({"error": "Rows統合が利用できません"}), 503

    rows = integrations.get("rows")
    if not rows or not rows.is_available():
        return jsonify({"error": "Rowsが初期化されていません"}), 503

    try:
        data = request.json
        spreadsheet_id = data.get("spreadsheet_id", "")
        csv_file_path = data.get("csv_file_path", "")
        sheet_name = data.get("sheet_name", "Sheet1")
        has_header = data.get("has_header", True)

        result = rows.import_from_csv(
            spreadsheet_id=spreadsheet_id,
            csv_file_path=csv_file_path,
            sheet_name=sheet_name,
            has_header=has_header
        )
        return jsonify({"result": result, "status": "success"})
    except Exception as e:
        logger.error(f"Rows CSVインポートエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/rows/export/csv", methods=["POST"])
def rows_export_csv():
    """RowsのデータをCSVにエクスポート"""
    missing_resp = _require_env_for_integration("Rows", ["ROWS_API_KEY"])
    if missing_resp:
        return missing_resp

    if not ROWS_AVAILABLE:
        return jsonify({"error": "Rows統合が利用できません"}), 503

    rows = integrations.get("rows")
    if not rows or not rows.is_available():
        return jsonify({"error": "Rowsが初期化されていません"}), 503

    try:
        data = request.json
        spreadsheet_id = data.get("spreadsheet_id", "")
        sheet_name = data.get("sheet_name", "Sheet1")
        range_ref = data.get("range", "A1:Z1000")
        output_path = data.get("output_path", f"rows_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

        result = rows.export_to_csv(
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            range_ref=range_ref,
            output_path=output_path
        )
        return jsonify({"result": result, "status": "success"})
    except Exception as e:
        logger.error(f"Rows CSVエクスポートエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/rows/sync/auto", methods=["POST"])
def rows_auto_sync():
    """Rowsの自動同期を実行"""
    missing_resp = _require_env_for_integration("Rows", ["ROWS_API_KEY"])
    if missing_resp:
        return missing_resp

    if not ROWS_AVAILABLE:
        return jsonify({"error": "Rows統合が利用できません"}), 503

    rows = integrations.get("rows")
    if not rows or not rows.is_available():
        return jsonify({"error": "Rowsが初期化されていません"}), 503

    try:
        data = request.json
        spreadsheet_id = data.get("spreadsheet_id", "")
        source_data = data.get("source_data", [])
        key_column = data.get("key_column", "id")
        sheet_name = data.get("sheet_name", "Sheet1")

        result = rows.auto_sync(
            spreadsheet_id=spreadsheet_id,
            source_data=source_data,
            key_column=key_column,
            sheet_name=sheet_name
        )
        return jsonify({"result": result, "status": "success"})
    except Exception as e:
        logger.error(f"Rows自動同期エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/rows/dashboard/create", methods=["POST"])
def rows_create_dashboard():
    """Rowsダッシュボードを作成"""
    missing_resp = _require_env_for_integration("Rows", ["ROWS_API_KEY"])
    if missing_resp:
        return missing_resp

    if not ROWS_AVAILABLE:
        return jsonify({"error": "Rows統合が利用できません"}), 503

    rows = integrations.get("rows")
    if not rows or not rows.is_available():
        return jsonify({"error": "Rowsが初期化されていません"}), 503

    try:
        data = request.json
        spreadsheet_id = data.get("spreadsheet_id", "")
        dashboard_config = data.get("dashboard_config", {})
        sheet_name = data.get("sheet_name", "Dashboard")

        result = rows.create_dashboard(
            spreadsheet_id=spreadsheet_id,
            dashboard_config=dashboard_config,
            sheet_name=sheet_name
        )
        return jsonify({"result": result, "status": "success"})
    except Exception as e:
        logger.error(f"Rowsダッシュボード作成エラー: {e}")
        return jsonify({"error": str(e)}), 500


# ========== Excel/LLM処理 API ==========

@app.route("/api/excel/process", methods=["POST"])
def excel_process():
    """Excel/CSVファイルをLLMで処理"""
    try:
        if not EXCEL_LLM_AVAILABLE:
            return jsonify({"error": "Excel/LLM処理統合が利用できません"}), 503

        excel_llm = integrations.get("excel_llm")
        if not excel_llm:
            # 統合が初期化されていない場合、即座に初期化を試みる
            try:
                logger.info("Excel/LLM統合が初期化されていないため、即座に初期化を試みます")
                excel_llm = ExcelLLMIntegration(
                    ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
                    model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
                )
                integrations["excel_llm"] = excel_llm
                logger.info("Excel/LLM統合を即座に初期化しました")
            except Exception as e:
                logger.error(f"Excel/LLM統合の即座初期化に失敗: {e}")
                return jsonify({"error": f"Excel/LLM処理の初期化に失敗しました: {str(e)}"}), 503
        
        if not excel_llm.is_available():
            return jsonify({"error": "Excel/LLM処理が利用できません（Ollamaサービスが起動していない可能性があります）"}), 503

        data = request.json or {}
        file_path = data.get("file_path", "")
        task = data.get("task", "異常値検出")

        if not file_path:
            return jsonify({"error": "file_pathが必要です"}), 400

        # ファイルパスの存在確認（絶対パスに変換）
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            # 相対パスの場合、現在の作業ディレクトリからの相対パスとして扱う
            file_path_obj = Path.cwd() / file_path_obj
        
        if not file_path_obj.exists():
            return jsonify({"error": f"ファイルが見つかりません: {file_path_obj}"}), 404

        result = excel_llm.process_file(str(file_path_obj), task)

        if result["success"]:
            return jsonify({
                "success": True,
                "response": result.get("response", ""),
                "model": result.get("model", ""),
                "output_file": result.get("output_file", ""),
                "rows": result.get("rows", 0),
                "columns": result.get("columns", 0)
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "処理に失敗しました")
            }), 500

    except Exception as e:
        logger.error(f"Excel/LLM処理エラー: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/excel/summary", methods=["POST"])
def excel_summary():
    """Excel/CSVファイルの要約を取得（LLMを使わずに）"""
    try:
        if not EXCEL_LLM_AVAILABLE:
            return jsonify({"error": "Excel/LLM処理統合が利用できません"}), 503

        excel_llm = integrations.get("excel_llm")
        if not excel_llm:
            # 統合が初期化されていない場合、即座に初期化を試みる
            try:
                logger.info("Excel/LLM統合が初期化されていないため、即座に初期化を試みます")
                excel_llm = ExcelLLMIntegration(
                    ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
                    model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
                )
                integrations["excel_llm"] = excel_llm
                logger.info("Excel/LLM統合を即座に初期化しました")
            except Exception as e:
                logger.error(f"Excel/LLM統合の即座初期化に失敗: {e}")
                return jsonify({"error": f"Excel/LLM処理の初期化に失敗しました: {str(e)}"}), 503
        
        if not excel_llm.is_available():
            return jsonify({"error": "Excel/LLM処理が利用できません（Ollamaサービスが起動していない可能性があります）"}), 503

        data = request.json or {}
        file_path = data.get("file_path", "")

        if not file_path:
            return jsonify({"error": "file_pathが必要です"}), 400

        # ファイルパスの存在確認
        if not Path(file_path).exists():
            return jsonify({"error": f"ファイルが見つかりません: {file_path}"}), 404

        result = excel_llm.get_summary(file_path)

        if result["success"]:
            return jsonify({
                "success": True,
                "summary": result.get("summary", ""),
                "rows": result.get("rows", 0),
                "columns": result.get("columns", 0),
                "column_names": result.get("column_names", [])
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "要約取得に失敗しました")
            }), 500

    except Exception as e:
        logger.error(f"Excel要約取得エラー: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ========== Step-Deep-Research API ==========

@app.route("/api/research/create", methods=["POST"])
def research_create():
    """調査ジョブを作成"""
    if not STEP_DEEP_RESEARCH_AVAILABLE:
        return jsonify({"error": "Step-Deep-Research統合が利用できません"}), 503

    orchestrator = integrations.get("step_deep_research")
    if not orchestrator:
        return jsonify({"error": "Step-Deep-Researchが初期化されていません"}), 503

    try:
        data = request.json
        query = data.get("query", "")

        if not query:
            return jsonify({"error": "queryが必要です"}), 400

        job_id = orchestrator.create_job(query)
        return jsonify({
            "job_id": job_id,
            "status": "created",
            "query": query
        })
    except Exception as e:
        logger.error(f"調査ジョブ作成エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/research/execute/<job_id>", methods=["POST"])
def research_execute(job_id):
    """調査ジョブを実行"""
    if not STEP_DEEP_RESEARCH_AVAILABLE:
        return jsonify({"error": "Step-Deep-Research統合が利用できません"}), 503

    orchestrator = integrations.get("step_deep_research")
    if not orchestrator:
        return jsonify({"error": "Step-Deep-Researchが初期化されていません"}), 503

    try:
        data = request.json or {}
        use_cache = data.get("use_cache", True)

        result = orchestrator.execute_job(job_id, use_cache=use_cache)
        return jsonify(result)
    except Exception as e:
        logger.error(f"調査ジョブ実行エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/research/status/<job_id>", methods=["GET"])
def research_status(job_id):
    """調査ジョブの状態を取得"""
    if not STEP_DEEP_RESEARCH_AVAILABLE:
        return jsonify({"error": "Step-Deep-Research統合が利用できません"}), 503

    orchestrator = integrations.get("step_deep_research")
    if not orchestrator:
        return jsonify({"error": "Step-Deep-Researchが初期化されていません"}), 503

    try:
        job_state = orchestrator.get_job(job_id)
        if not job_state:
            return jsonify({"error": "ジョブが見つかりません"}), 404

        return jsonify({
            "job_id": job_id,
            "status": job_state.status.value,
            "user_query": job_state.user_query,
            "created_at": job_state.created_at.isoformat() if hasattr(job_state.created_at, 'isoformat') else str(job_state.created_at)
        })
    except Exception as e:
        logger.error(f"調査ジョブ状態取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/research/quick", methods=["POST"])
def research_quick():
    """クイック調査（作成→実行を一度に）"""
    if not STEP_DEEP_RESEARCH_AVAILABLE:
        return jsonify({"error": "Step-Deep-Research統合が利用できません"}), 503

    orchestrator = integrations.get("step_deep_research")
    if not orchestrator:
        return jsonify({"error": "Step-Deep-Researchが初期化されていません"}), 503

    try:
        data = request.json
        query = data.get("query", "")
        use_cache = data.get("use_cache", True)

        if not query:
            return jsonify({"error": "queryが必要です"}), 400

        # ジョブ作成→実行
        job_id = orchestrator.create_job(query)
        result = orchestrator.execute_job(job_id, use_cache=use_cache)

        return jsonify(result)
    except Exception as e:
        logger.error(f"クイック調査エラー: {e}")
        return jsonify({"error": str(e)}), 500


# ========== 緊急操作パネル用エンドポイント ==========

# 許可されたsystemdサービス（安全な操作のみ）
ALLOWED_SERVICES = [
    "n8n",
    "mana-ocr-api",
    "mana-intent",
    "manaos-command-hub",
    "sd-webui",
    "manaos-api"
]

# 許可されたn8nワークフロー（緊急用）
ALLOWED_WORKFLOWS = [
    "daily_report",
    "pdf_to_excel",
    "image_generation",
    "remi_command"
]


@app.route("/emergency", methods=["GET"])
def emergency_panel():
    """緊急操作パネルのHTMLを返す"""
    try:
        template_dir = Path(__file__).parent.parent / "templates"
        html_file = template_dir / "emergency_panel.html"

        if html_file.exists():
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        else:
            logger.error(f"緊急パネルHTMLファイルが見つかりません: {html_file}")
            return jsonify({"error": "緊急パネルHTMLファイルが見つかりません"}), 404
    except Exception as e:
        logger.error(f"緊急パネルHTML読み込みエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/emergency/logs", methods=["GET"])
def emergency_logs():
    """ログを取得（最後N行）"""
    try:
        service = request.args.get("service", "system")
        lines = int(request.args.get("lines", 50))

        log_paths = {
            "system": "/var/log/syslog",
            "n8n": "/root/.n8n/logs/n8n.log",
            "error": "/root/logs/error.log",
            "command-hub": "/root/logs/command-hub.log",
            "daily": "/root/logs/daily.log"
        }

        log_path = log_paths.get(service)
        if not log_path or not os.path.exists(log_path):
            return jsonify({"error": f"ログファイルが見つかりません: {service}"}), 404

        try:
            result = subprocess.run(
                ["tail", "-n", str(lines), log_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return jsonify({
                    "service": service,
                    "lines": lines,
                    "log": result.stdout
                })
            else:
                return jsonify({"error": "ログ取得に失敗しました"}), 500
        except subprocess.TimeoutExpired:
            return jsonify({"error": "ログ取得がタイムアウトしました"}), 504
        except Exception as e:
            logger.error(f"ログ取得エラー: {e}")
            return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"緊急ログ取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/emergency/workflow", methods=["POST"])
def emergency_workflow():
    """n8nワークフローを実行（許可されたもののみ）"""
    try:
        data = request.json or {}
        workflow = data.get("workflow", "")
        payload = data.get("payload", {})

        if workflow not in ALLOWED_WORKFLOWS:
            return jsonify({"error": f"許可されていないワークフロー: {workflow}"}), 403

        # n8n Webhook URLを構築
        n8n_base_url = os.getenv("N8N_BASE_URL", "http://localhost:5678")
        webhook_path = f"/webhook/{workflow}"

        if workflow == "remi_command":
            webhook_path = "/webhook/remi_command"

        webhook_url = f"{n8n_base_url}{webhook_path}"

        if not REQUESTS_AVAILABLE:
            return jsonify({"error": "requestsモジュールが利用できません"}), 503

        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            logger.info(f"緊急ワークフロー実行: {workflow}")
            return jsonify({
                "status": "success",
                "workflow": workflow,
                "response": response.json() if response.content else {}
            })
        except requests.exceptions.RequestException as e:
            logger.error(f"n8nワークフロー実行エラー: {e}")
            return jsonify({"error": f"ワークフロー実行に失敗: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"緊急ワークフロー実行エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/emergency/service", methods=["POST"])
def emergency_service():
    """systemdサービスを操作（許可されたもののみ、安全な操作のみ）"""
    try:
        data = request.json or {}
        service = data.get("service", "")
        action = data.get("action", "")  # start, stop, restart, status

        if service not in ALLOWED_SERVICES:
            return jsonify({"error": f"許可されていないサービス: {service}"}), 403

        if action not in ["start", "stop", "restart", "status"]:
            return jsonify({"error": f"許可されていない操作: {action}"}), 403

        # systemctlコマンドを実行
        try:
            cmd = ["systemctl", action, service]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info(f"緊急サービス操作成功: {action} {service}")
                return jsonify({
                    "status": "success",
                    "service": service,
                    "action": action,
                    "output": result.stdout
                })
            else:
                logger.warning(f"緊急サービス操作失敗: {action} {service} - {result.stderr}")
                return jsonify({
                    "status": "error",
                    "service": service,
                    "action": action,
                    "error": result.stderr
                }), 500
        except subprocess.TimeoutExpired:
            return jsonify({"error": "サービス操作がタイムアウトしました"}), 504
        except Exception as e:
            logger.error(f"サービス操作エラー: {e}")
            return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"緊急サービス操作エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/emergency/status", methods=["GET"])
def emergency_status():
    """緊急操作パネル用の統合ステータスを取得"""
    try:
        # /statusから基本情報を取得
        status_data = {}
        try:
            if REQUESTS_AVAILABLE:
                base_url = request.host_url.rstrip("/")
                response = requests.get(f"{base_url}/status", timeout=5)
                if response.status_code == 200:
                    status_data = response.json()
        except Exception as e:
            logger.warning(f"ステータス取得エラー: {e}")

        # 主要サービスの状態を取得
        services_status = {}
        for service in ALLOWED_SERVICES:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                services_status[service] = {
                    "status": "running" if result.returncode == 0 else "stopped",
                    "output": result.stdout.strip()
                }
            except Exception:
                services_status[service] = {"status": "unknown", "output": ""}

        return jsonify({
            "system_status": status_data,
            "services": services_status,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"緊急ステータス取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/system/docker/containers", methods=["GET"])
def get_docker_containers():
    """Dockerコンテナの状態を取得（レミ先輩仕様：確実に動く実装）"""
    try:
        import subprocess
        import json

        # dockerコマンドでコンテナ一覧を取得（ホストから実行）
        # レミ先輩仕様：確実に動くように、ホストのdockerコマンドを直接実行
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=(sys.platform == "win32")
        )

        if result.returncode != 0:
            return jsonify({
                "error": "dockerコマンドの実行に失敗しました",
                "stderr": result.stderr
            }), 500

        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    container = json.loads(line)
                    container_name = container.get("Names", "")
                    status = container.get("Status", "")

                    # 死活判定
                    is_running = "Up" in status

                    containers.append({
                        "name": container_name,
                        "status": "running" if is_running else "stopped",
                        "image": container.get("Image", ""),
                        "ports": container.get("Ports", ""),
                        "status_detail": status,
                        "id": container.get("ID", "")[:12] if container.get("ID") else ""
                    })
                except json.JSONDecodeError:
                    continue

        return jsonify({
            "status": "success",
            "containers": containers,
            "count": len(containers)
        })
    except FileNotFoundError:
        return jsonify({
            "error": "dockerコマンドが見つかりません。Docker Desktopがインストールされているか確認してください。"
        }), 503
    except subprocess.TimeoutExpired:
        return jsonify({
            "error": "dockerコマンドの実行がタイムアウトしました"
        }), 504
    except Exception as e:
        logger.error(f"Dockerコンテナ取得エラー: {e}", exc_info=True)
        return jsonify({
            "error": f"Dockerコンテナの取得に失敗しました: {str(e)}"
        }), 500

@app.route("/api/system/docker/logs", methods=["GET"])
def get_docker_logs():
    """Dockerコンテナのログを取得（レミ先輩仕様：確実に動く実装）"""
    try:
        import subprocess

        container_name = request.args.get("container", "")
        lines = int(request.args.get("lines", 100))

        if not container_name:
            return jsonify({"error": "containerパラメータが必要です"}), 400

        # docker logsコマンドでログを取得
        result = subprocess.run(
            ["docker", "logs", "--tail", str(lines), container_name],
            capture_output=True,
            text=True,
            timeout=30,
            shell=(sys.platform == "win32")
        )

        if result.returncode != 0:
            return jsonify({
                "error": f"コンテナ '{container_name}' のログ取得に失敗しました",
                "stderr": result.stderr
            }), 500

        logs = result.stdout.split('\n')

        # エラーパターンを検索
        errors = []
        error_patterns = ["ERROR", "error", "Error", "Exception", "Traceback", "Failed", "failed"]

        for i, line in enumerate(logs):
            for pattern in error_patterns:
                if pattern in line:
                    context_start = max(0, i - 3)
                    context_end = min(len(logs), i + 4)
                    context = logs[context_start:context_end]

                    errors.append({
                        "line_number": i + 1,
                        "error_line": line,
                        "context": context,
                        "pattern": pattern
                    })
                    break

        return jsonify({
            "status": "success",
            "container": container_name,
            "logs": logs[-100:],  # 最新100行
            "errors": errors[:50],  # 最大50件
            "error_count": len(errors),
            "total_lines": len(logs)
        })
    except subprocess.TimeoutExpired:
        return jsonify({
            "error": "ログ取得がタイムアウトしました"
        }), 504
    except Exception as e:
        logger.error(f"Dockerログ取得エラー: {e}", exc_info=True)
        return jsonify({
            "error": f"ログ取得に失敗しました: {str(e)}"
        }), 500

def start_initialization_background():
    """初期化をバックグラウンドスレッドで実行"""
    def init_thread():
        initialize_integrations()

    thread = threading.Thread(target=init_thread, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    print("ManaOS統合APIサーバーを起動中...")

    # 初期化をバックグラウンドで開始
    init_thread = start_initialization_background()

    port = int(os.getenv("MANAOS_INTEGRATION_PORT", 9500))
    host = os.getenv("MANAOS_INTEGRATION_HOST", "0.0.0.0")

    print(f"サーバー起動: http://{host}:{port}")
    print("利用可能なエンドポイント:")
    print("  GET  /health - ヘルスチェック（軽量：プロセス生存のみ）")
    print("  GET  /ready - レディネスチェック（初期化完了確認）")
    print("  GET  /api/integrations/status - 統合システム状態")
    print("\n【緊急操作パネル】")
    print("  GET  /emergency - 緊急操作パネル（HTML）")
    print("  GET  /api/emergency/status - 緊急用統合ステータス")
    print("  GET  /api/emergency/logs - ログ取得")
    print("  POST /api/emergency/workflow - n8nワークフロー実行")
    print("  POST /api/emergency/service - systemdサービス操作")
    print("  POST /api/comfyui/generate - ComfyUI画像生成")
    print("  POST /api/svi/generate - SVI × Wan 2.2動画生成")
    print("  POST /api/svi/extend - 動画延長")
    print("  POST /api/svi/story - ストーリー動画生成")
    print("  GET  /api/svi/queue - キュー状態取得")
    print("  GET  /api/svi/history - 実行履歴取得")
    print("  POST /api/svi/batch/generate - バッチ動画生成")
    print("  POST /api/ltx2/generate - LTX-2動画生成（Super LTX-2設定）")
    print("  GET  /api/ltx2/queue - LTX-2キュー状態取得")
    print("  GET  /api/ltx2/history - LTX-2実行履歴取得")
    print("  GET  /api/ltx2/status/<prompt_id> - LTX-2実行状態取得")
    print("  GET  /api/svi/status/<prompt_id> - 実行状態取得")
    print("\n【SVI自動化 API】")
    print("  POST /api/svi/automation/watch - フォルダ監視開始")
    print("  POST /api/svi/automation/schedule - スケジュールタスク追加")
    print("  POST /api/svi/automation/batch - フォルダ一括処理")
    print("  POST /api/google_drive/upload - GoogleDriveアップロード")
    print("  GET  /api/civitai/search - CivitAI検索")
    print("  POST /api/langchain/chat - LangChainチャット")
    print("  POST /api/mem0/add - Mem0メモリ追加")
    print("  POST /api/obsidian/create - Obsidianノート作成")
    print("  GET  /api/local-llm/systems - ローカルLLMシステム一覧")
    print("\n【キャッシュ・パフォーマンス API】")
    print("  GET  /api/cache/get - キャッシュ取得（統一キャッシュシステム優先）")
    print("  POST /api/cache/set - キャッシュ保存（統一キャッシュシステム優先）")
    print("  GET  /api/cache/stats - キャッシュ統計")
    print("  GET  /api/performance/stats - パフォーマンス統計")
    print("\n【拡張フェーズ API】")
    print("  POST /api/llm/route - LLMルーティング")
    print("  POST /api/memory/store - 記憶への保存")
    print("  GET  /api/memory/recall - 記憶からの検索")
    print("  POST /api/notification/send - 通知送信")
    print("  POST /api/secretary/morning - 朝のルーチン")
    print("  POST /api/secretary/noon - 昼のルーチン")
    print("  POST /api/secretary/evening - 夜のルーチン")
    print("  POST /api/image/stock - 画像をストック")
    print("  GET  /api/image/search - 画像検索")
    print("  GET  /api/image/statistics - 画像統計情報")
    print("\n【LFM 2.5専用 API】")
    print("  POST /api/lfm25/chat - LFM 2.5チャット（超軽量・超高速）")
    print("  POST /api/lfm25/lightweight - LFM 2.5軽量会話（オフライン会話・下書き・整理専用）")
    print("  POST /api/lfm25/batch - LFM 2.5バッチチャット")
    print("  GET  /api/lfm25/status - LFM 2.5の状態を取得")
    print("\n【Rows統合 API】")
    print("  GET  /api/rows/spreadsheets - スプレッドシート一覧")
    print("  POST /api/rows/spreadsheets - スプレッドシート作成")
    print("  GET  /api/rows/spreadsheets/<id> - スプレッドシート取得")
    print("  POST /api/rows/ai/query - AI自然言語クエリ")
    print("  POST /api/rows/ai/analyze - AIデータ分析")
    print("  POST /api/rows/data/send - データ送信")
    print("  POST /api/rows/export/slack - Slack送信")
    print("  POST /api/rows/webhook - Webhook受信")
    print("  POST /api/rows/batch/update - バッチ更新")
    print("  POST /api/rows/import/csv - CSVインポート")
    print("  POST /api/rows/export/csv - CSVエクスポート")
    print("  POST /api/rows/sync/auto - 自動同期")
    print("  POST /api/rows/dashboard/create - ダッシュボード作成")
    print("  POST /api/rows/batch/update - 一括更新")
    print("  POST /api/rows/import/csv - CSVインポート")
    print("  POST /api/rows/export/csv - CSVエクスポート")
    print("  POST /api/rows/sync/auto - 自動同期")
    print("  POST /api/rows/dashboard/create - ダッシュボード作成")

    app.run(host=host, port=port, debug=True)
