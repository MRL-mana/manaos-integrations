"""
ComfyUI Pipeline — 実際の画像生成ワークフロー実行
===================================================
デュアルモード:
  1. proxy   — 既存 Unified API (9502) 経由 (フォールバック)
  2. direct  — ComfyUI (8188) に直接ワークフロー投入 (推奨)

自動切替: ComfyUI に直接到達可能ならダイレクト、不可ならプロキシ。
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

from .models import ImageGenerateRequest

_log = logging.getLogger("manaos.image_pipeline")

_UNIFIED_API_BASE = os.getenv("MANAOS_UNIFIED_API_URL", "http://localhost:9502")
_COMFYUI_BASE = os.getenv("COMFYUI_URL", "http://localhost:8188")
_COMFYUI_OUTPUT_DIR = os.getenv(
    "COMFYUI_OUTPUT_DIR",
    str(Path.home() / "ComfyUI" / "output"),
)
_CLIENT_ID = "manaos-image-service"


def _comfyui_alive() -> bool:
    """ComfyUI 直通可能かチェック (50ms timeout)"""
    try:
        req = urllib.request.Request(f"{_COMFYUI_BASE}/system_stats", method="GET")
        with urllib.request.urlopen(req, timeout=0.5):
            return True
    except Exception:
        return False


class ComfyUIPipeline:
    """ComfyUI を使った画像生成パイプライン (デュアルモード)"""

    def __init__(self):
        self._direct_available: Optional[bool] = None

    def _check_mode(self) -> str:
        """接続モードを判定 (direct / proxy)"""
        if self._direct_available is None:
            self._direct_available = _comfyui_alive()
            _log.info("Pipeline mode: %s", "direct" if self._direct_available else "proxy")
        return "direct" if self._direct_available else "proxy"

    async def generate(self, req: ImageGenerateRequest) -> Optional[str]:
        """
        画像生成を実行し、ComfyUI の prompt_id を返す。
        direct が使えなければ proxy にフォールバック。
        """
        mode = self._check_mode()
        if mode == "direct":
            try:
                return await self._direct_comfyui(req)
            except Exception as e:
                _log.warning("Direct ComfyUI failed, falling back to proxy: %s", e)
                self._direct_available = False

        return await self._proxy_via_unified_api(req)

    # ─── Direct ComfyUI ──────────────────────────────

    async def _direct_comfyui(
        self, req: ImageGenerateRequest
    ) -> Optional[str]:
        """ComfyUI に直接ワークフロー JSON を投入"""

        # チェックポイント解決
        resolved_model = req.model or ""
        if not resolved_model:
            ckpts = self._list_checkpoints()
            resolved_model = ckpts[0] if ckpts else "v1-5-pruned-emaonly.safetensors"

        seed = req.seed if req.seed >= 0 else int(time.time() * 1000) % (2**32)

        # 標準 txt2img ワークフロー
        workflow = {
            "1": {
                "inputs": {"ckpt_name": resolved_model},
                "class_type": "CheckpointLoaderSimple",
            },
            "2": {
                "inputs": {"text": req.prompt, "clip": ["1", 1]},
                "class_type": "CLIPTextEncode",
            },
            "3": {
                "inputs": {"text": req.negative_prompt or "", "clip": ["1", 1]},
                "class_type": "CLIPTextEncode",
            },
            "4": {
                "inputs": {
                    "seed": seed,
                    "steps": req.steps,
                    "cfg": req.cfg_scale,
                    "sampler_name": req.sampler,
                    "scheduler": req.scheduler,
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
                    "width": req.width,
                    "height": req.height,
                    "batch_size": req.batch_size,
                },
                "class_type": "EmptyLatentImage",
            },
            "6": {
                "inputs": {"samples": ["4", 0], "vae": ["1", 2]},
                "class_type": "VAEDecode",
            },
            "7": {
                "inputs": {
                    "filename_prefix": f"manaos_{req.style.value if req.style else 'gen'}",
                    "images": ["6", 0],
                },
                "class_type": "SaveImage",
            },
        }

        # LoRA ノード挿入
        if req.loras:
            lora_node_id = 10
            prev_model = "1"
            prev_clip = "1"
            for lora in req.loras:
                workflow[str(lora_node_id)] = {
                    "inputs": {
                        "lora_name": lora.get("name", ""),
                        "strength_model": lora.get("weight", 1.0),
                        "strength_clip": lora.get("weight", 1.0),
                        "model": [prev_model, 0],
                        "clip": [prev_clip, 1],
                    },
                    "class_type": "LoraLoader",
                }
                prev_model = str(lora_node_id)
                prev_clip = str(lora_node_id)
                lora_node_id += 1

            # KSampler のモデル入力を最後の LoRA に結線
            workflow["4"]["inputs"]["model"] = [prev_model, 0]
            workflow["2"]["inputs"]["clip"] = [prev_clip, 1]
            workflow["3"]["inputs"]["clip"] = [prev_clip, 1]

        # 投入
        payload = json.dumps({
            "prompt": workflow,
            "client_id": _CLIENT_ID,
        }).encode("utf-8")

        http_req = urllib.request.Request(
            f"{_COMFYUI_BASE}/prompt",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(http_req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                prompt_id = body.get("prompt_id")
                if prompt_id:
                    _log.info("Direct ComfyUI generation started: %s", prompt_id)
                    return prompt_id
                raise RuntimeError(f"Unexpected ComfyUI response: {body}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Cannot reach ComfyUI at {_COMFYUI_BASE}: {e}") from e

    def _list_checkpoints(self) -> list[str]:
        """利用可能なチェックポイントを列挙"""
        try:
            url = f"{_COMFYUI_BASE}/object_info/CheckpointLoaderSimple"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ckpts = (
                    data.get("CheckpointLoaderSimple", {})
                    .get("input", {})
                    .get("required", {})
                    .get("ckpt_name", [[[]]])[0]
                )
                return list(ckpts) if ckpts else []
        except Exception:
            return []

    # ─── Proxy (Unified API 経由) ────────────────────

    async def _proxy_via_unified_api(
        self, req: ImageGenerateRequest
    ) -> Optional[str]:
        """既存の /api/comfyui/generate にリクエストをフォワード (フォールバック)"""
        url = f"{_UNIFIED_API_BASE}/api/comfyui/generate"

        payload = {
            "prompt": req.prompt,
            "negative_prompt": req.negative_prompt,
            "width": req.width,
            "height": req.height,
            "steps": req.steps,
            "cfg_scale": req.cfg_scale,
            "sampler": req.sampler,
            "scheduler": req.scheduler,
            "seed": req.seed,
            "model": req.model,
            "mufufu_mode": req.mufufu_mode,
            "lab_mode": req.lab_mode,
        }
        if req.loras:
            payload["loras"] = req.loras

        data = json.dumps(payload).encode("utf-8")
        http_req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(http_req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                prompt_id = body.get("prompt_id")
                if prompt_id:
                    _log.info("ComfyUI generation started: %s", prompt_id)
                    return prompt_id
                raise RuntimeError(f"Unexpected response: {body}")
        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Cannot reach Unified API at {url}: {e}"
            ) from e

    async def get_result_images(self, prompt_id: str) -> list[str]:
        """
        生成完了後の画像パスを取得。
        ComfyUI の history API → 出力ディレクトリのフルパスを返す。
        """
        url = f"{_COMFYUI_BASE}/history/{prompt_id}"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                history = json.loads(resp.read().decode("utf-8"))
                outputs = history.get(prompt_id, {}).get("outputs", {})
                images = []
                for node_output in outputs.values():
                    for img in node_output.get("images", []):
                        filename = img.get("filename", "")
                        subfolder = img.get("subfolder", "")
                        # フルパスを構築
                        output_dir = Path(_COMFYUI_OUTPUT_DIR)
                        if subfolder:
                            full_path = output_dir / subfolder / filename
                        else:
                            full_path = output_dir / filename
                        if full_path.exists():
                            images.append(str(full_path))
                        else:
                            # パスが見つからない場合は相対パスで返す
                            images.append(f"{subfolder}/{filename}" if subfolder else filename)
                return images
        except Exception as e:
            _log.warning("Failed to get result images for %s: %s", prompt_id, e)
            return []

    async def wait_for_completion(
        self, prompt_id: str, timeout: float = 120, poll_interval: float = 1.0,
    ) -> bool:
        """
        prompt_id の完了をポーリングで待機。

        Returns:
            True: 完了、 False: タイムアウト
        """
        import asyncio
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            try:
                url = f"{_COMFYUI_BASE}/history/{prompt_id}"
                with urllib.request.urlopen(url, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if prompt_id in data:
                        return True
            except Exception:
                pass
            await asyncio.sleep(poll_interval)
        return False
