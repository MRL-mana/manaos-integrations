"""
Prompt Enhancer — プロンプト自動強化
======================================
入力プロンプトを商用品質の出力に導くよう自動拡張する。

機能:
  1. 日本語→英語 自動翻訳 (Ollama 経由)
  2. スタイルプリセット注入
  3. ネガティブプロンプト自動補完
  4. 品質タグ自動追加
  5. LoRA 自動選択 (スタイルベース)
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from typing import Optional, Tuple

from .models import ImageGenerateRequest, StylePreset

_log = logging.getLogger("manaos.prompt_enhancer")

_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# ─── スタイルプリセット辞書 ─────────────────────────

_STYLE_PRESETS = {
    StylePreset.anime: {
        "suffix": ", anime style, cel shading, vibrant colors, detailed eyes",
        "negative_add": "realistic, photograph, 3d render",
        "recommended_steps": 25,
        "cfg_boost": 0.5,
    },
    StylePreset.photorealistic: {
        "suffix": ", photorealistic, 8k uhd, DSLR, soft lighting, high quality, film grain",
        "negative_add": "cartoon, painting, illustration, anime, drawing",
        "recommended_steps": 30,
        "cfg_boost": 0.0,
    },
    StylePreset.illustration: {
        "suffix": ", digital illustration, concept art, artstation trending, vivid",
        "negative_add": "photograph, realistic, 3d",
        "recommended_steps": 25,
        "cfg_boost": 0.0,
    },
    StylePreset.watercolor: {
        "suffix": ", watercolor painting, soft edges, artistic, traditional media",
        "negative_add": "digital, sharp, photograph, 3d render",
        "recommended_steps": 25,
        "cfg_boost": -0.5,
    },
    StylePreset.oil_painting: {
        "suffix": ", oil painting, masterpiece, museum quality, classical, brush strokes visible",
        "negative_add": "digital, photograph, flat, anime",
        "recommended_steps": 30,
        "cfg_boost": 0.0,
    },
    StylePreset.cyberpunk: {
        "suffix": ", cyberpunk, neon lights, dystopian, futuristic, rain, dark atmosphere",
        "negative_add": "nature, pastoral, bright, cheerful",
        "recommended_steps": 28,
        "cfg_boost": 0.5,
    },
    StylePreset.fantasy: {
        "suffix": ", fantasy art, magical, ethereal, epic, detailed environment",
        "negative_add": "modern, realistic, mundane",
        "recommended_steps": 28,
        "cfg_boost": 0.0,
    },
    StylePreset.minimalist: {
        "suffix": ", minimalist, clean, simple, white space, modern design",
        "negative_add": "cluttered, detailed, busy, complex",
        "recommended_steps": 20,
        "cfg_boost": -1.0,
    },
    StylePreset.retro: {
        "suffix": ", retro style, vintage, 1980s, synthwave, warm tones",
        "negative_add": "modern, digital, cold tones",
        "recommended_steps": 25,
        "cfg_boost": 0.0,
    },
    StylePreset.abstract: {
        "suffix": ", abstract art, geometric, non-representational, bold colors",
        "negative_add": "realistic, figurative, detailed face",
        "recommended_steps": 22,
        "cfg_boost": -0.5,
    },
    StylePreset.mufufu: {
        "suffix": ", detailed, high quality, beautiful, attractive, professional",
        "negative_add": "low quality, ugly, deformed, blurry, bad anatomy",
        "recommended_steps": 30,
        "cfg_boost": 1.0,
    },
    StylePreset.lab: {
        "suffix": ", experimental, avant-garde, surreal, cinematic",
        "negative_add": "boring, simple, flat",
        "recommended_steps": 35,
        "cfg_boost": 1.5,
    },
}

# ─── 共通品質ブースター ─────────────────────────────

_QUALITY_TAGS = (
    "masterpiece, best quality, highly detailed, "
    "sharp focus, professional"
)

_BASE_NEGATIVE = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, "
    "extra digit, fewer digits, cropped, worst quality, low quality, "
    "normal quality, jpeg artifacts, signature, watermark, username, blurry, "
    "deformed, mutated, disfigured"
)


def _is_japanese(text: str) -> bool:
    """テキストに日本語文字が含まれるか"""
    for ch in text:
        cp = ord(ch)
        if (0x3040 <= cp <= 0x309F or  # ひらがな
            0x30A0 <= cp <= 0x30FF or  # カタカナ
            0x4E00 <= cp <= 0x9FFF or  # 漢字
            0xFF66 <= cp <= 0xFF9F):   # 半角カナ
            return True
    return False


def _translate_via_ollama(text: str) -> Optional[str]:
    """Ollama を使って日本語→英語翻訳"""
    try:
        payload = json.dumps({
            "model": "gemma3:4b",
            "prompt": (
                f"Translate the following Japanese text to English for use as a "
                f"Stable Diffusion image generation prompt. "
                f"Output ONLY the English translation, nothing else.\n\n"
                f"Japanese: {text}\n\nEnglish:"
            ),
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 200},
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{_OLLAMA_URL}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            translated = body.get("response", "").strip()
            if translated:
                _log.info("Translated: '%s' → '%s'", text[:50], translated[:80])
                return translated
    except Exception as e:
        _log.warning("Translation failed (falling back to original): %s", e)
    return None


class PromptEnhancer:
    """プロンプト自動強化エンジン"""

    def __init__(self, enable_translation: bool = True):
        self._translate = enable_translation

    async def enhance(
        self, req: ImageGenerateRequest
    ) -> ImageGenerateRequest:
        """
        リクエストのプロンプトとパラメータを強化して返す。
        元のリクエストは変更しない (コピーして返す)。
        """
        # Pydantic v2 の model_copy
        enhanced = req.model_copy(deep=True)

        # 1) 日本語翻訳
        if self._translate and _is_japanese(enhanced.prompt):
            translated = _translate_via_ollama(enhanced.prompt)
            if translated:
                enhanced.prompt = translated

        # 2) スタイルプリセット適用
        if enhanced.style and enhanced.style in _STYLE_PRESETS:
            preset = _STYLE_PRESETS[enhanced.style]
            enhanced.prompt += preset["suffix"]

            # ネガティブプロンプト強化
            if preset.get("negative_add"):
                parts = [enhanced.negative_prompt] if enhanced.negative_prompt else []
                parts.append(preset["negative_add"])
                enhanced.negative_prompt = ", ".join(p for p in parts if p)

            # ステップ数推奨 (明示指定がなければ)
            if req.steps == 20:  # デフォルト値の場合のみ上書き
                enhanced.steps = preset.get("recommended_steps", req.steps)

            # CFG 微調整
            enhanced.cfg_scale = max(
                1.0,
                min(30.0, enhanced.cfg_scale + preset.get("cfg_boost", 0)),
            )

        # 3) 品質タグ追加 (fast モード以外)
        if enhanced.quality_mode.value != "fast":
            if _QUALITY_TAGS.split(",")[0].strip() not in enhanced.prompt.lower():
                enhanced.prompt = f"{_QUALITY_TAGS}, {enhanced.prompt}"

        # 4) ネガティブプロンプト自動補完
        if not enhanced.negative_prompt or len(enhanced.negative_prompt) < 20:
            enhanced.negative_prompt = _BASE_NEGATIVE
        elif "bad anatomy" not in enhanced.negative_prompt.lower():
            enhanced.negative_prompt = f"{enhanced.negative_prompt}, {_BASE_NEGATIVE}"

        # 5) best モードの場合のステップ数保証
        if enhanced.quality_mode.value == "best" and enhanced.steps < 30:
            enhanced.steps = max(enhanced.steps, 30)

        _log.info(
            "Prompt enhanced: style=%s, steps=%d→%d, prompt_len=%d→%d",
            enhanced.style,
            req.steps,
            enhanced.steps,
            len(req.prompt),
            len(enhanced.prompt),
        )

        return enhanced

    def estimate_enhanced_cost_multiplier(
        self, req: ImageGenerateRequest
    ) -> float:
        """強化後のコスト倍率を事前推定"""
        mult = 1.0
        if req.style and req.style in _STYLE_PRESETS:
            preset = _STYLE_PRESETS[req.style]
            step_ratio = preset.get("recommended_steps", 20) / 20
            mult *= step_ratio
        if req.quality_mode.value == "best":
            mult *= 1.5
        return round(mult, 2)
