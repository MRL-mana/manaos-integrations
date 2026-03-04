#!/usr/bin/env python3
"""
ManaOS Computer Use System - Vision Hybrid Engine
OCR + Template Matching のハイブリッド検出エンジン
"""

import logging
import sys
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# 相対import（パッケージ内から使用時）
try:
    from .template_matcher import TemplateMatcher
except ImportError:
    # 絶対import（単体実行時）
    from template_matcher import TemplateMatcher

logger = logging.getLogger(__name__)


class VisionHybrid:
    """
    ハイブリッドビジョンエンジン
    
    戦略:
    1. OCR でテキストベースのUI要素を検出
    2. テンプレートマッチで正確な座標を確定
    3. 確信度スコアを統合
    """
    
    # 優先語彙とテンプレートのマッピング
    KEYWORD_TEMPLATES = {
        # 日本語
        "保存": ["save_button_ja", "save_dialog_ja"],
        "開く": ["open_button_ja", "open_dialog_ja"],
        "OK": ["ok_button", "ok_button_ja"],
        "キャンセル": ["cancel_button_ja"],
        "閉じる": ["close_button_ja", "x_button"],
        "次へ": ["next_button_ja"],
        "戻る": ["back_button_ja"],
        
        # 英語
        "Save": ["save_button", "save_button_en"],
        "Open": ["open_button", "open_button_en"],
        "Cancel": ["cancel_button", "cancel_button_en"],
        "Close": ["close_button", "x_button"],
        "Next": ["next_button"],
        "Back": ["back_button"],
        
        # 汎用UI要素
        "×": ["x_button", "close_x"],
        "▶": ["play_button"],
        "■": ["stop_button"],
        "🔍": ["search_icon"],
    }
    
    def __init__(
        self,
        template_matcher: Optional[TemplateMatcher] = None
    ):
        """
        Args:
            template_matcher: テンプレートマッチャー
        """
        self.template_matcher = template_matcher or TemplateMatcher()
    
    def find_element(
        self,
        screenshot_path: str,
        target: str,
        ocr_results: Optional[Dict[str, Any]] = None,
        confidence_threshold: float = 0.7
    ) -> Optional[Dict[str, Any]]:
        """
        UI要素を検出（ハイブリッド）
        
        Args:
            screenshot_path: スクリーンショット画像パス
            target: 検索対象（例: "保存", "OK"）
            ocr_results: OCR結果（あれば使用）
            confidence_threshold: 確信度閾値
        
        Returns:
            Dict: 検出結果 or None
        """
        results = []
        
        # 戦略1: テンプレートマッチング
        template_result = self._find_by_template(
            screenshot_path,
            target,
            confidence_threshold
        )
        if template_result:
            results.append({
                **template_result,
                "method": "template",
                "weight": 1.0  # テンプレートマッチは高信頼
            })
        
        # 戦略2: OCR + テンプレート（リージョン絞り込み）
        if ocr_results:
            ocr_result = self._find_by_ocr_region(
                screenshot_path,
                target,
                ocr_results,
                confidence_threshold
            )
            if ocr_result:
                results.append({
                    **ocr_result,
                    "method": "ocr_template",
                    "weight": 0.9
                })
        
        # 最高スコアの結果を返す
        if not results:
            logger.debug(f"Element not found: {target}")
            return None
        
        # 重み付きスコアでソート
        results.sort(
            key=lambda r: r['confidence'] * r.get('weight', 1.0),
            reverse=True
        )
        
        best = results[0]
        logger.info(
            f"Element found: {target} at ({best['x']}, {best['y']}) "
            f"[{best['method']}, confidence={best['confidence']:.3f}]"
        )
        
        return best
    
    def _find_by_template(
        self,
        screenshot_path: str,
        target: str,
        threshold: float
    ) -> Optional[Dict[str, Any]]:
        """
        テンプレートマッチングで検索
        
        Args:
            screenshot_path: スクリーンショット
            target: 検索対象
            threshold: 閾値
        
        Returns:
            Dict: 検出結果 or None
        """
        # ターゲットに対応するテンプレートを取得
        templates = self.KEYWORD_TEMPLATES.get(target, [])
        
        if not templates:
            # テンプレート名を推測
            template_name = target.lower().replace(" ", "_")
            templates = [template_name]
        
        # 各テンプレートで試行
        for template_name in templates:
            result = self.template_matcher.match_template(
                screenshot_path,
                template_name,
                threshold=threshold
            )
            
            if result and result.get('found'):
                return result
        
        return None
    
    def _find_by_ocr_region(
        self,
        screenshot_path: str,
        target: str,
        ocr_results: Dict[str, Any],
        threshold: float
    ) -> Optional[Dict[str, Any]]:
        """
        OCRでテキスト位置を特定 → その周辺でテンプレートマッチ
        
        Args:
            screenshot_path: スクリーンショット
            target: 検索対象
            ocr_results: OCR結果
            threshold: 閾値
        
        Returns:
            Dict: 検出結果 or None
        """
        # OCRボックス情報を取得
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(screenshot_path)
            data = pytesseract.image_to_data(image, lang='eng+jpn', output_type=pytesseract.Output.DICT)
            
            # ターゲットテキストを含むボックスを検索
            target_boxes = []
            for i, text in enumerate(data['text']):
                if target.lower() in text.lower():
                    x = data['left'][i]
                    y = data['top'][i]
                    w = data['width'][i]
                    h = data['height'][i]
                    
                    # 周辺領域を含める（±50px）
                    margin = 50
                    roi = (
                        max(0, x - margin),
                        max(0, y - margin),
                        w + margin * 2,
                        h + margin * 2
                    )
                    target_boxes.append(roi)
            
            # 各ROIでテンプレートマッチを試行
            for roi in target_boxes:
                result = self._find_by_template_with_roi(
                    screenshot_path,
                    target,
                    roi,
                    threshold
                )
                if result:
                    return result
        
        except Exception as e:
            logger.debug(f"OCR region detection failed: {e}")
        
        # フォールバック: 全画面でテンプレートマッチ
        return self._find_by_template(screenshot_path, target, threshold)
    
    def _find_by_template_with_roi(
        self,
        screenshot_path: str,
        target: str,
        roi: tuple,
        threshold: float
    ) -> Optional[Dict[str, Any]]:
        """ROI指定でテンプレートマッチング"""
        templates = self.KEYWORD_TEMPLATES.get(target, [])
        
        if not templates:
            template_name = target.lower().replace(" ", "_")
            templates = [template_name]
        
        for template_name in templates:
            result = self.template_matcher.match_template(
                screenshot_path,
                template_name,
                threshold=threshold,
                roi=roi
            )
            
            if result and result.get('found'):
                return result
        
        return None
    
    def find_multiple(
        self,
        screenshot_path: str,
        target: str,
        confidence_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        複数の要素を検出
        
        Args:
            screenshot_path: スクリーンショット
            target: 検索対象
            confidence_threshold: 閾値
        
        Returns:
            List[Dict]: 検出結果のリスト
        """
        templates = self.KEYWORD_TEMPLATES.get(target, [target.lower()])
        
        all_matches = []
        
        for template_name in templates:
            matches = self.template_matcher.match_multiple(
                screenshot_path,
                template_name,
                threshold=confidence_threshold
            )
            
            for match in matches:
                match['method'] = 'template'
                all_matches.append(match)
        
        # 確信度でソート
        all_matches.sort(key=lambda m: m['confidence'], reverse=True)
        
        return all_matches
    
    def create_template_from_region(
        self,
        screenshot_path: str,
        template_name: str,
        region: Tuple[int, int, int, int]
    ) -> bool:
        """
        スクリーンショットからテンプレートを作成
        
        Args:
            screenshot_path: 元画像
            template_name: テンプレート名
            region: 切り出し領域 (x, y, width, height)
        
        Returns:
            bool: 成功
        """
        return self.template_matcher.save_template(
            screenshot_path,
            template_name,
            region
        )
    
    def get_confidence_boost(
        self,
        detection_method: str,
        template_matched: bool,
        ocr_matched: bool
    ) -> float:
        """
        検出方法に基づいて確信度ブーストを計算
        
        Args:
            detection_method: 検出方法
            template_matched: テンプレートマッチ成功
            ocr_matched: OCRマッチ成功
        
        Returns:
            float: ブースト係数（1.0 = 変化なし、>1.0 = ブースト）
        """
        boost = 1.0
        
        # 両方成功 = 高信頼
        if template_matched and ocr_matched:
            boost = 1.3
        
        # テンプレートのみ = 標準
        elif template_matched:
            boost = 1.0
        
        # OCRのみ = やや低信頼
        elif ocr_matched:
            boost = 0.8
        
        return boost


# ===== テスト用 =====

if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    print("🔍 Vision Hybrid Engine - テスト")
    print("=" * 60)
    
    hybrid = VisionHybrid()
    
    # テンプレート一覧
    templates = list(hybrid.template_matcher.template_dir.glob("*.png"))
    print(f"\n📦 利用可能なテンプレート: {len(templates)}")
    
    if not templates:
        print("⚠️  テンプレートを追加してください")
        print(f"   場所: {hybrid.template_matcher.template_dir}")
        sys.exit(0)
    
    # スクリーンショットでテスト
    screenshots_dir = Path("/root/x280_gui_automation/screenshots")
    screenshots = list(screenshots_dir.glob("*.png"))[:1]
    
    if screenshots:
        screenshot = screenshots[0]
        print("\n🧪 テスト実行:")
        print(f"  Screenshot: {screenshot.name}")
        
        # テスト1: 保存ボタンを探す
        print("\n📍 Test 1: Find '保存' button")
        result = hybrid.find_element(
            str(screenshot),
            "保存",
            confidence_threshold=0.7
        )
        
        if result:
            print(f"✅ Found at ({result['x']}, {result['y']})")
            print(f"   Confidence: {result['confidence']:.3f}")
            print(f"   Method: {result.get('method')}")
        else:
            print("❌ Not found")
        
        # テスト2: 複数検出
        print("\n📍 Test 2: Find multiple 'OK' buttons")
        results = hybrid.find_multiple(
            str(screenshot),
            "OK",
            confidence_threshold=0.6
        )
        
        print(f"Found {len(results)} matches")
        for i, r in enumerate(results[:3], 1):
            print(f"  {i}. ({r['x']}, {r['y']}) - confidence: {r['confidence']:.3f}")
    
    print("\n✅ Test completed")

