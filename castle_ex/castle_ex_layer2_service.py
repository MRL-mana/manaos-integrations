"""
CASTLE-EX Layer2 スタイル矯正 LoRA 推論サービス
────────────────────────────────────────────────
モデルをシングルトンで保持し、mode に応じてLoRAを動的に
attach / detach する。呼び出し元は mode を指定するだけでよい。

使用例:
    from castle_ex.castle_ex_layer2_service import Layer2InferenceService
    svc = Layer2InferenceService.get_instance()
    result = svc.generate("洗車機の大きさは？", mode="short")
    print(result)   # → "洗車機の大きさは小さいです。"
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  デフォルトパス（環境変数で上書き可）
# --------------------------------------------------------------------------- #
import os

BASE_MODEL_PATH = os.environ.get(
    "CASTLE_EX_BASE_MODEL",
    r"D:\castle_ex_training\castle_ex_v1_1",
)
LORA_LAYER2_PATH = os.environ.get(
    "CASTLE_EX_LAYER2_LORA",
    r"D:\castle_ex_training\lora_castle_ex_layer2_prod",
)

# --------------------------------------------------------------------------- #
#  mode → LoRA 使用フラグ
# --------------------------------------------------------------------------- #
ADAPTER_MODES = {"short"}           # これだけ LoRA ON
FREE_MODES    = {"free", "training_eval", "eval"}  # LoRA OFF


# --------------------------------------------------------------------------- #
#  サービス本体
# --------------------------------------------------------------------------- #
class Layer2InferenceService:
    """
    シングルトン推論サービス。
    初回 generate 呼び出し時に遅延ロードを行う。
    """

    _instance: Optional["Layer2InferenceService"] = None
    _lock = threading.Lock()

    # -- シングルトン取得 --------------------------------------------------- #
    @classmethod
    def get_instance(cls) -> "Layer2InferenceService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -- 初期化 ------------------------------------------------------------- #
    def __init__(self) -> None:
        self._model = None
        self._tokenizer = None
        self._lora_active: bool = False
        self._init_lock = threading.Lock()
        self._model_lock = threading.Lock()

    # -- 遅延ロード ---------------------------------------------------------- #
    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        with self._init_lock:
            if self._model is not None:
                return
            self._load_base()

    def _load_base(self) -> None:
        """base model だけロード（LoRA なし）"""
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM

        logger.info("[layer2] Loading base model: %s", BASE_MODEL_PATH)
        tok = AutoTokenizer.from_pretrained(
            BASE_MODEL_PATH, trust_remote_code=True
        )
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_PATH,
            torch_dtype=torch.float16,
            device_map="cuda:0",
            trust_remote_code=True,
        )
        model.eval()
        self._tokenizer = tok
        self._model = model
        self._lora_active = False
        logger.info("[layer2] Base model loaded OK")

    # -- アダプタ操作 -------------------------------------------------------- #
    def _attach_lora(self) -> None:
        """Layer2 LoRA をアタッチ"""
        if self._lora_active:
            return
        from peft import PeftModel
        lora_path = Path(LORA_LAYER2_PATH)
        if not lora_path.exists():
            raise FileNotFoundError(f"LoRA not found: {lora_path}")
        logger.info("[layer2] Attaching LoRA: %s", lora_path)
        self._model = PeftModel.from_pretrained(self._model, str(lora_path))
        self._model.eval()
        self._lora_active = True
        logger.info("[layer2] LoRA attached")

    def _detach_lora(self) -> None:
        """Layer2 LoRA をデタッチ（base に戻す）"""
        if not self._lora_active:
            return
        logger.info("[layer2] Detaching LoRA (merging disabled, unloading)")
        # PeftModel.unload() で base に戻す
        self._model = self._model.unload()  # type: ignore[union-attr]
        self._model.eval()
        self._lora_active = False
        logger.info("[layer2] LoRA detached")

    # -- 生成 --------------------------------------------------------------- #
    def generate(
        self,
        prompt: str,
        *,
        mode: str = "short",
        max_new_tokens: int = 64,
        temperature: float = 0.2,
        repetition_penalty: float = 1.1,
        do_sample: bool = False,
        no_repeat_ngram_size: int = 3,
    ) -> str:
        """
        Parameters
        ----------
        prompt : str
            推論プロンプト（ユーザーの質問文など）
        mode : str
            "short"           → LoRA ON  (スタイル矯正)
            "free"            → LoRA OFF (自然会話)
            "training_eval"   → LoRA OFF (評価干渉防止)
        max_new_tokens : int
            生成トークン上限。デフォルト 64（短文安定）
        temperature : float
            低いほど安定。デフォルト 0.2。
        repetition_penalty : float
            繰り返し抑制。デフォルト 1.1。
        do_sample : bool
            False = greedy（最速・安定）
        """
        import torch

        self._ensure_loaded()

        use_lora = mode in ADAPTER_MODES

        with self._model_lock:
            # アダプタ状態を mode に合わせる
            if use_lora and not self._lora_active:
                self._attach_lora()
            elif not use_lora and self._lora_active:
                self._detach_lora()

            tok = self._tokenizer
            inputs = tok(prompt, return_tensors="pt").to(self._model.device)
            input_len = inputs["input_ids"].shape[1]

            gen_kwargs: dict = dict(
                **inputs,
                max_new_tokens=max_new_tokens,
                repetition_penalty=repetition_penalty,
                no_repeat_ngram_size=no_repeat_ngram_size,
                do_sample=do_sample,
                pad_token_id=tok.pad_token_id,
                eos_token_id=tok.eos_token_id,
            )
            if do_sample:
                gen_kwargs["temperature"] = temperature

            with torch.no_grad():
                out = self._model.generate(**gen_kwargs)

        # 入力部分を除いたトークンだけデコード
        generated_ids = out[0][input_len:]
        text = tok.decode(generated_ids, skip_special_tokens=True).strip()
        return text

    # -- ヘルスチェック用 ---------------------------------------------------- #
    def status(self) -> dict:
        return {
            "loaded": self._model is not None,
            "lora_active": self._lora_active,
            "base_model": BASE_MODEL_PATH,
            "lora_path": LORA_LAYER2_PATH,
        }
