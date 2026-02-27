#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS 画像生成 CLI（統合API /api/comfyui/generate を呼ぶ）

VS Code タスク「ManaOS: Generate Image」やターミナルから利用。
前提: 統合API (9502) 起動、ComfyUI (8188) 起動。
"""

import argparse
import os
import sys
import time
from pathlib import Path

# リポジトリルートをパスに追加
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from _paths import UNIFIED_API_PORT
except ImportError:
    UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9502"))

try:
    import requests
except ImportError:
    requests = None


def _resolve_comfyui_base_url() -> str:
    return (
        os.getenv("COMFYUI_URL")
        or f"http://127.0.0.1:{os.getenv('COMFYUI_PORT', '8188')}"
    ).rstrip("/")


def _direct_comfyui_generate(payload: dict) -> tuple[bool, str]:
    base_url = _resolve_comfyui_base_url()

    try:
        ckpt_resp = requests.get(
            f"{base_url}/object_info/CheckpointLoaderSimple",
            timeout=20,
        )
        ckpt_resp.raise_for_status()
        ckpt_data = ckpt_resp.json() or {}
        ckpts = (
            ckpt_data.get("CheckpointLoaderSimple", {})
            .get("input", {})
            .get("required", {})
            .get("ckpt_name", [[[]]])[0]
        )
        if not ckpts:
            return False, "ComfyUI checkpoint が見つかりません"
        ckpt_name = ckpts[0]

        seed = payload.get("seed", -1)
        if seed is None or int(seed) < 0:
            seed = int(time.time() * 1000) % (2**32)

        workflow = {
            "1": {
                "inputs": {"ckpt_name": ckpt_name},
                "class_type": "CheckpointLoaderSimple",
            },
            "2": {
                "inputs": {"text": payload["prompt"], "clip": ["1", 1]},
                "class_type": "CLIPTextEncode",
            },
            "3": {
                "inputs": {
                    "text": payload.get("negative_prompt") or "",
                    "clip": ["1", 1],
                },
                "class_type": "CLIPTextEncode",
            },
            "4": {
                "inputs": {
                    "seed": int(seed),
                    "steps": int(payload.get("steps", 20)),
                    "cfg": 7.0,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "karras",
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
                    "width": int(payload.get("width", 512)),
                    "height": int(payload.get("height", 512)),
                    "batch_size": 1,
                },
                "class_type": "EmptyLatentImage",
            },
            "6": {
                "inputs": {"samples": ["4", 0], "vae": ["1", 2]},
                "class_type": "VAEDecode",
            },
            "7": {
                "inputs": {"filename_prefix": "manaos_txt2img", "images": ["6", 0]},
                "class_type": "SaveImage",
            },
        }

        submit = requests.post(
            f"{base_url}/prompt",
            json={"prompt": workflow, "client_id": "manaos-generate-image-cli"},
            timeout=30,
        )
        submit.raise_for_status()
        prompt_id = (submit.json() or {}).get("prompt_id")
        if prompt_id:
            return True, f"prompt_id: {prompt_id}"
        return False, f"ComfyUI応答異常: {submit.text[:200]}"
    except Exception as e:
        return False, f"{e}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ComfyUIで画像生成（統合API経由）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python scripts/generate_image_cli.py "a beautiful sunset"
  python scripts/generate_image_cli.py --mufufu "1girl, sexy lingerie"
  python scripts/generate_image_cli.py --lab "1girl, nude"
  python scripts/generate_image_cli.py --jp "猫がベッドで寝ている"  # 日本語→英語変換後に画像生成
  python scripts/generate_image_cli.py --width 768 --height 512 "mountain landscape"
  python scripts/generate_image_cli.py   # 対話でプロンプト入力
        """,
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="画像生成プロンプト（省略時は対話入力）",
    )
    parser.add_argument("--api-url", default=None, help="統合APIのベースURL")
    parser.add_argument("--width", type=int, default=512, help="幅 (default: 512)")
    parser.add_argument("--height", type=int, default=512, help="高さ (default: 512)")
    parser.add_argument("--steps", type=int, default=20, help="ステップ数 (default: 20)")
    parser.add_argument("--negative", "-n", dest="negative_prompt", default="", help="ネガティブプロンプト")
    parser.add_argument("--seed", type=int, default=-1, help="シード (-1=ランダム)")
    parser.add_argument("--mufufu", action="store_true", help="ムフフモード（セクシー寄り・身体崩れ対策）")
    parser.add_argument("--lab", action="store_true", help="闇の実験室モード（ネガ最小限・表現はモデルに委ねる）")
    parser.add_argument("--jp", action="store_true", help="プロンプトを日本語として扱い、SD用英語に変換してから画像生成（Ollama要）")
    args = parser.parse_args()

    prompt = args.prompt
    if not prompt or not prompt.strip():
        try:
            prompt = input("プロンプトを入力してください: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("キャンセルしました。")
            return 1
        if not prompt:
            print("プロンプトが空です。")
            return 1

    api_url = (
        args.api_url
        or os.getenv("MANAOS_INTEGRATION_API_URL")
        or os.getenv("MANAOS_API_URL")
        or f"http://127.0.0.1:{UNIFIED_API_PORT}"
    ).rstrip("/")

    # 日本語→SD英語プロンプト変換（--jp 指定時）
    if args.jp:
        sd_prompt_url = f"{api_url}/api/sd-prompt/generate"
        try:
            r = requests.post(
                sd_prompt_url,
                json={"description": prompt, "with_negative": False},
                timeout=90,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("success") and data.get("prompt"):
                translated = data["prompt"]
                print(f"📝 プロンプト変換: 「{prompt[:40]}...」→ {translated[:60]}...")
                prompt = translated
            else:
                print(f"⚠️ プロンプト変換に失敗しました。元のプロンプトで続行します。{data.get('error', '')}")
        except Exception as e:
            print(f"⚠️ プロンプト変換エラー ({e})。元のプロンプトで続行します。")

    url = f"{api_url}/api/comfyui/generate"

    if not requests:
        print("エラー: requests をインストールしてください (pip install requests)")
        return 1

    payload = {
        "prompt": prompt,
        "width": args.width,
        "height": args.height,
        "steps": args.steps,
        "negative_prompt": args.negative_prompt or "",
        "seed": args.seed if args.seed >= 0 else -1,
        "mufufu_mode": args.mufufu,
        "lab_mode": args.lab,
    }

    mode_str = []
    if args.lab:
        mode_str.append("lab")
    if args.mufufu:
        mode_str.append("mufufu")
    mode_label = f" [{', '.join(mode_str)}]" if mode_str else ""

    print(f"API: {url}")
    print(f"プロンプト: {prompt[:80]}{'...' if len(prompt) > 80 else ''}{mode_label}")

    try:
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        prompt_id = data.get("prompt_id")
        status = data.get("status", "unknown")
        if prompt_id:
            print(f"✅ 画像生成を開始しました (prompt_id: {prompt_id}, status: {status})")
            print("   画像は ComfyUI の出力フォルダで確認できます。")
            return 0
        print(f"⚠️ 応答: {data}")
        return 0
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 統合APIに接続できません: {url} ({e})")
        print("   統合API (例: python unified_api_server.py) と ComfyUI (8188) が起動しているか確認してください。")
        print("↪ ComfyUI直接生成にフォールバックします...")
        ok, detail = _direct_comfyui_generate(payload)
        if ok:
            print(f"✅ ComfyUI直生成を開始しました ({detail})")
            return 0
        print(f"❌ フォールバック失敗: {detail}")
        return 1
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP エラー: {e}")
        if hasattr(e, "response") and e.response is not None and e.response.text:
            print(e.response.text[:500])
        body = ""
        try:
            body = e.response.text if e.response is not None else ""
        except Exception:
            body = ""

        if e.response is not None and e.response.status_code == 503 and (
            "comfyui" in body.lower() or "unavailable" in body.lower()
        ):
            print("↪ ComfyUI直接生成にフォールバックします...")
            ok, detail = _direct_comfyui_generate(payload)
            if ok:
                print(f"✅ ComfyUI直生成を開始しました ({detail})")
                return 0
            print(f"❌ フォールバック失敗: {detail}")
        return 1
    except Exception as e:
        print(f"❌ エラー: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
