#!/usr/bin/env python3
"""
ManaOS Computer Use System - YOLO UI Detector (準備版)
YOLOv8を使ったUI要素検出（将来実装用の基盤）
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class YOLOUIDetector:
    """
    YOLO UI要素検出器（準備版）
    
    現状: 基盤のみ実装
    将来: YOLOv8で以下を自動検出
      - ボタン
      - テキストボックス
      - チェックボックス
      - ドロップダウン
      - メニュー項目
    """
    
    UI_CLASSES = [
        "button",
        "textbox",
        "checkbox",
        "dropdown",
        "menu",
        "icon",
        "dialog",
        "tab"
    ]
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Args:
            model_path: YOLOモデルのパス（Noneの場合は未使用）
        """
        self.model_path = model_path
        self.model = None
        self.enabled = False
        
        if model_path and Path(model_path).exists():
            self._load_model()
    
    def _load_model(self) -> None:
        """YOLOモデルを読み込み"""
        try:
            from ultralytics import YOLO
            
            self.model = YOLO(self.model_path)
            self.enabled = True
            logger.info(f"✅ YOLO model loaded: {self.model_path}")
        
        except ImportError:
            logger.warning("ultralytics not installed. Install with: pip install ultralytics")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
    
    def detect_ui_elements(
        self,
        screenshot_path: str,
        confidence_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        UI要素を検出
        
        Args:
            screenshot_path: スクリーンショット
            confidence_threshold: 確信度閾値
        
        Returns:
            List[Dict]: 検出されたUI要素のリスト
        """
        if not self.enabled:
            logger.debug("YOLO detector not enabled")
            return []
        
        try:
            # YOLO推論
            results = self.model(screenshot_path, conf=confidence_threshold)
            
            detections = []
            
            for result in results:
                boxes = result.boxes
                
                for box in boxes:
                    # バウンディングボックス
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    
                    # 中心座標
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    
                    # クラス名
                    class_id = int(box.cls[0])
                    class_name = self.UI_CLASSES[class_id] if class_id < len(self.UI_CLASSES) else "unknown"
                    
                    # 確信度
                    confidence = float(box.conf[0])
                    
                    detections.append({
                        "class": class_name,
                        "confidence": confidence,
                        "x": center_x,
                        "y": center_y,
                        "bbox": {
                            "x1": int(x1),
                            "y1": int(y1),
                            "x2": int(x2),
                            "y2": int(y2)
                        }
                    })
            
            logger.info(f"Detected {len(detections)} UI elements")
            return detections
        
        except Exception as e:
            logger.error(f"YOLO detection failed: {e}")
            return []
    
    def find_element_by_class(
        self,
        screenshot_path: str,
        element_class: str,
        confidence_threshold: float = 0.5
    ) -> Optional[Dict[str, Any]]:
        """
        特定クラスのUI要素を検索
        
        Args:
            screenshot_path: スクリーンショット
            element_class: 要素クラス（例: "button"）
            confidence_threshold: 確信度閾値
        
        Returns:
            Dict: 最も確信度が高い要素 or None
        """
        detections = self.detect_ui_elements(screenshot_path, confidence_threshold)
        
        # 指定クラスでフィルタ
        filtered = [d for d in detections if d['class'] == element_class]
        
        if not filtered:
            return None
        
        # 確信度でソート
        filtered.sort(key=lambda x: x['confidence'], reverse=True)
        
        return filtered[0]
    
    @staticmethod
    def get_installation_guide() -> str:
        """インストールガイド"""
        return """
# YOLO UI Detector セットアップ

## 1. Ultralytics インストール
pip install ultralytics

## 2. モデルダウンロード（初回のみ）
# YOLOv8n（軽量）
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

## 3. カスタムモデル訓練（推奨）
# UI要素のデータセットでfine-tuning
# 詳細: https://docs.ultralytics.com/modes/train/

## 4. 使用例
from yolo_detector import YOLOUIDetector

detector = YOLOUIDetector(model_path="yolov8n.pt")
elements = detector.detect_ui_elements("screenshot.png")

for elem in elements:
    print(f"{elem['class']}: ({elem['x']}, {elem['y']}) - {elem['confidence']:.2f}")
"""


# ===== テスト用 =====

if __name__ == "__main__":
    print("🤖 YOLO UI Detector - セットアップガイド")
    print("=" * 60)
    print(YOLOUIDetector.get_installation_guide())
    
    print("\n📦 Current status:")
    detector = YOLOUIDetector()
    
    if detector.enabled:
        print("✅ YOLO enabled")
    else:
        print("⚠️  YOLO not available (install ultralytics)")
        print("   pip install ultralytics")

