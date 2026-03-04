#!/usr/bin/env python3
"""
サンプルテンプレート生成スクリプト
OpenCVで一般的なUIパターンを生成
"""

import cv2
import numpy as np
from pathlib import Path
import json

def create_button_template(text, width=80, height=30, lang='ja'):
    """
    テキストボタンのテンプレートを生成
    
    Args:
        text: ボタンテキスト
        width: 幅
        height: 高さ
        lang: 言語
    """
    # 背景（グレー）
    img = np.ones((height, width, 3), dtype=np.uint8) * 240
    
    # ボーダー
    cv2.rectangle(img, (0, 0), (width-1, height-1), (180, 180, 180), 1)
    
    # テキスト（中央）
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    thickness = 1
    
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    text_x = (width - text_size[0]) // 2
    text_y = (height + text_size[1]) // 2
    
    cv2.putText(img, text, (text_x, text_y), font, font_scale, (0, 0, 0), thickness)
    
    return img


def create_icon_template(shape='x', size=30):
    """
    アイコンテンプレートを生成
    
    Args:
        shape: 'x', 'menu', 'search', etc.
        size: サイズ
    """
    img = np.ones((size, size, 3), dtype=np.uint8) * 255
    
    if shape == 'x':
        # ×マーク
        cv2.line(img, (5, 5), (size-5, size-5), (100, 100, 100), 2)
        cv2.line(img, (size-5, 5), (5, size-5), (100, 100, 100), 2)
    
    elif shape == 'menu':
        # ≡メニュー
        for i in range(3):
            y = 8 + i * 8
            cv2.line(img, (5, y), (size-5, y), (100, 100, 100), 2)
    
    elif shape == 'search':
        # 🔍虫眼鏡
        cv2.circle(img, (size//2-3, size//2-3), 8, (100, 100, 100), 2)
        cv2.line(img, (size//2+4, size//2+4), (size-5, size-5), (100, 100, 100), 2)
    
    elif shape == 'home':
        # 🏠家
        points = np.array([[size//2, 5], [size-5, size//2], [size-8, size//2], 
                          [size-8, size-5], [8, size-5], [8, size//2], [5, size//2]], np.int32)
        cv2.polylines(img, [points], True, (100, 100, 100), 2)
    
    return img


def generate_sample_templates():
    """サンプルテンプレートを生成"""
    templates_dir = Path("/root/manaos_computer_use/templates")
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    print("🎨 Generating sample templates...")
    print("=" * 60)
    
    # ボタンテンプレート
    buttons = [
        ("save_button_ja", "保存", 80, 30, 'ja'),
        ("ok_button", "OK", 60, 30, 'en'),
        ("cancel_button_ja", "キャンセル", 90, 30, 'ja'),
        ("save_button_en", "Save", 70, 30, 'en'),
        ("cancel_button_en", "Cancel", 80, 30, 'en'),
        ("open_button_ja", "開く", 70, 30, 'ja'),
        ("close_button_ja", "閉じる", 80, 30, 'ja'),
        ("next_button_ja", "次へ", 70, 30, 'ja'),
        ("back_button_ja", "戻る", 70, 30, 'ja'),
        ("apply_button_ja", "適用", 70, 30, 'ja'),
    ]
    
    for name, text, w, h, lang in buttons:
        img = create_button_template(text, w, h, lang)
        filepath = templates_dir / f"{name}.png"
        cv2.imwrite(str(filepath), img)
        print(f"✅ Created: {name}.png ({text})")
    
    # アイコンテンプレート
    icons = [
        ("close_x", 'x', 30),
        ("menu_icon", 'menu', 25),
        ("search_icon", 'search', 25),
        ("home_icon", 'home', 25),
    ]
    
    for name, shape, size in icons:
        img = create_icon_template(shape, size)
        filepath = templates_dir / f"{name}.png"
        cv2.imwrite(str(filepath), img)
        print(f"✅ Created: {name}.png (icon)")
    
    # メタデータ保存
    metadata = {
        "generated_at": str(datetime.now()),
        "note": "These are SAMPLE templates. For production, capture actual UI elements.",
        "count": len(buttons) + len(icons),
        "recommendation": "Replace with real screenshots from target applications"
    }
    
    metadata_file = templates_dir / "SAMPLE_TEMPLATES.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print("=" * 60)
    print(f"✅ Generated {len(buttons) + len(icons)} sample templates")
    print(f"📁 Location: {templates_dir}")
    print("\n⚠️  NOTE: これはサンプルです。本番環境では実際のUIから作成してください。")
    print("         詳細: templates/README_TEMPLATE_CREATION.md")


if __name__ == "__main__":
    from datetime import datetime
    generate_sample_templates()

