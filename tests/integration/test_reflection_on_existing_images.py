#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存の生成画像に対して自動反省・改善システムを実行
"""

import sys
import os
import requests
import json
from pathlib import Path
from datetime import datetime

# Windowsでのエンコーディング問題を回避
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

# 画像ディレクトリを検索
POSSIBLE_IMAGE_DIRS = [
    Path("gallery_images"),
    Path("generated_images"),
    Path("data/image_stock/generated"),
    Path("C:/ComfyUI/output"),
    Path("C:/mana_workspace/generated_images"),
]

def find_image_directories():
    """画像ディレクトリを検索"""
    found_dirs = []
    for dir_path in POSSIBLE_IMAGE_DIRS:
        if dir_path.exists() and dir_path.is_dir():
            # PNGファイルがあるか確認
            png_files = list(dir_path.glob("*.png"))
            if png_files:
                found_dirs.append((dir_path, len(png_files)))
    return found_dirs

def get_recent_images_from_filesystem(limit=5):
    """ファイルシステムから最近の画像を取得"""
    found_dirs = find_image_directories()
    
    if not found_dirs:
        print("[WARN] 画像ディレクトリが見つかりません")
        return []
    
    all_images = []
    
    for dir_path, count in found_dirs:
        print(f"[INFO] ディレクトリ発見: {dir_path} ({count}件のPNGファイル)")
        
        # PNGファイルを取得
        png_files = list(dir_path.glob("*.png"))
        
        for png_file in png_files:
            # メタデータファイルを探す
            metadata_file = dir_path / f"{png_file.name}.json"
            metadata = {}
            
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except Exception:
                    pass
            
            # ファイル情報を追加
            stat = png_file.stat()
            all_images.append({
                "filename": png_file.name,
                "path": str(png_file),
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "metadata": metadata
            })
    
    # 作成日時でソート（新しい順）
    sorted_images = sorted(
        all_images,
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )
    
    return sorted_images[:limit]

def evaluate_image(image_info):
    """画像を評価"""
    filename = image_info.get("filename")
    metadata = image_info.get("metadata", {})
    
    if not filename:
        print("[ERROR] ファイル名がありません")
        return None
    
    # 画像パスを取得
    image_path = image_info.get("path")
    if not image_path:
        # パスがない場合はファイル名から構築
        image_path = str(Path(filename))
    
    if not os.path.exists(image_path):
        print(f"[ERROR] 画像ファイルが見つかりません: {image_path}")
        return None
    
    print(f"\n{'='*60}")
    print(f"[評価開始] {filename}")
    print(f"{'='*60}")
    
    # メタデータから情報を取得
    prompt = metadata.get("prompt", "")
    negative_prompt = metadata.get("negative_prompt", "")
    model = metadata.get("model", "")
    parameters = {
        "steps": metadata.get("steps", 50),
        "guidance_scale": metadata.get("guidance_scale", 7.5),
        "width": metadata.get("width", 1024),
        "height": metadata.get("height", 1024),
        "sampler": metadata.get("sampler", "dpmpp_2m"),
        "scheduler": metadata.get("scheduler", "karras"),
        "seed": metadata.get("seed")
    }
    
    print(f"プロンプト: {prompt[:80]}...")
    print(f"モデル: {model}")
    print(f"パラメータ: steps={parameters['steps']}, size={parameters['width']}x{parameters['height']}")
    
    # 評価APIを呼び出し（APIが使えない場合は直接評価）
    try:
        # まずAPIを試す
        response = requests.post(
            "http://127.0.0.1:5559/api/reflection/evaluate",
            json={
                "image_path": image_path,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "model": model,
                "parameters": parameters,
                "auto_improve": True,
                "threshold": 0.7
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return result.get("result")
            else:
                print(f"[ERROR] 評価失敗: {result.get('error')}")
                return None
        else:
            print(f"[ERROR] HTTPエラー: {response.status_code}")
            print(f"レスポンス: {response.text[:200]}")
            # APIが使えない場合は直接評価システムを使用
            return evaluate_directly(image_path, prompt, negative_prompt, model, parameters)
            
    except Exception:
        # APIが使えない場合は直接評価システムを使用
        print("[WARN] APIが使用できません。直接評価システムを使用します...")
        return evaluate_directly(image_path, prompt, negative_prompt, model, parameters)

def evaluate_directly(image_path, prompt, negative_prompt, model, parameters):
    """直接評価システムを使用"""
    try:
        from auto_reflection_improvement import get_auto_reflection_system
        
        auto_system = get_auto_reflection_system()
        result = auto_system.process_generated_image(
            image_path=image_path,
            prompt=prompt,
            negative_prompt=negative_prompt,
            model=model,
            parameters=parameters,
            auto_improve=True,
            threshold=0.7
        )
        return result
    except Exception as e:
        print(f"[ERROR] 直接評価エラー: {e}")
        import traceback
        traceback.print_exc()
        return None

def display_evaluation_result(result):
    """評価結果を表示"""
    if not result:
        return
    
    evaluation = result.get("evaluation", {})
    improvement = result.get("improvement")
    should_regenerate = result.get("should_regenerate", False)
    
    print(f"\n{'='*60}")
    print("[評価結果]")
    print(f"{'='*60}")
    
    print(f"\n[スコア]")
    print(f"  総合スコア: {evaluation.get('overall_score', 0):.2f}")
    print(f"  身体崩れスコア: {evaluation.get('anatomy_score', 0):.2f}")
    print(f"  品質スコア: {evaluation.get('quality_score', 0):.2f}")
    print(f"  プロンプト一致度: {evaluation.get('prompt_match_score', 0):.2f}")
    
    # 問題点
    anatomy_issues = evaluation.get("anatomy_issues", [])
    quality_issues = evaluation.get("quality_issues", [])
    prompt_mismatches = evaluation.get("prompt_mismatches", [])
    
    if anatomy_issues or quality_issues or prompt_mismatches:
        print(f"\n[問題点]")
        if anatomy_issues:
            print(f"  身体崩れ関連:")
            for issue in anatomy_issues:
                print(f"    - {issue}")
        if quality_issues:
            print(f"  品質関連:")
            for issue in quality_issues:
                print(f"    - {issue}")
        if prompt_mismatches:
            print(f"  プロンプト不一致:")
            for mismatch in prompt_mismatches:
                print(f"    - {mismatch}")
    
    # 改善提案
    improvements = evaluation.get("improvements", [])
    if improvements:
        print(f"\n[改善提案]")
        for i, imp in enumerate(improvements, 1):
            print(f"  {i}. {imp}")
    
    # 改善計画
    if improvement:
        print(f"\n{'='*60}")
        print("[改善計画]")
        print(f"{'='*60}")
        print(f"改善理由: {improvement.get('reason', '')}")
        print(f"期待される改善度: {improvement.get('expected_improvement', 0):.2f}")
        
        print(f"\n[プロンプト改善]")
        print(f"  元: {improvement.get('original_prompt', '')[:80]}...")
        print(f"  改善後: {improvement.get('improved_prompt', '')[:80]}...")
        
        print(f"\n[パラメータ改善]")
        orig_params = improvement.get("original_parameters", {})
        improved_params = improvement.get("improved_parameters", {})
        
        for key in ["steps", "width", "height", "guidance_scale"]:
            orig_val = orig_params.get(key, "N/A")
            improved_val = improved_params.get(key, "N/A")
            if orig_val != improved_val:
                print(f"  {key}: {orig_val} -> {improved_val}")
        
        if should_regenerate:
            print(f"\n[再生成推奨] 改善されたパラメータで再生成することを推奨します")
    
    print(f"\n{'='*60}")

def main():
    """メイン処理"""
    print("="*60)
    print("既存画像の自動反省・改善テスト")
    print("="*60)
    
    # 最近の画像を取得
    print("\n[1] 最近の画像を取得中...")
    
    # まずAPIから取得を試みる
    images = []
    try:
        response = requests.get(f"http://127.0.0.1:5559/api/images", timeout=5)
        if response.status_code == 200:
            images = response.json()
            sorted_images = sorted(
                images,
                key=lambda x: x.get("created_at", ""),
                reverse=True
            )
            images = sorted_images[:5]
            print(f"[OK] APIから{len(images)}件の画像を取得")
    except Exception:
        print("[WARN] APIから取得できません。ファイルシステムから検索します...")
        images = get_recent_images_from_filesystem(limit=5)
    
    if not images:
        print("[ERROR] 画像が見つかりません")
        return
    
    print(f"[OK] {len(images)}件の画像を取得")
    
    # 統計情報を取得
    print("\n[2] 統計情報を取得中...")
    try:
        response = requests.get("http://127.0.0.1:5559/api/reflection/statistics", timeout=5)
        if response.status_code == 200:
            stats = response.json().get("statistics", {})
            print(f"[OK] 統計情報:")
            print(f"  総評価数: {stats.get('total_evaluations', 0)}")
            print(f"  平均スコア: {stats.get('average_score', 0):.2f}")
            print(f"  改善提案数: {stats.get('total_improvements', 0)}")
            print(f"  改善率: {stats.get('improvement_rate', 0):.2%}")
    except Exception:
        print("[WARN] 統計情報取得エラー（APIサーバーが起動していない可能性）")
    
    # 各画像を評価
    print(f"\n[3] 画像を評価中...")
    results = []
    
    for i, image_info in enumerate(images, 1):
        print(f"\n[{i}/{len(images)}] 画像を評価中...")
        result = evaluate_image(image_info)
        if result:
            results.append((image_info, result))
            display_evaluation_result(result)
    
    # サマリー
    print(f"\n{'='*60}")
    print("[サマリー]")
    print(f"{'='*60}")
    print(f"評価した画像数: {len(results)}")
    
    if results:
        avg_score = sum(
            r[1].get("evaluation", {}).get("overall_score", 0)
            for r in results
        ) / len(results)
        print(f"平均スコア: {avg_score:.2f}")
        
        improvement_count = sum(
            1 for r in results
            if r[1].get("should_regenerate", False)
        )
        print(f"改善推奨数: {improvement_count}/{len(results)}")
    
    print(f"\n{'='*60}")


