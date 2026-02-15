"""
🚀 常時起動LLM Pythonクライアント
簡単にLLMを呼び出せるクライアントライブラリ
"""

import requests
import hashlib
import json
import time
import logging
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

try:
    from _paths import OLLAMA_PORT, LM_STUDIO_PORT, UNIFIED_API_PORT
except Exception:
    OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))
    LM_STUDIO_PORT = int(os.getenv("LM_STUDIO_PORT", "1234"))
    UNIFIED_API_PORT = int(os.getenv("PORT", os.getenv("UNIFIED_API_PORT", "9502")))

try:
    from manaos_logger import get_logger
    _logger = get_service_logger("always-ready-llm-client")
except ImportError:
    _logger = logging.getLogger(__name__)


class ModelType(Enum):
    """モデルタイプ"""
    ULTRA_LIGHT = "lfm2.5:1.2b"              # LFM 2.5: 超軽量・超高速・日本語特化（1.2B）
    LIGHT = "qwen2.5-coder-7b-instruct"      # 軽量・高速（LM Studio）
    MEDIUM = "qwen2.5-coder-14b-instruct"    # バランス型・高品質（LM Studio 14B）
    HEAVY = "qwen2.5-coder-14b-instruct"     # 高品質生成（LM Studio 14B）
    REASONING = "qwen2.5-coder-14b-instruct" # 複雑な推論（LM Studio 14B）


class TaskType(Enum):
    """タスクタイプ"""
    CONVERSATION = "conversation"              # 会話
    LIGHTWEIGHT_CONVERSATION = "lightweight_conversation"  # 常駐軽量LLM（オフライン会話・下書き・整理）
    REASONING = "reasoning"                    # 推論
    AUTOMATION = "automation"                 # 自動処理
    GENERATION = "generation"                  # 生成


@dataclass
class LLMResponse:
    """LLMレスポンス"""
    response: str
    model: str
    cached: bool
    latency_ms: float
    tokens: Optional[int] = None
    source: str = "ollama"
    integration_results: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """初期化後の処理"""
        if self.integration_results is None:
            self.integration_results = {}


class AlwaysReadyLLMClient:
    """常時起動LLMクライアント"""
    
    def __init__(
        self,
        n8n_webhook_url: str = None,
        ollama_url: Optional[str] = None,
        lm_studio_url: Optional[str] = None,
        cache_api_url: Optional[str] = None,
        use_cache: bool = True,
        default_model: ModelType = ModelType.MEDIUM,  # デフォルトをMEDIUM（14B）に変更
        prefer_lm_studio: bool = True  # LM Studioを優先
    ):
        """
        初期化
        
        Args:
            n8n_webhook_url: n8n Webhook URL
            ollama_url: OllamaサーバーURL
            lm_studio_url: LM StudioサーバーURL（OpenAI互換API）
            cache_api_url: キャッシュAPI URL
            use_cache: キャッシュを使用するか
            default_model: デフォルトモデル
            prefer_lm_studio: LM Studioを優先するか
        """
        self.n8n_webhook_url = n8n_webhook_url
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")
        self.lm_studio_url = lm_studio_url or os.getenv(
            "LM_STUDIO_URL",
            f"http://127.0.0.1:{LM_STUDIO_PORT}/v1",
        )
        self.cache_api_url = cache_api_url or os.getenv(
            "CACHE_API_URL",
            f"http://127.0.0.1:{UNIFIED_API_PORT}/api/cache",
        )
        self.use_cache = use_cache
        self.default_model = default_model
        self.prefer_lm_studio = prefer_lm_studio
        self._lm_studio_available = None  # キャッシュ用
    
    def _generate_cache_key(self, message: str, model: str, task_type: str) -> str:
        """キャッシュキー生成"""
        key_string = f"{task_type}:{model}:{message}"
        return f"llm:{hashlib.sha256(key_string.encode()).hexdigest()}"
    
    def _get_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """キャッシュから取得"""
        if not self.use_cache:
            return None
        
        try:
            response = requests.get(
                f"{self.cache_api_url}/get",
                params={"key": cache_key},
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("found"):
                    return data.get("data")
        except Exception as e:
            _logger.debug("キャッシュ取得失敗: %s", e)
        
        return None
    
    def _set_cache(self, cache_key: str, value: Dict[str, Any], ttl_seconds: int = 86400):
        """キャッシュに保存"""
        if not self.use_cache:
            return
        
        try:
            requests.post(
                f"{self.cache_api_url}/set",
                json={
                    "key": cache_key,
                    "value": value,
                    "ttl_seconds": ttl_seconds
                },
                timeout=2
            )
        except Exception as e:
            _logger.debug("キャッシュ保存失敗: %s", e)
    
    def chat(
        self,
        message: str,
        model: Optional[ModelType] = None,
        task_type: TaskType = TaskType.CONVERSATION,
        use_cache: Optional[bool] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        LLMとチャット
        
        Args:
            message: メッセージ
            model: モデル（Noneの場合はデフォルト）
            task_type: タスクタイプ
            use_cache: キャッシュを使用するか（Noneの場合はインスタンス設定を使用）
            temperature: 温度パラメータ
            max_tokens: 最大トークン数
        
        Returns:
            LLMResponse
        """
        model_str = (model or self.default_model).value
        use_cache_flag = use_cache if use_cache is not None else self.use_cache
        
        # キャッシュキー生成
        cache_key = self._generate_cache_key(message, model_str, task_type.value)
        
        # キャッシュチェック
        if use_cache_flag:
            cached_data = self._get_cache(cache_key)
            if cached_data:
                return LLMResponse(
                    response=cached_data.get("response", ""),
                    model=cached_data.get("model", model_str),
                    cached=True,
                    latency_ms=0.0,
                    tokens=cached_data.get("tokens"),
                    source="cache"
                )
        
        # LLM呼び出し（優先順位: LM Studio > n8n > Ollama）
        start_time = time.time()
        
        # LM Studioを優先的に使用
        if self.prefer_lm_studio:
            try:
                return self._call_lm_studio(message, model_str, start_time, cache_key, use_cache_flag, temperature, max_tokens)
            except Exception as e:
                # LM Studioが使えない場合はフォールバック
                pass
        
        # n8n Webhook経由で呼び出し（設定されている場合のみ）
        if self.n8n_webhook_url:
            try:
                response = requests.post(
                    self.n8n_webhook_url,
                    json={
                        "message": message,
                        "model": model_str,
                        "task_type": task_type.value,
                        "use_cache": use_cache_flag
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    data = response.json()
                    latency_ms = (time.time() - start_time) * 1000
                    
                    result = LLMResponse(
                        response=data.get("response", ""),
                        model=data.get("model", model_str),
                        cached=data.get("cached", False),
                        latency_ms=latency_ms,
                        tokens=data.get("tokens"),
                        source=data.get("source", "n8n")
                    )
                    
                    # キャッシュに保存
                    if use_cache_flag and not result.cached:
                        self._set_cache(cache_key, {
                            "response": result.response,
                            "model": result.model,
                            "tokens": result.tokens
                        })
                    
                    return result
                else:
                    # n8n Webhookエラー時は直接Ollama呼び出しにフォールバック
                    return self._call_ollama_direct(message, model_str, start_time, cache_key, use_cache_flag)
            
            except requests.exceptions.RequestException:
                # n8nが使えない場合は直接Ollama呼び出し
                return self._call_ollama_direct(message, model_str, start_time, cache_key, use_cache_flag)
        else:
            # n8n Webhook URLが設定されていない場合は直接Ollama呼び出し
            return self._call_ollama_direct(message, model_str, start_time, cache_key, use_cache_flag)
    
    def _check_lm_studio_available(self) -> bool:
        """LM Studioが利用可能かチェック"""
        if self._lm_studio_available is not None:
            return self._lm_studio_available
        
        try:
            response = requests.get(f"{self.lm_studio_url}/models", timeout=2)
            self._lm_studio_available = response.status_code == 200
            return self._lm_studio_available
        except (requests.RequestException, OSError) as e:
            _logger.debug("LM Studio不可: %s", e)
            self._lm_studio_available = False
            return False
    
    def _call_lm_studio(
        self,
        message: str,
        model: str,
        start_time: float,
        cache_key: str,
        use_cache: bool,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """LM Studio呼び出し（OpenAI互換API）"""
        if not self._check_lm_studio_available():
            raise Exception("LM Studioが利用できません")
        
        try:
            # OpenAI互換APIを使用
            response = requests.post(
                f"{self.lm_studio_url}/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": message}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                latency_ms = (time.time() - start_time) * 1000
                
                # OpenAI互換形式からレスポンスを取得
                choices = data.get("choices", [])
                if choices and len(choices) > 0:
                    response_text = choices[0].get("message", {}).get("content", "")
                else:
                    response_text = ""
                
                result = LLMResponse(
                    response=response_text,
                    model=model,
                    cached=False,
                    latency_ms=latency_ms,
                    tokens=data.get("usage", {}).get("total_tokens"),
                    source="lm_studio"
                )
                
                # キャッシュに保存
                if use_cache:
                    self._set_cache(cache_key, {
                        "response": result.response,
                        "model": result.model,
                        "tokens": result.tokens
                    })
                
                return result
            else:
                raise Exception(f"LM Studioエラー: {response.status_code} - {response.text}")
        
        except Exception as e:
            raise Exception(f"LM Studio呼び出し失敗: {e}")
    
    def _call_ollama_direct(
        self,
        message: str,
        model: str,
        start_time: float,
        cache_key: str,
        use_cache: bool
    ) -> LLMResponse:
        """Ollama直接呼び出し（フォールバック）"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": message,
                    "stream": False,
                    "options": {
                        "temperature": 0.7
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                latency_ms = (time.time() - start_time) * 1000
                
                result = LLMResponse(
                    response=data.get("response", ""),
                    model=model,
                    cached=False,
                    latency_ms=latency_ms,
                    tokens=data.get("eval_count"),
                    source="ollama_direct"
                )
                
                # キャッシュに保存
                if use_cache:
                    self._set_cache(cache_key, {
                        "response": result.response,
                        "model": result.model,
                        "tokens": result.tokens
                    })
                
                return result
            else:
                raise Exception(f"Ollamaエラー: {response.status_code}")
        
        except Exception as e:
            raise Exception(f"LLM呼び出し失敗: {e}")
    
    def batch_chat(
        self,
        messages: List[str],
        model: Optional[ModelType] = None,
        task_type: TaskType = TaskType.CONVERSATION
    ) -> List[LLMResponse]:
        """
        バッチチャット（複数メッセージを順次処理）
        
        Args:
            messages: メッセージリスト
            model: モデル
            task_type: タスクタイプ
        
        Returns:
            LLMResponseリスト
        """
        results = []
        for message in messages:
            try:
                result = self.chat(message, model, task_type)
                results.append(result)
            except Exception as e:
                # エラー時は空レスポンスを追加
                results.append(LLMResponse(
                    response=f"エラー: {e}",
                    model=(model or self.default_model).value,
                    cached=False,
                    latency_ms=0.0,
                    source="error"
                ))
        
        return results
    
    def stream_chat(
        self,
        message: str,
        model: Optional[ModelType] = None,
        callback=None
    ) -> str:
        """
        ストリーミングチャット（リアルタイム生成）
        
        Args:
            message: メッセージ
            model: モデル
            callback: チャンク受信時のコールバック関数
        
        Returns:
            完全なレスポンス
        """
        model_str = (model or self.default_model).value
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model_str,
                    "prompt": message,
                    "stream": True
                },
                stream=True,
                timeout=120
            )
            
            full_response = ""
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    chunk = data.get("response", "")
                    full_response += chunk
                    
                    if callback:
                        callback(chunk)
            
            return full_response
        
        except Exception as e:
            raise Exception(f"ストリーミングエラー: {e}")


# 便利関数
def quick_chat(message: str, model: ModelType = ModelType.LIGHT) -> str:
    """
    クイックチャット（簡単に使える関数）
    
    Args:
        message: メッセージ
        model: モデル
    
    Returns:
        レスポンステキスト
    """
    client = AlwaysReadyLLMClient()
    response = client.chat(message, model)
    return response.response


# 使用例
if __name__ == "__main__":
    # クライアント初期化
    client = AlwaysReadyLLMClient()
    
    # 簡単なチャット
    print("=== 簡単なチャット ===")
    response = quick_chat("こんにちは！", ModelType.LIGHT)
    print(f"レスポンス: {response}")
    
    # 詳細なチャット
    print("\n=== 詳細なチャット ===")
    response = client.chat(
        "Pythonでクイックソートを実装してください",
        model=ModelType.MEDIUM,
        task_type=TaskType.AUTOMATION
    )
    print(f"レスポンス: {response.response}")
    print(f"モデル: {response.model}")
    print(f"キャッシュ: {response.cached}")
    print(f"レイテンシ: {response.latency_ms:.2f}ms")
    
    # バッチ処理
    print("\n=== バッチ処理 ===")
    messages = [
        "こんにちは",
        "今日の天気は？",
        "ありがとう"
    ]
    results = client.batch_chat(messages, ModelType.LIGHT)
    for i, result in enumerate(results):
        print(f"{i+1}. {result.response[:50]}...")
    
    # ストリーミング
    print("\n=== ストリーミング ===")
    def print_chunk(chunk):
        print(chunk, end="", flush=True)
    
    stream_response = client.stream_chat(
        "短い物語を書いてください",
        ModelType.MEDIUM,
        callback=print_chunk
    )
    print(f"\n\n完全なレスポンス: {len(stream_response)}文字")

