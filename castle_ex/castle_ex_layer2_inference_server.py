"""
CASTLE-EX Layer2 推論サーバー (standalone, port 9520)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FastAPI で Layer2 LoRA を載せた推論エンドポイントを提供する。
GPU プロセスとして独立起動するため、他サービスに影響しない。

起動方法:
    py -3.10 castle_ex/castle_ex_layer2_inference_server.py
    # または
    powershell -File start_castle_ex_layer2.ps1

エンドポイント:
    POST /generate      -- メイン生成
    GET  /status        -- サービス状態
    GET  /health        -- ヘルスチェック (LB用)
"""
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

# ─── logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("castle_ex.layer2")

# ─── FastAPI ─────────────────────────────────────────────────────────────────
try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    import uvicorn
    from pydantic import BaseModel, Field
except ImportError:
    logger.error("fastapi / uvicorn が見つかりません。pip install fastapi uvicorn をお試しください。")
    sys.exit(1)

# ─── 推論サービス ─────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from castle_ex.castle_ex_layer2_service import Layer2InferenceService  # type: ignore
except ImportError:
    # 同ディレクトリからの直接起動にも対応
    from castle_ex_layer2_service import Layer2InferenceService  # type: ignore

# ─── 設定 ────────────────────────────────────────────────────────────────────
PORT = int(os.environ.get("LAYER2_SERVER_PORT", "9520"))
HOST = os.environ.get("LAYER2_SERVER_HOST", "127.0.0.1")
PRELOAD_MODEL = os.environ.get("LAYER2_PRELOAD", "0") == "1"  # デフォルトは遅延ロード

# ─── Pydantic モデル ──────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="推論プロンプト")
    mode: str = Field(
        default="short",
        description="'short' = LoRA ON (スタイル矯正) | 'free' = LoRA OFF | 'training_eval' = LoRA OFF",
    )
    max_new_tokens: int = Field(default=64, ge=1, le=256, description="生成上限トークン数 (max 256)")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    repetition_penalty: float = Field(default=1.1, ge=1.0, le=2.0)
    do_sample: bool = Field(default=False)


class GenerateResponse(BaseModel):
    text: str
    mode: str
    lora_active: bool
    latency_ms: float


# ─── FastAPI アプリ ───────────────────────────────────────────────────────────
app = FastAPI(
    title="CASTLE-EX Layer2 推論サーバー",
    description="Layer2 スタイル矯正 LoRA (v1.1.6 production) の推論エンドポイント",
    version="1.1.6",
)

_svc: Layer2InferenceService | None = None


def get_svc() -> Layer2InferenceService:
    global _svc
    if _svc is None:
        _svc = Layer2InferenceService.get_instance()
    return _svc


# ─── ルート ──────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    """ロードバランサー/ヘルスチェック用"""
    return {"status": "ok", "service": "castle_ex_layer2"}


@app.get("/status")
async def status():
    """サービス詳細状態"""
    svc = get_svc()
    return svc.status()


@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    """
    Layer2 LoRA を使った生成。

    - mode="short"         → LoRA ON  (短文・property答え強制)
    - mode="free"          → LoRA OFF (通常生成)
    - mode="training_eval" → LoRA OFF (評価干渉防止)
    """
    svc = get_svc()
    t0 = time.perf_counter()
    try:
        text = svc.generate(
            req.prompt,
            mode=req.mode,
            max_new_tokens=req.max_new_tokens,
            temperature=req.temperature,
            repetition_penalty=req.repetition_penalty,
            do_sample=req.do_sample,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("generate failed")
        raise HTTPException(status_code=500, detail=str(e))
    latency = (time.perf_counter() - t0) * 1000

    return GenerateResponse(
        text=text,
        mode=req.mode,
        lora_active=svc.status()["lora_active"],
        latency_ms=round(latency, 1),
    )


# ─── エントリポイント ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("CASTLE-EX Layer2 推論サーバー 起動中 port=%d", PORT)
    logger.info("=" * 60)

    if PRELOAD_MODEL:
        logger.info("[preload] モデルを事前ロード中...")
        get_svc()._ensure_loaded()
        logger.info("[preload] 完了")

    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
