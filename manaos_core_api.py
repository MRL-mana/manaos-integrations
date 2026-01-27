"""
manaOS 標準API（単一I/O - 共通API化のコア）
全機能はこの4つのAPIを通じてアクセス
"""

import logging
import os
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime
import uuid

# .envファイルから環境変数を読み込む
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ManaOSCoreAPI:
    """manaOS標準API"""
    
    # 危険な操作の定義
    DANGEROUS_ACTIONS = {
        "file_delete": {
            "description": "ファイル削除",
            "blocked": True,
            "allowed_paths": []  # 空の場合はすべてブロック
        },
        "system_command": {
            "description": "システムコマンド実行",
            "blocked": True,
            "allowed_commands": []  # 空の場合はすべてブロック
        },
        "database_drop": {
            "description": "データベース削除",
            "blocked": True
        },
        "network_request": {
            "description": "外部ネットワークリクエスト",
            "blocked": False,  # デフォルトは許可（ただしURLチェック）
            "allowed_domains": ["localhost", "127.0.0.1", "api.openai.com", "api.anthropic.com"]  # 許可ドメイン
        },
        "file_write": {
            "description": "ファイル書き込み",
            "blocked": False,  # デフォルトは許可（ただしパスチェック）
            "blocked_paths": ["/etc", "/sys", "/proc", "C:\\Windows", "C:\\Program Files"]  # ブロックパス
        }
    }
    
    def __init__(self):
        """初期化"""
        self.event_history: List[Dict[str, Any]] = []
        self.memory_storage: List[Dict[str, Any]] = []
        self.action_history: List[Dict[str, Any]] = []
        
        # 統合モジュール（遅延インポート）
        self._llm_router = None
        self._notification_hub = None
        self._unified_memory = None
        self._mrl_memory = None  # MRL Memory System統合
        self._hf_integration = None
        self._searxng_integration = None
        self._brave_search_integration = None
        self._base_ai_integration = {}  # use_freeをキーとする辞書
    
    def _get_llm_router(self):
        """LLMルーターを取得（遅延インポート）"""
        if self._llm_router is None:
            try:
                from llm_routing import LLMRouter
                self._llm_router = LLMRouter()
            except ImportError:
                logger.warning("LLMルーターが利用できません")
        return self._llm_router
    
    def _get_notification_hub(self):
        """通知ハブを取得（遅延インポート）"""
        if self._notification_hub is None:
            try:
                from notification_hub import NotificationHub
                self._notification_hub = NotificationHub()
            except ImportError:
                logger.warning("通知ハブが利用できません")
        return self._notification_hub
    
    def _get_unified_memory(self):
        """統一記憶システムを取得（遅延インポート）"""
        if self._unified_memory is None:
            try:
                from memory_unified import UnifiedMemory
                self._unified_memory = UnifiedMemory()
            except ImportError:
                logger.warning("統一記憶システムが利用できません")
        return self._unified_memory
    
    def _get_mrl_memory(self):
        """MRL Memory Systemを取得（遅延インポート・API経由）"""
        if self._mrl_memory is None:
            try:
                import requests
                import os
                # MRL Memory APIのURL
                api_url = os.getenv("MRL_MEMORY_API_URL", "http://localhost:5105")
                # APIキーは環境変数から取得（MRL_MEMORY_API_KEY または API_KEY）
                api_key = os.getenv("MRL_MEMORY_API_KEY") or os.getenv("API_KEY", "")
                
                # ヘルスチェック（認証不要）
                try:
                    response = requests.get(f"{api_url}/health", timeout=2)
                    if response.status_code == 200:
                        # 認証が必要かどうかを確認（/healthは認証不要なので、実際のAPI呼び出しで確認）
                        self._mrl_memory = {
                            "api_url": api_url,
                            "api_key": api_key,
                            "available": True,
                            "auth_required": bool(api_key)  # APIキーが設定されている場合は認証が必要と仮定
                        }
                        logger.info("MRL Memory Systemが利用可能です")
                    else:
                        self._mrl_memory = {"available": False}
                        logger.warning("MRL Memory APIが応答しません")
                except requests.exceptions.RequestException:
                    self._mrl_memory = {"available": False}
                    logger.debug("MRL Memory APIに接続できません（未起動の可能性）")
            except Exception as e:
                logger.warning(f"MRL Memory Systemの初期化エラー: {e}")
                self._mrl_memory = {"available": False}
        return self._mrl_memory
    
    def _get_hf_integration(self):
        """Hugging Face統合を取得（遅延インポート）"""
        if self._hf_integration is None:
            try:
                from huggingface_integration import HuggingFaceManaOSIntegration
                output_dir = os.getenv("HF_OUTPUT_DIR", "generated_images")
                self._hf_integration = HuggingFaceManaOSIntegration(output_dir=output_dir)
            except ImportError as e:
                logger.warning(f"Hugging Face統合が利用できません: {e}")
        return self._hf_integration
    
    def _get_searxng_integration(self):
        """SearXNG統合を取得（遅延インポート）"""
        if self._searxng_integration is None:
            try:
                from searxng_integration import SearXNGIntegration
                base_url = os.getenv("SEARXNG_BASE_URL", "http://localhost:8080")
                self._searxng_integration = SearXNGIntegration(base_url=base_url)
            except ImportError as e:
                logger.warning(f"SearXNG統合が利用できません: {e}")
        return self._searxng_integration
    
    def _get_brave_search_integration(self):
        """Brave Search統合を取得（遅延インポート）"""
        if self._brave_search_integration is None:
            try:
                from brave_search_integration import BraveSearchIntegration
                self._brave_search_integration = BraveSearchIntegration()
            except ImportError as e:
                logger.warning(f"Brave Search統合が利用できません: {e}")
        return self._brave_search_integration
    
    def _get_base_ai_integration(self, use_free: bool = False):
        """Base AI統合を取得（遅延インポート）"""
        if not isinstance(self._base_ai_integration, dict):
            self._base_ai_integration = {}
        
        if use_free not in self._base_ai_integration:
            try:
                from base_ai_integration import BaseAIIntegration
                self._base_ai_integration[use_free] = BaseAIIntegration(use_free=use_free)
            except ImportError as e:
                logger.warning(f"Base AI統合が利用できません: {e}")
                return None
        
        return self._base_ai_integration.get(use_free)
    
    def emit(self, event_type: str, payload: Dict[str, Any], priority: str = "normal"):
        """
        イベント発行（通知・ログ・状態変化）
        
        Args:
            event_type: イベントタイプ
            payload: ペイロード
            priority: 優先度（"critical", "important", "normal", "low"）
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "payload": payload,
            "priority": priority,
            "timestamp": datetime.now().isoformat()
        }
        
        self.event_history.append(event)
        
        # 通知ハブに送信
        notification_hub = self._get_notification_hub()
        if notification_hub:
            try:
                message = f"[{event_type}] {payload.get('message', str(payload))}"
                notification_hub.notify(message, priority)
            except Exception as e:
                logger.error(f"通知送信エラー: {e}")
        
        # 自動保存: 重要なイベントを記憶システムに保存
        if priority in ["critical", "important"]:
            self._auto_save_event(event)
        
        logger.info(f"[Emit] {event_type} ({priority}): {payload}")
        return event
    
    def _auto_save_event(self, event: Dict[str, Any]):
        """
        重要なイベントを自動的に記憶システムに保存
        
        Args:
            event: イベント情報
        """
        try:
            event_content = {
                "content": f"イベント: {event.get('event_type')} - {str(event.get('payload', {}))[:200]}",
                "metadata": {
                    "event_id": event.get("event_id"),
                    "event_type": event.get("event_type"),
                    "priority": event.get("priority"),
                    "timestamp": event.get("timestamp"),
                    "source": "manaos_event"
                }
            }
            
            unified_memory = self._get_unified_memory()
            if unified_memory:
                unified_memory.store(event_content, format_type="system")
                logger.debug(f"[Auto Save] イベントを保存: {event.get('event_type')}")
        except Exception as e:
            logger.warning(f"イベント自動保存エラー: {e}")
    
    def remember(self, input_data: Dict[str, Any], format_type: str = "auto"):
        """
        記憶への保存（入力）
        
        Args:
            input_data: 入力データ
            format_type: フォーマットタイプ（"conversation", "memo", "research", "system", "auto"）
        """
        memory_entry = {
            "memory_id": str(uuid.uuid4()),
            "format_type": format_type,
            "input_data": input_data,
            "timestamp": datetime.now().isoformat()
        }
        
        self.memory_storage.append(memory_entry)
        
        # 統一記憶システムに保存
        unified_memory = self._get_unified_memory()
        if unified_memory:
            try:
                unified_memory.store(input_data, format_type)
            except Exception as e:
                logger.error(f"記憶保存エラー: {e}")
        
        # MRL Memory Systemに保存（API経由）
        mrl_memory = self._get_mrl_memory()
        if mrl_memory and mrl_memory.get("available"):
            try:
                import requests
                text_content = input_data.get("content", str(input_data))
                if isinstance(text_content, dict):
                    text_content = str(text_content)
                
                api_url = mrl_memory["api_url"]
                api_key = mrl_memory.get("api_key", "")
                headers = {"Content-Type": "application/json"}
                # APIキーが設定されている場合のみヘッダーに追加
                if api_key:
                    headers["X-API-Key"] = api_key
                
                response = requests.post(
                    f"{api_url}/api/memory/process",
                    json={
                        "text": text_content,
                        "source": "manaos",
                        "enable_rehearsal": True,
                        "enable_promotion": False
                    },
                    headers=headers,
                    timeout=5
                )
                if response.status_code == 200:
                    logger.debug(f"[MRL Memory] 保存成功: {format_type}")
                elif response.status_code == 401:
                    # 認証エラーの場合、APIキーが未設定の可能性
                    logger.debug(f"[MRL Memory] 認証エラー（APIキー未設定の可能性）: HTTP 401")
                else:
                    logger.debug(f"[MRL Memory] 保存失敗: HTTP {response.status_code}")
            except Exception as e:
                logger.debug(f"MRL Memory保存エラー（無視）: {e}")
        
        logger.info(f"[Remember] {format_type}: {input_data.get('content', str(input_data))[:50]}...")
        return memory_entry
    
    def recall(self, query: str, scope: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
        """
        記憶からの検索（出力）
        
        Args:
            query: 検索クエリ
            scope: スコープ（"all", "today", "week", "month"）
            limit: 取得件数
        
        Returns:
            検索結果のリスト
        """
        # 簡易検索（実装は後で拡張）
        results = []
        query_lower = query.lower()
        
        for entry in self.memory_storage:
            content = str(entry.get("input_data", {})).lower()
            if query_lower in content:
                results.append(entry)
                if len(results) >= limit:
                    break
        
        # 統一記憶システムから検索
        unified_memory = self._get_unified_memory()
        if unified_memory:
            try:
                unified_results = unified_memory.recall(query, scope, limit)
                results.extend(unified_results)
            except Exception as e:
                logger.error(f"記憶検索エラー: {e}")
        
        # MRL Memory Systemから検索（API経由）
        mrl_memory = self._get_mrl_memory()
        if mrl_memory and mrl_memory.get("available"):
            try:
                import requests
                api_url = mrl_memory["api_url"]
                api_key = mrl_memory.get("api_key", "")
                headers = {"Content-Type": "application/json"}
                # APIキーが設定されている場合のみヘッダーに追加
                if api_key:
                    headers["X-API-Key"] = api_key
                
                response = requests.post(
                    f"{api_url}/api/memory/search",
                    json={
                        "query": query,
                        "limit": limit
                    },
                    headers=headers,
                    timeout=5
                )
                if response.status_code == 200:
                    mrl_results = response.json()
                    if isinstance(mrl_results, dict) and "results" in mrl_results:
                        # MRL Memoryの結果を統一フォーマットに変換
                        for item in mrl_results["results"]:
                            results.append({
                                "memory_id": item.get("id", str(uuid.uuid4())),
                                "format_type": "mrl_memory",
                                "input_data": {"content": item.get("content", ""), "metadata": item.get("metadata", {})},
                                "timestamp": item.get("timestamp", datetime.now().isoformat()),
                                "score": item.get("score", 0.0)
                            })
                        logger.debug(f"[MRL Memory] 検索成功: {len(mrl_results.get('results', []))}件")
                elif response.status_code == 401:
                    # 認証エラーの場合、APIキーが未設定の可能性
                    logger.debug(f"[MRL Memory] 認証エラー（APIキー未設定の可能性）: HTTP 401")
                else:
                    logger.debug(f"[MRL Memory] 検索失敗: HTTP {response.status_code}")
            except Exception as e:
                logger.debug(f"MRL Memory検索エラー（無視）: {e}")
        
        # スコアでソート（MRL Memoryの結果が含まれる場合）
        results = sorted(results, key=lambda x: x.get("score", 0.0), reverse=True)[:limit]
        
        logger.info(f"[Recall] query: {query}, results: {len(results)}")
        return results
    
    def _check_safety(self, action_type: str, args: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        安全柵：危険な操作をチェック
        
        Returns:
            (is_safe, error_message): (True/False, エラーメッセージ)
        """
        # 危険な操作のチェック
        if action_type in self.DANGEROUS_ACTIONS:
            danger_config = self.DANGEROUS_ACTIONS[action_type]
            
            # ブロックされている操作
            if danger_config.get("blocked", False):
                return False, f"危険な操作がブロックされました: {danger_config['description']} ({action_type})"
            
            # パス/コマンド/ドメインのチェック
            if action_type == "file_delete":
                path = args.get("path", "")
                allowed_paths = danger_config.get("allowed_paths", [])
                if allowed_paths and path not in allowed_paths:
                    return False, f"ファイル削除がブロックされました: {path} (許可されていないパス)"
            
            elif action_type == "system_command":
                command = args.get("command", "")
                allowed_commands = danger_config.get("allowed_commands", [])
                if allowed_commands and command not in allowed_commands:
                    return False, f"システムコマンドがブロックされました: {command} (許可されていないコマンド)"
            
            elif action_type == "network_request":
                url = args.get("url", "")
                allowed_domains = danger_config.get("allowed_domains", [])
                if allowed_domains:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    domain = parsed.netloc.split(':')[0]  # ポート番号を除去
                    if domain not in allowed_domains:
                        return False, f"ネットワークリクエストがブロックされました: {url} (許可されていないドメイン)"
            
            elif action_type == "file_write":
                path = args.get("path", "")
                blocked_paths = danger_config.get("blocked_paths", [])
                for blocked_path in blocked_paths:
                    if path.startswith(blocked_path):
                        return False, f"ファイル書き込みがブロックされました: {path} (ブロックされたパス: {blocked_path})"
        
        return True, None
    
    def act(self, action_type: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        アクション実行（タスク・ツール呼び出し）
        
        Args:
            action_type: アクションタイプ（"llm_call", "generate_image", "run_workflow", etc.）
            args: 引数
        
        Returns:
            実行結果
        """
        # 安全柵チェック
        is_safe, error_message = self._check_safety(action_type, args)
        if not is_safe:
            logger.warning(f"[Safety Guard] ブロック: {action_type} - {error_message}")
            return {
                "error": "safety_guard_blocked",
                "message": error_message,
                "action_type": action_type
            }
        
        action = {
            "action_id": str(uuid.uuid4()),
            "action_type": action_type,
            "args": args,
            "timestamp": datetime.now().isoformat()
        }
        
        self.action_history.append(action)
        
        # 自動保存: ManaOS操作を記憶システムに保存
        self._auto_save_action(action)
        
        # LLM呼び出し
        if action_type == "llm_call":
            router = self._get_llm_router()
            if router:
                try:
                    task_type = args.get("task_type", "conversation")
                    prompt = args.get("prompt", "")
                    memory_refs = args.get("memory_refs", [])
                    tools_used = args.get("tools_used", [])
                    
                    # lightweight_conversationタスクタイプのサポート
                    if task_type == "lightweight_conversation":
                        # LFM 2.5専用タスクタイプとして処理
                        result = router.route(
                            task_type="lightweight_conversation",
                            prompt=prompt,
                            memory_refs=memory_refs,
                            tools_used=tools_used
                        )
                    else:
                        result = router.route(
                            task_type=task_type,
                            prompt=prompt,
                            memory_refs=memory_refs,
                            tools_used=tools_used
                        )
                    
                    action["result"] = result
                    logger.info(f"[Act] LLM call: {task_type} -> {result['model']}")
                    return result
                except Exception as e:
                    logger.error(f"LLM呼び出しエラー: {e}")
                    action["error"] = str(e)
                    return {"error": str(e)}
        
        # LFM 2.5専用呼び出し
        if action_type == "lfm25_call" or action_type == "lightweight_llm":
            try:
                from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType
                client = AlwaysReadyLLMClient()
                message = args.get("message", args.get("prompt", ""))
                task_type = args.get("task_type", "lightweight_conversation")
                
                if task_type == "lightweight_conversation":
                    task_type_enum = TaskType.LIGHTWEIGHT_CONVERSATION
                else:
                    task_type_enum = TaskType.CONVERSATION
                
                response = client.chat(
                    message=message,
                    model=ModelType.ULTRA_LIGHT,
                    task_type=task_type_enum
                )
                
                result = {
                    "response": response.response,
                    "model": response.model,
                    "latency_ms": response.latency_ms,
                    "cached": response.cached,
                    "source": response.source
                }
                
                action["result"] = result
                logger.info(f"[Act] LFM 2.5 call: {task_type} -> {response.latency_ms:.2f}ms")
                return result
            except ImportError:
                logger.error("LFM 2.5クライアントが利用できません")
                return {"error": "LFM 2.5クライアントが利用できません"}
            except Exception as e:
                logger.error(f"LFM 2.5呼び出しエラー: {e}")
                action["error"] = str(e)
                return {"error": str(e)}
        
        # SVI動画生成
        if action_type == "generate_video" or action_type == "svi_generate":
            try:
                import requests
                api_url = os.getenv("MANAOS_INTEGRATION_API_URL", "http://localhost:9500")
                
                response = requests.post(
                    f"{api_url}/api/svi/generate",
                    json=args,
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                
                action["result"] = result
                logger.info(f"[Act] SVI動画生成: {result.get('prompt_id', 'N/A')}")
                return result
            except ImportError:
                logger.error("requestsライブラリが利用できません")
                return {"error": "requestsライブラリが必要です"}
            except Exception as e:
                logger.error(f"SVI動画生成エラー: {e}")
                action["error"] = str(e)
                return {"error": str(e)}
        
        # SVI動画延長
        if action_type == "extend_video" or action_type == "svi_extend":
            try:
                import requests
                api_url = os.getenv("MANAOS_INTEGRATION_API_URL", "http://localhost:9500")
                
                response = requests.post(
                    f"{api_url}/api/svi/extend",
                    json=args,
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                
                action["result"] = result
                logger.info(f"[Act] SVI動画延長: {result.get('prompt_id', 'N/A')}")
                return result
            except ImportError:
                logger.error("requestsライブラリが利用できません")
                return {"error": "requestsライブラリが必要です"}
            except Exception as e:
                logger.error(f"SVI動画延長エラー: {e}")
                action["error"] = str(e)
                return {"error": str(e)}
        
        # SVIストーリー動画生成
        if action_type == "create_story_video" or action_type == "svi_story":
            try:
                import requests
                api_url = os.getenv("MANAOS_INTEGRATION_API_URL", "http://localhost:9500")
                
                response = requests.post(
                    f"{api_url}/api/svi/story",
                    json=args,
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                
                action["result"] = result
                logger.info(f"[Act] SVIストーリー動画生成: {len(result.get('execution_ids', []))}セグメント")
                return result
            except ImportError:
                logger.error("requestsライブラリが利用できません")
                return {"error": "requestsライブラリが必要です"}
            except Exception as e:
                logger.error(f"SVIストーリー動画生成エラー: {e}")
                action["error"] = str(e)
                return {"error": str(e)}
        
        # Hugging Face画像生成
        if action_type == "generate_image" or action_type == "hf_generate":
            hf = self._get_hf_integration()
            if not hf:
                return {"error": "Hugging Face統合が利用できません"}
            
            try:
                prompt = args.get("prompt", "")
                if not prompt:
                    return {"error": "プロンプトが指定されていません"}
                
                result = hf.generate_image(
                    prompt=prompt,
                    negative_prompt=args.get("negative_prompt", ""),
                    model_id=args.get("model_id", "runwayml/stable-diffusion-v1-5"),
                    width=args.get("width", 512),
                    height=args.get("height", 512),
                    num_inference_steps=args.get("num_inference_steps", 50),
                    guidance_scale=args.get("guidance_scale", 7.5),
                    seed=args.get("seed"),
                    auto_stock=args.get("auto_stock", True)
                )
                
                action["result"] = result
                if result.get("success"):
                    logger.info(f"[Act] Hugging Face画像生成: {result.get('count', 0)}枚生成")
                    # イベント発行
                    self.emit("image_generated", {
                        "model_id": result.get("model_id"),
                        "prompt": prompt,
                        "count": result.get("count", 0),
                        "images": result.get("images", [])
                    }, "normal")
                return result
            except Exception as e:
                logger.error(f"Hugging Face画像生成エラー: {e}")
                action["error"] = str(e)
                return {"error": str(e)}
        
        # Hugging Faceモデル検索
        if action_type == "search_models" or action_type == "hf_search":
            hf = self._get_hf_integration()
            if not hf:
                return {"error": "Hugging Face統合が利用できません"}
            
            try:
                query = args.get("query", "")
                if not query:
                    return {"error": "検索クエリが指定されていません"}
                
                results = hf.search_models(
                    query=query,
                    task=args.get("task"),
                    limit=args.get("limit", 10)
                )
                
                action["result"] = {"models": results, "count": len(results)}
                logger.info(f"[Act] Hugging Faceモデル検索: {len(results)}件")
                return action["result"]
            except Exception as e:
                logger.error(f"Hugging Faceモデル検索エラー: {e}")
                action["error"] = str(e)
                return {"error": str(e)}
        
        # Hugging Faceモデル情報取得
        if action_type == "get_model_info" or action_type == "hf_model_info":
            hf = self._get_hf_integration()
            if not hf:
                return {"error": "Hugging Face統合が利用できません"}
            
            try:
                model_id = args.get("model_id", "")
                if not model_id:
                    return {"error": "モデルIDが指定されていません"}
                
                info = hf.get_model_info(model_id)
                action["result"] = {"model_info": info}
                logger.info(f"[Act] Hugging Faceモデル情報取得: {model_id}")
                return action["result"]
            except Exception as e:
                logger.error(f"Hugging Faceモデル情報取得エラー: {e}")
                action["error"] = str(e)
                return {"error": str(e)}
        
        # Stable Diffusion プロンプト生成（Ollama統合）
        if action_type == "generate_sd_prompt" or action_type == "sd_prompt":
            try:
                import requests
                
                japanese_description = args.get("prompt", args.get("description", ""))
                if not japanese_description:
                    return {"error": "日本語の説明が指定されていません"}
                
                model_name = args.get("model", "llama3-uncensored")
                temperature = args.get("temperature", 0.9)
                ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
                
                # システムプロンプト
                system_prompt = "You are an expert at creating detailed prompts for Stable Diffusion image generation. Convert the following Japanese description into a detailed, descriptive English prompt suitable for Stable Diffusion. Include style, composition, lighting, and other relevant details. Output only the prompt, no explanations."
                
                # Ollama APIを呼び出し
                request_body = {
                    "model": model_name,
                    "prompt": f"{system_prompt}\n\nJapanese description: {japanese_description}\n\nEnglish prompt for Stable Diffusion:",
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "top_p": 0.95,
                        "top_k": 40
                    }
                }
                
                response = requests.post(
                    f"{ollama_url}/api/generate",
                    json=request_body,
                    timeout=60
                )
                response.raise_for_status()
                result_data = response.json()
                
                generated_prompt = result_data.get("response", "")
                if not generated_prompt:
                    return {"error": "プロンプトの生成に失敗しました"}
                
                result = {
                    "success": True,
                    "prompt": generated_prompt,
                    "japanese_description": japanese_description,
                    "model": model_name,
                    "temperature": temperature
                }
                
                action["result"] = result
                logger.info(f"[Act] SDプロンプト生成: {japanese_description[:50]}...")
                return result
                
            except ImportError:
                logger.error("requestsライブラリが利用できません")
                return {"error": "requestsライブラリが必要です"}
            except Exception as e:
                logger.error(f"SDプロンプト生成エラー: {e}")
                action["error"] = str(e)
                return {"error": str(e)}
        
        # SearXNG Web検索
        if action_type == "web_search" or action_type == "search_web":
            searxng = self._get_searxng_integration()
            if not searxng:
                return {"error": "SearXNG統合が利用できません"}
            
            try:
                query = args.get("query", "")
                if not query:
                    return {"error": "検索クエリが指定されていません"}
                
                result = searxng.search(
                    query=query,
                    max_results=args.get("max_results", 10),
                    language=args.get("language", "ja"),
                    categories=args.get("categories"),
                    time_range=args.get("time_range")
                )
                
                action["result"] = result
                logger.info(f"[Act] Web検索: {query} -> {result.get('count', 0)}件")
                return result
            except Exception as e:
                logger.error(f"Web検索エラー: {e}")
                action["error"] = str(e)
                return {"error": str(e)}
        
        # Brave Search Web検索
        if action_type == "brave_search" or action_type == "brave_web_search":
            brave = self._get_brave_search_integration()
            if not brave or not brave.is_available():
                return {"error": "Brave Search統合が利用できません"}
            
            try:
                query = args.get("query", "")
                if not query:
                    return {"error": "検索クエリが指定されていません"}
                
                results = brave.search(
                    query=query,
                    count=args.get("count", 10),
                    search_lang=args.get("search_lang", "jp"),
                    country=args.get("country", "JP"),
                    freshness=args.get("freshness")
                )
                
                result = {
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
                }
                
                action["result"] = result
                logger.info(f"[Act] Brave Search: {query} -> {len(results)}件")
                # イベント発行
                self.emit("web_search", {
                    "provider": "brave",
                    "query": query,
                    "count": len(results)
                }, "normal")
                return result
            except Exception as e:
                logger.error(f"Brave Searchエラー: {e}")
                action["error"] = str(e)
                return {"error": str(e)}
        
        # Base AI チャット
        if action_type == "base_ai_chat" or action_type == "base_ai_completion":
            use_free = args.get("use_free", False)
            base_ai = self._get_base_ai_integration(use_free=use_free)
            if not base_ai or not base_ai.is_available():
                return {"error": "Base AI統合が利用できません"}
            
            try:
                prompt = args.get("prompt", "")
                system_prompt = args.get("system_prompt")
                if not prompt:
                    return {"error": "プロンプトが指定されていません"}
                
                response = base_ai.chat_simple(
                    prompt=prompt,
                    system_prompt=system_prompt
                )
                
                result = {
                    "response": response,
                    "model": "base-ai",
                    "use_free": use_free
                }
                
                action["result"] = result
                logger.info(f"[Act] Base AIチャット: {prompt[:50]}...")
                # イベント発行
                self.emit("llm_call", {
                    "provider": "base_ai",
                    "prompt": prompt[:100],
                    "use_free": use_free
                }, "normal")
                return result
            except Exception as e:
                logger.error(f"Base AIチャットエラー: {e}")
                action["error"] = str(e)
                return {"error": str(e)}
        
        # その他のアクション（実装予定）
        logger.info(f"[Act] {action_type}: {args}")
        return action
    
    def _auto_save_action(self, action: Dict[str, Any]):
        """
        ManaOS操作を自動的に記憶システムに保存
        
        Args:
            action: アクション情報
        """
        try:
            # 重要な操作のみ自動保存（フィルタリング）
            important_actions = [
                "llm_call", "generate_image", "generate_video", 
                "svi_generate", "svi_extend", "svi_story",
                "run_workflow", "search_models", "get_model_info",
                "web_search", "search_web", "brave_search", "brave_web_search",
                "base_ai_chat", "base_ai_completion",
                "generate_sd_prompt", "sd_prompt"
            ]
            
            action_type = action.get("action_type", "")
            if action_type not in important_actions:
                return  # 重要でない操作はスキップ
            
            # 操作内容を記憶システムに保存
            action_content = {
                "content": f"ManaOS操作: {action_type}",
                "metadata": {
                    "action_id": action.get("action_id"),
                    "action_type": action_type,
                    "args_summary": str(action.get("args", {}))[:200],
                    "timestamp": action.get("timestamp"),
                    "source": "manaos_operation"
                }
            }
            
            unified_memory = self._get_unified_memory()
            if unified_memory:
                unified_memory.store(action_content, format_type="system")
                logger.debug(f"[Auto Save] ManaOS操作を保存: {action_type}")
        except Exception as e:
            logger.warning(f"自動保存エラー: {e}")
    
    def save_conversation(self, user_message: str, assistant_response: str, context: Optional[Dict[str, Any]] = None):
        """
        Cursorでの会話を自動的に記憶システムに保存
        
        Args:
            user_message: ユーザーのメッセージ
            assistant_response: アシスタントの応答
            context: 追加コンテキスト（オプション）
        
        Returns:
            保存されたメモリID（成功時）、None（失敗時）
        """
        try:
            conversation_content = {
                "content": f"user: {user_message}\nassistant: {assistant_response}",
                "metadata": {
                    "source": "cursor",
                    "user": context.get("user", "default") if context else "default",
                    "timestamp": datetime.now().isoformat(),
                    **(context or {})
                }
            }
            
            unified_memory = self._get_unified_memory()
            if unified_memory:
                memory_id = unified_memory.store(conversation_content, format_type="conversation")
                logger.info(f"[Auto Save] Cursor会話を保存: {memory_id}")
                return memory_id
        except Exception as e:
            logger.warning(f"会話保存エラー: {e}")
        return None


# グローバルインスタンス
_manaos_api = None


def get_manaos_api() -> ManaOSCoreAPI:
    """manaOS APIのグローバルインスタンスを取得"""
    global _manaos_api
    if _manaos_api is None:
        _manaos_api = ManaOSCoreAPI()
    return _manaos_api


# 便利関数（標準APIとして使用）
def emit(event_type: str, payload: Dict[str, Any], priority: str = "normal"):
    """イベント発行"""
    return get_manaos_api().emit(event_type, payload, priority)


def remember(input_data: Dict[str, Any], format_type: str = "auto"):
    """記憶への保存"""
    return get_manaos_api().remember(input_data, format_type)


def recall(query: str, scope: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
    """記憶からの検索"""
    return get_manaos_api().recall(query, scope, limit)


def act(action_type: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """アクション実行"""
    return get_manaos_api().act(action_type, args)


def save_conversation(user_message: str, assistant_response: str, context: Optional[Dict[str, Any]] = None):
    """Cursorでの会話を自動的に記憶システムに保存"""
    return get_manaos_api().save_conversation(user_message, assistant_response, context)


# 使用例
if __name__ == "__main__":
    # 標準APIの使用例
    import manaos_core_api as manaos
    
    # イベント発行
    manaos.emit("task_completed", {"task_id": "123", "message": "タスク完了"}, "important")
    
    # 記憶への保存
    manaos.remember({"type": "conversation", "content": "こんにちは"}, "conversation")
    
    # 記憶からの検索
    results = manaos.recall("こんにちは", scope="all", limit=5)
    print(f"検索結果: {len(results)}件")
    
    # LLM呼び出し
    result = manaos.act("llm_call", {
        "task_type": "conversation",
        "prompt": "こんにちは、今日はいい天気ですね。"
    })
    print(f"LLM応答: {result.get('response', '')[:100]}...")

