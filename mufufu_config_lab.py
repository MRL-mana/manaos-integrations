#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
闇の実験室用ムフフ設定（mufufu_config_lab）

- ネガティブは「崩壊防止のみ」。露骨表現抑制用の safe タグは付けない。
- 通常世界（mufufu_config）と分離し、表現の上限を「モデル・LoRA」に委ねる。
"""

# 身体崩れ・品質のみ（露骨表現の抑制タグは一切入れない）。崩れ対策を優先してやや多めに指定。
LAB_NEGATIVE_PROMPT = (
    "bad anatomy, bad proportions, bad body structure, "
    "deformed body, malformed limbs, incorrect anatomy, "
    "wrong anatomy, broken anatomy, distorted anatomy, "
    "bad hands, missing fingers, extra fingers, fused fingers, "
    "too many fingers, fewer digits, missing digits, "
    "bad feet, malformed feet, extra feet, missing feet, "
    "bad arms, malformed arms, extra arms, missing arms, "
    "bad legs, malformed legs, extra legs, missing legs, "
    "wrong hands, wrong feet, wrong limbs, "
    "disconnected limbs, floating limbs, "
    "bad joints, malformed joints, impossible joints, "
    "deformed face, bad face, asymmetric eyes, "
    "lowres, worst quality, low quality, normal quality, "
    "jpeg artifacts, signature, watermark, username, blurry, "
    "text, error, cropped, duplicate, ugly, deformed, "
    "poorly drawn, bad body, out of frame, extra limbs, "
    "disfigured, mutation, mutated, mutilated, bad art, bad structure"
)

# 安全用ネガは追加しない（実験室では表現をモデルに委ねる）
def get_default_negative_prompt_safe() -> str:
    """実験室では追加しない（空文字）"""
    return ""


# 以下は mufufu_config と同じ（解剖・品質タグはそのまま使う）
try:
    from mufufu_config import (
        ANATOMY_POSITIVE_TAGS,
        QUALITY_TAGS,
        OPTIMIZED_PARAMS,
        RECOMMENDED_MODEL_LORA_PAIRS,
        build_ordered_prompt,
        build_mufufu_prompt,
        get_optimized_params,
        PROMPT_ORDER,
        PROMPT_TEMPLATES,
    )
except ImportError:
    ANATOMY_POSITIVE_TAGS = (
        "perfect anatomy, correct anatomy, accurate anatomy, "
        "proper proportions, well-proportioned body, "
        "correct hands, perfect hands, detailed hands, "
        "correct feet, perfect feet, detailed feet, "
        "natural joints, correct joints, "
        "symmetrical body, balanced body, "
        "realistic body structure, accurate body structure"
    )
    QUALITY_TAGS = (
        "masterpiece, best quality, ultra detailed, 8k, "
        "cinematic lighting, depth of field, soft skin, beautiful anatomy"
    )
    OPTIMIZED_PARAMS = {
        "steps": 50,
        "guidance_scale": 7.5,
        "sampler": "dpmpp_2m",
        "scheduler": "karras",
        "min_width": 1024,
        "min_height": 1024,
    }
    RECOMMENDED_MODEL_LORA_PAIRS = {}
    PROMPT_ORDER = ["anatomy", "quality", "character", "outfit", "pose", "expression", "body", "scene", "lighting", "trailing_quality"]
    PROMPT_TEMPLATES = {"default": "{quality_tags}, {character_tags}, {situation}, {action}", "mufufu": "{anatomy_tags}, {quality_tags}, {character_tags}, {situation}, {action}, mischievous expression"}

    def build_ordered_prompt(sections: dict) -> str:
        parts = []
        for key in PROMPT_ORDER:
            val = sections.get(key)
            if not val:
                continue
            if isinstance(val, (list, tuple)):
                val = ", ".join(str(v) for v in val)
            val = val.strip()
            if val:
                parts.append(val)
        return ", ".join(parts)

    def build_mufufu_prompt(character_tags: str, situation: str = "", action: str = "", include_anatomy_tags: bool = True) -> str:
        parts = []
        if include_anatomy_tags:
            parts.append(ANATOMY_POSITIVE_TAGS)
        parts.append(QUALITY_TAGS)
        parts.append(character_tags)
        if situation:
            parts.append(situation)
        if action:
            parts.append(action)
        parts.append("mischievous expression, playful smile")
        return ", ".join(parts)

    def get_optimized_params(**overrides) -> dict:
        params = OPTIMIZED_PARAMS.copy()
        params.update(overrides)
        return params
