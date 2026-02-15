#!/usr/bin/env python3
"""
⚡ LLM役割分担最適化システム
GPU効率化・フィルタ機能・動的モデル管理
"""

import os
import json
import httpx
import subprocess
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque
import platform

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("LLMOptimization")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

try:
    from ._paths import OLLAMA_PORT  # type: ignore
except Exception:  # pragma: no cover
    try:
        from _paths import OLLAMA_PORT  # type: ignore
    except Exception:  # pragma: no cover
        try:
            from manaos_integrations._paths import OLLAMA_PORT
        except Exception:  # pragma: no cover
            OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))


DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}").rstrip("/")

# 設定ファイル検証の初期化
config_validator = ConfigValidator("LLMOptimization")


class ModelRole(str, Enum):
    """モデル役割"""
    CONVERSATION = "conversation"  # 会話（軽量7B）
    REASONING = "reasoning"  # 判断（中型13B）
    GENERATION = "generation"  # 生成（クラウド/重量）
    FILTER = "filter"  # フィルタ（超軽量）


@dataclass
class ModelInfo:
    """モデル情報"""
    model_name: str
    role: ModelRole
    size_gb: float
    vram_required_gb: float
    loaded: bool = False
    last_used: Optional[str] = None
    usage_count: int = 0


@dataclass
class GPUStatus:
    """GPU状態"""
    utilization: float  # 0-100
    vram_used_gb: float
    vram_total_gb: float
    temperature: Optional[float]
    available: bool


class LLMOptimization:
    """LLM役割分担最適化システム"""
    
    def __init__(
        self,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        config_path: Optional[Path] = None
    ):
        """
        初期化
        
        Args:
            ollama_url: Ollama API URL
            config_path: 設定ファイルのパス
        """
        self.ollama_url = ollama_url
        self.config_path = config_path or Path(__file__).parent / "llm_optimization_config.json"
        self.config = self._load_config()
        
        # モデル管理
        self.models: Dict[str, ModelInfo] = {}
        self._init_models()
        
        # GPU状態監視
        self.gpu_status: Optional[GPUStatus] = None
        self.gpu_monitor_thread = None
        self.monitoring = False
        
        # フィルタモデル（超軽量）
        self.filter_model = self.config.get("filter_model", "llama3.2:1b")
        
        # モデルロード/アンロードのキュー
        self.model_queue = deque()
        self.model_lock = threading.Lock()
        
        logger.info(f"✅ LLM最適化システム初期化完了")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 設定ファイルの検証
                schema = {
                    "required": [],
                    "fields": {
                        "ollama_url": {"type": str, "default": DEFAULT_OLLAMA_URL},
                        "filter_model": {"type": str, "default": "llama3.2:1b"}
                    }
                }
                
                is_valid, errors = config_validator.validate_config(config, schema, self.config_path)
                if not is_valid:
                    logger.warning(f"設定ファイル検証エラー: {errors}")
                    # エラーがあってもデフォルト設定にマージして続行
                    default_config = self._get_default_config()
                    default_config.update(config)
                    return default_config
                
                return config
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"config_file": str(self.config_path)},
                    user_message="設定ファイルの読み込みに失敗しました"
                )
                logger.warning(f"設定読み込みエラー: {error.message}")
        
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定"""
        return {
            "ollama_url": DEFAULT_OLLAMA_URL,
            "filter_model": "llama3.2:1b",
            "role_models": {
                "conversation": {
                    "primary": "llama3.2:3b",
                    "fallback": "qwen2.5:7b",
                    "vram_gb": 4.0
                },
                "reasoning": {
                    "primary": "qwen2.5:14b",
                    "fallback": "llama3.1:8b",
                    "vram_gb": 8.0
                },
                "generation": {
                    "primary": "qwen2.5:32b",
                    "fallback": "qwen2.5:14b",
                    "vram_gb": 20.0
                },
                "filter": {
                    "primary": "llama3.2:1b",
                    "vram_gb": 2.0
                }
            },
            "gpu_efficiency": {
                "enable_dynamic_loading": True,
                "unload_idle_timeout_seconds": 300,
                "max_concurrent_models": 2,
                "vram_threshold_percent": 80
            },
            "filter": {
                "enabled": True,
                "threshold": 0.5
            }
        }
    
    def _init_models(self):
        """モデルを初期化"""
        role_models = self.config.get("role_models", {})
        
        for role_str, model_config in role_models.items():
            try:
                role = ModelRole(role_str)
                primary = model_config.get("primary", "")
                vram = model_config.get("vram_gb", 4.0)
                
                if primary:
                    self.models[primary] = ModelInfo(
                        model_name=primary,
                        role=role,
                        size_gb=vram * 0.5,  # 概算
                        vram_required_gb=vram,
                        loaded=False
                    )
            except (ValueError, KeyError) as e:
                logger.warning(f"モデル初期化エラー ({role_str}): {e}")
                continue
        
        logger.info(f"✅ モデル初期化完了: {len(self.models)}個")
    
    def start_gpu_monitoring(self):
        """GPU監視を開始"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.gpu_monitor_thread = threading.Thread(target=self._gpu_monitor_loop, daemon=True)
        self.gpu_monitor_thread.start()
        logger.info("✅ GPU監視開始")
    
    def stop_gpu_monitoring(self):
        """GPU監視を停止"""
        self.monitoring = False
        if self.gpu_monitor_thread:
            self.gpu_monitor_thread.join(timeout=5)
        logger.info("🛑 GPU監視停止")
    
    def _gpu_monitor_loop(self):
        """GPU監視ループ"""
        while self.monitoring:
            try:
                self.gpu_status = self._get_gpu_status()
                time.sleep(5)  # 5秒ごとに更新
            except Exception as e:
                logger.error(f"GPU監視エラー: {e}")
                time.sleep(10)
    
    def _get_gpu_status(self) -> GPUStatus:
        """GPU状態を取得（内部メソッド）"""
        try:
            if platform.system() == "Windows":
                # nvidia-smiでチェック
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                if result.returncode == 0:
                    parts = result.stdout.strip().split(',')
                    if len(parts) >= 4:
                        utilization = float(parts[0].strip())
                        vram_used = float(parts[1].strip()) / 1024  # MB to GB
                        vram_total = float(parts[2].strip()) / 1024
                        temperature = float(parts[3].strip()) if parts[3].strip() != 'N/A' else None
                        
                        return GPUStatus(
                            utilization=utilization,
                            vram_used_gb=vram_used,
                            vram_total_gb=vram_total,
                            temperature=temperature,
                            available=True
                        )
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug(f"GPU状態取得エラー: {e}")
        
        # GPUが利用できない場合
        return GPUStatus(
            utilization=0.0,
            vram_used_gb=0.0,
            vram_total_gb=0.0,
            temperature=None,
            available=False
        )
    
    def get_gpu_status(self) -> Optional[GPUStatus]:
        """
        GPU状態を取得（公開メソッド）
        
        Returns:
            GPU状態（利用できない場合はNone）
        """
        try:
            status = self._get_gpu_status()
            self.gpu_status = status
            return status
        except Exception as e:
            logger.warning(f"GPU状態取得エラー: {e}")
            return None
    
    def filter_request(self, prompt: str) -> Tuple[bool, float]:
        """
        リクエストをフィルタ（超軽量モデルで前処理）
        
        Args:
            prompt: プロンプト
        
        Returns:
            (should_process, confidence): 処理すべきか、信頼度
        """
        if not self.config.get("filter", {}).get("enabled", True):
            return True, 1.0
        
        try:
            filter_prompt = f"""以下のリクエストを評価してください。処理すべきかどうかを0.0-1.0で判定してください。

リクエスト: {prompt[:200]}

処理すべき: 1.0
処理不要: 0.0
不明: 0.5

数値のみ回答:"""
            
            response = httpx.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.filter_model,
                    "prompt": filter_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 10
                    }
                },
                timeout=timeout_config.get("api_call", 10.0)
            )
            
            if response.status_code == 200:
                result_text = response.json().get("response", "").strip()
                try:
                    confidence = float(result_text.split()[0])
                    confidence = max(0.0, min(1.0, confidence))
                    
                    threshold = self.config.get("filter", {}).get("threshold", 0.5)
                    should_process = confidence >= threshold
                    
                    return should_process, confidence
                except (ValueError, IndexError):
                    pass
        except Exception as e:
            logger.warning(f"フィルタ処理エラー: {e}")
        
        # エラー時は処理する
        return True, 0.5
    
    def select_model_for_role(self, role: ModelRole, prompt: str = "") -> Optional[str]:
        """
        役割に応じたモデルを選択（GPU効率化）
        
        Args:
            role: モデル役割
            prompt: プロンプト（オプション）
        
        Returns:
            選択されたモデル名
        """
        # GPU状態を確認
        if self.gpu_status and self.gpu_status.available:
            vram_available = self.gpu_status.vram_total_gb - self.gpu_status.vram_used_gb
            vram_threshold = self.gpu_status.vram_total_gb * (self.config.get("gpu_efficiency", {}).get("vram_threshold_percent", 80) / 100)
            
            # VRAMが不足している場合は軽量モデルを選択
            if vram_available < vram_threshold:
                logger.info(f"⚠️ VRAM不足のため軽量モデルを選択: {vram_available:.1f}GB < {vram_threshold:.1f}GB")
                role_config = self.config.get("role_models", {}).get(role.value, {})
                return role_config.get("fallback", role_config.get("primary", ""))
        
        # 通常の選択
        role_config = self.config.get("role_models", {}).get(role.value, {})
        return role_config.get("primary", "")
    
    def optimize_model_loading(self):
        """モデルロードを最適化"""
        if not self.config.get("gpu_efficiency", {}).get("enable_dynamic_loading", True):
            return
        
        if not self.gpu_status or not self.gpu_status.available:
            return
        
        # 使用されていないモデルをアンロード
        timeout_seconds = self.config.get("gpu_efficiency", {}).get("unload_idle_timeout_seconds", 300)
        current_time = datetime.now()
        
        with self.model_lock:
            for model_name, model_info in list(self.models.items()):
                if model_info.loaded and model_info.last_used:
                    last_used = datetime.fromisoformat(model_info.last_used)
                    idle_seconds = (current_time - last_used).total_seconds()
                    
                    if idle_seconds > timeout_seconds:
                        logger.info(f"🔄 アイドルモデルをアンロード: {model_name} ({idle_seconds:.0f}秒)")
                        self._unload_model(model_name)
    
    def _unload_model(self, model_name: str):
        """モデルをアンロード"""
        try:
            # Ollama APIでモデルをアンロード
            response = httpx.delete(
                f"{self.ollama_url}/api/generate",
                json={"model": model_name},
                timeout=10
            )
            
            if model_name in self.models:
                self.models[model_name].loaded = False
                logger.info(f"✅ モデルアンロード完了: {model_name}")
        except Exception as e:
            logger.warning(f"モデルアンロードエラー: {e}")
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """最適化統計を取得"""
        loaded_models = [m for m in self.models.values() if m.loaded]
        
        return {
            "total_models": len(self.models),
            "loaded_models": len(loaded_models),
            "gpu_status": asdict(self.gpu_status) if self.gpu_status else None,
            "models": {
                name: {
                    "role": info.role.value,
                    "loaded": info.loaded,
                    "usage_count": info.usage_count,
                    "last_used": info.last_used
                }
                for name, info in self.models.items()
            },
            "filter_enabled": self.config.get("filter", {}).get("enabled", True),
            "dynamic_loading_enabled": self.config.get("gpu_efficiency", {}).get("enable_dynamic_loading", True)
        }


# Flask APIサーバー
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# グローバルインスタンス
optimizer = None

def init_optimizer():
    """オプティマイザーを初期化"""
    global optimizer
    if optimizer is None:
        optimizer = LLMOptimization()
        optimizer.start_gpu_monitoring()
    return optimizer

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "LLM Optimization"})

@app.route('/api/filter', methods=['POST'])
def filter_endpoint():
    """フィルタエンドポイント"""
    data = request.get_json() or {}
    prompt = data.get("prompt", "")
    
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    
    optimizer = init_optimizer()
    should_process, confidence = optimizer.filter_request(prompt)
    
    return jsonify({
        "should_process": should_process,
        "confidence": confidence
    })

@app.route('/api/select-model', methods=['POST'])
def select_model_endpoint():
    """モデル選択エンドポイント"""
    data = request.get_json() or {}
    role_str = data.get("role", "conversation")
    prompt = data.get("prompt", "")
    
    try:
        role = ModelRole(role_str)
    except ValueError:
        return jsonify({"error": f"Invalid role: {role_str}"}), 400
    
    optimizer = init_optimizer()
    model_name = optimizer.select_model_for_role(role, prompt)
    
    if not model_name:
        return jsonify({"error": "No model available"}), 404
    
    return jsonify({
        "role": role.value,
        "model": model_name
    })

@app.route('/api/stats', methods=['GET'])
def get_stats_endpoint():
    """最適化統計エンドポイント"""
    optimizer = init_optimizer()
    stats = optimizer.get_optimization_stats()
    return jsonify(stats)

@app.route('/api/optimize', methods=['POST'])
def optimize_endpoint():
    """最適化実行エンドポイント"""
    optimizer = init_optimizer()
    optimizer.optimize_model_loading()
    return jsonify({"status": "optimized"})


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5110))
    logger.info(f"⚡ LLM最適化システム起動中... (ポート: {port})")
    init_optimizer()
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

