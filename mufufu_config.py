#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ムフフモード画像生成の設定ファイル
身体崩れ対策を強化したバージョン
"""

# 身体崩れ対策を強化したネガティブプロンプト
MUFUFU_NEGATIVE_PROMPT = (
    # 身体崩れ対策（最優先・詳細化）
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
    "broken bones, distorted bones, "
    "bad neck, long neck, short neck, missing neck, "
    "bad waist, malformed waist, "
    "bad hips, malformed hips, "
    "bad shoulders, malformed shoulders, "
    "asymmetric body, unbalanced body, "
    # 品質問題
    "lowres, worst quality, low quality, normal quality, "
    "jpeg artifacts, signature, watermark, username, blurry, "
    "text, error, cropped, duplicate, ugly, deformed, "
    "poorly drawn, bad body, out of frame, extra limbs, "
    "disfigured, mutation, mutated, mutilated, bad art, bad structure"
)

# 身体の正確性を保証するポジティブタグ
ANATOMY_POSITIVE_TAGS = (
    "perfect anatomy, correct anatomy, accurate anatomy, "
    "proper proportions, well-proportioned body, "
    "correct hands, perfect hands, detailed hands, "
    "correct feet, perfect feet, detailed feet, "
    "natural joints, correct joints, "
    "symmetrical body, balanced body, "
    "realistic body structure, accurate body structure"
)

# 品質タグ
QUALITY_TAGS = (
    "masterpiece, best quality, ultra detailed, 8k, "
    "cinematic lighting, depth of field, soft skin, beautiful anatomy"
)

# 推奨モデル＋LoRA組み合わせ（オプション）。キーはモデル名の一部一致、値はLoRA名のリスト。
# 例: {"pony": ["Beautiful_Realistic_Asians.safetensors"], "flux": ["flux_dev.safetensors"]}
RECOMMENDED_MODEL_LORA_PAIRS = {}

# 身体崩れを減らすための推奨パラメータ
OPTIMIZED_PARAMS = {
    "steps": 50,  # 30以下だと身体崩れが増える
    "guidance_scale": 7.5,  # 7.0-8.0が最適
    "sampler": "dpmpp_2m",  # 身体崩れが少ないサンプラー
    "scheduler": "karras",  # 安定した生成
    "min_width": 1024,  # 512以下だと身体崩れが増える
    "min_height": 1024,  # 512以下だと身体崩れが増える
}

# プロンプトテンプレート
PROMPT_TEMPLATES = {
    "default": "{quality_tags}, {character_tags}, {situation}, {action}",
    "mufufu": "{anatomy_tags}, {quality_tags}, {character_tags}, {situation}, {action}, mischievous expression",
}

# プロンプト構築の推奨順序（品質・解剖→キャラ→状況→アクション→仕上げ）
PROMPT_ORDER = [
    "anatomy",
    "quality",
    "character",
    "outfit",
    "pose",
    "expression",
    "body",
    "scene",
    "lighting",
    "trailing_quality",
]


def build_ordered_prompt(sections: dict) -> str:
    """
    推奨順序でプロンプトを結合（品質・解剖→キャラ→状況→アクション→仕上げ）。

    Args:
        sections: PROMPT_ORDER のキーに対応する文字列またはリスト
                  例: {"quality": "masterpiece, 8k", "character": "1girl, Japanese woman"}

    Returns:
        カンマ区切りで結合したプロンプト
    """
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


def build_mufufu_prompt(
    character_tags: str, situation: str = "", action: str = "", include_anatomy_tags: bool = True
) -> str:
    """
    ムフフプロンプトを構築

    Args:
        character_tags: キャラクターのタグ
        situation: シチュエーション
        action: アクション
        include_anatomy_tags: 身体崩れ対策タグを含めるか

    Returns:
        構築されたプロンプト
    """
    parts = []

    # 身体崩れ対策タグを先頭に配置（重要）
    if include_anatomy_tags:
        parts.append(ANATOMY_POSITIVE_TAGS)

    # 品質タグ
    parts.append(QUALITY_TAGS)

    # キャラクタータグ
    parts.append(character_tags)

    # シチュエーション
    if situation:
        parts.append(situation)

    # アクション
    if action:
        parts.append(action)

    # ムフフ表現
    parts.append("mischievous expression, playful smile")

    return ", ".join(parts)


def get_default_negative_prompt_safe() -> str:
    """露骨表現を避けるためのネガティブプロンプト（未成年・性表現の誘発抑制）"""
    return (
        "child, loli, teen, underage, young, schoolgirl, "
        "nude, naked, nipples, areola, pussy, penis, testicles, sex, intercourse, blowjob, fellatio, anal"
    )


def get_optimized_params(**overrides) -> dict:
    """
    最適化されたパラメータを取得（オーバーライド可能）

    Args:
        **overrides: パラメータのオーバーライド

    Returns:
        最適化されたパラメータ
    """
    params = OPTIMIZED_PARAMS.copy()
    params.update(overrides)
    return params
