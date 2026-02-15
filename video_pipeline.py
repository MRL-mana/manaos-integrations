"""
ManaOS 動画生成パイプライン
=========================
画像 + VOICEVOX音声 → MoviePy でプロモーション動画を自動生成

「ローカルAI三銃士」との連携:
  - 品質担当 (llama3-uncensored): ナレーション原稿の執筆
  - 速度担当 (dolphin-mistral:7b): タイトル・テロップ生成
  - 視覚担当 (llava): 画像解析→ALTテキスト・説明文生成

Usage:
    from video_pipeline import VideoPipeline
    pipeline = VideoPipeline()
    result = pipeline.create_promo_video(
        images=["img1.jpg", "img2.jpg"],
        narration_text="ナレーション原稿...",
        output_path="output/promo.mp4"
    )
"""

import os
import json
import time
import wave
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# 統一モジュール
try:
    from manaos_logger import get_logger

    logger = get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

error_handler = None
try:
    from manaos_error_handler import (
        ManaOSErrorHandler,
        ErrorCategory,
        ErrorSeverity,
    )

    error_handler = ManaOSErrorHandler("VideoPipeline")
except ImportError:
    pass

# MoviePy
try:
    from moviepy import (
        ImageClip,
        AudioFileClip,
        TextClip,
        CompositeVideoClip,
        concatenate_videoclips,
    )

    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logger.warning("MoviePy が見つかりません。`pip install moviepy` を実行してください")

# Pillow（画像処理）
try:
    from PIL import Image

    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger.warning("Pillow が見つかりません。`pip install Pillow` を実行してください")

# HTTP リクエスト（VOICEVOX / Ollama）
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# ========================================
# 設定
# ========================================

DEFAULT_CONFIG = {
    # Ollama
    "ollama_url": "http://127.0.0.1:11434",
    "models": {
        "quality": "dolphin-llama3:8b",  # 品質担当: ナレーション原稿
        "speed": "dolphin-mistral:7b",  # 速度担当: タイトル・テロップ
        "vision": "llava:latest",  # 視覚担当: 画像解析
    },
    # VOICEVOX
    "voicevox_url": "http://127.0.0.1:50021",
    "voicevox_speaker_id": 3,  # デフォルトスピーカー
    "voicevox_speed": 1.1,
    # 動画設定
    "video": {
        "width": 1920,
        "height": 1080,
        "fps": 24,
        "duration_per_image": 5.0,  # 1枚あたりの表示秒数
        "max_duration": 60.0,  # 最大動画長（秒）
        "transition_duration": 0.5,  # トランジション秒数
        "bg_color": (10, 10, 10),  # 背景色 (RGB)
    },
    # テロップ
    "subtitle": {
        "font_size": 36,
        "font_color": "white",
        "bg_opacity": 0.7,
        "position": ("center", "bottom"),
        "margin_bottom": 60,
    },
    # 出力
    "output_dir": "output/videos",
    "output_format": "mp4",
    "codec": "libx264",
    "audio_codec": "aac",
    "bitrate": "5000k",
}


# ========================================
# ローカルLLM連携
# ========================================


class LocalLLMClient:
    """Ollama API経由でローカルLLMにリクエスト"""

    def __init__(self, ollama_url: str = "http://127.0.0.1:11434"):
        self.ollama_url = ollama_url

    def generate(
        self,
        prompt: str,
        model: str,
        system: str = "",
        temperature: float = 0.8,
        max_tokens: int = 2048,
    ) -> str:
        """テキスト生成"""
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("requests ライブラリが必要です")

        payload = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate", json=payload, timeout=120
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            logger.error(f"LLM生成エラー [{model}]: {e}")
            raise

    def analyze_image(
        self,
        image_path: str,
        prompt: str = "この画像の内容を日本語で詳しく説明してください。",
        model: str = "llava:latest",
    ) -> str:
        """Llavaで画像を解析"""
        import base64

        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "model": model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 512},
        }

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate", json=payload, timeout=120
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            logger.error(f"画像解析エラー [{model}]: {e}")
            raise


# ========================================
# VOICEVOX 音声合成
# ========================================


class VoicevoxTTS:
    """VOICEVOX APIで音声合成"""

    def __init__(
        self,
        url: str = "http://127.0.0.1:50021",
        speaker_id: int = 3,
        speed: float = 1.1,
    ):
        self.url = url
        self.speaker_id = speaker_id
        self.speed = speed

    def is_available(self) -> bool:
        """VOICEVOXが起動しているか確認"""
        try:
            resp = requests.get(f"{self.url}/version", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def synthesize(
        self,
        text: str,
        speaker_id: Optional[int] = None,
        speed: Optional[float] = None,
    ) -> bytes:
        """テキストから音声WAVデータを生成"""
        sid = speaker_id or self.speaker_id
        spd = speed or self.speed

        # 1. 音声クエリ生成
        query_resp = requests.post(
            f"{self.url}/audio_query",
            params={"text": str(text), "speaker": str(sid)},
            timeout=30,
        )
        query_resp.raise_for_status()
        audio_query = query_resp.json()
        audio_query["speedScale"] = spd

        # 2. 音声合成
        synth_resp = requests.post(
            f"{self.url}/synthesis",
            params={"speaker": str(sid)},
            json=audio_query,
            timeout=60,
        )
        synth_resp.raise_for_status()
        return synth_resp.content

    def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        speaker_id: Optional[int] = None,
        speed: Optional[float] = None,
    ) -> str:
        """テキストからWAVファイルを生成し保存"""
        wav_data = self.synthesize(text, speaker_id, speed)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(wav_data)
        logger.info(f"音声ファイル保存: {output_path} ({len(wav_data)} bytes)")
        return output_path

    def get_speakers(self) -> List[Dict]:
        """利用可能なスピーカー一覧を取得"""
        try:
            resp = requests.get(f"{self.url}/speakers", timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"スピーカー一覧取得エラー: {e}")
            return []


# ========================================
# MoviePy 動画生成パイプライン
# ========================================


class VideoPipeline:
    """
    画像 + 音声 → プロモーション動画を自動生成するパイプライン

    フロー:
        1. (任意) LLMでナレーション原稿を生成
        2. (任意) LLMでタイトル/テロップを生成
        3. (任意) Llavaで画像を解析してALTテキスト生成
        4. VOICEVOXでナレーションを音声合成
        5. MoviePyで画像+音声+テロップを合成して動画出力
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.llm = LocalLLMClient(self.config["ollama_url"])
        self.tts = VoicevoxTTS(
            url=self.config["voicevox_url"],
            speaker_id=self.config["voicevox_speaker_id"],
            speed=self.config["voicevox_speed"],
        )
        self.output_dir = Path(self.config["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # --- LLM連携メソッド ---

    def generate_narration(
        self,
        topic: str,
        style: str = "エモーショナルで読者の興奮を誘うレビュー",
        max_tokens: int = 1024,
    ) -> str:
        """品質担当モデルでナレーション原稿を生成"""
        model = self.config["models"]["quality"]
        system_prompt = (
            f"あなたは優秀なコンテンツライターです。{style}を書いてください。"
            "日本語で、口語的で親しみやすいトーンで書いてください。"
            "60秒のナレーションに適した長さ（300-500文字）にしてください。"
        )
        prompt = f"以下のテーマでナレーション原稿を書いてください：\n\n{topic}"

        logger.info(f"ナレーション生成中... [model={model}]")
        return self.llm.generate(
            prompt=prompt,
            model=model,
            system=system_prompt,
            temperature=0.85,
            max_tokens=max_tokens,
        )

    def generate_title_and_subtitles(
        self,
        topic: str,
        narration: str = "",
        num_subtitles: int = 5,
    ) -> Dict[str, Any]:
        """速度担当モデルでタイトルとテロップを高速生成"""
        model = self.config["models"]["speed"]
        prompt = (
            f"テーマ: {topic}\n"
            f"ナレーション概要: {narration[:200] if narration else '（なし）'}\n\n"
            "以下のJSON形式で出力してください:\n"
            "{\n"
            '  "title": "キャッチーなタイトル",\n'
            f'  "subtitles": ["テロップ1", "テロップ2", ... (計{num_subtitles}個)],\n'
            '  "hashtags": ["#ハッシュタグ1", "#ハッシュタグ2", ...]\n'
            "}"
        )

        logger.info(f"タイトル・テロップ生成中... [model={model}]")
        raw = self.llm.generate(
            prompt=prompt,
            model=model,
            system="JSONのみを出力してください。説明不要。",
            temperature=0.9,
            max_tokens=512,
        )

        # JSONパース試行
        try:
            # JSON部分を抽出
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except (json.JSONDecodeError, ValueError):
            logger.warning("タイトルJSONパース失敗、フォールバック")

        return {
            "title": topic,
            "subtitles": [topic] * num_subtitles,
            "hashtags": [],
        }

    def analyze_images(self, image_paths: List[str]) -> List[Dict[str, str]]:
        """視覚担当モデルで画像を解析"""
        model = self.config["models"]["vision"]
        results = []

        for path in image_paths:
            if not os.path.exists(path):
                logger.warning(f"画像が見つかりません: {path}")
                results.append({"path": path, "description": "", "alt_text": ""})
                continue

            logger.info(f"画像解析中: {path} [model={model}]")
            try:
                description = self.llm.analyze_image(
                    image_path=path,
                    prompt="この画像の内容を日本語で客観的に説明してください。SEO向けのALTテキストとしても使える簡潔な説明を含めてください。",
                    model=model,
                )
                # ALTテキスト（最初の一文）
                alt_text = description.split("。")[0] + "。" if "。" in description else description[:80]
                results.append(
                    {
                        "path": path,
                        "description": description,
                        "alt_text": alt_text,
                    }
                )
            except Exception as e:
                logger.error(f"画像解析エラー {path}: {e}")
                results.append({"path": path, "description": "", "alt_text": ""})

        return results

    # --- 動画生成メソッド ---

    def _resize_image(self, image_path: str, width: int, height: int) -> str:
        """画像をリサイズしてアスペクト比を維持（黒帯追加）"""
        if not PILLOW_AVAILABLE:
            return image_path

        img = Image.open(image_path).convert("RGB")
        bg_color = self.config["video"]["bg_color"]

        # アスペクト比計算
        img_ratio = img.width / img.height
        target_ratio = width / height

        if img_ratio > target_ratio:
            new_w = width
            new_h = int(width / img_ratio)
        else:
            new_h = height
            new_w = int(height * img_ratio)

        resample = getattr(
            getattr(Image, "Resampling", Image),
            "LANCZOS",
            getattr(Image, "BICUBIC", 3),
        )
        img = img.resize((new_w, new_h), resample)

        # キャンバスに配置
        canvas = Image.new("RGB", (width, height), bg_color)
        x = (width - new_w) // 2
        y = (height - new_h) // 2
        canvas.paste(img, (x, y))

        # 一時ファイルに保存
        tmp_path = tempfile.mktemp(suffix=".png")
        canvas.save(tmp_path, "PNG")
        return tmp_path

    def _get_audio_duration(self, wav_path: str) -> float:
        """WAVファイルの長さ（秒）を取得"""
        with wave.open(wav_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)

    def create_promo_video(
        self,
        images: List[str],
        narration_text: Optional[str] = None,
        topic: Optional[str] = None,
        subtitles: Optional[List[str]] = None,
        output_path: Optional[str] = None,
        speaker_id: Optional[int] = None,
        with_llm: bool = True,
    ) -> Dict[str, Any]:
        """
        プロモーション動画を生成するメインメソッド

        Args:
            images: 使用する画像ファイルパスのリスト
            narration_text: ナレーション原稿（Noneの場合LLMで生成）
            topic: テーマ（LLM生成に使用）
            subtitles: テロップテキストのリスト（Noneの場合LLMで生成）
            output_path: 出力ファイルパス
            speaker_id: VOICEVOXのスピーカーID
            with_llm: LLM連携を使用するか

        Returns:
            生成結果の辞書
        """
        if not MOVIEPY_AVAILABLE:
            raise RuntimeError(
                "MoviePy が必要です。`pip install moviepy` を実行してください"
            )

        start_time = time.time()
        video_cfg = self.config["video"]
        w, h = video_cfg["width"], video_cfg["height"]
        result = {
            "success": False,
            "output_path": None,
            "narration": None,
            "title": None,
            "subtitles": None,
            "image_analyses": None,
            "duration": 0,
            "elapsed_time": 0,
        }

        try:
            # ステップ1: LLM連携（任意）
            title_data = {}
            if with_llm and topic:
                logger.info("=== ステップ1: LLM連携 ===")

                # ナレーション生成
                if not narration_text:
                    narration_text = self.generate_narration(topic)
                    logger.info(
                        f"ナレーション生成完了: {len(narration_text)}文字"
                    )
                result["narration"] = narration_text

                # タイトル・テロップ生成
                if not subtitles:
                    title_data = self.generate_title_and_subtitles(
                        topic, narration_text, num_subtitles=len(images)
                    )
                    subtitles = title_data.get("subtitles", [])
                    result["title"] = title_data.get("title", topic)

                # 画像解析
                result["image_analyses"] = self.analyze_images(images)

            result["subtitles"] = subtitles or []

            # ステップ2: 音声合成
            logger.info("=== ステップ2: VOICEVOX音声合成 ===")
            audio_path = None
            audio_duration = 0

            if narration_text and self.tts.is_available():
                audio_path = str(
                    self.output_dir / f"narration_{int(time.time())}.wav"
                )
                self.tts.synthesize_to_file(
                    narration_text, audio_path, speaker_id=speaker_id
                )
                audio_duration = self._get_audio_duration(audio_path)
                logger.info(f"音声合成完了: {audio_duration:.1f}秒")
            elif narration_text:
                logger.warning(
                    "VOICEVOX未起動のため音声合成スキップ。"
                    "各画像は固定秒数で表示します。"
                )

            # ステップ3: 動画生成
            logger.info("=== ステップ3: MoviePy動画合成 ===")

            # 画像のリサイズ
            resized_images = []
            for img_path in images:
                if os.path.exists(img_path):
                    resized = self._resize_image(img_path, w, h)
                    resized_images.append(resized)
                else:
                    logger.warning(f"画像スキップ（不在）: {img_path}")

            if not resized_images:
                raise ValueError("有効な画像がありません")

            # 各画像の表示時間を計算
            if audio_duration > 0:
                duration_per = min(
                    audio_duration / len(resized_images),
                    video_cfg["max_duration"] / len(resized_images),
                )
            else:
                duration_per = video_cfg["duration_per_image"]

            total_duration = duration_per * len(resized_images)
            total_duration = min(total_duration, video_cfg["max_duration"])

            # クリップ生成
            clips = []
            for i, img_path in enumerate(resized_images):
                clip = ImageClip(img_path, duration=duration_per)

                # テロップ追加
                if subtitles and i < len(subtitles) and subtitles[i]:
                    try:
                        sub_cfg = self.config["subtitle"]
                        txt_clip = TextClip(
                            text=subtitles[i],
                            font_size=sub_cfg["font_size"],
                            color=sub_cfg["font_color"],
                            size=(w - 100, None),
                            method="caption",
                        )
                        txt_clip = txt_clip.with_duration(duration_per)
                        txt_clip = txt_clip.with_position(
                            ("center", h - sub_cfg["margin_bottom"] - sub_cfg["font_size"])
                        )
                        clip = CompositeVideoClip([clip, txt_clip])
                    except Exception as e:
                        logger.warning(f"テロップ追加失敗: {e}")

                clips.append(clip)

            # 結合
            final_video = concatenate_videoclips(clips, method="compose")

            # 音声追加
            if audio_path and os.path.exists(audio_path):
                audio_clip = AudioFileClip(audio_path)
                # 音声が長い場合は動画に合わせてカット
                if audio_clip.duration > final_video.duration:
                    audio_clip = audio_clip.subclipped(0, final_video.duration)
                final_video = final_video.with_audio(audio_clip)

            # 出力パス決定
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = str(
                    self.output_dir / f"promo_{timestamp}.{self.config['output_format']}"
                )

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # レンダリング
            logger.info(f"動画レンダリング中... → {output_path}")
            final_video.write_videofile(
                output_path,
                fps=video_cfg["fps"],
                codec=self.config["codec"],
                audio_codec=self.config["audio_codec"],
                bitrate=self.config["bitrate"],
                logger=None,  # moviepyの進捗ログを抑制
            )

            # クリーンアップ
            final_video.close()
            for clip in clips:
                clip.close()

            # 一時ファイル削除
            for tmp in resized_images:
                if tmp not in images and os.path.exists(tmp):
                    try:
                        os.unlink(tmp)
                    except Exception:
                        pass

            elapsed = time.time() - start_time
            result.update(
                {
                    "success": True,
                    "output_path": output_path,
                    "duration": total_duration,
                    "elapsed_time": round(elapsed, 1),
                    "images_used": len(resized_images),
                    "has_audio": audio_path is not None,
                    "title": result.get("title") or title_data.get("title", ""),
                    "hashtags": title_data.get("hashtags", []),
                }
            )

            logger.info(
                f"✅ 動画生成完了! {output_path} "
                f"({total_duration:.1f}秒, {elapsed:.1f}秒で処理)"
            )
            return result

        except Exception as e:
            elapsed = time.time() - start_time
            result["elapsed_time"] = round(elapsed, 1)
            result["error"] = str(e)
            logger.error(f"動画生成エラー: {e}", exc_info=True)
            if error_handler:
                error_handler.handle_error(
                    error=e,
                    category=ErrorCategory.INTERNAL,
                    severity=ErrorSeverity.HIGH,
                    context={"operation": "create_promo_video", "topic": topic},
                )
            return result

    def create_simple_slideshow(
        self,
        images: List[str],
        audio_path: Optional[str] = None,
        output_path: Optional[str] = None,
        duration_per_image: float = 5.0,
    ) -> Dict[str, Any]:
        """
        シンプルなスライドショー動画を生成（LLM不使用）

        Args:
            images: 画像ファイルパスのリスト
            audio_path: BGM音声ファイルパス（任意）
            output_path: 出力ファイルパス
            duration_per_image: 1枚あたりの秒数
        """
        if not MOVIEPY_AVAILABLE:
            raise RuntimeError("MoviePy が必要です")

        video_cfg = self.config["video"]
        w, h = video_cfg["width"], video_cfg["height"]

        resized = [
            self._resize_image(img, w, h)
            for img in images
            if os.path.exists(img)
        ]
        if not resized:
            raise ValueError("有効な画像がありません")

        clips = [ImageClip(img, duration=duration_per_image) for img in resized]
        final = concatenate_videoclips(clips, method="compose")

        if audio_path and os.path.exists(audio_path):
            audio = AudioFileClip(audio_path)
            if audio.duration > final.duration:
                audio = audio.subclipped(0, final.duration)
            final = final.with_audio(audio)

        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(self.output_dir / f"slideshow_{timestamp}.mp4")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        final.write_videofile(
            output_path,
            fps=video_cfg["fps"],
            codec=self.config["codec"],
            audio_codec=self.config["audio_codec"],
            logger=None,
        )
        final.close()

        # 一時ファイル削除
        for tmp in resized:
            if tmp not in images:
                try:
                    os.unlink(tmp)
                except Exception:
                    pass

        return {
            "success": True,
            "output_path": output_path,
            "duration": duration_per_image * len(resized),
            "images_used": len(resized),
        }


# ========================================
# CLI / テスト用
# ========================================


def demo():
    """デモ: システム状態を確認して簡単な動画を生成"""
    print("=" * 60)
    print("ManaOS 動画パイプライン - システムチェック")
    print("=" * 60)

    # 依存関係チェック
    checks = {
        "MoviePy": MOVIEPY_AVAILABLE,
        "Pillow": PILLOW_AVAILABLE,
        "requests": REQUESTS_AVAILABLE,
    }

    for name, ok in checks.items():
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")

    # Ollamaチェック
    try:
        resp = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        print(f"  ✅ Ollama ({len(models)}モデル)")
        for m in models:
            marker = "🎯" if "dolphin" in m or "uncensored" in m or "llava" in m else "  "
            print(f"     {marker} {m}")
    except Exception:
        print("  ❌ Ollama (未起動)")

    # VOICEVOXチェック
    vox = VoicevoxTTS()
    if vox.is_available():
        speakers = vox.get_speakers()
        print(f"  ✅ VOICEVOX ({len(speakers)}スピーカー)")
    else:
        print("  ❌ VOICEVOX (未起動)")

    print()
    print("使用例:")
    print("  from video_pipeline import VideoPipeline")
    print('  pipeline = VideoPipeline()')
    print('  result = pipeline.create_promo_video(')
    print('      images=["img1.jpg", "img2.jpg"],')
    print('      topic="今日のおすすめコンテンツ"')
    print('  )')


if __name__ == "__main__":
    demo()
