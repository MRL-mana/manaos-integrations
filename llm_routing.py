"""
LLMルーティングシステム
ロール別モデル + fallback + 監査ログ
"""

import os
import yaml
import uuid
import time
import logging
import requests
import subprocess
import platform
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AuditLog:
    """監査ログデータクラス"""
    request_id: str
    timestamp: str
    routed_model: str
    task_type: str
    memory_refs: List[str]
    tools_used: List[str]
    input_summary: str
    output_summary: str
    cost: float
    latency_ms: int
    fallback_used: bool
    fallback_reason_code: Optional[str] = None  # "GPU_OOM", "TIMEOUT", "MODEL_DOWN", "DB_UNAVAILABLE", "GPU_BUSY"
    fallback_reason_detail: Optional[str] = None  # 詳細情報（使用率、待ち時間等）
    trigger_metric: Optional[Dict[str, Any]] = None  # トリガーとなったメトリクス（VRAM使用率、待ち時間等）


class ModelUnavailableError(Exception):
    """モデルが利用できない場合のエラー"""
    pass


class AllModelsUnavailableError(Exception):
    """すべてのモデルが利用できない場合のエラー"""
    pass


class LLMRouter:
    """LLMルーティングシステム（fallback付き）"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス（Noneの場合はデフォルト）
        """
        if config_path is None:
            config_path = Path(__file__).parent / "llm_routing_config.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.ollama_url = self.config.get("ollama_url", "http://localhost:11434")
        self.routing_config = self.config.get("routing", {})
        self.audit_config = self.config.get("audit_log", {})
        
        # 監査ログのストレージ
        self.audit_logs: List[AuditLog] = []
        
        # 記憶システムの初期化（オプション）
        self._unified_memory = None
        self._init_memory_system()
        
        # 人格設定の読み込み（オプション）
        self.persona_config = self._load_persona_config()
        self.system_prompt = self.persona_config.get("persona", {}).get("system_prompt", "")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込む"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"設定ファイルが見つかりません: {self.config_path}")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"設定ファイルの読み込みエラー: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を返す"""
        return {
            "ollama_url": "http://localhost:11434",
            "routing": {
                "conversation": {
                    "primary": "llama3.2:3b",
                    "fallback": ["qwen2.5:7b", "llama3.1:8b"],
                    "priority": "latency",
                    "max_tokens": 2048
                },
                "reasoning": {
                    "primary": "qwen2.5:72b",
                    "fallback": ["qwen2.5:32b", "llama3.1:70b"],
                    "priority": "quality",
                    "max_tokens": 8192
                },
                "automation": {
                    "primary": "qwen2.5:14b",
                    "fallback": ["llama3.1:8b", "mistral:7b"],
                    "priority": "tool_use",
                    "max_tokens": 4096
                }
            },
            "audit_log": {
                "enabled": True,
                "storage": "obsidian"
            },
            "memory": {
                "enabled": True,
                "auto_save": True,
                "load_history": True
            }
        }
    
    def _init_memory_system(self):
        """記憶システムを初期化"""
        try:
            from memory_unified import UnifiedMemory
            self._unified_memory = UnifiedMemory()
            logger.info("統一記憶システムを初期化しました")
        except ImportError:
            logger.warning("統一記憶システムが利用できません")
            self._unified_memory = None
        except Exception as e:
            logger.warning(f"記憶システムの初期化エラー: {e}")
            self._unified_memory = None
    
    def _load_persona_config(self) -> Dict[str, Any]:
        """人格設定を読み込む"""
        persona_path = Path(__file__).parent / "persona_config.yaml"
        try:
            if persona_path.exists():
                with open(persona_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    logger.info("人格設定を読み込みました")
                    return config
            else:
                logger.debug("人格設定ファイルが見つかりません（デフォルト設定を使用）")
                return {}
        except Exception as e:
            logger.warning(f"人格設定の読み込みエラー: {e}")
            return {}
    
    def _check_gpu_in_use(self) -> Tuple[bool, Dict[str, Any]]:
        """
        GPUが他のプロセスで使用されているかチェック
        
        Returns:
            (is_in_use, metrics): (True/False, メトリクス情報)
        """
        metrics = {
            "gpu_utilization": None,
            "vram_usage_mb": None,
            "ollama_processes": 0,
            "check_method": "unknown"
        }
        
        try:
            # Windows環境でのチェック
            if platform.system() == "Windows":
                metrics["check_method"] = "windows_tasklist"
                # ollamaプロセスが複数実行されているかチェック
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq ollama.exe"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                # ollamaプロセス数をカウント
                lines = [line for line in result.stdout.split('\n') if 'ollama.exe' in line]
                metrics["ollama_processes"] = len(lines)
                
                # ollamaプロセスが2つ以上あれば、GPUが使用中と判断
                # ただし、CPUモードで実行されている場合は除外
                if len(lines) >= 2:
                    # ollama psでCPUモードか確認
                    try:
                        ps_result = subprocess.run(
                            ["ollama", "ps"],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        if ps_result.returncode == 0:
                            # CPUモードで実行されている場合は、GPUが利用可能と判断
                            if "100% CPU" in ps_result.stdout:
                                logger.debug(f"OllamaがCPUモードで実行中（GPU利用可能）")
                                return False, metrics  # GPUが利用可能
                    except:
                        pass
                    logger.info(f"GPUが他のプロセスで使用中と判断（ollamaプロセス: {len(lines)}個）")
                    return True, metrics
                
                # nvidia-smiが利用可能な場合は詳細情報を取得
                try:
                    nvidia_result = subprocess.run(
                        ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if nvidia_result.returncode == 0:
                        lines = nvidia_result.stdout.strip().split('\n')
                        if lines:
                            parts = lines[0].split(',')
                            if len(parts) >= 2:
                                metrics["gpu_utilization"] = int(parts[0].strip())
                                metrics["vram_usage_mb"] = int(parts[1].strip())
                                metrics["check_method"] = "windows_nvidia_smi"
                                # GPU使用率が50%以上なら使用中と判断
                                if metrics["gpu_utilization"] > 50:
                                    logger.info(f"GPU使用率が高いためCPUモードに切り替え: {metrics['gpu_utilization']}%")
                                    return True, metrics
                except FileNotFoundError:
                    pass
                
                return False, metrics
            else:
                # Linux/Mac環境
                metrics["check_method"] = "linux_nvidia_smi"
                # nvidia-smiでチェック（利用可能な場合）
                try:
                    result = subprocess.run(
                        ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        if lines:
                            parts = lines[0].split(',')
                            if len(parts) >= 2:
                                metrics["gpu_utilization"] = int(parts[0].strip())
                                metrics["vram_usage_mb"] = int(parts[1].strip())
                                # GPU使用率が50%以上なら使用中と判断
                                if metrics["gpu_utilization"] > 50:
                                    logger.info(f"GPU使用率が高いためCPUモードに切り替え: {metrics['gpu_utilization']}%")
                                    return True, metrics
                except FileNotFoundError:
                    metrics["check_method"] = "nvidia_smi_unavailable"
                    pass
                
                return False, metrics
        except Exception as e:
            logger.warning(f"GPU使用状況チェックエラー: {e}")
            metrics["error"] = str(e)
            # エラー時は安全のため、GPU使用中と判断
            return True, metrics
    
    def _check_model_available(self, model: str) -> Tuple[bool, Optional[str]]:
        """
        モデルが利用可能かチェック
        
        Returns:
            (is_available, error_detail): (True/False, エラー詳細)
        """
        try:
            response = requests.get(
                f"{self.ollama_url}/api/tags",
                timeout=2.0
            )
            if response.status_code == 200:
                models = [m.get("name", "") for m in response.json().get("models", [])]
                if model in models:
                    return True, None
                else:
                    return False, f"モデル '{model}' がインストールされていません"
            else:
                return False, f"Ollama APIエラー: HTTP {response.status_code}"
        except requests.exceptions.Timeout:
            return False, "Ollama APIタイムアウト（2秒）"
        except requests.exceptions.ConnectionError:
            return False, "Ollama API接続エラー"
        except Exception as e:
            logger.warning(f"モデルチェックエラー: {e}")
            return False, f"モデルチェックエラー: {str(e)}"
    
    def _call_model(
        self,
        model: str,
        prompt: str,
        task_type: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Ollama APIを呼び出す
        
        Args:
            model: モデル名
            prompt: プロンプト
            task_type: タスクタイプ
            max_tokens: 最大トークン数
            temperature: 温度パラメータ
        
        Returns:
            APIレスポンス
        
        Raises:
            ModelUnavailableError: モデルが利用できない場合（エラー詳細を含む）
        """
        # モデルが利用可能かチェック
        is_available, error_detail = self._check_model_available(model)
        if not is_available:
            error_msg = f"モデルが利用できません: {model}"
            if error_detail:
                error_msg += f" ({error_detail})"
            raise ModelUnavailableError(error_msg)
        
        # GPU使用状況をチェック
        gpu_in_use, gpu_metrics = self._check_gpu_in_use()
        
        # パラメータ設定
        params = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        # オプション設定
        options = {}
        
        # GPUが使用中の場合はCPUモードに切り替え
        if gpu_in_use:
            options["num_gpu"] = 0  # CPUのみで実行
            logger.info(f"GPU使用中を検出: {model}をCPUモードで実行")
        else:
            # GPUが利用可能な場合はGPUを明示的に使用
            # num_gpuを指定しないと、OllamaがCPUモードで実行される可能性がある
            # 大きな値（99）を指定することで、可能な限りGPUレイヤーを使用
            options["num_gpu"] = 99  # GPUを最大限使用
            logger.info(f"GPU利用可能: {model}をGPUモードで実行（num_gpu=99）")
        
        if max_tokens:
            options["num_predict"] = max_tokens
        if temperature is not None:
            options["temperature"] = temperature
        
        if options:
            params["options"] = options
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=params,
                timeout=300.0  # 5分タイムアウト
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_detail = f"HTTP {response.status_code}"
                try:
                    error_body = response.json()
                    if "error" in error_body:
                        error_detail += f": {error_body['error']}"
                except:
                    error_detail += f": {response.text[:200]}"
                raise ModelUnavailableError(f"APIエラー: {error_detail}")
        
        except requests.exceptions.Timeout as e:
            logger.error(f"API呼び出しタイムアウト: {e}")
            raise ModelUnavailableError(f"API呼び出しタイムアウト（300秒）")
        except requests.exceptions.RequestException as e:
            logger.error(f"API呼び出しエラー: {e}")
            raise ModelUnavailableError(f"API呼び出しエラー: {str(e)}")
    
    def _log_routing(
        self,
        task_type: str,
        model: str,
        source: str,
        request_id: str,
        latency_ms: int,
        input_summary: str,
        output_summary: str,
        memory_refs: List[str] = None,
        tools_used: List[str] = None,
        cpu_mode: bool = False,
        fallback_reason_code: Optional[str] = None,
        fallback_reason_detail: Optional[str] = None,
        trigger_metric: Optional[Dict[str, Any]] = None
    ):
        """
        ルーティングログを記録（「なぜそのモデルになったか」を記録）
        
        Args:
            task_type: タスクタイプ
            model: 使用したモデル
            source: "primary" or "fallback"
            request_id: リクエストID
            latency_ms: レイテンシ（ミリ秒）
            input_summary: 入力の要約
            output_summary: 出力の要約
            memory_refs: 参照したノートID
            tools_used: 使用したツール
        """
        if not self.audit_config.get("enabled", True):
            return
        
        audit_log = AuditLog(
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
            routed_model=model,
            task_type=task_type,
            memory_refs=memory_refs or [],
            tools_used=tools_used or [],
            input_summary=input_summary[:200],  # 最初の200文字
            output_summary=output_summary[:200],  # 最初の200文字
            cost=0.0,  # ローカルLLMの場合は0
            latency_ms=latency_ms,
            fallback_used=(source == "fallback"),
            fallback_reason_code=fallback_reason_code,
            fallback_reason_detail=fallback_reason_detail,
            trigger_metric=trigger_metric
        )
        
        self.audit_logs.append(audit_log)
        
        # ログに記録
        mode_str = "CPU" if cpu_mode else "GPU"
        logger.info(
            f"[LLM Routing] {task_type} -> {model} ({source}, {mode_str}) "
            f"| latency: {latency_ms}ms | fallback: {source == 'fallback'}"
        )
        
        # Obsidianに保存（実装予定）
        if self.audit_config.get("storage") == "obsidian":
            self._save_audit_log_to_obsidian(audit_log)
        else:
            self._save_audit_log_to_local(audit_log)
    
    def _save_audit_log_to_obsidian(self, audit_log: AuditLog):
        """監査ログをObsidianに保存（実装予定）"""
        # TODO: Obsidian統合を実装
        logger.debug(f"監査ログをObsidianに保存: {audit_log.request_id}")
    
    def _save_audit_log_to_local(self, audit_log: AuditLog):
        """監査ログをローカルに保存"""
        log_dir = Path(__file__).parent.parent / "logs" / "llm_routing"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        try:
            import json
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(audit_log), ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"監査ログの保存エラー: {e}")
    
    def route(
        self,
        task_type: str,
        prompt: str,
        memory_refs: Optional[List[str]] = None,
        tools_used: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        LLMをルーティング（fallback付き）
        
        Args:
            task_type: タスクタイプ（"conversation", "reasoning", "automation"）
            prompt: プロンプト
            memory_refs: 参照したノートID
            tools_used: 使用したツール
        
        Returns:
            LLMレスポンス
        
        Raises:
            AllModelsUnavailableError: すべてのモデルが利用できない場合
        """
        if task_type not in self.routing_config:
            raise ValueError(f"不明なタスクタイプ: {task_type}")
        
        config = self.routing_config[task_type]
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # GPU使用状況をチェック（一度だけ）
        gpu_in_use, gpu_metrics = self._check_gpu_in_use()
        
        # Primaryモデルを試す
        primary_error_detail = None
        try:
            result = self._call_model(
                model=config["primary"],
                prompt=prompt,
                task_type=task_type,
                max_tokens=config.get("max_tokens"),
                temperature=config.get("temperature")
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # ログに記録
            self._log_routing(
                task_type=task_type,
                model=config["primary"],
                source="primary",
                request_id=request_id,
                latency_ms=latency_ms,
                input_summary=prompt[:200],
                output_summary=result.get("response", "")[:200],
                memory_refs=memory_refs,
                tools_used=tools_used,
                cpu_mode=gpu_in_use,
                trigger_metric=gpu_metrics if gpu_in_use else None
            )
            
            return {
                "response": result.get("response", ""),
                "model": config["primary"],
                "source": "primary",
                "request_id": request_id,
                "latency_ms": latency_ms,
                "cpu_mode": gpu_in_use
            }
        
        except ModelUnavailableError as e:
            # Primary失敗の理由を記録
            primary_error_detail = str(e)
            
            # Fallback発動理由を特定
            fallback_reason_code = "MODEL_DOWN"
            fallback_reason_detail = primary_error_detail
            
            # エラーメッセージから詳細を抽出
            if "タイムアウト" in primary_error_detail or "timeout" in primary_error_detail.lower():
                fallback_reason_code = "TIMEOUT"
            elif "接続" in primary_error_detail or "connection" in primary_error_detail.lower():
                fallback_reason_code = "DB_UNAVAILABLE"  # Ollama接続エラー
            elif gpu_in_use and gpu_metrics.get("gpu_utilization", 0) > 80:
                fallback_reason_code = "GPU_OOM"
                fallback_reason_detail = f"GPU使用率が高い: {gpu_metrics.get('gpu_utilization')}%"
            elif gpu_in_use:
                fallback_reason_code = "GPU_BUSY"
                fallback_reason_detail = f"GPU使用中: {gpu_metrics}"
            
            # Fallbackモデルを試す
            for fallback_model in config.get("fallback", []):
                try:
                    result = self._call_model(
                        model=fallback_model,
                        prompt=prompt,
                        task_type=task_type,
                        max_tokens=config.get("max_tokens"),
                        temperature=config.get("temperature")
                    )
                    
                    latency_ms = int((time.time() - start_time) * 1000)
                    
                    # ログに記録（fallback発動理由を含む）
                    self._log_routing(
                        task_type=task_type,
                        model=fallback_model,
                        source="fallback",
                        request_id=request_id,
                        latency_ms=latency_ms,
                        input_summary=prompt[:200],
                        output_summary=result.get("response", "")[:200],
                        memory_refs=memory_refs,
                        tools_used=tools_used,
                        cpu_mode=gpu_in_use,
                        fallback_reason_code=fallback_reason_code,
                        fallback_reason_detail=fallback_reason_detail,
                        trigger_metric=gpu_metrics if gpu_in_use else None
                    )
                    
                    return {
                        "response": result.get("response", ""),
                        "model": fallback_model,
                        "source": "fallback",
                        "request_id": request_id,
                        "latency_ms": latency_ms,
                        "cpu_mode": gpu_in_use,
                        "fallback_reason": fallback_reason_code
                    }
                
                except ModelUnavailableError:
                    continue
            
            # すべてのモデルが利用できない
            raise AllModelsUnavailableError(
                f"すべてのモデルが利用できません: {task_type}"
            )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        user_id: str = "default",
        load_history: bool = True,
        auto_save: bool = True
    ) -> Dict[str, Any]:
        """
        OllamaのチャットAPIを使用して会話（記憶システムと自動連携）
        
        Args:
            messages: メッセージのリスト [{"role": "user", "content": "..."}]
            model: 使用するモデル名（Noneの場合はconversationタスクのprimaryモデル）
            user_id: ユーザーID（記憶システム用）
            load_history: 過去の会話履歴を読み込むか
            auto_save: 会話を自動保存するか
        
        Returns:
            チャットレスポンス
        """
        if model is None:
            # conversationタスクのprimaryモデルを使用
            model = self.routing_config.get("conversation", {}).get("primary", "qwen2.5:7b")
        
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # メッセージを準備
        context_messages = messages.copy()
        
        # システムプロンプト（人格設定）を追加
        if self.system_prompt:
            # 既にシステムメッセージがあるかチェック
            has_system = any(msg.get("role") == "system" for msg in context_messages)
            if not has_system:
                # システムメッセージを先頭に追加
                context_messages.insert(0, {
                    "role": "system",
                    "content": self.system_prompt
                })
                logger.debug("システムプロンプト（人格設定）を追加しました")
        
        # 過去の会話履歴を読み込む（オプション）
        if load_history and self._unified_memory:
            try:
                # 最新の会話履歴を検索
                history_results = self._unified_memory.recall(
                    query=messages[-1].get("content", "") if messages else "",
                    scope="week",
                    limit=5
                )
                
                # 過去の会話をコンテキストに追加
                if history_results:
                    history_context = []
                    for result in history_results:
                        content = result.get("content", "")
                        if content:
                            history_context.append({
                                "role": "system",
                                "content": f"[過去の会話] {content[:200]}"
                            })
                    
                    # システムメッセージとして追加
                    if history_context:
                        context_messages = history_context + context_messages
                        logger.info(f"過去の会話履歴を{len(history_context)}件読み込みました")
            except Exception as e:
                logger.warning(f"会話履歴の読み込みエラー: {e}")
        
        # OllamaのチャットAPIを呼び出す
        try:
            # GPU使用状況をチェック
            gpu_in_use, gpu_metrics = self._check_gpu_in_use()
            
            # リクエストパラメータ
            request_params = {
                "model": model,
                "messages": context_messages,
                "stream": False
            }
            
            # GPUが利用可能な場合はGPUを明示的に使用
            # num_gpuを指定しないと、OllamaがCPUモードで実行される可能性がある
            if not gpu_in_use:
                request_params["options"] = {
                    "num_gpu": 99  # GPUを最大限使用（可能な限りGPUレイヤーを使用）
                }
                logger.info(f"GPUモードで実行: {model} (num_gpu=99)")
            else:
                request_params["options"] = {
                    "num_gpu": 0  # CPUモード
                }
                logger.info(f"CPUモードで実行: {model} (GPU使用中)")
            
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=request_params,
                timeout=300.0
            )
            
            if response.status_code != 200:
                raise ModelUnavailableError(f"Ollama APIエラー: HTTP {response.status_code}")
            
            result = response.json()
            response_text = result.get("message", {}).get("content", "")
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 会話を自動保存（オプション）
            if auto_save and self._unified_memory:
                try:
                    # 会話全体を保存
                    conversation_text = "\n".join([
                        f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                        for msg in messages
                    ])
                    conversation_text += f"\nassistant: {response_text}"
                    
                    memory_id = self._unified_memory.store(
                        {
                            "content": conversation_text,
                            "metadata": {
                                "user_id": user_id,
                                "model": model,
                                "request_id": request_id,
                                "message_count": len(messages)
                            }
                        },
                        format_type="conversation"
                    )
                    logger.info(f"会話を記憶システムに保存しました: {memory_id}")
                except Exception as e:
                    logger.warning(f"会話の保存エラー: {e}")
            
            # ログに記録
            self._log_routing(
                task_type="conversation",
                model=model,
                source="primary",
                request_id=request_id,
                latency_ms=latency_ms,
                input_summary=messages[-1].get("content", "")[:200] if messages else "",
                output_summary=response_text[:200],
                memory_refs=[],
                tools_used=[]
            )
            
            return {
                "response": response_text,
                "model": model,
                "request_id": request_id,
                "latency_ms": latency_ms,
                "message": result.get("message", {})
            }
            
        except requests.exceptions.Timeout:
            raise ModelUnavailableError("Ollama API呼び出しタイムアウト（300秒）")
        except requests.exceptions.RequestException as e:
            raise ModelUnavailableError(f"Ollama API呼び出しエラー: {str(e)}")
    
    def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """監査ログを取得"""
        return [asdict(log) for log in self.audit_logs[-limit:]]


# 使用例
if __name__ == "__main__":
    router = LLMRouter()
    
    # 会話タスク
    try:
        result = router.route(
            task_type="conversation",
            prompt="こんにちは、今日はいい天気ですね。"
        )
        print(f"会話: {result['response'][:100]}...")
        print(f"モデル: {result['model']} ({result['source']})")
    except Exception as e:
        print(f"エラー: {e}")
    
    # 推論タスク
    try:
        result = router.route(
            task_type="reasoning",
            prompt="以下の問題を分析してください: プロジェクトの優先順位を決定する方法は？"
        )
        print(f"推論: {result['response'][:100]}...")
        print(f"モデル: {result['model']} ({result['source']})")
    except Exception as e:
        print(f"エラー: {e}")
    
    # 監査ログを表示
    print("\n監査ログ:")
    for log in router.get_audit_logs(limit=5):
        print(f"  {log['timestamp']} | {log['task_type']} -> {log['routed_model']} ({log['source']})")

