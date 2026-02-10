#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存の生成画像から学習データを蓄積
評価 → 改善提案 → 学習データ記録
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

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
            png_files = list(dir_path.glob("*.png"))
            if png_files:
                found_dirs.append((dir_path, len(png_files)))
    return found_dirs

def get_recent_images_from_filesystem(limit=200, random_sample=False):
    """ファイルシステムから最近の画像を取得"""
    found_dirs = find_image_directories()
    
    if not found_dirs:
        print("[WARN] 画像ディレクトリが見つかりません")
        return []
    
    all_images = []
    
    for dir_path, count in found_dirs:
        print(f"[INFO] ディレクトリ発見: {dir_path} ({count}件のPNGファイル)")
        
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
    
    # ランダムサンプリングの場合は、ランダムに選択
    if random_sample and len(sorted_images) > limit:
        import random
        return random.sample(sorted_images, limit)
    
    return sorted_images[:limit]

def evaluate_and_learn(image_info, auto_system):
    """画像を評価して学習データを記録"""
    filename = image_info.get("filename")
    metadata = image_info.get("metadata", {})
    image_path = image_info.get("path")
    
    if not image_path or not os.path.exists(image_path):
        print(f"[ERROR] 画像ファイルが見つかりません: {image_path}")
        return None
    
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
    
    print(f"\n{'='*60}")
    print(f"[評価・学習] {filename}")
    print(f"{'='*60}")
    print(f"プロンプト: {prompt[:80]}...")
    print(f"モデル: {model}")
    
    try:
        # 評価と改善提案を生成
        result = auto_system.process_generated_image(
            image_path=image_path,
            prompt=prompt,
            negative_prompt=negative_prompt,
            model=model,
            parameters=parameters,
            auto_improve=True,
            threshold=0.75  # 閾値を上げて、より多くの改善提案を生成
        )
        
        if not result:
            print(f"[ERROR] 評価結果がNoneです")
            return None
        
        evaluation = result.get("evaluation", {})
        improvement = result.get("improvement")
        should_regenerate = result.get("should_regenerate", False)
        
        # スコア表示
        print(f"\n[スコア]")
        print(f"  総合スコア: {evaluation.get('overall_score', 0):.2f}")
        print(f"  身体崩れスコア: {evaluation.get('anatomy_score', 0):.2f}")
        print(f"  品質スコア: {evaluation.get('quality_score', 0):.2f}")
        print(f"  プロンプト一致度: {evaluation.get('prompt_match_score', 0):.2f}")
        
        # 改善提案がある場合（またはスコアが低い場合）
        if improvement and should_regenerate:
            print(f"\n[改善提案あり] 学習データに記録します...")
            
            # 評価オブジェクトを再構築
            from auto_reflection_improvement import ImageEvaluation, ImprovementPlan
            from dataclasses import asdict
            
            image_eval = ImageEvaluation(
                image_path=image_path,
                prompt=prompt,
                negative_prompt=negative_prompt,
                model=model,
                parameters=parameters,
                overall_score=evaluation.get('overall_score', 0),
                anatomy_score=evaluation.get('anatomy_score', 0),
                quality_score=evaluation.get('quality_score', 0),
                prompt_match_score=evaluation.get('prompt_match_score', 0),
                anatomy_issues=evaluation.get('anatomy_issues', []),
                quality_issues=evaluation.get('quality_issues', []),
                prompt_mismatches=evaluation.get('prompt_mismatches', []),
                improvements=evaluation.get('improvements', [])
            )
            
            improvement_plan = ImprovementPlan(
                original_prompt=improvement.get('original_prompt', prompt),
                improved_prompt=improvement.get('improved_prompt', prompt),
                original_negative_prompt=improvement.get('original_negative_prompt', negative_prompt),
                improved_negative_prompt=improvement.get('improved_negative_prompt', negative_prompt),
                original_parameters=improvement.get('original_parameters', parameters),
                improved_parameters=improvement.get('improved_parameters', parameters),
                reason=improvement.get('reason', ''),
                expected_improvement=improvement.get('expected_improvement', 0)
            )
            
            # 学習データに記録（改善提案を記録）
            # 実際の再生成は行わないが、改善提案自体を学習データとして記録
            if not hasattr(auto_system.improver, 'learning_data'):
                auto_system.improver.learning_data = {
                    "improvement_suggestions": [],
                    "successful_prompts": [],
                    "successful_parameters": [],
                    "failed_patterns": []
                }
            
            if "improvement_suggestions" not in auto_system.improver.learning_data:
                auto_system.improver.learning_data["improvement_suggestions"] = []
            
            auto_system.improver.learning_data["improvement_suggestions"].append({
                "evaluation": asdict(image_eval),
                "improvement": asdict(improvement_plan),
                "timestamp": datetime.now().isoformat(),
                "image_path": image_path
            })
            
            print(f"[学習記録] 改善提案を学習データに記録しました")
            print(f"  改善理由: {improvement.get('reason', '')[:60]}...")
            print(f"  期待される改善度: {improvement.get('expected_improvement', 0):.2f}")
            
            return {
                "success": True,
                "evaluation": evaluation,
                "improvement": improvement,
                "learned": True
            }
        else:
            # スコアが低い場合でも、評価データを学習に活用
            score = evaluation.get('overall_score', 0)
            if score < 0.75:  # スコアが0.75未満の場合は記録
                print(f"\n[学習記録] スコアが低め（{score:.2f}）のため、評価データを記録します...")
                
                from auto_reflection_improvement import ImageEvaluation
                from dataclasses import asdict
                
                image_eval = ImageEvaluation(
                    image_path=image_path,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    model=model,
                    parameters=parameters,
                    overall_score=evaluation.get('overall_score', 0),
                    anatomy_score=evaluation.get('anatomy_score', 0),
                    quality_score=evaluation.get('quality_score', 0),
                    prompt_match_score=evaluation.get('prompt_match_score', 0),
                    anatomy_issues=evaluation.get('anatomy_issues', []),
                    quality_issues=evaluation.get('quality_issues', []),
                    prompt_mismatches=evaluation.get('prompt_mismatches', []),
                    improvements=evaluation.get('improvements', [])
                )
                
                # 低スコアパターンを記録
                if not hasattr(auto_system.improver, 'learning_data'):
                    auto_system.improver.learning_data = {
                        "improvement_suggestions": [],
                        "successful_prompts": [],
                        "successful_parameters": [],
                        "failed_patterns": [],
                        "low_score_patterns": []
                    }
                
                if "low_score_patterns" not in auto_system.improver.learning_data:
                    auto_system.improver.learning_data["low_score_patterns"] = []
                
                auto_system.improver.learning_data["low_score_patterns"].append({
                    "evaluation": asdict(image_eval),
                    "timestamp": datetime.now().isoformat(),
                    "image_path": image_path
                })
                
                print(f"[学習記録] 低スコアパターンを記録しました（スコア: {score:.2f}）")
                return {
                    "success": True,
                    "evaluation": evaluation,
                    "improvement": None,
                    "learned": True
                }
            else:
                print(f"\n[改善不要] スコアが良好です（学習データには記録しません）")
                return {
                    "success": True,
                    "evaluation": evaluation,
                    "improvement": None,
                    "learned": False
                }
            
    except Exception as e:
        print(f"[ERROR] 評価エラー: {e}")
        import traceback
        traceback.print_exc()
        # エラーが発生しても、評価データがあれば記録を試みる
        return None

def save_learning_data(auto_system):
    """学習データを保存"""
    try:
        # learning_dataが存在しない場合は初期化
        if not hasattr(auto_system.improver, 'learning_data'):
            auto_system.improver.learning_data = {
                "improvement_suggestions": [],
                "successful_prompts": [],
                "successful_parameters": [],
                "failed_patterns": []
            }
        
        learning_data = auto_system.improver.learning_data
        
        # 学習データをJSONファイルに保存
        learning_file = Path("learning_data.json")
        learning_backup = {
            "improvement_suggestions": learning_data.get("improvement_suggestions", []),
            "successful_prompts": learning_data.get("successful_prompts", []),
            "successful_parameters": learning_data.get("successful_parameters", []),
            "failed_patterns": learning_data.get("failed_patterns", []),
            "low_score_patterns": learning_data.get("low_score_patterns", []),
            "last_updated": datetime.now().isoformat()
        }
        
        with open(learning_file, 'w', encoding='utf-8') as f:
            json.dump(learning_backup, f, ensure_ascii=False, indent=2)
        
        print(f"\n[保存] 学習データを {learning_file} に保存しました")
        print(f"  改善提案数: {len(learning_backup['improvement_suggestions'])}")
        print(f"  成功パターン数: {len(learning_backup['successful_prompts'])}")
        print(f"  失敗パターン数: {len(learning_backup['failed_patterns'])}")
        print(f"  低スコアパターン数: {len(learning_backup['low_score_patterns'])}")
        
    except Exception as e:
        print(f"[ERROR] 学習データ保存エラー: {e}")
        import traceback
        traceback.print_exc()

def main():
    """メイン処理"""
    print("="*60)
    print("既存画像からの学習データ蓄積")
    print("="*60)
    
    # 自動反省システムを初期化
    try:
        from auto_reflection_improvement import get_auto_reflection_system
        auto_system = get_auto_reflection_system()
        print("[OK] 自動反省システムを初期化しました")
    except Exception as e:
        print(f"[ERROR] 自動反省システムの初期化に失敗: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 最近の画像を取得（より多くの画像を評価）
    print("\n[1] 最近の画像を取得中...")
    images = get_recent_images_from_filesystem(limit=200)  # 200件の画像を評価
    
    if not images:
        print("[ERROR] 画像が見つかりません")
        return
    
    print(f"[OK] {len(images)}件の画像を取得")
    
    # 各画像を評価して学習
    print(f"\n[2] 画像を評価・学習中...")
    print(f"  評価対象: {len(images)}件の画像")
    print(f"  進捗は10件ごとに表示されます...")
    
    results = []
    learned_count = 0
    improvement_count = 0
    
    for i, image_info in enumerate(images, 1):
        # 進捗表示（10件ごと）
        if i % 10 == 0 or i == 1:
            print(f"\n[進捗] {i}/{len(images)}件処理中... (学習記録: {learned_count}件, 改善提案: {improvement_count}件)")
        
        result = evaluate_and_learn(image_info, auto_system)
        if result:
            results.append(result)
            if result.get("learned"):
                learned_count += 1
            if result.get("improvement"):
                improvement_count += 1
    
    # サマリー
    print(f"\n{'='*60}")
    print("[サマリー]")
    print(f"{'='*60}")
    print(f"評価した画像数: {len(results)}")
    print(f"学習データに記録した数: {learned_count}")
    
    if results:
        avg_score = sum(
            r.get("evaluation", {}).get("overall_score", 0)
            for r in results
        ) / len(results)
        print(f"平均スコア: {avg_score:.2f}")
        
        improvement_count = sum(
            1 for r in results
            if r.get("improvement")
        )
        print(f"改善提案数: {improvement_count}/{len(results)}")
        
        # スコア分布を表示
        scores = [r.get("evaluation", {}).get("overall_score", 0) for r in results]
        if scores:
            print(f"\n[スコア分布]")
            print(f"  最低スコア: {min(scores):.2f}")
            print(f"  最高スコア: {max(scores):.2f}")
            print(f"  平均スコア: {sum(scores)/len(scores):.2f}")
            
            # スコア範囲別の集計
            low_scores = sum(1 for s in scores if s < 0.7)
            medium_scores = sum(1 for s in scores if 0.7 <= s < 0.8)
            high_scores = sum(1 for s in scores if s >= 0.8)
            print(f"  低スコア (<0.7): {low_scores}件")
            print(f"  中スコア (0.7-0.8): {medium_scores}件")
            print(f"  高スコア (>=0.8): {high_scores}件")
    
    # 学習データを保存
    print(f"\n[3] 学習データを保存中...")
    save_learning_data(auto_system)
    
    # 統計情報を表示
    print(f"\n[4] 統計情報を取得中...")
    try:
        stats = auto_system.get_statistics()
        print(f"[OK] 統計情報:")
        print(f"  総評価数: {stats.get('total_evaluations', 0)}")
        print(f"  平均スコア: {stats.get('average_score', 0):.2f}")
        print(f"  改善提案数: {stats.get('total_improvements', 0)}")
        print(f"  改善率: {stats.get('improvement_rate', 0):.2%}")
    except Exception as e:
        print(f"[WARN] 統計情報取得エラー: {e}")
    
    print(f"\n{'='*60}")
    print("[完了] 学習データの蓄積が完了しました！")
    print(f"{'='*60}")
    
    # 画像を評価結果に応じてフォルダ分け
    print(f"\n[5] 画像を評価結果に応じてフォルダ分け中...")
    try:
        from organize_images_by_evaluation import organize_from_learning_data
        organize_from_learning_data()
    except Exception as e:
        print(f"[WARN] 画像整理エラー: {e}")
        print(f"  後で organize_images_by_evaluation.py を実行してください")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[中断] ユーザーによって中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
