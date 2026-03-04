#!/usr/bin/env python3
"""
ManaOS Computer Use System - Template Matcher
OpenCVベースのテンプレートマッチング for 高精度座標検出
"""

import cv2
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TemplateMatcher:
    """
    テンプレートマッチングエンジン
    
    OCRで大まかな位置を特定 → テンプレートマッチで正確な座標を確定
    """
    
    # マッチング手法
    METHOD_CCOEFF_NORMED = cv2.TM_CCOEFF_NORMED
    METHOD_CCORR_NORMED = cv2.TM_CCORR_NORMED
    METHOD_SQDIFF_NORMED = cv2.TM_SQDIFF_NORMED
    
    def __init__(self, template_dir: Optional[Path] = None):
        """
        Args:
            template_dir: テンプレート画像を格納するディレクトリ
        """
        self.template_dir = template_dir or Path("/root/manaos_computer_use/templates")
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # テンプレートキャッシュ
        self.template_cache: Dict[str, np.ndarray] = {}
    
    def match_template(
        self,
        screenshot_path: str,
        template_name: str,
        threshold: float = 0.8,
        method: int = None,
        roi: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        テンプレートマッチングを実行
        
        Args:
            screenshot_path: スクリーンショット画像パス
            template_name: テンプレート名（例: "save_button"）
            threshold: マッチング閾値（0.0-1.0）
            method: マッチング手法
            roi: 検索領域 (x, y, width, height)
        
        Returns:
            Dict: マッチング結果 or None
        """
        method = method or self.METHOD_CCOEFF_NORMED
        
        # 画像読み込み
        screenshot = cv2.imread(screenshot_path)
        if screenshot is None:
            logger.error(f"Failed to load screenshot: {screenshot_path}")
            return None
        
        template = self._load_template(template_name)
        if template is None:
            return None
        
        # ROI設定
        if roi:
            x, y, w, h = roi
            search_area = screenshot[y:y+h, x:x+w]
            offset_x, offset_y = x, y
        else:
            search_area = screenshot
            offset_x, offset_y = 0, 0
        
        # テンプレートマッチング実行
        result = cv2.matchTemplate(search_area, template, method)
        
        # スコアに応じて処理
        if method == self.METHOD_SQDIFF_NORMED:
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            match_val = 1.0 - min_val  # 反転
            match_loc = min_loc
        else:
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            match_val = max_val
            match_loc = max_loc
        
        # 閾値チェック
        if match_val < threshold:
            logger.debug(f"Match score too low: {match_val:.3f} < {threshold}")
            return None
        
        # テンプレートサイズ
        th, tw = template.shape[:2]
        
        # 中心座標（オフセット込み）
        center_x = match_loc[0] + tw // 2 + offset_x
        center_y = match_loc[1] + th // 2 + offset_y
        
        return {
            "found": True,
            "x": center_x,
            "y": center_y,
            "confidence": float(match_val),
            "top_left": (match_loc[0] + offset_x, match_loc[1] + offset_y),
            "bottom_right": (match_loc[0] + tw + offset_x, match_loc[1] + th + offset_y),
            "template_size": (tw, th),
            "method": method
        }
    
    def match_multiple(
        self,
        screenshot_path: str,
        template_name: str,
        threshold: float = 0.8,
        method: int = None
    ) -> List[Dict[str, Any]]:
        """
        複数のマッチを検出（同じテンプレートが複数ある場合）
        
        Args:
            screenshot_path: スクリーンショット画像パス
            template_name: テンプレート名
            threshold: マッチング閾値
            method: マッチング手法
        
        Returns:
            List[Dict]: マッチング結果のリスト
        """
        method = method or self.METHOD_CCOEFF_NORMED
        
        screenshot = cv2.imread(screenshot_path)
        if screenshot is None:
            return []
        
        template = self._load_template(template_name)
        if template is None:
            return []
        
        # テンプレートマッチング
        result = cv2.matchTemplate(screenshot, template, method)
        
        # 閾値を超えるすべての位置を取得
        if method == self.METHOD_SQDIFF_NORMED:
            locations = np.where(result <= (1.0 - threshold))
        else:
            locations = np.where(result >= threshold)
        
        matches = []
        th, tw = template.shape[:2]
        
        for pt in zip(*locations[::-1]):  # (x, y)
            x, y = pt
            confidence = result[y, x]
            
            if method == self.METHOD_SQDIFF_NORMED:
                confidence = 1.0 - confidence
            
            matches.append({
                "found": True,
                "x": int(x + tw // 2),
                "y": int(y + th // 2),
                "confidence": float(confidence),
                "top_left": (int(x), int(y)),
                "bottom_right": (int(x + tw), int(y + th)),
                "template_size": (tw, th)
            })
        
        # 確信度でソート
        matches.sort(key=lambda m: m['confidence'], reverse=True)
        
        # 重複を除去（Non-Maximum Suppression）
        matches = self._non_max_suppression(matches, overlap_threshold=0.5)
        
        return matches
    
    def _load_template(self, template_name: str) -> Optional[np.ndarray]:
        """
        テンプレート画像を読み込み（キャッシュ対応）
        
        Args:
            template_name: テンプレート名
        
        Returns:
            np.ndarray: テンプレート画像 or None
        """
        if template_name in self.template_cache:
            return self.template_cache[template_name]
        
        # ファイルパス
        template_path = self.template_dir / f"{template_name}.png"
        
        if not template_path.exists():
            logger.error(f"Template not found: {template_path}")
            return None
        
        # 画像読み込み
        template = cv2.imread(str(template_path))
        
        if template is None:
            logger.error(f"Failed to load template: {template_path}")
            return None
        
        # キャッシュに保存
        self.template_cache[template_name] = template
        
        logger.debug(f"Loaded template: {template_name} ({template.shape})")
        return template
    
    def save_template(
        self,
        screenshot_path: str,
        template_name: str,
        region: Tuple[int, int, int, int]
    ) -> bool:
        """
        スクリーンショットからテンプレートを切り出して保存
        
        Args:
            screenshot_path: 元のスクリーンショット
            template_name: テンプレート名
            region: 切り出し領域 (x, y, width, height)
        
        Returns:
            bool: 成功
        """
        screenshot = cv2.imread(screenshot_path)
        if screenshot is None:
            logger.error(f"Failed to load screenshot: {screenshot_path}")
            return False
        
        x, y, w, h = region
        template = screenshot[y:y+h, x:x+w]
        
        template_path = self.template_dir / f"{template_name}.png"
        success = cv2.imwrite(str(template_path), template)
        
        if success:
            logger.info(f"Template saved: {template_path}")
            # キャッシュクリア
            self.template_cache.pop(template_name, None)
        
        return success
    
    def _non_max_suppression(
        self,
        matches: List[Dict[str, Any]],
        overlap_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Non-Maximum Suppression（重複除去）
        
        Args:
            matches: マッチング結果リスト
            overlap_threshold: 重複判定の閾値
        
        Returns:
            List[Dict]: 重複除去後のリスト
        """
        if not matches:
            return []
        
        # 座標を numpy 配列に変換
        boxes = np.array([
            [m['top_left'][0], m['top_left'][1], 
             m['bottom_right'][0], m['bottom_right'][1]]
            for m in matches
        ])
        
        confidences = np.array([m['confidence'] for m in matches])
        
        # ソート（確信度降順）
        idxs = np.argsort(confidences)[::-1]
        
        keep = []
        
        while len(idxs) > 0:
            # 最高スコアのインデックス
            current = idxs[0]
            keep.append(current)
            
            # 残りのボックスとのIoU計算
            if len(idxs) == 1:
                break
            
            current_box = boxes[current]
            other_boxes = boxes[idxs[1:]]
            
            ious = self._compute_iou(current_box, other_boxes)
            
            # IoUが閾値以下のものを保持
            idxs = idxs[1:][ious <= overlap_threshold]
        
        return [matches[i] for i in keep]
    
    def _compute_iou(
        self,
        box: np.ndarray,
        boxes: np.ndarray
    ) -> np.ndarray:
        """
        IoU（Intersection over Union）を計算
        
        Args:
            box: 単一のボックス [x1, y1, x2, y2]
            boxes: 複数のボックス [[x1, y1, x2, y2], ...]
        
        Returns:
            np.ndarray: IoUの配列
        """
        # 交差領域
        x1 = np.maximum(box[0], boxes[:, 0])
        y1 = np.maximum(box[1], boxes[:, 1])
        x2 = np.minimum(box[2], boxes[:, 2])
        y2 = np.minimum(box[3], boxes[:, 3])
        
        intersection = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
        
        # 各ボックスの面積
        box_area = (box[2] - box[0]) * (box[3] - box[1])
        boxes_area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        
        # Union
        union = box_area + boxes_area - intersection
        
        # IoU
        iou = intersection / (union + 1e-6)
        
        return iou


# ===== テスト用 =====

if __name__ == "__main__":
    import sys
    
    print("🔍 Template Matcher - テスト")
    print("=" * 60)
    
    matcher = TemplateMatcher()
    
    # テストファイルの確認
    templates = list(matcher.template_dir.glob("*.png"))
    
    if not templates:
        print("⚠️  テンプレートが見つかりません")
        print(f"   場所: {matcher.template_dir}")
        print("   テンプレートを追加してから再実行してください。")
        sys.exit(0)
    
    print(f"\n📦 利用可能なテンプレート: {len(templates)}")
    for template in templates:
        print(f"  - {template.stem}")
    
    # スクリーンショットがあれば実際にテスト
    screenshots_dir = Path("/root/x280_gui_automation/screenshots")
    screenshots = list(screenshots_dir.glob("*.png"))[:1]
    
    if screenshots:
        print("\n🧪 テスト実行:")
        screenshot = screenshots[0]
        template = templates[0]
        
        print(f"  Screenshot: {screenshot.name}")
        print(f"  Template: {template.stem}")
        
        result = matcher.match_template(
            str(screenshot),
            template.stem,
            threshold=0.7
        )
        
        if result:
            print("\n✅ Match found!")
            print(f"   Position: ({result['x']}, {result['y']})")
            print(f"   Confidence: {result['confidence']:.3f}")
        else:
            print("\n❌ No match found")
    
    print("\n✅ Test completed")

