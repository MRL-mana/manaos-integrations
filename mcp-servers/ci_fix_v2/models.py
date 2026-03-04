"""
API I/O 契約 — Pydantic スキーマ
=================================
ここが「動かない壁」。このスキーマが全サービスの境界を決める。

設計原則:
  - 既存 /api/comfyui/generate の入力パラメータを完全互換
  - 出力に quality_score, cost_estimate を追加（初期は null 許容）
  - job_id ベースの非同期モデル（生成は重い処理なので）
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────

class JobStatus(str, enum.Enum):
    """ジョブのライフサイクル"""
    queued = "queued"
    processing = "processing"
    scoring = "scoring"       # 品質評価中
    improving = "improving"   # 自動改善中（RLAnything）
    completed = "completed"
    failed = "failed"


class QualityMode(str, enum.Enum):
    """品質モード — 速度 vs 品質のトレードオフ"""
    fast = "fast"         # 少ステップ・スコアなし
    standard = "standard"  # 標準ステップ・スコア付き
    best = "best"         # 多ステップ・自動改善あり


class StylePreset(str, enum.Enum):
    """プリセットスタイル"""
    anime = "anime"
    photorealistic = "photorealistic"
    illustration = "illustration"
    watercolor = "watercolor"
    oil_painting = "oil_painting"
    cyberpunk = "cyberpunk"
    fantasy = "fantasy"
    minimalist = "minimalist"
    retro = "retro"
    abstract = "abstract"
    mufufu = "mufufu"   # 🔥
    lab = "lab"          # 闇の実験室


# ─── Request ──────────────────────────────────────────

class ImageGenerateRequest(BaseModel):
    """POST /api/v1/images/generate のリクエストボディ"""

    # 必須
    prompt: str = Field(..., min_length=1, max_length=2000,
                        description="生成プロンプト（英語推奨。日本語の場合は自動翻訳）")

    # オプション — 生成パラメータ
    negative_prompt: str = Field("", max_length=2000,
                                 description="除外プロンプト")
    width: int = Field(512, ge=256, le=2048, description="画像幅 (px)")
    height: int = Field(512, ge=256, le=2048, description="画像高さ (px)")
    steps: int = Field(20, ge=1, le=100, description="生成ステップ数")
    cfg_scale: float = Field(7.0, ge=1.0, le=30.0,
                             description="プロンプト追従度 (CFG)")
    sampler: str = Field("euler_ancestral", description="サンプラー名")
    scheduler: str = Field("karras", description="スケジューラー名")
    seed: int = Field(-1, description="シード値 (-1 = ランダム)")
    model: str = Field("", description="チェックポイント名 (空 = デフォルト)")
    loras: Optional[List[Dict[str, Any]]] = Field(
        None, description="LoRA設定 [{name, weight}]")

    # 高レベルオプション
    style: Optional[StylePreset] = Field(
        None, description="プリセットスタイル（指定するとパラメータ自動調整）")
    quality_mode: QualityMode = Field(
        QualityMode.standard, description="品質モード")
    batch_size: int = Field(1, ge=1, le=4,
                            description="同時生成枚数（ベスト選択用）")
    auto_improve: bool = Field(
        False, description="True: 品質スコア低の場合に自動リプロンプト")

    # 内部フラグ（既存互換）
    mufufu_mode: bool = Field(False, description="ムフフモード 🔥")
    lab_mode: bool = Field(False, description="闇の実験室モード")


# ─── Response ─────────────────────────────────────────

class QualityScore(BaseModel):
    """品質評価スコア（5指標）"""
    clip_score: Optional[float] = Field(
        None, ge=0, le=1, description="プロンプト一致度 (CLIP)")
    aesthetic_score: Optional[float] = Field(
        None, ge=0, le=10, description="美的品質スコア")
    technical_score: Optional[float] = Field(
        None, ge=0, le=10, description="技術品質（解像度/ノイズ/アーティファクト）")
    anatomy_score: Optional[float] = Field(
        None, ge=0, le=10, description="破綻検出（指・顔・身体構造）")
    commercial_score: Optional[float] = Field(
        None, ge=0, le=10, description="商用レベル判定")
    overall: Optional[float] = Field(
        None, ge=0, le=10, description="総合スコア（加重平均）")


class ImageGenerateResponse(BaseModel):
    """POST /api/v1/images/generate のレスポンス"""
    job_id: str = Field(default_factory=lambda: str(uuid4()),
                        description="ジョブID")
    status: JobStatus = Field(JobStatus.queued,
                              description="ジョブステータス")
    message: str = Field("", description="人間向けステータスメッセージ")

    # 生成パラメータ（入力のエコーバック）
    prompt: str = Field("", description="使用されたプロンプト")
    seed: int = Field(-1, description="使用されたシード")

    # ComfyUI連携
    comfyui_prompt_id: Optional[str] = Field(
        None, description="ComfyUI内部のprompt_id（既存互換）")

    # 結果（完了後に埋まる）
    image_url: Optional[str] = Field(
        None, description="生成画像のURL")
    thumbnail_url: Optional[str] = Field(
        None, description="サムネイルURL (256px)")
    quality_score: Optional[QualityScore] = Field(
        None, description="品質評価スコア（評価完了後）")

    # メタデータ
    generation_time_ms: Optional[int] = Field(
        None, description="生成時間 (ms)")
    cost_estimate_yen: Optional[float] = Field(
        None, description="推定コスト (円)")
    created_at: datetime = Field(
        default_factory=datetime.now, description="作成日時")


class JobStatusResponse(BaseModel):
    """GET /api/v1/images/{job_id} のレスポンス"""
    job_id: str
    status: JobStatus
    progress: Optional[float] = Field(
        None, ge=0, le=100, description="進捗率 (%)")
    result: Optional[ImageGenerateResponse] = Field(
        None, description="完了時の結果")


class ErrorResponse(BaseModel):
    """エラーレスポンス共通形式"""
    error: str = Field(..., description="エラーコード")
    message: str = Field(..., description="人間向けエラー詳細")
    detail: Optional[Dict[str, Any]] = Field(None)
