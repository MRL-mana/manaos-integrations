"""Minimal ComfyUI text-to-image client.

- Submits a simple SD 1.x-style workflow to ComfyUI's /prompt endpoint.
- Polls /history/{prompt_id} until outputs are available.
- Downloads generated images via /view.

Usage (PowerShell):
    .\\.venv\\Scripts\\python.exe .\\comfyui_generate_image.py --prompt "..." --negative "..." --width 512 --height 768

Notes:
- Requires ComfyUI running on http://127.0.0.1:8188
- Requires at least one checkpoint available in CheckpointLoaderSimple
"""

from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests


DEFAULT_BASE_URL = "http://127.0.0.1:8188"


@dataclass(frozen=True)
class ComfyResult:
    prompt_id: str
    files: Tuple[Path, ...]


def _get_checkpoint_choices(base_url: str, timeout_s: int = 10) -> list[str]:
    r = requests.get(f"{base_url}/object_info/CheckpointLoaderSimple", timeout=timeout_s)
    r.raise_for_status()
    data = r.json()
    ckpts = (
        data.get("CheckpointLoaderSimple", {})
        .get("input", {})
        .get("required", {})
        .get("ckpt_name", [[[]]])[0]
    )
    return list(ckpts)


def _build_txt2img_workflow(
    prompt: str,
    negative: str,
    ckpt_name: str,
    width: int,
    height: int,
    steps: int,
    cfg: float,
    sampler_name: str,
    scheduler: str,
    seed: int,
) -> Dict[str, Any]:
    # Node IDs are arbitrary strings, but must be consistent within the graph.
    # This workflow matches the canonical ComfyUI SD1.x txt2img pipeline.
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": ckpt_name},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler_name,
                "scheduler": scheduler,
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"images": ["6", 0], "filename_prefix": "manaos_txt2img"},
        },
    }


def _queue_prompt(base_url: str, workflow: Dict[str, Any], timeout_s: int = 30) -> str:
    payload = {"prompt": workflow}
    r = requests.post(f"{base_url}/prompt", json=payload, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()
    prompt_id = data.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"No prompt_id in response: {data}")
    return str(prompt_id)


def _poll_history_for_images(
    base_url: str,
    prompt_id: str,
    timeout_s: int = 300,
    poll_interval_s: float = 1.0,
) -> list[dict[str, Any]]:
    deadline = time.time() + timeout_s
    last_error: Optional[str] = None
    while time.time() < deadline:
        try:
            r = requests.get(f"{base_url}/history/{prompt_id}", timeout=10)
            r.raise_for_status()
            data = r.json()
            prompt_entry = data.get(prompt_id)
            if not prompt_entry:
                time.sleep(poll_interval_s)
                continue
            outputs = prompt_entry.get("outputs", {})
            images: list[dict[str, Any]] = []
            for _node_id, node_out in outputs.items():
                for img in node_out.get("images", []) or []:
                    images.append(img)
            if images:
                return images
        except Exception as e:
            last_error = str(e)
        time.sleep(poll_interval_s)

    raise TimeoutError(f"Timed out waiting for images (prompt_id={prompt_id}). Last error={last_error}")


def _download_image(
    base_url: str,
    img_desc: dict[str, Any],
    out_dir: Path,
    timeout_s: int = 60,
) -> Path:
    filename = img_desc.get("filename")
    subfolder = img_desc.get("subfolder", "")
    img_type = img_desc.get("type", "output")
    if not filename:
        raise RuntimeError(f"Missing filename in image descriptor: {img_desc}")

    params = {"filename": filename, "subfolder": subfolder, "type": img_type}
    r = requests.get(f"{base_url}/view", params=params, timeout=timeout_s)
    r.raise_for_status()

    out_dir.mkdir(parents=True, exist_ok=True)
    safe_sub = subfolder.replace("/", "_").replace("\\", "_") if subfolder else ""
    out_name = f"{Path(filename).stem}{('_' + safe_sub) if safe_sub else ''}{Path(filename).suffix}"
    out_path = out_dir / out_name
    out_path.write_bytes(r.content)
    return out_path


def generate_image(
    base_url: str,
    prompt: str,
    negative: str,
    ckpt_name: Optional[str],
    width: int,
    height: int,
    steps: int,
    cfg: float,
    sampler_name: str,
    scheduler: str,
    seed: Optional[int],
    out_dir: Path,
) -> ComfyResult:
    ckpts = _get_checkpoint_choices(base_url)
    if not ckpts:
        raise RuntimeError("No checkpoints found in ComfyUI (CheckpointLoaderSimple)")

    chosen_ckpt = ckpt_name or ckpts[0]
    if chosen_ckpt not in ckpts:
        raise ValueError(
            "Checkpoint not found. Available examples:\n"
            + "\n".join(ckpts[:20])
        )

    resolved_seed = int(seed if seed is not None else random.randint(1, 2**31 - 1))

    workflow = _build_txt2img_workflow(
        prompt=prompt,
        negative=negative,
        ckpt_name=chosen_ckpt,
        width=width,
        height=height,
        steps=steps,
        cfg=cfg,
        sampler_name=sampler_name,
        scheduler=scheduler,
        seed=resolved_seed,
    )

    prompt_id = _queue_prompt(base_url, workflow)
    images = _poll_history_for_images(base_url, prompt_id)

    files: list[Path] = []
    for img in images:
        files.append(_download_image(base_url, img, out_dir=out_dir))

    return ComfyResult(prompt_id=prompt_id, files=tuple(files))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--negative", default="low quality, blurry, deformed, bad anatomy, text, watermark")
    parser.add_argument("--ckpt", default=None)
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--cfg", type=float, default=7.0)
    parser.add_argument("--sampler", default="euler")
    parser.add_argument("--scheduler", default="normal")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out-dir", default=str(Path.cwd() / "output" / "comfyui"))
    args = parser.parse_args()

    result = generate_image(
        base_url=args.base_url,
        prompt=args.prompt,
        negative=args.negative,
        ckpt_name=args.ckpt,
        width=args.width,
        height=args.height,
        steps=args.steps,
        cfg=args.cfg,
        sampler_name=args.sampler,
        scheduler=args.scheduler,
        seed=args.seed,
        out_dir=Path(args.out_dir),
    )

    print(json.dumps({"prompt_id": result.prompt_id, "files": [str(p) for p in result.files]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
