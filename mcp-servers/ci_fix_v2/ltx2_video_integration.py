#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LTX-2 動画生成統合（統一API用）

このリポジトリには `run_ltx2_generate.py` が既に存在するため、
統合クラスはそれを薄くラップする形で最小実装します。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from run_ltx2_generate import (
    check_comfyui,
    extract_output_paths,
    fix_workflow_paths,
    load_workflow,
    submit_workflow,
    validate_workflow_nodes,
    wait_for_completion,
)

import requests


@dataclass
class LTX2VideoIntegration:
    base_url: str | None = None

    def __post_init__(self) -> None:
        self.base_url = (self.base_url or os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")).rstrip("/")

    def is_available(self) -> bool:
        return check_comfyui(self.base_url)  # type: ignore

    def get_queue_status(self) -> Dict[str, Any]:
        try:
            r = requests.get(f"{self.base_url}/queue", timeout=5)
            r.raise_for_status()
            return r.json() or {}
        except Exception as e:
            return {"error": str(e)}

    def get_history(self, prompt_id: str) -> Dict[str, Any]:
        pid = (prompt_id or "").strip()
        if not pid:
            return {"error": "prompt_id is required"}
        try:
            r = requests.get(f"{self.base_url}/history/{pid}", timeout=10)
            if r.status_code == 404:
                return {"error": "not_found"}
            r.raise_for_status()
            return r.json() or {}
        except Exception as e:
            return {"error": str(e)}

    def create_ltx2_workflow(
        self,
        start_image_path: str | None = None,
        prompt: str = "",
        negative_prompt: str = "",
        video_length_seconds: int | None = None,
        width: int | None = None,
        height: int | None = None,
        use_two_pass: bool | None = None,
        use_nag: bool | None = None,
        use_res2s_sampler: bool | None = None,
        model_name: str | None = None,
        workflow_path: str | None = None,
    ) -> Dict[str, Any]:
        """互換API: 既存テスト向けにワークフローdictを返す。

        本プロジェクトでは Export(API) したJSONを使うのが確実なので、
        ここでは以下の順でロードする:
          1) workflow_path 指定
          2) ltx2_workflows/ltx2_i2v_ready.json
          3) ltx2_workflow_debug.json
        """

        base = Path(__file__).resolve().parent
        candidates = []
        if workflow_path:
            candidates.append(Path(workflow_path))
        candidates.append(base / "ltx2_workflows" / "ltx2_i2v_ready.json")
        candidates.append(base / "ltx2_workflow_debug.json")

        chosen = None
        for c in candidates:
            if c.is_file():
                chosen = c
                break
        if not chosen:
            return {}

        wf = load_workflow(str(chosen))
        fix_workflow_paths(wf)

        # best-effort patch
        if prompt:
            for node in wf.values():
                if isinstance(node, dict) and isinstance(node.get("inputs"), dict):
                    for k in ("prompt", "text", "positive", "positive_prompt"):
                        if k in node["inputs"] and isinstance(node["inputs"][k], str):
                            node["inputs"][k] = prompt

        if negative_prompt:
            for node in wf.values():
                if isinstance(node, dict) and isinstance(node.get("inputs"), dict):
                    for k in ("negative", "negative_prompt"):
                        if k in node["inputs"] and isinstance(node["inputs"][k], str):
                            node["inputs"][k] = negative_prompt

        if start_image_path:
            img_name = Path(start_image_path).name
            for node in wf.values():
                if isinstance(node, dict) and isinstance(node.get("inputs"), dict):
                    for k in ("image", "filename", "image_name"):
                        if k in node["inputs"] and isinstance(node["inputs"][k], str):
                            node["inputs"][k] = img_name

        # そのほかパラメータはワークフロー依存のため、ここでは触らない
        _ = (video_length_seconds, width, height, use_two_pass, use_nag, use_res2s_sampler, model_name)
        return wf

    def generate(
        self,
        prompt: str,
        workflow_path: str | None = None,
        image: str | None = None,
        timeout: float = 600.0,
    ) -> Dict[str, Any]:
        base = Path(__file__).resolve().parent
        workflow_path = workflow_path or str(base / "ltx2_workflow_debug.json")
        if not Path(workflow_path).is_file():
            # よく使う ready を優先
            fallback = base / "ltx2_workflows" / "ltx2_i2v_ready.json"
            if fallback.exists():
                workflow_path = str(fallback)
            else:
                return {"success": False, "error": f"workflow_not_found: {workflow_path}"}

        wf = load_workflow(workflow_path)
        fix_workflow_paths(wf)

        # prompt/image の上書きはワークフロー依存のため、ここでは“できる範囲”のみ
        if prompt:
            for node in wf.values():
                if isinstance(node, dict) and isinstance(node.get("inputs"), dict):
                    for k in ("prompt", "text", "positive", "positive_prompt"):
                        if k in node["inputs"] and isinstance(node["inputs"][k], str):
                            node["inputs"][k] = prompt
        if image:
            for node in wf.values():
                if isinstance(node, dict) and isinstance(node.get("inputs"), dict):
                    for k in ("image", "filename", "image_name"):
                        if k in node["inputs"] and isinstance(node["inputs"][k], str):
                            node["inputs"][k] = image

        # ノード検証（接続できない場合はスキップ）
        val = validate_workflow_nodes(self.base_url, wf)  # type: ignore
        if val is not None:
            ok, missing = val
            if not ok:
                return {"success": False, "error": "missing_nodes", "missing": missing}

        prompt_id = submit_workflow(self.base_url, wf, client_id="manaos_ltx2")  # type: ignore
        if not prompt_id:
            return {"success": False, "error": "submit_failed"}

        hist = wait_for_completion(self.base_url, prompt_id, timeout=timeout)  # type: ignore
        if not hist:
            return {"success": False, "error": "no_history", "prompt_id": prompt_id}

        outputs: List[Tuple[str, str]] = extract_output_paths(hist, prompt_id)
        return {"success": True, "prompt_id": prompt_id, "outputs": outputs, "history": hist.get(prompt_id)}
