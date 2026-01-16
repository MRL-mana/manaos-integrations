"""
OCR マルチプロバイダー統合
複数のOCRプロバイダーに対応
"""

import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
import statistics
import re
import numpy as np
from bisect import bisect_right

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiProviderOCR:
    """複数OCRプロバイダー対応クラス"""
    
    def __init__(self):
        """初期化"""
        self.providers = {
            "tesseract": False,
            "google": False,
            "microsoft": False,
            "amazon": False,
            "easyocr": False,
            "paddleocr": False
        }
        self.ocr_scripts_path = Path("repos/OCR_Python-Scripts")
        self._check_providers()
    
    def _check_providers(self):
        """利用可能なプロバイダーを確認"""
        # Tesseract
        try:
            import pytesseract
            from pathlib import Path
            
            # Tesseractのパスを自動検出
            tesseract_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]
            
            tesseract_found = False
            for tesseract_path in tesseract_paths:
                if Path(tesseract_path).exists():
                    pytesseract.pytesseract.tesseract_cmd = tesseract_path
                    tesseract_found = True
                    logger.info(f"Tesseract OCRが見つかりました: {tesseract_path}")
                    break
            
            # PATHからも検索を試みる
            if not tesseract_found:
                try:
                    import shutil
                    tesseract_cmd = shutil.which("tesseract")
                    if tesseract_cmd:
                        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
                        tesseract_found = True
                        logger.info(f"Tesseract OCRがPATHから見つかりました: {tesseract_cmd}")
                except:
                    pass
            
            if tesseract_found:
                self.providers["tesseract"] = True
                logger.info("Tesseract OCRが利用可能です")
            else:
                logger.warning("Tesseract OCRが見つかりません。PATHに追加するか、pytesseract.pytesseract.tesseract_cmdを設定してください")
        except ImportError:
            logger.debug("pytesseractがインストールされていません")
        
        # Google Cloud Vision
        try:
            from google.cloud import vision
            self.providers["google"] = True
            logger.info("Google Cloud Vision APIが利用可能です")
        except ImportError:
            logger.debug("Google Cloud Vision APIが利用できません")
        
        # Microsoft Azure
        try:
            from azure.cognitiveservices.vision.computervision import ComputerVisionClient
            self.providers["microsoft"] = True
            logger.info("Microsoft Azure Computer Visionが利用可能です")
        except ImportError:
            logger.debug("Microsoft Azure Computer Visionが利用できません")
        
        # Amazon Textract
        try:
            import boto3
            # boto3 があっても、認証情報が無いと実行時に毎回失敗して遅くなるため
            # ここで「設定済みか」を確認して、未設定なら利用不可扱いにする（ローカル運用向け）
            try:
                sess = boto3.Session()
                creds = sess.get_credentials()
                if creds is None:
                    self.providers["amazon"] = False
                    logger.info("Amazon Textractは未設定（AWS認証情報なし）のため無効化しました")
                else:
                    self.providers["amazon"] = True
                    logger.info("Amazon Textractが利用可能です（AWS認証情報あり）")
            except Exception as e:
                self.providers["amazon"] = False
                logger.info(f"Amazon Textractは初期化に失敗したため無効化しました: {e}")
        except ImportError:
            logger.debug("Amazon Textractが利用できません")
        
        # EasyOCR（日本語に強い）
        try:
            import easyocr
            self.providers["easyocr"] = True
            logger.info("EasyOCRが利用可能です")
        except ImportError:
            logger.debug("EasyOCRがインストールされていません（pip install easyocr でインストール可能）")
        
        # PaddleOCR（日本語に非常に強い）
        try:
            from paddleocr import PaddleOCR
            self.providers["paddleocr"] = True
            logger.info("PaddleOCRが利用可能です")
        except ImportError:
            logger.debug("PaddleOCRがインストールされていません（pip install paddlepaddle paddleocr でインストール可能）")
    
    def get_available_providers(self) -> List[str]:
        """利用可能なプロバイダー一覧を取得"""
        return [provider for provider, available in self.providers.items() if available]
    
    def recognize(self, image_path: str, provider: str = "tesseract", **kwargs) -> Optional[Dict[str, Any]]:
        """
        OCRを実行
        
        Args:
            image_path: 画像ファイルのパス
            provider: 使用するプロバイダー（tesseract, google, microsoft, amazon）
            **kwargs: プロバイダー固有のオプション
            
        Returns:
            OCR結果（テキストとメタデータ）、エラーの場合はNone
        """
        if provider not in self.providers:
            logger.error(f"不明なプロバイダー: {provider}")
            return None
        
        if not self.providers[provider]:
            logger.error(f"{provider} OCRが利用できません")
            return None
        
        if not os.path.exists(image_path):
            logger.error(f"画像ファイルが見つかりません: {image_path}")
            return None
        
        try:
            if provider == "tesseract":
                # layout=True の場合は位置情報（grid_data）も返す
                layout = bool(kwargs.pop("layout", False))
                if layout:
                    return self._recognize_tesseract_with_layout(image_path, **kwargs)
                return self._recognize_tesseract(image_path, **kwargs)
            elif provider == "google":
                return self._recognize_google(image_path, **kwargs)
            elif provider == "microsoft":
                return self._recognize_microsoft(image_path, **kwargs)
            elif provider == "amazon":
                return self._recognize_amazon(image_path, **kwargs)
            elif provider == "easyocr":
                return self._recognize_easyocr(image_path, **kwargs)
            elif provider == "paddleocr":
                return self._recognize_paddleocr(image_path, **kwargs)
        except Exception as e:
            logger.error(f"OCR実行エラー ({provider}): {e}")
            return None

    def _deskew_image(self, image) -> Any:
        """画像の傾きを補正（簡易版）"""
        try:
            import cv2
            img_array = np.array(image)
            # エッジ検出
            edges = cv2.Canny(img_array, 50, 150, apertureSize=3)
            # 直線検出（Hough変換）
            lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
            if lines is not None and len(lines) > 0:
                angles = []
                for rho, theta in lines[:20]:  # 最初の20本
                    angle = (theta * 180 / np.pi) - 90
                    if -45 < angle < 45:  # 合理的な範囲
                        angles.append(angle)
                if angles:
                    median_angle = statistics.median(angles)
                    if abs(median_angle) > 0.5:  # 0.5度以上傾いている場合のみ補正
                        # 回転補正
                        img_array = self._rotate_image(img_array, -median_angle)
                        from PIL import Image as PILImage
                        return PILImage.fromarray(img_array)
        except (ImportError, Exception):
            pass
        return image
    
    def _rotate_image(self, image_array: np.ndarray, angle: float) -> np.ndarray:
        """画像を回転（簡易版）"""
        try:
            import cv2
            h, w = image_array.shape
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(image_array, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            return rotated
        except ImportError:
            # OpenCVが無い場合は元の画像を返す
            return image_array

    def _cluster_line_positions(self, mask_1d: np.ndarray, min_gap: int) -> List[int]:
        """True領域（連続区間）をクラスタ化して中心位置を返す"""
        idx = np.where(mask_1d)[0]
        if idx.size == 0:
            return []
        clusters: List[List[int]] = []
        current = [int(idx[0])]
        for x in idx[1:]:
            x = int(x)
            if x - current[-1] <= 1:
                current.append(x)
            else:
                clusters.append(current)
                current = [x]
        clusters.append(current)

        centers = [int(statistics.median(c)) for c in clusters if c]

        # 近すぎる中心はさらにマージ
        merged: List[int] = []
        for c in sorted(centers):
            if not merged or (c - merged[-1]) >= min_gap:
                merged.append(c)
            else:
                merged[-1] = int((merged[-1] + c) / 2)
        return merged

    def _detect_table_grid_lines(self, image) -> Optional[Dict[str, List[int]]]:
        """
        罫線（枠線）から表のグリッド線を推定する（OpenCV使用）。
        戻り値: {"x": [..], "y": [..]}（境界線座標の昇順配列）
        """
        try:
            import cv2
        except Exception:
            return None

        img = np.array(image)
        if img.ndim == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        h, w = img.shape[:2]
        if h < 50 or w < 50:
            return None

        # 二値化（線検出向けに反転）
        bw = cv2.adaptiveThreshold(
            img, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 10
        )

        # 水平線/垂直線の抽出（解像度に応じてパラメータを調整）
        # 高解像度（600 DPI）では画像サイズが大きいため、カーネルサイズも大きくする
        # 解像度を推定（一般的に400 DPI = 3300px幅、600 DPI = 4950px幅程度）
        estimated_dpi = min(600, max(300, int(w / 8.27)))  # A4幅8.27インチを基準
        scale_factor = estimated_dpi / 400.0  # 400 DPIを基準にスケール
        
        hor_len = max(int(15 * scale_factor), w // 40)
        ver_len = max(int(15 * scale_factor), h // 40)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (hor_len, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, ver_len))

        horizontal = cv2.erode(bw, horizontal_kernel, iterations=1)
        horizontal = cv2.dilate(horizontal, horizontal_kernel, iterations=2)

        vertical = cv2.erode(bw, vertical_kernel, iterations=1)
        vertical = cv2.dilate(vertical, vertical_kernel, iterations=2)

        # 投影で線位置を推定（ピーク抽出）
        col_sum = vertical.sum(axis=0)
        row_sum = horizontal.sum(axis=1)

        # 閾値（最大値に対する比）- より多くの列を検出するために閾値を下げる
        # 0.3に下げて、より細かい罫線も検出できるようにする
        col_thr = float(col_sum.max()) * 0.3  # 0.4/0.5 → 0.3に下げる
        row_thr = float(row_sum.max()) * 0.3  # 0.4/0.5 → 0.3に下げる

        x_mask = col_sum > col_thr
        y_mask = row_sum > row_thr

        # min_gapも解像度に応じて調整（より細かい列も検出できるように小さくする）
        x_lines = self._cluster_line_positions(x_mask, min_gap=max(int(5 * scale_factor), w // 300))  # 200 → 300に変更
        y_lines = self._cluster_line_positions(y_mask, min_gap=max(int(5 * scale_factor), h // 300))  # 200 → 300に変更

        # 端の境界も追加（外枠が途切れてもセル割当できるように）
        if 0 not in x_lines:
            x_lines = [0] + x_lines
        if (w - 1) not in x_lines:
            x_lines = x_lines + [w - 1]
        if 0 not in y_lines:
            y_lines = [0] + y_lines
        if (h - 1) not in y_lines:
            y_lines = y_lines + [h - 1]

        x_lines = sorted(set(x_lines))
        y_lines = sorted(set(y_lines))

        # 線が少なすぎる場合は無効
        if len(x_lines) < 3 or len(y_lines) < 3:
            return None

        return {"x": x_lines, "y": y_lines}

    def _score_text(self, text: str, conf_0_100: float) -> float:
        """OCR結果の簡易スコア（ローカル最適化向け）"""
        t = (text or "").strip()
        if not t:
            return -1e9

        # 文字数（一定以上で頭打ち）
        length_score = min(len(t) / 5000.0, 1.0)

        # 日本語らしさ（帳票での誤認識抑制）
        jp_chars = re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]", t)
        jp_ratio = len(jp_chars) / max(len(t), 1)

        # 文字化け/ゴミ指標
        mojibake = t.count("�")
        weird_chars = len(re.findall(r"[\|\^\~`\{\}\[\]\\/]", t))
        junk_ratio = (mojibake * 2 + weird_chars) / max(len(t), 1)

        # 信頼度スコア（非線形：高信頼度を重視）
        conf_score = max(min(conf_0_100, 100.0), 0.0) / 100.0
        conf_score = conf_score ** 1.5  # 高信頼度をより重視

        # 数字・記号のバランス（帳票では数字が多い）
        digits = len(re.findall(r"\d", t))
        digit_ratio = digits / max(len(t), 1)

        return conf_score + 0.3 * length_score + 0.25 * jp_ratio + 0.1 * digit_ratio - 1.0 * junk_ratio
    
    def _recognize_tesseract(self, image_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Tesseract OCRで認識（高精度版）"""
        try:
            import pytesseract
            from PIL import Image, ImageEnhance, ImageFilter, ImageOps
            
            # 日本語+英語で認識を試みる
            lang = kwargs.get('lang', 'jpn+eng')
            # auto=True の場合、前処理×PSM を複数試してベストを選ぶ
            auto = bool(kwargs.pop("auto", False))
            psm_list = kwargs.pop("psm_list", [6, 4, 11, 1, 3, 12, 13])  # 表に適したPSMを追加

            # 画像を読み込んで前処理（ベース）
            base = Image.open(image_path)
            original_size = base.size
            if base.mode != 'L':
                base = base.convert('L')
            
            # 傾き補正（オプション、時間がかかるのでauto時のみ）
            if auto:
                try:
                    base = self._deskew_image(base)
                except Exception:
                    pass  # 傾き補正失敗時はスキップ
            
            # 複数のコントラスト値で試行（auto時）
            contrast_values = [2.0]  # デフォルト
            if auto:
                contrast_values = [1.5, 1.8, 2.0, 2.2, 2.5, 3.0, 3.5, 4.0, 5.0]  # より広範囲のコントラスト調整（薄い文字も拾う）
            
            variants = []
            for contrast_val in contrast_values:
                img = ImageEnhance.Contrast(base).enhance(contrast_val)
                # シャープ化を強化（数字・細線の読み取り向上）
                img = ImageEnhance.Sharpness(img).enhance(2.5)  # 2.0 → 2.5
                # ノイズ除去（軽め）
                img = img.filter(ImageFilter.MedianFilter(size=3))
                variants.append((f"base_c{contrast_val:.1f}", img))
            
            if auto:
                # 二値化（複数の閾値で試行・薄い文字も拾うために低閾値も追加）
                for thr in [120, 140, 150, 160, 180, 200]:
                    bin_img = base.point(lambda p: 255 if p > thr else 0)
                    variants.append((f"bin_{thr}", bin_img))
                
                # 適応的閾値処理（複数パターン）
                try:
                    import cv2
                    img_array = np.array(base)
                    # 通常の適応的閾値
                    adaptive = cv2.adaptiveThreshold(
                        img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY, 11, 2
                    )
                    variants.append(("adaptive", Image.fromarray(adaptive)))
                    # より敏感な適応的閾値（薄い文字用）
                    adaptive2 = cv2.adaptiveThreshold(
                        img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY, 15, 5
                    )
                    variants.append(("adaptive2", Image.fromarray(adaptive2)))
                    # Otsu閾値（自動最適化）
                    _, otsu = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    variants.append(("otsu", Image.fromarray(otsu)))
                    # ヒストグラム均一化（コントラスト改善）
                    equalized = cv2.equalizeHist(img_array)
                    variants.append(("equalized", Image.fromarray(equalized)))
                except ImportError:
                    pass  # OpenCVが無い場合はスキップ
                
                # 反転（白抜き文字/暗背景対策）
                variants.append(("invert", ImageOps.invert(base)))
                
                # 追加のシャープ（細線強調・強化版）
                variants.append(("sharp", base.filter(ImageFilter.UnsharpMask(radius=1.5, percent=200, threshold=2))))
                
                # より強力なシャープ（数字・文字のエッジ強調）
                extra_sharp = ImageEnhance.Sharpness(base).enhance(4.0)
                variants.append(("extra_sharp", extra_sharp))
                
                # ガウシアンブラー + シャープ（ノイズ除去後シャープ・強化版）
                blurred = base.filter(ImageFilter.GaussianBlur(radius=0.5))
                sharpened = ImageEnhance.Sharpness(blurred).enhance(4.0)  # 3.0 → 4.0
                variants.append(("blur_sharp", sharpened))
                
                # モルフォロジー演算（開演算・閉演算の簡易版）
                # ノイズ除去強化
                denoised = base.filter(ImageFilter.MedianFilter(size=5))
                variants.append(("denoise5", denoised))

            best = None
            best_score = -1e9

            # 日本語データの有無を事前確認
            jpn_available = False
            try:
                import subprocess
                result = subprocess.run(
                    [pytesseract.pytesseract.tesseract_cmd, '--list-langs'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if 'jpn' in result.stdout.lower():
                    jpn_available = True
                    logger.info("日本語OCRデータが利用可能です")
                else:
                    logger.warning("日本語OCRデータが見つかりません。英語のみで試行します...")
            except Exception:
                logger.warning("日本語OCRデータの確認に失敗。英語のみで試行します...")
            
            # 日本語が利用可能な場合のみ jpn+eng を試行
            if jpn_available and 'jpn' in lang.lower():
                try:
                    for vname, img in variants:
                        for psm in (psm_list if auto else [kwargs.pop("psm", 6)]):
                            config = f"--psm {psm}"
                            t = pytesseract.image_to_string(img, lang=lang, config=config, **{k: v for k, v in kwargs.items() if k != 'lang'})
                            d = pytesseract.image_to_data(img, lang=lang, config=config, output_type=pytesseract.Output.DICT, **{k: v for k, v in kwargs.items() if k != 'lang'})
                            conf = self._calculate_confidence(d)
                            score = self._score_text(t, conf)
                            if score > best_score:
                                best_score = score
                                best = (t, d, conf, vname, psm)
                except Exception as e:
                    logger.warning(f"日本語OCR実行エラー: {e}。英語のみで試行します...")
                    jpn_available = False
            
            # 日本語が利用できない場合は英語のみ
            if not jpn_available:
                for vname, img in variants:
                    for psm in (psm_list if auto else [kwargs.pop("psm", 6)]):
                        config = f"--psm {psm}"
                        t = pytesseract.image_to_string(img, config=config, **kwargs)
                        d = pytesseract.image_to_data(img, config=config, output_type=pytesseract.Output.DICT, **kwargs)
                        conf = self._calculate_confidence(d)
                        score = self._score_text(t, conf)
                        if score > best_score:
                            best_score = score
                            best = (t, d, conf, vname, psm)

            if not best:
                return None

            text, data, conf, vname, psm = best
            
            return {
                "provider": "tesseract",
                "text": text.strip(),
                "grid_data": None,
                "confidence": conf,
                "raw_data": data
            }
        except Exception as e:
            logger.error(f"Tesseract OCRエラー: {e}")
            return None

    def _recognize_tesseract_with_layout(self, image_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Tesseract OCRで認識（レイアウト情報付き）"""
        try:
            import pytesseract
            from PIL import Image, ImageEnhance, ImageFilter, ImageOps

            lang = kwargs.get("lang", "jpn+eng")
            auto = bool(kwargs.pop("auto", True))
            psm_list = kwargs.pop("psm_list", [6, 4, 11])
            max_cols = int(kwargs.pop("max_cols", 80))
            use_gridlines = bool(kwargs.pop("use_gridlines", True))

            # 前処理（精度向上・薄い文字も拾う）
            base = Image.open(image_path)
            if base.mode != "L":
                base = base.convert("L")
            
            # 傾き補正
            try:
                base = self._deskew_image(base)
            except Exception:
                pass
            
            # 罫線（枠線）からグリッド線を推定（1回だけ）
            grid_lines = None
            if use_gridlines:
                try:
                    grid_lines = self._detect_table_grid_lines(base)
                except Exception:
                    grid_lines = None

            # 複数の前処理パターン（薄い文字も拾う）
            variants = []
            # ベース（複数のコントラスト値）
            for cval in [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
                img = ImageEnhance.Contrast(base).enhance(cval)
                img = ImageEnhance.Sharpness(img).enhance(2.5)
                img = img.filter(ImageFilter.MedianFilter(size=3))
                variants.append((f"base_c{cval:.1f}", img))
            
            if auto:
                # 二値化（低閾値も追加・薄い文字用）
                for thr in [120, 140, 150, 160, 180, 200]:
                    bin_img = base.point(lambda p: 255 if p > thr else 0)
                    variants.append((f"bin_{thr}", bin_img))
                
                # 適応的閾値処理
                try:
                    import cv2
                    img_array = np.array(base)
                    adaptive = cv2.adaptiveThreshold(
                        img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY, 11, 2
                    )
                    variants.append(("adaptive", Image.fromarray(adaptive)))
                    # Otsu閾値
                    _, otsu = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    variants.append(("otsu", Image.fromarray(otsu)))
                    # ヒストグラム均一化
                    equalized = cv2.equalizeHist(img_array)
                    variants.append(("equalized", Image.fromarray(equalized)))
                except ImportError:
                    pass
                
                variants.append(("invert", ImageOps.invert(base)))
                variants.append(("sharp", base.filter(ImageFilter.UnsharpMask(radius=1.5, percent=200, threshold=2))))
                # より強力なシャープ
                extra_sharp = ImageEnhance.Sharpness(base).enhance(4.0)
                variants.append(("extra_sharp", extra_sharp))

            tess_kwargs = {k: v for k, v in kwargs.items() if k not in ("lang",)}

            # 日本語データの有無を事前確認
            jpn_available = False
            if 'jpn' in lang.lower():
                try:
                    import subprocess
                    result = subprocess.run(
                        [pytesseract.pytesseract.tesseract_cmd, '--list-langs'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if 'jpn' in result.stdout.lower():
                        jpn_available = True
                        logger.info("日本語OCRデータが利用可能です（レイアウト版）")
                    else:
                        logger.warning("日本語OCRデータが見つかりません。英語のみで試行します（レイアウト版）...")
                except Exception:
                    logger.warning("日本語OCRデータの確認に失敗。英語のみで試行します（レイアウト版）...")

            # アンサンブル方式：複数の結果をマージして空欄を埋める
            all_grid_results: List[Dict[str, Any]] = []  # グリッド結果をすべて保持
            
            best = None
            best_score = -1e9

            for vname, img in variants:
                for psm in (psm_list if auto else [6]):
                    config = f"--psm {psm}"
                    try:
                        # 日本語が利用可能な場合のみ jpn+eng を試行
                        if jpn_available and 'jpn' in lang.lower():
                            data = pytesseract.image_to_data(
                                img,
                                output_type=pytesseract.Output.DICT,
                                lang=lang,
                                config=config,
                                **tess_kwargs,
                            )
                        else:
                            # 英語のみ
                            data = pytesseract.image_to_data(
                                img,
                                output_type=pytesseract.Output.DICT,
                                config=config,
                                **tess_kwargs,
                            )
                    except Exception as e:
                        # エラー時は英語のみで再試行
                        logger.debug(f"OCR実行エラー（{lang}）: {e}。英語のみで再試行...")
                        data = pytesseract.image_to_data(
                            img,
                            output_type=pytesseract.Output.DICT,
                            config=config,
                            **tess_kwargs,
                        )

                    texts: List[str] = []
                    positions: List[Dict[str, int]] = []
                    confs: List[float] = []
                    row_keys: List[tuple] = []

                    n = len(data.get("text", []))
                    for i in range(n):
                        t = (data["text"][i] or "").strip()
                        if not t:
                            continue
                        try:
                            left = int(data["left"][i])
                            top = int(data["top"][i])
                            width = int(data["width"][i])
                            height = int(data["height"][i])
                        except Exception:
                            continue

                        conf_raw = data.get("conf", [None] * n)[i]
                        try:
                            conf_val = float(conf_raw)
                        except Exception:
                            conf_val = 0.0
                        if conf_val < 0:
                            conf_val = 0.0

                        texts.append(t)
                        positions.append(
                            {
                                "x": left,
                                "y": top,
                                "width": width,
                                "height": height,
                                "center_x": left + width // 2,
                                "center_y": top + height // 2,
                            }
                        )
                        confs.append(conf_val)
                        # Tesseractの行情報（ある場合はこれを優先して行を作る）
                        try:
                            block_num = int(data.get("block_num", [0] * n)[i])
                            par_num = int(data.get("par_num", [0] * n)[i])
                            line_num = int(data.get("line_num", [0] * n)[i])
                            row_keys.append((block_num, par_num, line_num))
                        except Exception:
                            row_keys.append((0, 0, positions[-1]["center_y"]))

                    if not positions:
                        continue

                    # 罫線グリッドが取れている場合は、まずそれに割り当てる（枠線＝セル境界）
                    if grid_lines is not None:
                        x_lines = grid_lines["x"]
                        y_lines = grid_lines["y"]
                        cols_n = len(x_lines) - 1
                        rows_n = len(y_lines) - 1

                        # 異常に列が多い場合はスキップ（別手法へ）
                        if 2 <= cols_n <= max_cols and 2 <= rows_n <= 500:
                            grid2: List[List[str]] = [[""] * cols_n for _ in range(rows_n)]
                            for i, pos in enumerate(positions):
                                cx = pos["center_x"]
                                cy = pos["center_y"]
                                c = bisect_right(x_lines, cx) - 1
                                r = bisect_right(y_lines, cy) - 1
                                if r < 0 or c < 0 or r >= rows_n or c >= cols_n:
                                    continue
                                if grid2[r][c]:
                                    grid2[r][c] += " " + texts[i]
                                else:
                                    grid2[r][c] = texts[i]

                            # 空の末尾行/列をトリム
                            last_row = -1
                            for ri, row in enumerate(grid2):
                                if any((v or "").strip() for v in row):
                                    last_row = ri
                            if last_row >= 0:
                                grid2 = grid2[: last_row + 1]

                            last_col = -1
                            for ci in range(cols_n):
                                if any((row[ci] or "").strip() for row in grid2):
                                    last_col = ci
                            if last_col >= 0:
                                grid2 = [row[: last_col + 1] for row in grid2]

                            conf = (sum(confs) / len(confs)) if confs else 0.0
                            text_joined = "\n".join(texts)
                            score = self._score_text(text_joined, conf)
                            # グリッド線でセル化できた場合は優先（軽いボーナス）
                            score += 0.15
                            # ただし極端な行/列はペナルティ
                            score -= max(0.0, (len(grid2) - 200) / 400.0)
                            score -= max(0.0, (len(grid2[0]) - 60) / 80.0) if grid2 else 0.0

                            # すべての結果を保持（マージ用）
                            all_grid_results.append({
                                "grid_data": grid2,
                                "score": score,
                                "confidence": conf,
                                "variant": vname,
                                "psm": psm,
                                "cols": len(grid2[0]) if grid2 else 0,
                                "rows": len(grid2),
                            })
                            
                            if score > best_score:
                                best_score = score
                                best = {
                                    "provider": "tesseract",
                                    "text": text_joined,
                                    "grid_data": grid2,
                                    "confidence": conf,
                                    "raw_data": data,
                                    "_meta": {"variant": vname, "psm": psm, "cols": len(grid2[0]) if grid2 else 0, "rows": len(grid2), "grid": "lines"},
                                }

                    # 行/列のクラスタリング（列暴発を抑制）
                    heights = [p["height"] for p in positions if p.get("height", 0) > 0]
                    median_h = statistics.median(heights) if heights else 12
                    row_thresh = max(int(median_h * 0.9), 8)

                    widths = [p["width"] for p in positions if p.get("width", 0) > 0]
                    median_w = statistics.median(widths) if widths else 20
                    x_thresh = max(int(median_w * 1.5), 18)

                    # rows: まずTesseractの(line_num)を優先。無い/壊れている場合はyクラスタでフォールバック
                    use_line_keys = any(k[0] != 0 or k[1] != 0 for k in row_keys)
                    if use_line_keys:
                        # 行キーごとに平均Yで並べる
                        row_y: Dict[tuple, List[int]] = {}
                        for i, rk in enumerate(row_keys):
                            row_y.setdefault(rk, []).append(positions[i]["center_y"])
                        row_items = sorted(
                            [(rk, int(sum(ys) / len(ys))) for rk, ys in row_y.items()],
                            key=lambda x: x[1],
                        )
                        # 行が暴発する場合は line_num ベースを諦めてYクラスタにフォールバック
                        if len(row_items) > 200:
                            use_line_keys = False
                        else:
                            row_keys_sorted = [rk for rk, _ in row_items]
                            row_index = {rk: idx for idx, rk in enumerate(row_keys_sorted)}
                            row_count = len(row_keys_sorted)
                            # row_centers は nearest_index 用にダミーで保持
                            row_centers = [y for _, y in row_items]
                    if not use_line_keys:
                        y_centers = sorted([p["center_y"] for p in positions])
                        row_centers = []
                        for y in y_centers:
                            if not row_centers or abs(y - row_centers[-1]) > row_thresh:
                                row_centers.append(y)
                            else:
                                row_centers[-1] = int((row_centers[-1] + y) / 2)
                        row_count = len(row_centers)
                        row_index = None

                    x_centers = sorted([p["center_x"] for p in positions])
                    # cols: greedy cluster by x_thresh; expand threshold until <= max_cols
                    def make_cols(th: int) -> List[int]:
                        cols: List[int] = []
                        for x in x_centers:
                            if not cols or abs(x - cols[-1]) > th:
                                cols.append(x)
                            else:
                                cols[-1] = int((cols[-1] + x) / 2)
                        return cols

                    cols = make_cols(x_thresh)
                    while len(cols) > max_cols and x_thresh < 400:
                        x_thresh = int(x_thresh * 1.25) + 1
                        cols = make_cols(x_thresh)

                    # 列がまだ多すぎる場合は諦めてテキスト列に落とす（暴発防止）
                    if len(cols) > max_cols:
                        conf = (sum(confs) / len(confs)) if confs else 0.0
                        text_joined = "\n".join(texts)
                        score = self._score_text(text_joined, conf) - 0.5  # ペナルティ
                        if score > best_score:
                            best_score = score
                            best = {
                                "provider": "tesseract",
                                "text": text_joined,
                                "grid_data": None,
                                "confidence": conf,
                                "raw_data": data,
                                "_meta": {"variant": vname, "psm": psm, "cols": len(cols), "rows": len(row_centers)},
                            }
                        continue

                    # 近傍割当
                    def nearest_index(val: int, centers: List[int]) -> int:
                        best_i = 0
                        best_d = None
                        for i, c in enumerate(centers):
                            d = abs(val - c)
                            if best_d is None or d < best_d:
                                best_d = d
                                best_i = i
                        return best_i

                    grid: List[List[str]] = [[""] * len(cols) for _ in range(row_count)]
                    for i, pos in enumerate(positions):
                        if row_index is not None:
                            r = row_index.get(row_keys[i], 0)
                        else:
                            r = nearest_index(pos["center_y"], row_centers)
                        c = nearest_index(pos["center_x"], cols)
                        if grid[r][c]:
                            grid[r][c] += " " + texts[i]
                        else:
                            grid[r][c] = texts[i]

                    # 末尾の空列をトリム（全行が空の列を削る）
                    last_nonempty = -1
                    for ci in range(len(cols)):
                        if any((row[ci] or "").strip() for row in grid):
                            last_nonempty = ci
                    if last_nonempty >= 0:
                        grid = [row[: last_nonempty + 1] for row in grid]

                    conf = (sum(confs) / len(confs)) if confs else 0.0
                    text_joined = "\n".join(texts)
                    score = self._score_text(text_joined, conf)
                    # 極端に列が多いほどペナルティ（表の見やすさ優先）
                    score -= max(0.0, (len(cols) - 60) / 80.0)
                    # 行が多すぎる場合もペナルティ（行暴発を抑える）
                    score -= max(0.0, (row_count - 120) / 250.0)

                    if score > best_score:
                        best_score = score
                        best = {
                            "provider": "tesseract",
                            "text": text_joined,
                            "grid_data": grid,
                            "confidence": conf,
                            "raw_data": data,
                            "_meta": {"variant": vname, "psm": psm, "cols": len(cols), "rows": len(row_centers)},
                        }

            if not best:
                # フォールバック：通常文字列（空になる可能性あり）
                try:
                    text = pytesseract.image_to_string(base, lang=lang, **tess_kwargs)
                except Exception:
                    text = pytesseract.image_to_string(base, **tess_kwargs)
                return {
                    "provider": "tesseract",
                    "text": (text or "").strip(),
                    "grid_data": None,
                    "confidence": 0.0,
                    "raw_data": {},
                }
            
            # アンサンブル方式：複数の結果をマージして空欄を埋める
            if all_grid_results and best.get("grid_data"):
                base_grid = best["grid_data"]
                rows_base = len(base_grid)
                cols_base = len(base_grid[0]) if base_grid else 0
                
                # すべての結果から空欄を埋める
                merged_grid = [row[:] for row in base_grid]  # コピー
                
                for result in all_grid_results:
                    other_grid = result.get("grid_data")
                    if not other_grid:
                        continue
                    
                    # グリッドサイズが異なる場合はスキップ（安全のため）
                    if len(other_grid) != rows_base or (other_grid and len(other_grid[0]) != cols_base):
                        continue
                    
                    # 空欄を埋める（信頼度が高い結果を優先）
                    for r in range(min(rows_base, len(other_grid))):
                        for c in range(min(cols_base, len(other_grid[r]) if other_grid[r] else 0)):
                            base_val = (merged_grid[r][c] or "").strip()
                            other_val = (other_grid[r][c] or "").strip()
                            
                            # 空欄を埋める（信頼度が高い結果を優先、ただし空欄を埋める場合は採用）
                            if not base_val and other_val:
                                # 空欄を埋める
                                merged_grid[r][c] = other_val
                            elif base_val and other_val and base_val != other_val:
                                # 両方に値がある場合、文字化けの少ない方を選ぶ
                                base_mojibake = base_val.count('') + len([c for c in base_val if ord(c) > 0xFFFF])
                                other_mojibake = other_val.count('') + len([c for c in other_val if ord(c) > 0xFFFF])
                                
                                # 文字化けが少ない方を優先
                                if other_mojibake < base_mojibake:
                                    merged_grid[r][c] = other_val
                                elif other_mojibake == base_mojibake:
                                    # 文字化けが同じ場合は信頼度が高い方を採用
                                    base_conf = best.get("confidence", 0.0)
                                    other_conf = result.get("confidence", 0.0)
                                    if other_conf > base_conf + 3.0:  # 3%以上の差があれば採用
                                        merged_grid[r][c] = other_val
                                # 文字数が多い方を優先（読み取り不足を防ぐ）
                                if len(other_val) > len(base_val) * 1.2:  # 20%以上多い場合
                                    merged_grid[r][c] = other_val
                
                # マージ結果を反映
                best["grid_data"] = merged_grid
                # テキストも更新
                best["text"] = "\n".join([" ".join(row) for row in merged_grid])
            
            best.pop("_meta", None)
            return best
        except Exception as e:
            logger.error(f"Tesseract OCR（レイアウト付き）エラー: {e}")
            return None
    
    def _recognize_google(self, image_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Google Cloud Vision APIで認識"""
        try:
            from google.cloud import vision
            
            client = vision.ImageAnnotatorClient()
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = client.text_detection(image=image)
            texts = response.text_annotations
            
            if texts:
                text = texts[0].description
                return {
                    "provider": "google",
                    "text": text,
                    "confidence": response.text_annotations[0].confidence if hasattr(response.text_annotations[0], 'confidence') else None,
                    "text_count": len(texts)
                }
            return None
        except Exception as e:
            logger.error(f"Google Cloud Vision APIエラー: {e}")
            return None
    
    def _recognize_microsoft(self, image_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Microsoft Azure Computer Visionで認識"""
        try:
            from azure.cognitiveservices.vision.computervision import ComputerVisionClient
            from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
            from msrest.authentication import CognitiveServicesCredentials
            
            endpoint = os.getenv("AZURE_VISION_ENDPOINT")
            key = os.getenv("AZURE_VISION_KEY")
            
            if not endpoint or not key:
                logger.error("Azure Vision APIの認証情報が設定されていません")
                return None
            
            client = ComputerVisionClient(
                endpoint,
                CognitiveServicesCredentials(key)
            )
            
            with open(image_path, 'rb') as image_file:
                result = client.read_in_stream(image_file, raw=True)
            
            # 簡易実装（実際の実装はより複雑）
            return {
                "provider": "microsoft",
                "text": "",  # 実際の実装が必要
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Microsoft Azure Computer Visionエラー: {e}")
            return None
    
    def _recognize_amazon(self, image_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Amazon Textractで認識"""
        try:
            import boto3
            import os
            
            # リージョンを環境変数または引数から取得
            region = kwargs.get('region') or os.getenv('AWS_REGION') or os.getenv('AWS_DEFAULT_REGION') or 'us-east-1'
            
            textract = boto3.client('textract', region_name=region)
            with open(image_path, 'rb') as document:
                response = textract.detect_document_text(Document={'Bytes': document.read()})
            
            text = ""
            for item in response['Blocks']:
                if item['BlockType'] == 'LINE':
                    text += item['Text'] + '\n'
            
            return {
                "provider": "amazon",
                "text": text.strip(),
                "blocks": len(response['Blocks'])
            }
        except Exception as e:
            logger.error(f"Amazon Textractエラー: {e}")
            return None
    
    def _recognize_easyocr(self, image_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """EasyOCRで認識（日本語に強い）"""
        try:
            import easyocr
            from PIL import Image
            import signal
            import sys
            
            # 日本語と英語をサポート
            langs = kwargs.get('lang', ['ja', 'en'])
            if isinstance(langs, str):
                langs = [langs]
            
            # EasyOCRリーダーを初期化（初回のみ時間がかかる）
            # GPU使用を試行（利用可能な場合）
            # NOTE: EasyOCR(GPU)は環境によってクラッシュすることがあるため、デフォルトはCPU。
            #       GPUを使いたい場合は呼び出し側から gpu=True を渡す。
            use_gpu = kwargs.get('gpu', False)
            if not hasattr(self, '_easyocr_reader'):
                logger.info(f"EasyOCRリーダーを初期化中（初回のみ時間がかかります、GPU: {use_gpu}）...")
                
                try:
                    # より安全な初期化（メモリ制限とエラーハンドリング）
                    # verbose=Falseでログを抑制、モデルダウンロードの進捗を抑制
                    if use_gpu:
                        # GPU使用を試行
                        import torch
                        if torch.cuda.is_available():
                            try:
                                self._easyocr_reader = easyocr.Reader(langs, gpu=True, verbose=False)
                                logger.info("EasyOCR: GPUを使用します")
                            except (MemoryError, OSError, RuntimeError) as gpu_err:
                                logger.warning(f"EasyOCR GPU初期化失敗: {gpu_err}。CPUで再試行...")
                                self._easyocr_reader = easyocr.Reader(langs, gpu=False, verbose=False)
                        else:
                            logger.warning("EasyOCR: GPUが利用できないためCPUを使用します")
                            self._easyocr_reader = easyocr.Reader(langs, gpu=False, verbose=False)
                    else:
                        # CPUで初期化（verbose=Falseでログを抑制）
                        self._easyocr_reader = easyocr.Reader(langs, gpu=False, verbose=False)
                        logger.info("EasyOCR: CPUで初期化完了")
                except MemoryError as me:
                    logger.error(f"EasyOCR: メモリ不足エラー: {me}")
                    # メモリ不足の場合はNoneを返してTesseractにフォールバック
                    return None
                except OSError as ose:
                    logger.error(f"EasyOCR: OSエラー（モデルダウンロード失敗の可能性）: {ose}")
                    return None
                except RuntimeError as re:
                    logger.error(f"EasyOCR: ランタイムエラー: {re}")
                    return None
                except Exception as e:
                    logger.error(f"EasyOCR初期化エラー: {type(e).__name__}: {e}")
                    # エラーの詳細を記録
                    import traceback
                    logger.debug(f"EasyOCR初期化エラー詳細:\n{traceback.format_exc()}")
                    return None
            
            # OCR実行（エラーハンドリングを強化）
            try:
                results = self._easyocr_reader.readtext(image_path)
            except Exception as e:
                logger.error(f"EasyOCR実行エラー: {type(e).__name__}: {e}")
                return None
            
            # テキストを結合
            text_lines = []
            for (bbox, text, conf) in results:
                if text.strip():
                    text_lines.append(text)
            
            text = "\n".join(text_lines)
            
            # グリッドデータも作成（レイアウト情報がある場合）
            grid_data = None
            layout = kwargs.get('layout', False)
            if layout and results:
                try:
                    # 罫線検出と組み合わせてグリッドを作成
                    from PIL import Image
                    img = Image.open(image_path)
                    grid_lines = self._detect_table_grid_lines(img)
                    
                    if grid_lines:
                        x_lines = grid_lines["x"]
                        y_lines = grid_lines["y"]
                        cols_n = len(x_lines) - 1
                        rows_n = len(y_lines) - 1
                        
                        if 2 <= cols_n <= 100 and 2 <= rows_n <= 500:
                            grid2: List[List[str]] = [[""] * cols_n for _ in range(rows_n)]
                            
                            # EasyOCRの結果をグリッドに割り当て
                            for (bbox, text, conf) in results:
                                if not text.strip():
                                    continue
                                # bboxは4点の座標 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                                if len(bbox) >= 4:
                                    # 中心座標を計算
                                    cx = sum([p[0] for p in bbox]) / len(bbox)
                                    cy = sum([p[1] for p in bbox]) / len(bbox)
                                    
                                    c = bisect_right(x_lines, cx) - 1
                                    r = bisect_right(y_lines, cy) - 1
                                    
                                    if 0 <= r < rows_n and 0 <= c < cols_n:
                                        if grid2[r][c]:
                                            grid2[r][c] += " " + text
                                        else:
                                            grid2[r][c] = text
                            
                            # 空の末尾行/列をトリム
                            last_row = -1
                            for ri, row in enumerate(grid2):
                                if any((v or "").strip() for v in row):
                                    last_row = ri
                            if last_row >= 0:
                                grid2 = grid2[: last_row + 1]
                            
                            last_col = -1
                            for ci in range(cols_n):
                                if any((row[ci] or "").strip() for row in grid2):
                                    last_col = ci
                            if last_col >= 0:
                                grid2 = [row[: last_col + 1] for row in grid2]
                            
                            grid_data = grid2
                except Exception as e:
                    logger.debug(f"EasyOCRグリッド作成エラー: {e}")
            
            return {
                "provider": "easyocr",
                "text": text.strip(),
                "confidence": sum([conf for _, _, conf in results]) / len(results) if results else 0.0,
                "grid_data": grid_data,
                "raw_data": results
            }
        except Exception as e:
            logger.error(f"EasyOCRエラー: {e}")
            return None
    
    def _recognize_paddleocr(self, image_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """PaddleOCRで認識（日本語に非常に強い）"""
        try:
            from paddleocr import PaddleOCR
            import numpy as np
            from PIL import Image
            
            # 日本語と英語をサポート
            use_angle_cls = kwargs.get('use_angle_cls', True)
            lang = kwargs.get('lang', 'japan')  # 'japan'は日本語+英語
            
            # PaddleOCRを初期化（初回のみ時間がかかる）
            # GPU使用を試行（利用可能な場合）
            use_gpu = kwargs.get('gpu', True)  # デフォルトでGPUを試行
            if not hasattr(self, '_paddleocr_reader'):
                logger.info(f"PaddleOCRリーダーを初期化中（初回のみ時間がかかります、GPU: {use_gpu}）...")
                try:
                    self._paddleocr_reader = PaddleOCR(
                        use_angle_cls=use_angle_cls,
                        lang=lang,
                        use_gpu=use_gpu
                    )
                except Exception as e:
                    logger.warning(f"GPU初期化失敗、CPUで再試行: {e}")
                    self._paddleocr_reader = PaddleOCR(
                        use_angle_cls=use_angle_cls,
                        lang=lang,
                        use_gpu=False
                    )
            
            # OCR実行
            results = self._paddleocr_reader.ocr(image_path, cls=use_angle_cls)
            
            # テキストを結合
            text_lines = []
            confs = []
            if results and results[0]:
                for line in results[0]:
                    if line and len(line) >= 2:
                        bbox, (text, conf) = line[0], line[1]
                        if text.strip():
                            text_lines.append(text)
                            confs.append(conf)
            
            text = "\n".join(text_lines)
            
            # グリッドデータも作成（レイアウト情報がある場合）
            grid_data = None
            layout = kwargs.get('layout', False)
            if layout and results and results[0]:
                try:
                    # 罫線検出と組み合わせてグリッドを作成
                    from PIL import Image
                    img = Image.open(image_path)
                    grid_lines = self._detect_table_grid_lines(img)
                    
                    if grid_lines:
                        x_lines = grid_lines["x"]
                        y_lines = grid_lines["y"]
                        cols_n = len(x_lines) - 1
                        rows_n = len(y_lines) - 1
                        
                        if 2 <= cols_n <= 100 and 2 <= rows_n <= 500:
                            grid2: List[List[str]] = [[""] * cols_n for _ in range(rows_n)]
                            
                            # PaddleOCRの結果をグリッドに割り当て
                            for line in results[0]:
                                if line and len(line) >= 2:
                                    bbox, (text, conf) = line[0], line[1]
                                    if not text.strip():
                                        continue
                                    # bboxは4点の座標 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                                    if len(bbox) >= 4:
                                        # 中心座標を計算
                                        cx = sum([p[0] for p in bbox]) / len(bbox)
                                        cy = sum([p[1] for p in bbox]) / len(bbox)
                                        
                                        c = bisect_right(x_lines, cx) - 1
                                        r = bisect_right(y_lines, cy) - 1
                                        
                                        if 0 <= r < rows_n and 0 <= c < cols_n:
                                            if grid2[r][c]:
                                                grid2[r][c] += " " + text
                                            else:
                                                grid2[r][c] = text
                            
                            # 空の末尾行/列をトリム
                            last_row = -1
                            for ri, row in enumerate(grid2):
                                if any((v or "").strip() for v in row):
                                    last_row = ri
                            if last_row >= 0:
                                grid2 = grid2[: last_row + 1]
                            
                            last_col = -1
                            for ci in range(cols_n):
                                if any((row[ci] or "").strip() for row in grid2):
                                    last_col = ci
                            if last_col >= 0:
                                grid2 = [row[: last_col + 1] for row in grid2]
                            
                            grid_data = grid2
                except Exception as e:
                    logger.debug(f"PaddleOCRグリッド作成エラー: {e}")
            
            return {
                "provider": "paddleocr",
                "text": text.strip(),
                "confidence": sum(confs) / len(confs) if confs else 0.0,
                "grid_data": grid_data,
                "raw_data": results
            }
        except Exception as e:
            logger.error(f"PaddleOCRエラー: {e}")
            return None
    
    def _calculate_confidence(self, data: Dict) -> float:
        """Tesseractの信頼度を計算"""
        confs = data.get("conf")
        if confs:
            valid: List[float] = []
            for c in confs:
                try:
                    v = float(c)
                except Exception:
                    continue
                if v > 0:
                    valid.append(v)
            return (sum(valid) / len(valid)) if valid else 0.0
        return 0.0
    
    def get_status(self) -> Dict[str, Any]:
        """ステータス情報を取得"""
        return {
            "providers": self.providers,
            "available": self.get_available_providers(),
            "scripts_path": str(self.ocr_scripts_path)
        }


# 使用例
if __name__ == "__main__":
    ocr = MultiProviderOCR()
    
    print("利用可能なプロバイダー:", ocr.get_available_providers())
    print("ステータス:", ocr.get_status())
    
    # テスト（画像ファイルがある場合）
    # result = ocr.recognize("test_image.png", provider="tesseract")
    # print("OCR結果:", result)


















