"""
Image Quality Scorer — 品質評価（5指標）実装済み
==================================================
PIL + NumPy ベースでリアルタイム画像品質評価を実行する。

5指標:
  1. clip_score      — プロンプト一致度 (キーワードマッチ + 色彩分析)
  2. aesthetic_score  — 美的品質 (彩度/コントラスト/構図バランス)
  3. technical_score  — 技術品質 (解像度/ノイズ/シャープネス)
  4. anatomy_score    — 破綻検出 (異常領域の統計的検出)
  5. commercial_score — 商用レベル判定 (総合 + サイズ + バランス)

設計方針:
  - 外部モデル不要 (PIL + NumPy だけで即動作)
  - 全メトリクスが 0-10 / 0-1 の数値を返す
  - RTX 5080 の ONNX/TensorRT は将来拡張で差し替え可
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Optional

import numpy as np

from .models import QualityScore

_log = logging.getLogger("manaos.image_scorer")


def _load_image(path: Path) -> Optional["np.ndarray"]:
    """画像を numpy array (H, W, C) で読み込み。失敗時 None。"""
    try:
        from PIL import Image

        img = Image.open(path).convert("RGB")
        return np.array(img, dtype=np.float32)
    except Exception as e:
        _log.warning("Failed to load image %s: %s", path, e)
        return None


class ImageScorer:
    """画像品質の総合評価器 — PIL + NumPy 実装"""

    def __init__(self):
        self._initialized = False

    async def score(
        self,
        image_path: Path,
        prompt: str,
    ) -> QualityScore:
        """
        画像を 5 指標で評価する。

        Args:
            image_path: 生成画像のファイルパス
            prompt: 生成に使用したプロンプト

        Returns:
            QualityScore: 5指標 + overall
        """
        if not self._initialized:
            await self._lazy_init()

        clip = await self._clip_score(image_path, prompt)
        aesthetic = await self._aesthetic_score(image_path)
        technical = await self._technical_score(image_path)
        anatomy = await self._anatomy_score(image_path)
        commercial = await self._commercial_score(
            clip, aesthetic, technical, anatomy
        )

        overall = self._weighted_average(
            clip=clip,
            aesthetic=aesthetic,
            technical=technical,
            anatomy=anatomy,
            commercial=commercial,
        )

        return QualityScore(
            clip_score=clip,
            aesthetic_score=aesthetic,
            technical_score=technical,
            anatomy_score=anatomy,
            commercial_score=commercial,
            overall=overall,
        )

    # ─── Individual Scorers ───────────────────────────

    async def _clip_score(
        self, image_path: Path, prompt: str
    ) -> Optional[float]:
        """
        プロンプト一致度 (0-1)
        簡易実装: プロンプトの色キーワードと画像の実際の色分布の一致度。
        将来: CLIP / MiniLM の image-text similarity に置き換え。
        """
        arr = _load_image(image_path)
        if arr is None:
            return None

        prompt_lower = prompt.lower()

        # 色キーワード → RGB 期待値
        color_keywords = {
            "red": (200, 50, 50), "blue": (50, 50, 200),
            "green": (50, 180, 50), "yellow": (220, 200, 50),
            "purple": (150, 50, 180), "orange": (230, 140, 30),
            "pink": (230, 100, 150), "white": (240, 240, 240),
            "black": (20, 20, 20), "dark": (40, 40, 40),
            "bright": (200, 200, 200), "colorful": (128, 128, 128),
        }

        matches = 0
        checks = 0
        mean_color = arr.mean(axis=(0, 1))  # (R, G, B)

        for kw, expected_rgb in color_keywords.items():
            if kw in prompt_lower:
                checks += 1
                # ユークリッド距離で一致度を計算
                dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(mean_color, expected_rgb)))
                similarity = max(0, 1 - dist / 441)  # 441 = sqrt(255^2 * 3)
                matches += similarity

        # プロンプト長による基本スコア (長い = より具体的 = やや高め)
        base = min(0.7, 0.3 + len(prompt.split()) * 0.02)

        if checks > 0:
            color_match = matches / checks
            return round(base * 0.6 + color_match * 0.4, 4)

        return round(base, 4)

    async def _aesthetic_score(
        self, image_path: Path
    ) -> Optional[float]:
        """
        美的品質 (0-10)
        彩度分布 + コントラスト + 構図バランス (三分割法) で評価。
        """
        arr = _load_image(image_path)
        if arr is None:
            return None

        # --- 彩度 (HSV の S チャネル) ---
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        mx = np.maximum(np.maximum(r, g), b)
        mn = np.minimum(np.minimum(r, g), b)
        chroma = mx - mn
        saturation = np.where(mx > 0, chroma / mx, 0)
        mean_sat = float(saturation.mean())
        # 適度な彩度 (0.2-0.6) が高スコア
        sat_score = 1.0 - abs(mean_sat - 0.4) * 2.5
        sat_score = max(0, min(1, sat_score))

        # --- コントラスト (輝度の標準偏差) ---
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        contrast = float(lum.std())
        # 適度なコントラスト (40-80) が理想的
        con_score = 1.0 - abs(contrast - 60) / 100
        con_score = max(0, min(1, con_score))

        # --- 構図バランス (三分割法: 上下左右の輝度バランス) ---
        h, w = lum.shape
        top_avg = float(lum[: h // 3].mean())
        bot_avg = float(lum[2 * h // 3 :].mean())
        left_avg = float(lum[:, : w // 3].mean())
        right_avg = float(lum[:, 2 * w // 3 :].mean())
        tb_balance = 1.0 - abs(top_avg - bot_avg) / 255
        lr_balance = 1.0 - abs(left_avg - right_avg) / 255
        balance_score = (tb_balance + lr_balance) / 2

        # 加重合成 → 0-10
        raw = sat_score * 0.35 + con_score * 0.35 + balance_score * 0.30
        return round(raw * 10, 2)

    async def _technical_score(
        self, image_path: Path
    ) -> Optional[float]:
        """
        技術品質 (0-10)
        解像度 + シャープネス (Laplacian 分散) + ノイズ推定 で評価。
        """
        arr = _load_image(image_path)
        if arr is None:
            return None

        h, w, _ = arr.shape

        # --- 解像度スコア ---
        megapixels = (h * w) / 1_000_000
        # 1MP で 7, 4MP で 10
        res_score = min(1.0, 0.5 + megapixels * 0.125)

        # --- シャープネス (Laplacian 近似: 3x3 カーネルの分散) ---
        gray = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
        # Laplacian のシンプルなカーネル適用
        lap = (
            gray[:-2, 1:-1] + gray[2:, 1:-1] +
            gray[1:-1, :-2] + gray[1:-1, 2:] -
            4 * gray[1:-1, 1:-1]
        )
        sharpness = float(lap.var())
        # 適度なシャープネス (100-2000) が理想
        # 低すぎ = ぼやけ、高すぎ = ジャギー/ノイズ
        if sharpness < 10:
            sharp_score = 0.2
        elif sharpness < 100:
            sharp_score = 0.2 + 0.6 * (sharpness - 10) / 90
        elif sharpness < 2000:
            sharp_score = 0.8 + 0.2 * min(1, (sharpness - 100) / 1900)
        else:
            sharp_score = max(0.3, 1.0 - (sharpness - 2000) / 10000)

        # --- ノイズ推定 (高周波成分の比率) ---
        # Laplacian の絶対値平均を輝度レンジで正規化
        noise_level = float(np.abs(lap).mean()) / max(float(gray.std()), 1)
        noise_score = max(0, min(1, 1.0 - noise_level / 5))

        raw = res_score * 0.3 + sharp_score * 0.4 + noise_score * 0.3
        return round(raw * 10, 2)

    async def _anatomy_score(
        self, image_path: Path
    ) -> Optional[float]:
        """
        破綻検出 (0-10)
        統計的アプローチ: 局所パッチの色分布異常 + 対称性分析。
        将来: OpenPose / MediaPipe で指・顔・体の構造破綻を検出。
        """
        arr = _load_image(image_path)
        if arr is None:
            return None

        h, w, _ = arr.shape

        # --- パッチベースの色異常検出 ---
        patch_h, patch_w = max(1, h // 8), max(1, w // 8)
        patch_means = []
        for i in range(0, h - patch_h + 1, patch_h):
            for j in range(0, w - patch_w + 1, patch_w):
                patch = arr[i : i + patch_h, j : j + patch_w]
                patch_means.append(patch.mean(axis=(0, 1)))

        if len(patch_means) < 4:
            return 7.0  # 小さすぎて判定不能 → やや高め

        patch_arr = np.array(patch_means)
        global_mean = patch_arr.mean(axis=0)
        distances = np.sqrt(((patch_arr - global_mean) ** 2).sum(axis=1))
        mean_dist = float(distances.mean())
        std_dist = float(distances.std())

        # 異常パッチ = 平均 + 2σ を超えるもの
        anomaly_threshold = mean_dist + 2 * std_dist
        anomaly_ratio = float((distances > anomaly_threshold).mean())

        # --- 左右対称性 (人物画で特に重要) ---
        left_half = arr[:, : w // 2]
        right_half = np.flip(arr[:, w // 2 : w // 2 * 2], axis=1)
        # サイズ合わせ
        min_w2 = min(left_half.shape[1], right_half.shape[1])
        if min_w2 > 0:
            sym_diff = float(
                np.abs(left_half[:, :min_w2] - right_half[:, :min_w2]).mean()
            )
            symmetry_score = max(0, 1 - sym_diff / 100)
        else:
            symmetry_score = 0.5

        # 異常が少ない + 適度な対称性 = 高スコア
        anomaly_score = max(0, 1 - anomaly_ratio * 10)
        raw = anomaly_score * 0.6 + symmetry_score * 0.4
        return round(raw * 10, 2)

    async def _commercial_score(
        self,
        clip: Optional[float],
        aesthetic: Optional[float],
        technical: Optional[float],
        anatomy: Optional[float],
    ) -> Optional[float]:
        """
        商用レベル判定 (0-10)
        上位4指標の加重合成 + 最低基準チェック。
        """
        scores = {
            "clip": clip,
            "aesthetic": aesthetic,
            "technical": technical,
            "anatomy": anatomy,
        }
        valid = {k: v for k, v in scores.items() if v is not None}
        if not valid:
            return None

        # clip は 0-1 → 0-10 に変換
        normalized = {}
        for k, v in valid.items():
            normalized[k] = v * 10 if k == "clip" else v

        # 商用基準: 全指標が 5.0 以上であることがベースライン
        below_threshold = sum(1 for v in normalized.values() if v < 5.0)
        penalty = below_threshold * 1.5

        avg = sum(normalized.values()) / len(normalized)
        # 最低スコアの影響を加味 (弱点がある = 商用リスク)
        min_score = min(normalized.values())
        raw = avg * 0.6 + min_score * 0.4 - penalty

        return round(max(0, min(10, raw)), 2)

    # ─── Utilities ────────────────────────────────────

    @staticmethod
    def _weighted_average(**scores) -> Optional[float]:
        """非 None のスコアで加重平均を計算"""
        weights = {
            "clip": 2.0,
            "aesthetic": 3.0,
            "technical": 2.0,
            "anatomy": 2.0,
            "commercial": 1.0,
        }
        total_weight = 0.0
        total_score = 0.0
        for key, value in scores.items():
            if value is not None:
                w = weights.get(key, 1.0)
                # clip は 0-1 スケールなので 10 倍
                v = value * 10 if key == "clip" else value
                total_score += v * w
                total_weight += w
        if total_weight == 0:
            return None
        return round(total_score / total_weight, 2)

    async def _lazy_init(self):
        """初期化 (将来: ONNX モデルの読み込み)"""
        _log.info("ImageScorer: initialized (PIL + NumPy scorer v1)")
        self._initialized = True
