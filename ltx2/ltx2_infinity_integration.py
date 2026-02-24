#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LTX-2 Infinity 統合

目的:
- 統一API/テストが期待する import を成立させる
- "Infinity" の入口として、LTX-2生成を複数回呼び出せる枠組みを提供

注意:
- 実際の“無限”品質（滑らかな継ぎ目等）はワークフロー設計に依存します。
  ここでは「セグメント生成を反復する」最小構成を実装します。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ltx2_storage_manager import LTX2StorageManager
from ltx2_template_manager import LTX2TemplateManager
from ltx2_workflow_generator import LTX2WorkflowGenerator
from ltx2_nsfw_config import LTX2NSFWConfig, LTX2NSFWWorkflowBuilder
from ltx2_video_integration import LTX2VideoIntegration


@dataclass
class LTX2InfinityIntegration:
    base_url: str | None = None
    storage: LTX2StorageManager | None = None
    templates: LTX2TemplateManager | None = None
    workflow_generator: LTX2WorkflowGenerator | None = None
    nsfw: LTX2NSFWConfig | None = None

    def __post_init__(self) -> None:
        self.base_url = (self.base_url or os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")).rstrip("/")
        self.storage = self.storage or LTX2StorageManager()
        self.templates = self.templates or LTX2TemplateManager()
        self.workflow_generator = self.workflow_generator or LTX2WorkflowGenerator()
        self.nsfw = self.nsfw or LTX2NSFWConfig()
        self._ltx2 = LTX2VideoIntegration(base_url=self.base_url)

    def is_available(self) -> bool:
        return self._ltx2.is_available()

    def list_templates(self) -> List[Dict[str, Any]]:
        return self.templates.list_templates() if self.templates else []

    def get_storage_stats(self) -> Dict[str, Any]:
        return self.storage.get_storage_stats() if self.storage else {"total_size_gb": 0.0}

    def generate(
        self,
        prompt: str,
        segments: int = 1,
        workflow_path: str | None = None,
        image: str | None = None,
        timeout_per_segment: float = 600.0,
        positive_suffix: str | None = None,
        negative_suffix: str | None = None,
    ) -> Dict[str, Any]:
        """セグメントを反復生成する（最小Infinity）。

        返り値:
          - success
          - segments: 各セグメントの結果（prompt_id, outputs 等）
        """

        if segments <= 0:
            return {"success": False, "error": "segments_must_be_positive"}

        wf_cfg = self.nsfw.get_workflow_config() if self.nsfw else {}
        prompt2 = prompt
        prompt2 = LTX2NSFWWorkflowBuilder.apply_prompt_suffix(prompt2, wf_cfg.get("positive_prompt_append", ""))
        prompt2 = LTX2NSFWWorkflowBuilder.apply_prompt_suffix(prompt2, positive_suffix or "")

        # negative は workflow に依存するため、ここでは “情報として返す” のみにする
        negative2 = ""
        negative2 = LTX2NSFWWorkflowBuilder.apply_prompt_suffix(negative2, wf_cfg.get("negative_prompt_append", ""))
        negative2 = LTX2NSFWWorkflowBuilder.apply_prompt_suffix(negative2, negative_suffix or "")

        results: List[Dict[str, Any]] = []
        last_image = image
        for i in range(segments):
            r = self._ltx2.generate(
                prompt=prompt2,
                workflow_path=workflow_path,
                image=last_image,
                timeout=timeout_per_segment,
            )
            r["segment_index"] = i
            results.append(r)
            # 次セグメントの初期画像へ“自動接続”はワークフロー設計次第なので、ここでは行わない

            if not r.get("success"):
                return {"success": False, "error": "segment_failed", "failed_segment": i, "segments": results, "negative_prompt": negative2}

        return {"success": True, "segments": results, "negative_prompt": negative2}
