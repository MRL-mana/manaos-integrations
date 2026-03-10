# -*- coding: utf-8 -*-
"""LoRA訓練用データセット準備スクリプト（顔検出・切り抜き）"""

import os
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import List, Tuple, Optional
import shutil

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("警告: face_recognitionがインストールされていません。OpenCVのHaar Cascadeを使用します。")
    print("face_recognitionを使用する場合: pip install face-recognition")

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

class FaceExtractor:
    """顔検出・切り抜きクラス"""
    
    def __init__(self, method: str = "auto", face_margin: float = 0.3):
        """
        Args:
            method: 検出方法 ("face_recognition", "mediapipe", "opencv", "auto")
            face_margin: 顔の周りの余白（0.3 = 30%）
        """
        self.face_margin = face_margin
        self.method = method
        
        # 使用可能な方法を選択
        if method == "auto":
            if FACE_RECOGNITION_AVAILABLE:
                self.method = "face_recognition"
            elif MEDIAPIPE_AVAILABLE:
                self.method = "mediapipe"
            else:
                self.method = "opencv"
        
        # OpenCVのHaar Cascadeを読み込み（フォールバック用）
        if self.method == "opencv":
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if self.face_cascade.empty():
                raise ValueError("OpenCVの顔検出モデルが読み込めませんでした")
        
        # MediaPipe初期化
        if self.method == "mediapipe":
            self.mp_face_detection = mp.solutions.face_detection  # type: ignore[possibly-unbound]
            self.face_detection = self.mp_face_detection.FaceDetection(
                model_selection=1,  # 0=short-range, 1=full-range
                min_detection_confidence=0.5
            )
        
        print(f"顔検出方法: {self.method}")
    
    def detect_face_face_recognition(self, image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """face_recognitionを使用した顔検出"""
        # RGBに変換（face_recognitionはRGBを想定）
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 顔の位置を検出
        face_locations = face_recognition.face_locations(rgb_image, model="hog")  # type: ignore[possibly-unbound]
        
        if not face_locations:
            return None
        
        # 最初の顔を返す（複数顔の場合は最大のものを選択）
        top, right, bottom, left = face_locations[0]
        
        # 最大の顔を選択
        if len(face_locations) > 1:
            areas = [(b - t) * (r - l) for t, r, b, l in face_locations]
            max_idx = areas.index(max(areas))
            top, right, bottom, left = face_locations[max_idx]
        
        return (left, top, right, bottom)
    
    def detect_face_mediapipe(self, image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """MediaPipeを使用した顔検出"""
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(rgb_image)
        
        if not results.detections:
            return None
        
        # 最初の検出結果を使用（複数顔の場合は最大のものを選択）
        h, w = image.shape[:2]
        detections = results.detections
        
        if len(detections) > 1:
            # 最大の顔を選択
            areas = []
            for detection in detections:
                bbox = detection.location_data.relative_bounding_box
                area = bbox.width * bbox.height
                areas.append(area)
            max_idx = areas.index(max(areas))
            detection = detections[max_idx]
        else:
            detection = detections[0]
        
        bbox = detection.location_data.relative_bounding_box
        left = int(bbox.xmin * w)
        top = int(bbox.ymin * h)
        right = int((bbox.xmin + bbox.width) * w)
        bottom = int((bbox.ymin + bbox.height) * h)
        
        return (left, top, right, bottom)
    
    def detect_face_opencv(self, image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """OpenCVのHaar Cascadeを使用した顔検出"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        if len(faces) == 0:
            return None
        
        # 最大の顔を選択
        if len(faces) > 1:
            areas = [w * h for x, y, w, h in faces]
            max_idx = areas.index(max(areas))
            x, y, w, h = faces[max_idx]
        else:
            x, y, w, h = faces[0]
        
        return (x, y, x + w, y + h)
    
    def extract_face(self, image_path: str) -> Optional[Image.Image]:
        """画像から顔を検出して切り抜き"""
        # 画像を読み込み
        image = cv2.imread(image_path)
        if image is None:
            print(f"  画像を読み込めませんでした: {image_path}")
            return None
        
        # 顔を検出
        if self.method == "face_recognition":
            face_box = self.detect_face_face_recognition(image)
        elif self.method == "mediapipe":
            face_box = self.detect_face_mediapipe(image)
        else:  # opencv
            face_box = self.detect_face_opencv(image)
        
        if face_box is None:
            print(f"  顔を検出できませんでした: {image_path}")
            return None
        
        left, top, right, bottom = face_box
        
        # 余白を追加
        face_width = right - left
        face_height = bottom - top
        margin_x = int(face_width * self.face_margin)
        margin_y = int(face_height * self.face_margin)
        
        # 画像の境界を考慮
        h, w = image.shape[:2]
        crop_left = max(0, left - margin_x)
        crop_top = max(0, top - margin_y)
        crop_right = min(w, right + margin_x)
        crop_bottom = min(h, bottom + margin_y)
        
        # 顔を切り抜き
        face_crop = image[crop_top:crop_bottom, crop_left:crop_right]
        
        # PIL Imageに変換
        face_pil = Image.fromarray(cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB))
        
        return face_pil
    
    def cleanup(self):
        """リソースのクリーンアップ"""
        if self.method == "mediapipe" and hasattr(self, 'face_detection'):
            self.face_detection.close()


def prepare_lora_dataset(
    input_dir: str,
    output_dir: str,
    target_size: Tuple[int, int] = (512, 512),
    face_margin: float = 0.3,
    detection_method: str = "auto",
    create_captions: bool = False,
    caption_text: str = "woman, portrait"
):
    """
    LoRA訓練用データセットを準備
    
    Args:
        input_dir: 入力画像ディレクトリ
        output_dir: 出力ディレクトリ
        target_size: リサイズ後のサイズ (width, height)
        face_margin: 顔の周りの余白（0.3 = 30%）
        detection_method: 検出方法 ("face_recognition", "mediapipe", "opencv", "auto")
        create_captions: キャプションファイルを作成するか
        caption_text: キャプションテキスト（各画像に同じテキストを使用）
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # 出力ディレクトリを作成
    output_path.mkdir(parents=True, exist_ok=True)
    
    # サポートされている画像拡張子
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    
    # 画像ファイルを取得
    image_files = [f for f in input_path.iterdir() 
                   if f.suffix.lower() in image_extensions]
    
    if not image_files:
        print(f"画像ファイルが見つかりませんでした: {input_dir}")
        return
    
    print(f"画像ファイル数: {len(image_files)}")
    print(f"出力先: {output_dir}")
    print(f"ターゲットサイズ: {target_size[0]}x{target_size[1]}")
    print("-" * 60)
    
    # 顔検出器を初期化
    extractor = FaceExtractor(method=detection_method, face_margin=face_margin)
    
    success_count = 0
    fail_count = 0
    
    for i, image_file in enumerate(image_files, 1):
        print(f"[{i}/{len(image_files)}] 処理中: {image_file.name}")
        
        try:
            # 顔を検出して切り抜き
            face_image = extractor.extract_face(str(image_file))
            
            if face_image is None:
                fail_count += 1
                continue
            
            # リサイズ（アスペクト比を保持してから中央切り抜き）
            face_image.thumbnail(target_size, Image.Resampling.LANCZOS)
            
            # 中央切り抜きで正方形に
            new_image = Image.new('RGB', target_size, (0, 0, 0))
            offset_x = (target_size[0] - face_image.width) // 2
            offset_y = (target_size[1] - face_image.height) // 2
            new_image.paste(face_image, (offset_x, offset_y))
            
            # 出力ファイル名（元のファイル名を使用）
            output_filename = image_file.stem + ".png"
            output_file = output_path / output_filename
            
            # 画像を保存
            new_image.save(output_file, "PNG", quality=95)
            print(f"  [OK] 保存: {output_filename}")
            success_count += 1
            
            # キャプションファイルを作成
            if create_captions:
                caption_file = output_path / f"{image_file.stem}.txt"
                with open(caption_file, 'w', encoding='utf-8') as f:
                    f.write(caption_text)
        
        except Exception as e:
            print(f"  [ERROR] エラー: {e}")
            fail_count += 1
            continue
    
    # クリーンアップ
    extractor.cleanup()
    
    print("-" * 60)
    print(f"処理完了！")
    print(f"  成功: {success_count} 枚")
    print(f"  失敗: {fail_count} 枚")
    print(f"  出力先: {output_dir}")


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="LoRA training dataset preparation tool (face detection and cropping)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "input_dir",
        type=str,
        help="Input image directory"
    )
    
    parser.add_argument(
        "output_dir",
        type=str,
        help="Output directory"
    )
    
    parser.add_argument(
        "--size",
        type=int,
        nargs=2,
        default=[512, 512],
        metavar=("WIDTH", "HEIGHT"),
        help="Target size for resizing (default: 512 512)"
    )
    
    parser.add_argument(
        "--margin",
        type=float,
        default=0.3,
        help="Margin around face (default: 0.3 = 30%%)"
    )
    
    parser.add_argument(
        "--method",
        type=str,
        choices=["auto", "face_recognition", "mediapipe", "opencv"],
        default="auto",
        help="Face detection method (default: auto)"
    )
    
    parser.add_argument(
        "--caption",
        type=str,
        default=None,
        help="Caption text (creates caption files if specified)"
    )
    
    args = parser.parse_args()
    
    # キャプション作成フラグ
    create_captions = args.caption is not None
    caption_text = args.caption or "woman, portrait"
    
    prepare_lora_dataset(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        target_size=tuple(args.size),
        face_margin=args.margin,
        detection_method=args.method,
        create_captions=create_captions,
        caption_text=caption_text
    )


if __name__ == "__main__":
    main()

