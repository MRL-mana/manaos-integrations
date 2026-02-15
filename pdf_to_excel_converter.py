"""
PDFからExcelへの変換スクリプト
Google DriveからPDFをダウンロードしてExcelに変換
"""

import sys
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

logger = logging.getLogger(__name__)

# 必要なライブラリのインポートチェック
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandasがインストールされていません")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumberがインストールされていません")

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2imageがインストールされていません")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDFがインストールされていません")

try:
    from ocr_multi_provider import MultiProviderOCR
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR機能が利用できません")

try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False
    logger.warning("tabula-pyがインストールされていません")

try:
    from google_drive_integration import GoogleDriveIntegration
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    logger.warning("google_drive_integrationが利用できません")


class PDFToExcelConverter:
    """PDFからExcelへの変換クラス"""
    
    def __init__(self, google_drive: Optional[GoogleDriveIntegration] = None):
        """
        初期化
        
        Args:
            google_drive: Google Drive統合インスタンス（オプション）
        """
        self.google_drive = google_drive
        self.ocr = None
        self.page_data = []  # ページごとのデータを保存
        if OCR_AVAILABLE:
            try:
                self.ocr = MultiProviderOCR()
            except Exception as e:
                logger.warning(f"OCRの初期化に失敗: {e}")
        self.check_dependencies()
    
    def check_dependencies(self) -> Dict[str, bool]:
        """
        必要な依存関係をチェック
        
        Returns:
            依存関係の状態
        """
        status = {
            "pandas": PANDAS_AVAILABLE,
            "pdfplumber": PDFPLUMBER_AVAILABLE,
            "tabula": TABULA_AVAILABLE,
            "pdf2image": PDF2IMAGE_AVAILABLE,
            "pymupdf": PYMUPDF_AVAILABLE,
            "ocr": OCR_AVAILABLE and self.ocr is not None,
            "google_drive": GOOGLE_DRIVE_AVAILABLE and self.google_drive is not None
        }
        
        missing = [k for k, v in status.items() if not v]
        if missing:
            logger.warning(f"不足している依存関係: {', '.join(missing)}")
        
        return status
    
    def download_from_google_drive(
        self,
        file_url: str,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Google DriveからPDFをダウンロード
        
        Args:
            file_url: Google DriveのファイルURL
            output_path: 保存先パス（オプション）
            
        Returns:
            ダウンロードしたファイルのパス（成功時）、None（失敗時）
        """
        # まず、共有リンクから直接ダウンロードを試みる
        try:
            file_id = self._extract_file_id_from_url(file_url)
            if file_id:
                # 共有リンクから直接ダウンロード
                download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                logger.info(f"共有リンクからダウンロードを試みます: {file_id}")
                
                import requests
                response = requests.get(download_url, stream=True, allow_redirects=True)
                
                # 確認ページの場合は実際のダウンロードURLを取得
                if 'virus scan warning' in response.text.lower() or 'confirm' in response.text.lower():
                    # 確認トークンを抽出
                    import re
                    confirm_match = re.search(r'confirm=([^&]+)', response.text)
                    if confirm_match:
                        confirm_token = confirm_match.group(1)
                        download_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm_token}"
                        response = requests.get(download_url, stream=True)
                
                if response.status_code == 200:
                    if output_path:
                        output_file = Path(output_path)
                    else:
                        output_file = Path("temp_downloaded.pdf")
                    
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(output_file, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    logger.info(f"共有リンクからダウンロード成功: {output_file}")
                    return str(output_file)
        except Exception as e:
            logger.warning(f"共有リンクからのダウンロードに失敗: {e}")
        
        # APIを使用したダウンロードを試みる
        if not self.google_drive or not self.google_drive.is_available():
            logger.error("Google Drive統合が利用できません")
            return None
        
        try:
            # ファイルIDを抽出
            file_id = self._extract_file_id_from_url(file_url)
            if not file_id:
                logger.error("ファイルIDを抽出できませんでした")
                return None
            
            # ダウンロード
            downloaded_path = self.google_drive.download_file(
                file_id=file_id,
                output_path=output_path
            )
            
            return downloaded_path
            
        except Exception as e:
            logger.error(f"Google Drive APIからのダウンロードエラー: {e}", exc_info=True)
            return None
    
    def _extract_file_id_from_url(self, url: str) -> Optional[str]:
        """
        Google Drive URLからファイルIDを抽出
        
        Args:
            url: Google Drive URL
            
        Returns:
            ファイルID
        """
        if "/file/d/" in url:
            return url.split("/file/d/")[1].split("/")[0]
        elif "id=" in url:
            return url.split("id=")[1].split("&")[0]
        elif len(url) == 33 and url.isalnum():
            # 直接ファイルIDの場合
            return url
        return None
    
    def extract_tables_with_pdfplumber(self, pdf_path: str) -> List[pd.DataFrame]:
        """
        pdfplumberを使用してPDFからテーブルを抽出
        
        Args:
            pdf_path: PDFファイルのパス
            
        Returns:
            抽出されたテーブルのリスト
        """
        if not PDFPLUMBER_AVAILABLE:
            logger.error("pdfplumberが利用できません")
            return []
        
        tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    for table_num, table in enumerate(page_tables, 1):
                        if table:
                            # テーブルをDataFrameに変換
                            df = pd.DataFrame(table[1:], columns=table[0] if table else None)
                            df.attrs['page'] = page_num
                            df.attrs['table_num'] = table_num
                            tables.append(df)
                            logger.info(f"ページ {page_num} からテーブル {table_num} を抽出: {len(df)}行 × {len(df.columns)}列")
        except Exception as e:
            logger.error(f"pdfplumberでのテーブル抽出エラー: {e}", exc_info=True)
        
        return tables
    
    def extract_tables_with_tabula(self, pdf_path: str) -> List[pd.DataFrame]:
        """
        tabula-pyを使用してPDFからテーブルを抽出
        
        Args:
            pdf_path: PDFファイルのパス
            
        Returns:
            抽出されたテーブルのリスト
        """
        if not TABULA_AVAILABLE:
            logger.error("tabula-pyが利用できません")
            return []
        
        tables = []
        try:
            # すべてのページからテーブルを抽出
            dfs = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
            for i, df in enumerate(dfs, 1):
                if not df.empty:
                    df.attrs['table_num'] = i
                    tables.append(df)
                    logger.info(f"tabulaでテーブル {i} を抽出: {len(df)}行 × {len(df.columns)}列")
        except Exception as e:
            logger.error(f"tabulaでのテーブル抽出エラー: {e}", exc_info=True)
        
        return tables
    
    def _recognize_tesseract_with_layout(self, image_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Tesseract OCRで認識（レイアウト情報付き・高精度版）"""
        try:
            import pytesseract
            from PIL import Image, ImageEnhance, ImageFilter
            import numpy as np
            
            # 画像を読み込んで前処理
            image = Image.open(image_path)
            width, height = image.size
            
            # 画像の前処理（精度向上のため）
            # 1. グレースケール化
            if image.mode != 'L':
                image = image.convert('L')
            
            # 2. コントラスト強化
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)  # コントラストを2倍に
            
            # 3. シャープネス強化
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)  # シャープネスを2倍に
            
            # 4. ノイズ除去
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            # 位置情報付きでOCR実行（日本語+英語）
            # 日本語と英語の両方を認識
            try:
                data = pytesseract.image_to_data(
                    image, 
                    output_type=pytesseract.Output.DICT,
                    lang='jpn+eng',  # 日本語と英語
                    config='--psm 6'  # 均一なテキストブロックとして認識
                )
            except Exception:
                # 日本語が利用できない場合は英語のみ
                logger.warning("日本語OCRが利用できません。英語のみで試行します...")
                data = pytesseract.image_to_data(
                    image, 
                    output_type=pytesseract.Output.DICT,
                    config='--psm 6'
                )
            
            # テキストと位置情報を取得
            texts = []
            positions = []
            confidences = []
            
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                if text:  # 空でないテキストのみ
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    conf = data['conf'][i]
                    
                    texts.append(text)
                    positions.append({
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'center_x': x + w // 2,
                        'center_y': y + h // 2
                    })
                    confidences.append(float(conf) if conf != '-1' else 0.0)
            
            # グリッドに配置（セルサイズを計算・改善版）
            if positions:
                # セルサイズを推定（より正確に）
                heights = [p['height'] for p in positions if p['height'] > 0]
                if heights:
                    # 中央値を使用（外れ値の影響を減らす）
                    heights_sorted = sorted(heights)
                    median_height = heights_sorted[len(heights_sorted) // 2]
                    cell_height = max(int(median_height * 1.5), 15)  # より余裕を持たせる
                else:
                    cell_height = 20
                
                # 列を検出（X座標でクラスタリング・改善版）
                x_coords = [p['center_x'] for p in positions]
                if len(x_coords) > 1:
                    # X座標をソート
                    x_sorted = sorted(set(x_coords))
                    
                    # クラスタリングで列を検出
                    column_boundaries = []
                    if len(x_sorted) > 1:
                        # 間隔を計算
                        gaps = [x_sorted[i+1] - x_sorted[i] for i in range(len(x_sorted)-1)]
                        if gaps:
                            avg_gap = np.mean(gaps)
                            min_gap = avg_gap * 0.3  # 最小間隔
                            
                            # 列の境界を検出
                            current_col_start = x_sorted[0]
                            for i in range(len(x_sorted) - 1):
                                gap = x_sorted[i+1] - x_sorted[i]
                                if gap > min_gap:
                                    # 新しい列の開始
                                    column_boundaries.append((current_col_start + x_sorted[i]) // 2)
                                    current_col_start = x_sorted[i+1]
                            column_boundaries.append((current_col_start + x_sorted[-1]) // 2)
                            column_boundaries.append(x_sorted[-1] + 100)
                        else:
                            # フォールバック：等間隔で分割
                            num_cols = min(len(x_sorted), 20)  # 最大20列
                            for i in range(num_cols):
                                column_boundaries.append(x_sorted[0] + (x_sorted[-1] - x_sorted[0]) * (i + 1) / num_cols)
                    
                    # 各行をY座標でソート
                    rows = {}
                    for i, pos in enumerate(positions):
                        row_y = pos['center_y'] // cell_height
                        if row_y not in rows:
                            rows[row_y] = []
                        rows[row_y].append((i, pos))
                    
                    # グリッドデータを作成
                    grid_data = []
                    for row_y in sorted(rows.keys()):
                        row_items = rows[row_y]
                        # X座標でソート
                        row_items.sort(key=lambda x: x[1]['center_x'])
                        
                        # 列に配置
                        row = [''] * len(column_boundaries)
                        for idx, pos in row_items:
                            # どの列に属するか判定
                            col_idx = 0
                            for j, boundary in enumerate(column_boundaries):
                                if pos['center_x'] < boundary:
                                    col_idx = j
                                    break
                            else:
                                col_idx = len(column_boundaries) - 1
                            
                            # 既にセルにデータがある場合は結合
                            if row[col_idx]:
                                row[col_idx] += ' ' + texts[idx]
                            else:
                                row[col_idx] = texts[idx]
                        
                        grid_data.append(row)
                    
                    return {
                        "provider": "tesseract",
                        "text": '\n'.join(texts),  # 元のテキストも保持
                        "grid_data": grid_data,  # グリッド形式のデータ
                        "confidence": np.mean(confidences) if confidences else 0.0,
                        "raw_data": data
                    }
            
            # グリッド化できない場合は通常のテキスト
            text = pytesseract.image_to_string(image, **kwargs)
            return {
                "provider": "tesseract",
                "text": text.strip(),
                "grid_data": None,
                "confidence": self._calculate_confidence(data) if 'conf' in data else 0.0,
                "raw_data": data
            }
        except Exception as e:
            logger.error(f"Tesseract OCR（レイアウト付き）エラー: {e}")
            return None
    
    def _process_single_page(
        self,
        doc: Any,
        page_num: int,
        selected_provider: str,
        available_providers: List[str],
        zoom: float = 6.0
    ) -> Tuple[int, Optional[Dict[str, Any]]]:
        """単一ページを処理（並列処理用）"""
        try:
            page = doc[page_num]
            actual_page_num = page_num + 1
            
            # ページを画像に変換
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            temp_image_path = f"temp_page_{actual_page_num}_{os.getpid()}.png"
            pix.save(temp_image_path, output="png")
            
            # OCRで認識
            ocr_results = []
            providers_to_try = [selected_provider]
            
            if selected_provider != "paddleocr" and "paddleocr" in available_providers:
                providers_to_try.append("paddleocr")
            if selected_provider != "easyocr" and "easyocr" in available_providers:
                providers_to_try.append("easyocr")
            if selected_provider != "tesseract" and "tesseract" in available_providers:
                providers_to_try.append("tesseract")
            
            best_result = None
            best_score = -1e9
            
            for provider in providers_to_try:
                try:
                    if provider == "tesseract":
                        result = self.ocr.recognize(
                            temp_image_path,
                            provider="tesseract",
                            layout=True,
                            auto=True,
                            lang="jpn+eng",
                            max_cols=80,
                            psm_list=[6, 4, 11, 1, 3, 12, 13],
                            use_gridlines=True,
                        )
                    elif provider in ["easyocr", "paddleocr"]:
                        def _env_true(name: str, default: str = "0") -> bool:
                            v = (os.getenv(name, default) or "").strip().lower()
                            return v in ("1", "true", "yes", "y", "on")
                        
                        global_gpu = _env_true("MANA_OCR_USE_GPU", "1")
                        engine_gpu = (
                            _env_true("MANA_PADDLEOCR_USE_GPU", "1") if provider == "paddleocr"
                            else _env_true("MANA_EASYOCR_USE_GPU", "0")
                        )
                        
                        use_gpu = False
                        if global_gpu and engine_gpu:
                            try:
                                import torch
                                use_gpu = bool(torch.cuda.is_available())
                            except Exception:
                                use_gpu = False
                        
                        try:
                            result = self.ocr.recognize(
                                temp_image_path,
                                provider=provider,
                                layout=True,
                                lang="ja" if provider == "easyocr" else "japan",
                                gpu=use_gpu,
                            )
                            if result is None:
                                continue
                        except (MemoryError, OSError, RuntimeError):
                            continue
                    else:
                        result = self.ocr.recognize(temp_image_path, provider=provider)
                    
                    if result and result.get('text') and result.get('text').strip():
                        ocr_results.append(result)
                        conf = result.get('confidence', 0.0)
                        text_len = len(result.get('text', ''))
                        jp_chars = len(re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]", result.get('text', '')))
                        score = conf * 0.5 + min(text_len / 1000.0, 1.0) * 0.3 + min(jp_chars / max(text_len, 1), 1.0) * 0.2
                        
                        if score > best_score:
                            best_score = score
                            best_result = result
                except Exception:
                    continue
            
            # 最良の結果を選択
            ocr_result = best_result
            if ocr_result and len(ocr_results) > 1:
                best_score = -1e9
                best_result_merged = ocr_result
                
                for result in ocr_results:
                    if not result:
                        continue
                    grid = result.get('grid_data')
                    if not grid:
                        continue
                    
                    mojibake_count = 0
                    total_chars = 0
                    for row in grid:
                        for cell in row:
                            if cell:
                                cell_str = str(cell).strip()
                                if cell_str:
                                    total_chars += len(cell_str)
                                    mojibake_count += cell_str.count('')
                    
                    if total_chars < 100:
                        continue
                    
                    mojibake_ratio = mojibake_count / max(total_chars, 1)
                    score = total_chars * 0.6 - mojibake_count * 10 - mojibake_ratio * 1000
                    
                    if score > best_score:
                        best_score = score
                        best_result_merged = result
                
                ocr_result = best_result_merged
            
            # 一時ファイルを削除
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
            
            return (page_num, {
                'page_num': actual_page_num,
                'text': ocr_result.get('text', '') if ocr_result else '',
                'grid_data': ocr_result.get('grid_data') if ocr_result else None,
                'provider': ocr_result.get('provider', selected_provider) if ocr_result else None
            })
        except Exception as e:
            logger.error(f"ページ {page_num + 1} 処理エラー: {e}")
            return (page_num, None)
    
    def _process_pages_parallel(
        self,
        doc: Any,
        start: int,
        end: int,
        selected_provider: str,
        available_providers: List[str],
        max_workers: int
    ) -> Dict[int, Dict[str, Any]]:
        """複数ページを並列処理"""
        page_results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self._process_single_page,
                    doc,
                    page_num,
                    selected_provider,
                    available_providers
                ): page_num
                for page_num in range(start, end)
            }
            
            completed = 0
            total = len(futures)
            
            for future in as_completed(futures):
                page_num, result = future.result()
                if result:
                    page_results[page_num] = result
                    completed += 1
                    logger.info(f"✓ ページ {result['page_num']} 完了 ({completed}/{total})")
                else:
                    completed += 1
                    logger.warning(f"⚠ ページ {page_num + 1} 失敗 ({completed}/{total})")
        
        return page_results
    
    def extract_text(
        self,
        pdf_path: str,
        max_pages: Optional[int] = None,
        start_page: int = 0,
    ) -> str:
        """
        PDFからテキストを抽出
        
        Args:
            pdf_path: PDFファイルのパス
            
        Returns:
            抽出されたテキスト
        """
        text = ""
        
        # まずpdfplumberでテキスト抽出を試みる
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n\n"
                if text.strip():
                    logger.info("pdfplumberでテキスト抽出成功")
                    return text
            except Exception as e:
                logger.warning(f"pdfplumberでのテキスト抽出エラー: {e}")
        
        # PyMuPDFを使用してテキスト抽出を試みる
        if PYMUPDF_AVAILABLE:
            try:
                logger.info("PyMuPDFでテキスト抽出を試みます...")
                doc = fitz.open(pdf_path)
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    page_text = page.get_text()
                    if page_text:
                        text += f"=== ページ {page_num + 1} ===\n{page_text}\n\n"
                doc.close()
                if text.strip():
                    logger.info("PyMuPDFでテキスト抽出成功")
                    return text
            except Exception as e:
                logger.warning(f"PyMuPDFでのテキスト抽出エラー: {e}")
        
        # OCRを使用してテキスト抽出を試みる（画像ベースのPDFの場合）
        if self.ocr:
            try:
                logger.info("OCRを使用してテキスト抽出を試みます...")
                
                # ページデータをリセット
                self.page_data = []
                
                # 利用可能なOCRプロバイダーを確認（AIベースを優先）
                available_providers = self.ocr.get_available_providers()
                logger.info(f"利用可能なOCRプロバイダー: {available_providers}")
                
                # プロバイダーの優先順位（日本語に強い順）
                # Tesseractを優先（EasyOCRは不安定なため一旦スキップ）
                provider_priority = ["tesseract", "paddleocr", "easyocr", "amazon", "google", "microsoft"]
                selected_provider = None
                for provider in provider_priority:
                    if provider in available_providers:
                        selected_provider = provider
                        if provider in ["tesseract", "easyocr", "paddleocr"]:
                            logger.info(f"📄 ローカルOCR '{selected_provider}' を使用します（日本語対応）")
                        else:
                            logger.info(f"✨ AIベースOCR '{selected_provider}' を使用します")
                        break
                
                if not selected_provider:
                    logger.warning("利用可能なOCRプロバイダーがありません")
                    logger.info("💡 OCRエンジンをインストールするには:")
                    logger.info("   Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")
                    logger.info("   EasyOCR: pip install easyocr")
                    logger.info("   PaddleOCR: pip install paddlepaddle paddleocr")
                    return text
                
                # PyMuPDFで画像に変換
                if PYMUPDF_AVAILABLE:
                    doc = fitz.open(pdf_path)
                    doc_pages = len(doc)
                    start = max(int(start_page or 0), 0)
                    start = min(start, max(doc_pages - 1, 0)) if doc_pages else 0
                    end = doc_pages
                    if max_pages is not None:
                        end = min(doc_pages, start + int(max_pages))
                    total_target = max(end - start, 0)
                    
                    # 並列処理の設定（環境変数で制御可能）
                    use_parallel = os.getenv("MANA_OCR_PARALLEL", "1").strip().lower() in ("1", "true", "yes", "y", "on")
                    max_workers = int(os.getenv("MANA_OCR_MAX_WORKERS", "0")) or min(4, multiprocessing.cpu_count(), total_target)
                    
                    # GPU使用時は並列数を制限（メモリ使用量を考慮）
                    try:
                        import torch
                        if torch.cuda.is_available():
                            max_workers = min(max_workers, 2)  # GPU使用時は最大2並列
                            logger.info(f"GPU検出: 並列数を{max_workers}に制限します")
                    except Exception:
                        pass
                    
                    if use_parallel and total_target > 1:
                        logger.info(f"並列処理モード: {max_workers}並列で{total_target}ページを処理します")
                        page_results = self._process_pages_parallel(
                            doc, start, end, selected_provider, available_providers, max_workers
                        )
                        # 結果を順番に処理
                        for idx, (page_num, page_info) in enumerate(sorted(page_results.items()), start=1):
                            actual_page_num = page_num + 1
                    else:
                        # 順次処理（従来通り）
                        for idx, page_num in enumerate(range(start, end), start=1):
                            page = doc[page_num]
                            actual_page_num = page_num + 1
                        logger.info(f"ページ {actual_page_num}（範囲 {idx}/{total_target}）をOCR処理中...")
                        
                        # ページを画像に変換（超高解像度・精度向上）
                        # zoom 6.0 = 600 DPI相当（数字・文字の読み取り精度を最大化）
                        # 4.0 → 6.0 に向上（処理時間は増えるが精度が大幅向上）
                        zoom = 6.0
                        mat = fitz.Matrix(zoom, zoom)
                        pix = page.get_pixmap(matrix=mat, alpha=False)
                        temp_image_path = f"temp_page_{actual_page_num}.png"
                        pix.save(temp_image_path, output="png")
                        
                        # OCRで認識（複数エンジンで試行して最良の結果を選ぶ、またはマージ）
                        ocr_results = []
                        providers_to_try = [selected_provider]
                        
                        # 日本語に強いOCRエンジンも追加で試行（アンサンブル方式）
                        if selected_provider != "paddleocr" and "paddleocr" in available_providers:
                            providers_to_try.append("paddleocr")
                        if selected_provider != "easyocr" and "easyocr" in available_providers:
                            providers_to_try.append("easyocr")
                        if selected_provider != "tesseract" and "tesseract" in available_providers:
                            providers_to_try.append("tesseract")
                        
                        best_result = None
                        best_score = -1e9
                        
                        for provider in providers_to_try:
                            try:
                                # Tesseractの場合は MultiProviderOCR 側のレイアウト付き実装を使用
                                if provider == "tesseract":
                                    result = self.ocr.recognize(
                                        temp_image_path,
                                        provider="tesseract",
                                        layout=True,
                                        auto=True,  # 複数前処理×PSM探索を有効化
                                        lang="jpn+eng",
                                        max_cols=80,
                                        psm_list=[6, 4, 11, 1, 3, 12, 13],  # 表に適したPSMを追加
                                        use_gridlines=True,  # 罫線（枠線）からセル境界を推定
                                    )
                                elif provider in ["easyocr", "paddleocr"]:
                                    # EasyOCR/PaddleOCRは日本語に強い（GPU使用を試行、失敗時はCPU）
                                    # TesseractはGPU非対応なので、GPU化できるのはここだけ。
                                    #
                                    # 既定:
                                    # - PaddleOCR: GPU利用を試行（速い/安定しやすい）
                                    # - EasyOCR: 以前クラッシュ実績があるため「明示ON」時のみGPU利用
                                    #
                                    # 環境変数で切り替え:
                                    # - MANA_OCR_USE_GPU=1/0 (全体のON/OFF)
                                    # - MANA_EASYOCR_USE_GPU=1/0
                                    # - MANA_PADDLEOCR_USE_GPU=1/0
                                    def _env_true(name: str, default: str = "0") -> bool:
                                        v = (os.getenv(name, default) or "").strip().lower()
                                        return v in ("1", "true", "yes", "y", "on")

                                    global_gpu = _env_true("MANA_OCR_USE_GPU", "1")
                                    engine_gpu = (
                                        _env_true("MANA_PADDLEOCR_USE_GPU", "1") if provider == "paddleocr"
                                        else _env_true("MANA_EASYOCR_USE_GPU", "0")
                                    )

                                    use_gpu = False
                                    if global_gpu and engine_gpu:
                                        try:
                                            import torch
                                            use_gpu = bool(torch.cuda.is_available())
                                        except Exception:
                                            use_gpu = False

                                    if use_gpu:
                                        logger.info(f"  GPU有効: {provider} をGPUで実行します")
                                    else:
                                        logger.info(f"  GPU無効: {provider} はCPUで実行します")

                                    try:
                                        result = self.ocr.recognize(
                                            temp_image_path,
                                            provider=provider,
                                            layout=True,
                                            lang="ja" if provider == "easyocr" else "japan",
                                            gpu=use_gpu,
                                        )
                                        # EasyOCRがNoneを返した場合（初期化失敗）はスキップ
                                        if result is None:
                                            logger.warning(f"  {provider}: 初期化失敗、スキップ")
                                            continue
                                    except (MemoryError, OSError, RuntimeError) as critical_err:
                                        logger.error(f"  {provider}: 致命的エラー ({type(critical_err).__name__})、スキップ: {critical_err}")
                                        continue
                                else:
                                    result = self.ocr.recognize(temp_image_path, provider=provider)
                                
                                if result and result.get('text') and result.get('text').strip():
                                    ocr_results.append(result)
                                    # スコアリング（文字数、信頼度、日本語文字の割合）
                                    conf = result.get('confidence', 0.0)
                                    text_len = len(result.get('text', ''))
                                    jp_chars = len(re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]", result.get('text', '')))
                                    score = conf * 0.5 + min(text_len / 1000.0, 1.0) * 0.3 + min(jp_chars / max(text_len, 1), 1.0) * 0.2
                                    
                                    if score > best_score:
                                        best_score = score
                                        best_result = result
                                    
                                    logger.info(f"  ✓ {provider}: {len(result.get('text', ''))}文字, 信頼度: {conf:.1f}%")
                            except Exception as e:
                                error_msg = str(e)
                                logger.warning(f"プロバイダー '{provider}' でエラー: {error_msg[:100]}")
                                # 致命的エラーの場合は次のプロバイダーに進む
                                continue
                        
                        # 複数の結果をマージして文字化けを減らす
                        ocr_result = best_result
                        if ocr_result and len(ocr_results) > 1:
                            # 複数の結果がある場合、文字化けの少ない結果を優先（ただし文字数も考慮）
                            best_score = -1e9
                            best_result_merged = ocr_result
                            
                            for result in ocr_results:
                                if not result:
                                    continue
                                
                                grid = result.get('grid_data')
                                if not grid:
                                    continue
                                
                                # 文字化けの数をカウント
                                mojibake_count = 0
                                total_chars = 0
                                filled_cells = 0
                                
                                for row in grid:
                                    for cell in row:
                                        if cell:
                                            cell_str = str(cell).strip()
                                            if cell_str:
                                                filled_cells += 1
                                                total_chars += len(cell_str)
                                                mojibake_count += cell_str.count('')
                                                mojibake_count += len([c for c in cell_str if ord(c) > 0xFFFF])
                                
                                # スコアリング: 文字数が多い + 文字化けが少ない = 高スコア
                                # ただし、文字数が極端に少ない場合は除外
                                if total_chars < 100:  # 100文字未満は除外
                                    continue
                                
                                mojibake_ratio = mojibake_count / max(total_chars, 1)
                                score = total_chars * 0.6 - mojibake_count * 10 - mojibake_ratio * 1000
                                
                                if score > best_score:
                                    best_score = score
                                    best_result_merged = result
                            
                            ocr_result = best_result_merged
                            if ocr_result != best_result:
                                logger.info(f"  最良の結果を選択: {ocr_result.get('provider')} (文字数: {len(ocr_result.get('text', ''))}, スコア: {best_score:.1f})")
                        
                        if ocr_result:
                            # ページごとのデータを保存（後でシート分けに使用）
                            self.page_data.append({
                                'page_num': actual_page_num,
                                'text': ocr_result.get('text', ''),
                                'grid_data': ocr_result.get('grid_data'),
                                'provider': ocr_result.get('provider', selected_provider)
                            })
                            
                            page_text = ocr_result['text']
                            text += f"=== ページ {actual_page_num} ===\n{page_text}\n\n"
                            logger.info(f"✅ ページ {actual_page_num} からテキストを抽出しました ({len(page_text)}文字, {ocr_result.get('provider', selected_provider)})")
                        else:
                            logger.warning(f"⚠️ ページ {actual_page_num} からテキストを抽出できませんでした")
                        
                        # 一時ファイルを削除
                        import os
                        if os.path.exists(temp_image_path):
                            os.remove(temp_image_path)
                    doc.close()
                elif PDF2IMAGE_AVAILABLE:
                    images = convert_from_path(pdf_path, dpi=300)
                    logger.info(f"PDFを{len(images)}枚の画像に変換しました")
                    
                    for i, image in enumerate(images, 1):
                        logger.info(f"ページ {i}/{len(images)} をOCR処理中...")
                        temp_image_path = f"temp_page_{i}.png"
                        image.save(temp_image_path, 'PNG')
                        
                        ocr_result = self.ocr.recognize(temp_image_path)
                        if ocr_result and ocr_result.get('text'):
                            text += f"=== ページ {i} ===\n{ocr_result['text']}\n\n"
                            logger.info(f"ページ {i} からテキストを抽出しました")
                        
                        import os
                        if os.path.exists(temp_image_path):
                            os.remove(temp_image_path)
                
                if text.strip():
                    logger.info("OCRでテキスト抽出成功")
                    return text
            except Exception as e:
                logger.error(f"OCRでのテキスト抽出エラー: {e}", exc_info=True)
        
        return text
    
    def convert_to_excel(
        self,
        pdf_path: str,
        output_path: Optional[str] = None,
        method: str = "auto"
    ) -> Optional[str]:
        """
        PDFをExcelに変換
        
        Args:
            pdf_path: PDFファイルのパス
            output_path: 出力Excelファイルのパス（オプション）
            method: 抽出方法（"pdfplumber", "tabula", "auto"）
            
        Returns:
            出力ファイルのパス（成功時）、None（失敗時）
        """
        if not PANDAS_AVAILABLE:
            logger.error("pandasが利用できません")
            return None
        
        try:
            pdf_file = Path(pdf_path)
            if not pdf_file.exists():
                logger.error(f"PDFファイルが見つかりません: {pdf_path}")
                return None
            
            # 出力パスを決定
            if output_path:
                excel_file = Path(output_path)
            else:
                excel_file = pdf_file.with_suffix('.xlsx')
            
            # テーブルを抽出
            tables = []
            if method == "pdfplumber" or (method == "auto" and PDFPLUMBER_AVAILABLE):
                tables = self.extract_tables_with_pdfplumber(str(pdf_file))
            
            if not tables and (method == "tabula" or (method == "auto" and TABULA_AVAILABLE)):
                tables = self.extract_tables_with_tabula(str(pdf_file))
            
            # Excelファイルを作成（追記モード対応）
            writer_kwargs: Dict[str, Any] = {"engine": "openpyxl"}
            append_mode = bool(getattr(self, "_append_mode", False))
            if append_mode and excel_file.exists():
                writer_kwargs.update({"mode": "a", "if_sheet_exists": "replace"})

            with pd.ExcelWriter(excel_file, **writer_kwargs) as writer:
                if tables:
                    # テーブルをシートに分割
                    for i, df in enumerate(tables, 1):
                        sheet_name = f"Table_{i}"
                        if hasattr(df, 'attrs') and 'page' in df.attrs:
                            sheet_name = f"Page{df.attrs['page']}_Table{i}"
                        
                        # シート名の長さ制限（Excelは31文字まで）
                        if len(sheet_name) > 31:
                            sheet_name = sheet_name[:31]
                        
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        logger.info(f"シート '{sheet_name}' を作成: {len(df)}行 × {len(df.columns)}列")
                else:
                    # テーブルが見つからない場合はテキストを抽出
                    logger.warning("テーブルが見つかりませんでした。テキストを抽出します...")
                    # max_pages / start_page / append は main() 側で解釈して渡す
                    text = self.extract_text(
                        str(pdf_file),
                        max_pages=getattr(self, "_max_pages", None),
                        start_page=getattr(self, "_start_page", 0),
                    )
                    
                    # ページごとのデータがある場合は、各ページを別シートに
                    if hasattr(self, 'page_data') and self.page_data:
                        logger.info(f"各ページを別シートに分割します（{len(self.page_data)}ページ）...")
                        for page_info in self.page_data:
                            page_num = page_info['page_num']
                            grid_data = page_info.get('grid_data')
                            
                            # グリッドデータがある場合はそれを使用（レイアウト保持）
                            if grid_data and len(grid_data) > 0:
                                # 最大列数を取得
                                max_cols = max(len(row) for row in grid_data) if grid_data else 1
                                
                                # すべての行を同じ列数に揃える
                                normalized_grid = []
                                for row in grid_data:
                                    normalized_row = row + [''] * (max_cols - len(row))
                                    normalized_grid.append(normalized_row[:max_cols])
                                
                                df = pd.DataFrame(normalized_grid)
                                sheet_name = f"Page{page_num}"
                                if len(sheet_name) > 31:
                                    sheet_name = sheet_name[:31]
                                
                                df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                                logger.info(f"シート 'Page{page_num}' を作成: {len(df)}行 × {len(df.columns)}列（レイアウト保持）")
                            else:
                                # グリッドデータがない場合は通常のテキスト
                                page_text = page_info.get('text', '')
                                if page_text:
                                    lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                                    if lines:
                                        df = pd.DataFrame({'Text': lines})
                                        sheet_name = f"Page{page_num}"
                                        if len(sheet_name) > 31:
                                            sheet_name = sheet_name[:31]
                                        
                                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                                        logger.info(f"シート 'Page{page_num}' を作成: {len(lines)}行")
                    
                    # ページデータがない場合は従来通り
                    elif text and text.strip():
                        # テキストを行に分割してDataFrameに変換
                        lines = [line.strip() for line in text.split('\n') if line.strip()]
                        if lines:
                            df = pd.DataFrame({'Text': lines})
                            df.to_excel(writer, sheet_name='Text', index=False)
                            logger.info(f"テキストを抽出: {len(lines)}行")
                        else:
                            # 空のDataFrameでもシートを作成
                            df = pd.DataFrame({'Message': ['PDFからテキストを抽出できませんでした。']})
                            df.to_excel(writer, sheet_name='Info', index=False)
                            logger.warning("テキストが空でした")
                    else:
                        # 空のDataFrameでもシートを作成
                        df = pd.DataFrame({'Message': ['PDFからテキストを抽出できませんでした。PDFが画像のみの可能性があります。']})
                        df.to_excel(writer, sheet_name='Info', index=False)
                        logger.warning("テキストも抽出できませんでした")
            
            logger.info(f"Excelファイルを作成しました: {excel_file}")
            return str(excel_file)
            
        except Exception as e:
            logger.error(f"Excel変換エラー: {e}", exc_info=True)
            return None
    
    def convert_from_google_drive(
        self,
        file_url: str,
        output_path: Optional[str] = None,
        method: str = "auto"
    ) -> Optional[str]:
        """
        Google DriveからPDFをダウンロードしてExcelに変換
        
        Args:
            file_url: Google DriveのファイルURL
            output_path: 出力Excelファイルのパス（オプション）
            method: 抽出方法（"pdfplumber", "tabula", "auto"）
            
        Returns:
            出力ファイルのパス（成功時）、None（失敗時）
        """
        # 一時ファイルパス（並列実行やロック衝突を避けるためユニークにする）
        import uuid
        temp_pdf_path = Path(f"temp_downloaded_{uuid.uuid4().hex}.pdf")
        
        try:
            # Google Driveからダウンロード
            logger.info("Google DriveからPDFをダウンロード中...")
            downloaded_path = self.download_from_google_drive(file_url, str(temp_pdf_path))
            
            if not downloaded_path:
                logger.error("PDFのダウンロードに失敗しました")
                return None
            
            # Excelに変換
            logger.info("PDFをExcelに変換中...")
            excel_path = self.convert_to_excel(downloaded_path, output_path, method)
            
            return excel_path
            
        finally:
            # 一時ファイルを削除
            if temp_pdf_path.exists():
                try:
                    temp_pdf_path.unlink()
                    logger.debug("一時ファイルを削除しました")
                except PermissionError:
                    # Windowsで別プロセスが一時的に掴むことがあるため、削除失敗は無視
                    logger.warning("一時ファイルがロック中のため削除できませんでした（無視）")


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("使用方法: python pdf_to_excel_converter.py <PDFファイルパスまたはGoogle Drive URL> [出力パス]")
        print("例: python pdf_to_excel_converter.py file.pdf")
        print("例: python pdf_to_excel_converter.py https://drive.google.com/file/d/... output.xlsx")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    max_pages = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else None
    start_page = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 0
    append_flag = (sys.argv[5].lower() if len(sys.argv) > 5 else "") in ("a", "append", "true", "1", "yes")
    
    # Google Drive統合を初期化（URLの場合）
    google_drive = None
    if "drive.google.com" in input_path or input_path.startswith("http"):
        try:
            google_drive = GoogleDriveIntegration()
            if not google_drive.is_available():
                print("警告: Google Drive統合が利用できません。ローカルファイルとして処理します。")
        except Exception as e:
            print(f"警告: Google Drive統合の初期化に失敗: {e}")
    
    converter = PDFToExcelConverter(google_drive=google_drive)
    converter._max_pages = max_pages
    converter._start_page = start_page
    converter._append_mode = append_flag
    
    # 依存関係をチェック
    deps = converter.check_dependencies()
    if not deps["pandas"]:
        print("エラー: pandasがインストールされていません。")
        print("インストール: pip install pandas openpyxl")
        sys.exit(1)
    
    if not deps["pdfplumber"] and not deps["tabula"]:
        print("警告: PDF処理ライブラリがインストールされていません。")
        print("インストール: pip install pdfplumber")
        print("または: pip install tabula-py")
    
    # 変換を実行
    if "drive.google.com" in input_path or input_path.startswith("http"):
        print(f"Google Driveからダウンロードして変換中: {input_path}")
        result = converter.convert_from_google_drive(input_path, output_path)
    else:
        print(f"PDFをExcelに変換中: {input_path}")
        result = converter.convert_to_excel(input_path, output_path)
    
    if result:
        print(f"\n✓ 変換完了: {result}")
    else:
        print("\n✗ 変換に失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
