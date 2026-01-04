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
        self._hf_integration = None
    
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
        
        logger.info(f"[Recall] query: {query}, results: {len(results)}")
        return results[:limit]
    
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
                "run_workflow", "search_models", "get_model_info"
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

