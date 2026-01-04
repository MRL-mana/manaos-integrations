"""
ManaOS既存サービスとの統合ブリッジ
統合システムとManaOS既存サービスを連携
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_unified_client import get_unified_client

# 非同期クライアント（オプション）
try:
    from manaos_async_client import AsyncUnifiedAPIClient
    ASYNC_CLIENT_AVAILABLE = True
except ImportError:
    ASYNC_CLIENT_AVAILABLE = False
    AsyncUnifiedAPIClient = None

# 統一キャッシュシステム（オプション）
try:
    from unified_cache_system import get_unified_cache
    UNIFIED_CACHE_AVAILABLE = True
except ImportError:
    UNIFIED_CACHE_AVAILABLE = False
    get_unified_cache = None

# パフォーマンス最適化システム（オプション）
try:
    from manaos_performance_optimizer import PerformanceOptimizer
    PERFORMANCE_OPTIMIZER_AVAILABLE = True
except ImportError:
    PERFORMANCE_OPTIMIZER_AVAILABLE = False
    PerformanceOptimizer = None

# 統合システム
try:
    from comfyui_integration import ComfyUIIntegration
except ImportError:
    ComfyUIIntegration = None

try:
    from google_drive_integration import GoogleDriveIntegration
except ImportError:
    GoogleDriveIntegration = None

try:
    from civitai_integration import CivitAIIntegration
except ImportError:
    CivitAIIntegration = None

try:
    from langchain_integration import LangChainIntegration
except ImportError:
    LangChainIntegration = None

try:
    from mem0_integration import Mem0Integration
except ImportError:
    Mem0Integration = None

try:
    from obsidian_integration import ObsidianIntegration
except ImportError:
    ObsidianIntegration = None

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("ServiceBridge")


class ManaOSServiceBridge:
    """ManaOSサービスブリッジ（最適化版）"""
    
    def __init__(self):
        """初期化"""
        # 統合APIクライアントを使用
        self.client = get_unified_client()
        
        # ManaOS既存サービスのエンドポイント（統合APIクライアント経由でアクセス）
        self.command_hub_url = "http://localhost:9404"
        self.enhanced_api_url = "http://localhost:9406"
        self.monitoring_url = "http://localhost:9407"
        self.ocr_api_url = "http://localhost:9409"
        self.gallery_api_url = "http://localhost:5559"
        
        # 統一キャッシュシステム（オプション）
        self.cache = None
        if UNIFIED_CACHE_AVAILABLE:
            try:
                self.cache = get_unified_cache()
                logger.info("統一キャッシュシステムを有効化しました")
            except Exception as e:
                logger.warning(f"統一キャッシュシステムの初期化に失敗: {e}")
        
        # パフォーマンス最適化システム（オプション）
        self.performance_optimizer = None
        if PERFORMANCE_OPTIMIZER_AVAILABLE:
            try:
                self.performance_optimizer = PerformanceOptimizer()
                logger.info("パフォーマンス最適化システムを有効化しました")
            except Exception as e:
                logger.warning(f"パフォーマンス最適化システムの初期化に失敗: {e}")
        
        # 統合システム（オプショナル）
        self.comfyui = ComfyUIIntegration() if ComfyUIIntegration else None
        self.drive = GoogleDriveIntegration() if GoogleDriveIntegration else None
        self.civitai = CivitAIIntegration() if CivitAIIntegration else None
        self.langchain = LangChainIntegration() if LangChainIntegration else None
        self.mem0 = Mem0Integration() if Mem0Integration else None
        
        try:
            if ObsidianIntegration:
                default_vault = Path.home() / "Documents" / "Obsidian"
                if default_vault.exists():
                    self.obsidian = ObsidianIntegration(str(default_vault))
                else:
                    self.obsidian = ObsidianIntegration(str(Path.cwd()))
            else:
                self.obsidian = None
        except Exception as e:
            logger.warning(f"Obsidian統合の初期化に失敗: {e}")
            self.obsidian = None
        
        # パフォーマンスメトリクス
        self.metrics = {
            "workflow_executions": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "average_execution_time": 0.0
        }
    
    def check_manaos_services(self, use_parallel: bool = True) -> Dict[str, bool]:
        """
        ManaOSサービスの状態を確認（並列処理最適化版）
        
        Args:
            use_parallel: 並列処理を使用するか
        
        Returns:
            サービス名と状態の辞書
        """
        services = {
            "command_hub": False,
            "enhanced_api": False,
            "monitoring": False,
            "ocr_api": False,
            "gallery_api": False
        }
        
        # 並列チェック用の呼び出しリスト
        checks = [
            {"url": f"{self.command_hub_url}/health", "name": "command_hub"},
            {"url": f"{self.enhanced_api_url}/health", "name": "enhanced_api"},
            {"url": f"{self.monitoring_url}/health", "name": "monitoring"},
            {"url": f"{self.ocr_api_url}/health", "name": "ocr_api"},
            {"url": f"{self.gallery_api_url}/health", "name": "gallery_api"},
        ]
        
        if use_parallel:
            # 並列処理でチェック（ThreadPoolExecutor使用）
            def check_service(check_item: Dict[str, str]) -> tuple[str, bool]:
                """個別のサービスチェック関数"""
                try:
                    result = self.client._make_request(
                        check_item["url"],
                        "GET",
                        None,
                        None,
                        5.0
                    )
                    return check_item["name"], result.get("status") != "error"
                except Exception as e:
                    logger.debug(f"{check_item['name']}のヘルスチェック失敗: {e}")
                    return check_item["name"], False
            
            # 並列実行
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(check_service, check): check for check in checks}
                for future in as_completed(futures):
                    name, status = future.result()
                    services[name] = status
        else:
            # 順次処理（フォールバック）
            for check in checks:
                try:
                    result = self.client._make_request(
                        check["url"],
                        "GET",
                        None,
                        None,
                        5.0
                    )
                    services[check["name"]] = result.get("status") != "error"
                except Exception as e:
                    logger.debug(f"{check['name']}のヘルスチェック失敗: {e}")
                    services[check["name"]] = False
        
        return services
    
    async def check_manaos_services_async(self) -> Dict[str, bool]:
        """
        ManaOSサービスの状態を確認（非同期版）
        
        Returns:
            サービス名と状態の辞書
        """
        services = {
            "command_hub": False,
            "enhanced_api": False,
            "monitoring": False,
            "ocr_api": False,
            "gallery_api": False
        }
        
        if not ASYNC_CLIENT_AVAILABLE:
            logger.warning("非同期クライアントが利用できません。同期版を使用します。")
            return self.check_manaos_services(use_parallel=True)
        
        # 非同期クライアントを使用
        checks = [
            {"url": f"{self.command_hub_url}/health", "name": "command_hub"},
            {"url": f"{self.enhanced_api_url}/health", "name": "enhanced_api"},
            {"url": f"{self.monitoring_url}/health", "name": "monitoring"},
            {"url": f"{self.ocr_api_url}/health", "name": "ocr_api"},
            {"url": f"{self.gallery_api_url}/health", "name": "gallery_api"},
        ]
        
        async def check_service_async(check_item: Dict[str, str]) -> tuple[str, bool]:
            """個別のサービスチェック関数（非同期）"""
            try:
                async with AsyncUnifiedAPIClient() as async_client:
                    result = await async_client.call_service(
                        "external",
                        check_item["url"],
                        method="GET"
                    )
                    return check_item["name"], result.get("status") != "error"
            except Exception as e:
                logger.debug(f"{check_item['name']}のヘルスチェック失敗: {e}")
                return check_item["name"], False
        
        # 並列実行
        tasks = [check_service_async(check) for check in checks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"サービスチェックエラー: {result}")
                continue
            name, status = result
            services[name] = status
        
        return services
    
    def integrate_image_generation_workflow(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        画像生成ワークフローを統合実行（キャッシュ対応）
        
        Args:
            prompt: プロンプト
            negative_prompt: ネガティブプロンプト
            width: 画像幅
            height: 画像高さ
            use_cache: キャッシュを使用するか
            
        Returns:
            実行結果
        """
        import time
        start_time = time.time()
        
        # キャッシュキーを生成
        cache_key = f"image_gen_{hash((prompt, negative_prompt, width, height))}"
        
        # キャッシュから取得を試みる
        if use_cache and self.cache:
            cached_result = self.cache.get("workflow", cache_key)
            if cached_result:
                self.metrics["cache_hits"] += 1
                logger.info(f"画像生成ワークフローのキャッシュヒット: {cache_key}")
                return cached_result
            self.metrics["cache_misses"] += 1
        
        result = {
            "workflow": "画像生成統合",
            "steps": {},
            "cached": False
        }
        
        # 1. ComfyUIで画像生成
        if self.comfyui and self.comfyui.is_available():
            try:
                prompt_id = self.comfyui.generate_image(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height
                )
                result["steps"]["comfyui_generate"] = {
                    "success": prompt_id is not None,
                    "prompt_id": prompt_id
                }
            except Exception as e:
                logger.error(f"ComfyUI画像生成エラー: {e}")
                result["steps"]["comfyui_generate"] = {
                    "success": False,
                    "error": str(e)
                }
        else:
            result["steps"]["comfyui_generate"] = {"success": False, "reason": "ComfyUI利用不可"}
        
        # 2. Gallery APIに登録（生成された画像を）
        # 注意: 実際の実装では、生成された画像のパスを取得する必要があります
        try:
            gallery_result = self.client._make_request(
                f"{self.gallery_api_url}/api/images",
                "POST",
                {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": width,
                    "height": height
                },
                None,
                10.0
            )
            result["steps"]["gallery_register"] = {
                "success": gallery_result.get("status") != "error"
            }
        except Exception as e:
            logger.error(f"Gallery API登録エラー: {e}")
            result["steps"]["gallery_register"] = {"success": False, "error": str(e)}
        
        # 3. Mem0にメモリ保存
        if self.mem0 and self.mem0.is_available():
            try:
                memory_id = self.mem0.add_memory(
                    memory_text=f"画像生成: {prompt}",
                    user_id="mana",
                    metadata={
                        "type": "image_generation",
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                        "width": width,
                        "height": height
                    }
                )
                result["steps"]["mem0_save"] = {
                    "success": memory_id is not None,
                    "memory_id": memory_id
                }
            except Exception as e:
                logger.error(f"Mem0保存エラー: {e}")
                result["steps"]["mem0_save"] = {"success": False, "error": str(e)}
        else:
            result["steps"]["mem0_save"] = {"success": False, "reason": "Mem0利用不可"}
        
        # 4. Obsidianにノート作成
        if self.obsidian and self.obsidian.is_available():
            try:
                note_path = self.obsidian.create_note(
                    title=f"画像生成: {prompt[:50]}",
                    content=f"プロンプト: {prompt}\n\nネガティブプロンプト: {negative_prompt}\n\nサイズ: {width}x{height}",
                    tags=["画像生成", "ManaOS", "ComfyUI"]
                )
                result["steps"]["obsidian_note"] = {
                    "success": note_path is not None,
                    "note_path": str(note_path) if note_path else None
                }
            except Exception as e:
                logger.error(f"Obsidianノート作成エラー: {e}")
                result["steps"]["obsidian_note"] = {"success": False, "error": str(e)}
        else:
            result["steps"]["obsidian_note"] = {"success": False, "reason": "Obsidian利用不可"}
        
        # 実行時間を記録
        execution_time = time.time() - start_time
        result["execution_time"] = execution_time
        
        # メトリクスを更新
        self.metrics["workflow_executions"] += 1
        total_executions = self.metrics["workflow_executions"]
        current_avg = self.metrics["average_execution_time"]
        self.metrics["average_execution_time"] = (
            (current_avg * (total_executions - 1) + execution_time) / total_executions
        )
        
        # キャッシュに保存
        if use_cache and self.cache:
            try:
                self.cache.set("workflow", result, ttl_seconds=3600, key=cache_key)
                logger.debug(f"画像生成ワークフローの結果をキャッシュに保存: {cache_key}")
            except Exception as e:
                logger.warning(f"キャッシュ保存エラー: {e}")
        
        return result
    
    def integrate_model_search_workflow(
        self,
        query: str,
        limit: int = 10,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        モデル検索ワークフローを統合実行（キャッシュ対応）
        
        Args:
            query: 検索クエリ
            limit: 取得数
            use_cache: キャッシュを使用するか
            
        Returns:
            実行結果
        """
        import time
        start_time = time.time()
        
        # キャッシュキーを生成
        cache_key = f"model_search_{hash((query, limit))}"
        
        # キャッシュから取得を試みる
        if use_cache and self.cache:
            cached_result = self.cache.get("workflow", cache_key)
            if cached_result:
                self.metrics["cache_hits"] += 1
                logger.info(f"モデル検索ワークフローのキャッシュヒット: {cache_key}")
                return cached_result
            self.metrics["cache_misses"] += 1
        
        result = {
            "workflow": "モデル検索統合",
            "steps": {},
            "cached": False
        }
        
        # 1. CivitAIでモデル検索
        if self.civitai:
            try:
                models = self.civitai.search_models(query=query, limit=limit)
                result["steps"]["civitai_search"] = {
                    "success": True,
                    "models": models,
                    "count": len(models)
                }
            except Exception as e:
                logger.error(f"CivitAI検索エラー: {e}")
                result["steps"]["civitai_search"] = {
                    "success": False,
                    "error": str(e),
                    "models": [],
                    "count": 0
                }
        else:
            result["steps"]["civitai_search"] = {
                "success": False,
                "reason": "CivitAI利用不可",
                "models": [],
                "count": 0
            }
        
        # 2. Mem0にメモリ保存
        models = result["steps"]["civitai_search"].get("models", [])
        if self.mem0 and self.mem0.is_available() and models:
            try:
                for model in models[:3]:  # 上位3件を保存
                    memory_id = self.mem0.add_memory(
                        memory_text=f"モデル検索結果: {model.get('name')} (評価: {model.get('rating', 0)}/5)",
                        user_id="mana",
                        metadata={
                            "type": "model_search",
                            "query": query,
                            "model_id": model.get("id"),
                            "model_name": model.get("name")
                        }
                    )
            except Exception as e:
                logger.error(f"Mem0保存エラー: {e}")
        
        # 3. Obsidianにノート作成
        if self.obsidian and self.obsidian.is_available() and models:
            note_content = f"# モデル検索結果: {query}\n\n"
            for i, model in enumerate(models[:10], 1):
                note_content += f"## {i}. {model.get('name')}\n\n"
                note_content += f"- **ID**: {model.get('id')}\n"
                note_content += f"- **評価**: {model.get('rating', 0)}/5\n"
                note_content += f"- **ダウンロード数**: {model.get('downloadCount', 0)}\n\n"
            
            note_path = self.obsidian.create_note(
                title=f"モデル検索: {query}",
                content=note_content,
                tags=["CivitAI", "モデル検索", "ManaOS"]
            )
            result["steps"]["obsidian_note"] = {
                "success": note_path is not None,
                "note_path": str(note_path) if note_path else None
            }
        
        # 実行時間を記録
        execution_time = time.time() - start_time
        result["execution_time"] = execution_time
        
        # メトリクスを更新
        self.metrics["workflow_executions"] += 1
        total_executions = self.metrics["workflow_executions"]
        current_avg = self.metrics["average_execution_time"]
        self.metrics["average_execution_time"] = (
            (current_avg * (total_executions - 1) + execution_time) / total_executions
        )
        
        # キャッシュに保存
        if use_cache and self.cache:
            try:
                self.cache.set("workflow", result, ttl_seconds=1800, key=cache_key)  # 30分キャッシュ
                logger.debug(f"モデル検索ワークフローの結果をキャッシュに保存: {cache_key}")
            except Exception as e:
                logger.warning(f"キャッシュ保存エラー: {e}")
        
        return result
    
    def integrate_ai_chat_workflow(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        AIチャットワークフローを統合実行（キャッシュ対応）
        
        Args:
            message: ユーザーメッセージ
            system_prompt: システムプロンプト
            use_cache: キャッシュを使用するか
            
        Returns:
            実行結果
        """
        import time
        start_time = time.time()
        
        # キャッシュキーを生成（チャットはキャッシュしない方が良い場合もある）
        cache_key = f"ai_chat_{hash((message, system_prompt))}"
        
        # キャッシュから取得を試みる（オプション）
        if use_cache and self.cache:
            cached_result = self.cache.get("workflow", cache_key)
            if cached_result:
                self.metrics["cache_hits"] += 1
                logger.info(f"AIチャットワークフローのキャッシュヒット: {cache_key}")
                return cached_result
            self.metrics["cache_misses"] += 1
        
        result = {
            "workflow": "AIチャット統合",
            "steps": {},
            "cached": False
        }
        
        # 1. LangChainでチャット
        response = None
        if self.langchain and self.langchain.is_available():
            try:
                response = self.langchain.chat(message, system_prompt)
                result["steps"]["langchain_chat"] = {
                    "success": True,
                    "response": response
                }
            except Exception as e:
                logger.error(f"LangChainチャットエラー: {e}")
                result["steps"]["langchain_chat"] = {
                    "success": False,
                    "error": str(e)
                }
        else:
            result["steps"]["langchain_chat"] = {"success": False, "reason": "LangChain利用不可"}
        
        # 2. Mem0にメモリ保存
        if self.mem0 and self.mem0.is_available():
            try:
                memory_id = self.mem0.add_memory(
                    memory_text=f"チャット: {message}",
                    user_id="mana",
                    metadata={
                        "type": "chat",
                        "message": message,
                        "response": response
                    }
                )
                result["steps"]["mem0_save"] = {
                    "success": memory_id is not None,
                    "memory_id": memory_id
                }
            except Exception as e:
                logger.error(f"Mem0保存エラー: {e}")
                result["steps"]["mem0_save"] = {"success": False, "error": str(e)}
        else:
            result["steps"]["mem0_save"] = {"success": False, "reason": "Mem0利用不可"}
        
        # 3. Command Hubに記録（可能な場合）
        try:
            command_result = self.client._make_request(
                f"{self.command_hub_url}/api/commands",
                "POST",
                {
                    "command": "chat",
                    "input": message,
                    "output": response,
                    "timestamp": datetime.now().isoformat()
                },
                None,
                5.0
            )
            result["steps"]["command_hub_record"] = {
                "success": command_result.get("status") != "error"
            }
        except Exception as e:
            logger.error(f"Command Hub記録エラー: {e}")
            result["steps"]["command_hub_record"] = {"success": False, "error": str(e)}
        
        # 実行時間を記録
        execution_time = time.time() - start_time
        result["execution_time"] = execution_time
        
        # メトリクスを更新
        self.metrics["workflow_executions"] += 1
        total_executions = self.metrics["workflow_executions"]
        current_avg = self.metrics["average_execution_time"]
        self.metrics["average_execution_time"] = (
            (current_avg * (total_executions - 1) + execution_time) / total_executions
        )
        
        # キャッシュに保存（チャットは短いTTL）
        if use_cache and self.cache:
            try:
                self.cache.set("workflow", result, ttl_seconds=300, key=cache_key)  # 5分キャッシュ
                logger.debug(f"AIチャットワークフローの結果をキャッシュに保存: {cache_key}")
            except Exception as e:
                logger.warning(f"キャッシュ保存エラー: {e}")
        
        return result
    
    def get_integration_status(self) -> Dict[str, Any]:
        """
        統合状態を取得
        
        Returns:
            統合状態の辞書
        """
        status = {
            "manaos_services": self.check_manaos_services(),
            "integrations": {
                "comfyui": self.comfyui.is_available() if self.comfyui else False,
                "google_drive": self.drive.is_available() if self.drive else False,
                "civitai": self.civitai is not None,  # CivitAIは常に利用可能
                "langchain": self.langchain.is_available() if self.langchain else False,
                "mem0": self.mem0.is_available() if self.mem0 else False,
                "obsidian": self.obsidian.is_available() if self.obsidian else False
            },
            "client_stats": self.client.get_stats(),
            "metrics": self.metrics.copy(),
            "timestamp": datetime.now().isoformat()
        }
        
        # キャッシュ統計を追加
        if self.cache:
            try:
                cache_stats = self.cache.get_stats()
                status["cache_stats"] = cache_stats
            except Exception as e:
                logger.warning(f"キャッシュ統計取得エラー: {e}")
        
        # パフォーマンス統計を追加
        if self.performance_optimizer:
            try:
                perf_stats = {
                    "cache_stats": self.performance_optimizer.get_cache_stats(),
                    "http_pool_stats": self.performance_optimizer.get_http_pool_stats(),
                    "config_cache_stats": self.performance_optimizer.get_config_cache_stats()
                }
                status["performance_stats"] = perf_stats
            except Exception as e:
                logger.warning(f"パフォーマンス統計取得エラー: {e}")
        
        return status
    
    def execute_workflows_parallel(
        self,
        workflows: List[Dict[str, Any]],
        max_workers: int = 3
    ) -> List[Dict[str, Any]]:
        """
        複数のワークフローを並列実行
        
        Args:
            workflows: ワークフロー定義のリスト
                [{"type": "image_generation", "params": {...}}, ...]
            max_workers: 最大並列実行数
        
        Returns:
            実行結果のリスト
        """
        results = []
        
        def execute_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
            """個別のワークフロー実行関数"""
            workflow_type = workflow.get("type")
            params = workflow.get("params", {})
            
            try:
                if workflow_type == "image_generation":
                    return self.integrate_image_generation_workflow(**params)
                elif workflow_type == "model_search":
                    return self.integrate_model_search_workflow(**params)
                elif workflow_type == "ai_chat":
                    return self.integrate_ai_chat_workflow(**params)
                else:
                    return {
                        "success": False,
                        "error": f"未知のワークフロータイプ: {workflow_type}"
                    }
            except Exception as e:
                logger.error(f"ワークフロー実行エラー: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "workflow_type": workflow_type
                }
        
        # 並列実行
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(execute_workflow, wf): wf for wf in workflows}
            for future in as_completed(futures):
                workflow = futures[future]
                try:
                    result = future.result()
                    result["workflow"] = workflow
                    results.append(result)
                except Exception as e:
                    logger.error(f"ワークフロー実行エラー: {e}")
                    results.append({
                        "success": False,
                        "error": str(e),
                        "workflow": workflow
                    })
        
        return results


def main():
    """テスト用メイン関数"""
    print("ManaOSサービスブリッジテスト")
    print("=" * 60)
    
    bridge = ManaOSServiceBridge()
    
    # 統合状態を確認
    status = bridge.get_integration_status()
    print("\n統合状態:")
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    # 画像生成ワークフローテスト
    print("\n画像生成ワークフローを実行中...")
    result = bridge.integrate_image_generation_workflow(
        prompt="a beautiful landscape",
        width=512,
        height=512
    )
    print(f"結果: {json.dumps(result, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    main()



