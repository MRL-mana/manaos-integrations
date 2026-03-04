#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
画像生成テンプレテスト
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from file_secretary_image_templates import FileSecretaryImageTemplates

def main():
    print("=== 画像生成テンプレテスト ===\n")
    
    # 画像生成テンプレ初期化
    print("画像生成テンプレ初期化中...")
    templates = FileSecretaryImageTemplates()
    
    if not templates.comfyui_integration or not templates.comfyui_integration.is_available():
        print("⚠️ ComfyUI統合が利用できません")
        print("   設定が必要:")
        print("   - ComfyUIの起動（デフォルト: http://127.0.0.1:8188）")
        print("   - COMFYUI_URL環境変数（オプション）")
        return
    
    print("✅ ComfyUI統合利用可能\n")
    
    # クーポンテンプレート確認
    print("利用可能なクーポンテンプレート:")
    for coupon_type, template in templates.COUPON_TEMPLATES.items():
        print(f"\n  {coupon_type}:")
        print(f"    プロンプト: {template['prompt'][:50]}...")
        print(f"    サイズ: {template['width']}x{template['height']}")
    
    # クーポン生成テスト（実際には生成しない、設定確認のみ）
    print("\nクーポン生成テスト（設定確認）:")
    for coupon_type in templates.COUPON_TEMPLATES.keys():
        print(f"  {coupon_type}: テンプレート準備完了")
    
    print("\n⚠️ 実際の画像生成はComfyUIが起動している必要があります")
    print("   テスト実行: templates.generate_coupon('洗車')")


































