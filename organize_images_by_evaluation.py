#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
評価結果に応じて画像をフォルダ分け
"""

import sys
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import threading

# Windowsでのエンコーディング問題を回避
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

# フォルダ構成（デスクトップに作成）
DESKTOP_PATH = Path.home() / "Desktop"
ORGANIZED_DIR = DESKTOP_PATH / "画像評価整理"
# マナより：フォルダ分類は overall_score だけで決める
# 改善提案はタグ化（ファイル名やメタデータで管理）
FOLDER_STRUCTURE = {
    "high_quality": {
        "min_score": 0.8,
        "description": "高品質（スコア >= 0.8）"
    },
    "medium_quality": {
        "min_score": 0.7,
        "max_score": 0.8,
        "description": "中品質（0.7 <= スコア < 0.8）"
    },
    "low_quality": {
        "max_score": 0.7,
        "description": "低品質（スコア < 0.7）"
    }
    # needs_improvement はフォルダから削除（改善提案はタグ化）
}

def create_folder_structure(clear_existing=False):
    """フォルダ構造を作成"""
    ORGANIZED_DIR.mkdir(exist_ok=True)
    
    # 既存のフォルダをクリア
    if clear_existing:
        print(f"[INFO] 既存の整理フォルダをクリア中...")
        for folder_path in ORGANIZED_DIR.iterdir():
            if folder_path.is_dir():
                try:
                    shutil.rmtree(folder_path)
                    print(f"[OK] 削除: {folder_path.name}")
                except Exception as e:
                    print(f"[WARN] 削除失敗 ({folder_path.name}): {e}")
    
    for folder_name, config in FOLDER_STRUCTURE.items():
        folder_path = ORGANIZED_DIR / folder_name
        folder_path.mkdir(exist_ok=True)
        print(f"[OK] フォルダ作成: {folder_path} ({config['description']})")
    
    return ORGANIZED_DIR

def get_image_category(evaluation: Dict[str, Any], improvement: Optional[Dict[str, Any]] = None) -> str:
    """評価結果に基づいてカテゴリを決定（マナより：overall_score だけで分類）"""
    score = evaluation.get('overall_score', 0)
    
    # マナより：フォルダ分類は overall_score だけで決める
    # 改善提案はタグ化（ファイル名やメタデータで管理）
    if score >= 0.8:
        return "high_quality"
    elif score >= 0.7:
        return "medium_quality"
    else:
        return "low_quality"

def organize_image(
    image_path: Path,
    evaluation: Dict[str, Any],
    improvement: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """画像を評価結果に応じてフォルダに移動"""
    try:
        if not image_path.exists():
            print(f"[ERROR] 画像が見つかりません: {image_path}")
            return False
        
        # カテゴリを決定
        category = get_image_category(evaluation, improvement)
        target_folder = ORGANIZED_DIR / category
        
        # ファイル名を取得（改善提案がある場合はタグを追加）
        filename = image_path.name
        name_parts = filename.rsplit('.', 1)
        base_name = name_parts[0] if len(name_parts) == 2 else filename
        extension = name_parts[1] if len(name_parts) == 2 else ""
        
        # 改善提案がある場合はファイル名にタグを追加
        if improvement:
            if extension:
                tagged_filename = f"{base_name}_IMPROVE.{extension}"
            else:
                tagged_filename = f"{base_name}_IMPROVE"
        else:
            tagged_filename = filename
        
        target_path = target_folder / tagged_filename
        
        # 既に存在する場合はタイムスタンプを追加
        if target_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if extension:
                new_filename = f"{base_name}_{timestamp}.{extension}"
            else:
                new_filename = f"{base_name}_{timestamp}"
            target_path = target_folder / new_filename
        
        # 画像をコピー（移動ではなくコピー）
        shutil.copy2(image_path, target_path)
        
        # メタデータファイルもコピー
        metadata_file = image_path.parent / f"{image_path.name}.json"
        if metadata_file.exists():
            target_metadata = target_folder / f"{target_path.name}.json"
            shutil.copy2(metadata_file, target_metadata)
        
        # 評価結果と改善提案をメタデータに追加
        eval_metadata = {
            "original_path": str(image_path),
            "organized_at": datetime.now().isoformat(),
            "category": category,
            "evaluation": evaluation,
            "improvement": improvement
        }
        
        # 既存のメタデータとマージ
        if metadata:
            eval_metadata.update(metadata)
        
        # 評価メタデータを保存（改善提案がある場合は report.json も作成）
        eval_metadata_path = target_folder / f"{target_path.name}_eval.json"
        with open(eval_metadata_path, 'w', encoding='utf-8') as f:
            json.dump(eval_metadata, f, ensure_ascii=False, indent=2)
        
        # 改善提案がある場合は report.json も作成（マナより：タグ化）
        if improvement:
            report_path = target_folder / f"{target_path.stem}_report.json"
            report_data = {
                "has_improvement": True,
                "improvement_reason": improvement.get("reason", ""),
                "expected_improvement": improvement.get("expected_improvement", 0),
                "improvement": improvement,
                "original_score": evaluation.get("overall_score", 0),
                "created_at": datetime.now().isoformat()
            }
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 画像整理エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def organize_from_learning_data():
    """学習データから画像を整理"""
    learning_file = Path("learning_data.json")
    
    if not learning_file.exists():
        print(f"[ERROR] 学習データファイルが見つかりません: {learning_file}")
        return
    
    print(f"[INFO] 学習データを読み込み中: {learning_file}")
    
    with open(learning_file, 'r', encoding='utf-8') as f:
        learning_data = json.load(f)
    
    # フォルダ構造を作成
    create_folder_structure()
    
    # 改善提案から画像を整理
    improvement_suggestions = learning_data.get("improvement_suggestions", [])
    print(f"\n[1] 改善提案から画像を整理中... ({len(improvement_suggestions)}件)")
    
    organized_count = 0
    for i, suggestion in enumerate(improvement_suggestions, 1):
        if i % 10 == 0:
            print(f"  進捗: {i}/{len(improvement_suggestions)}件")
        
        evaluation = suggestion.get("evaluation", {})
        improvement = suggestion.get("improvement", {})
        image_path_str = suggestion.get("image_path", "")
        
        if not image_path_str:
            continue
        
        image_path = Path(image_path_str)
        if image_path.exists():
            if organize_image(image_path, evaluation, improvement):
                organized_count += 1
    
    print(f"[OK] {organized_count}件の画像を整理しました")
    
    # 低スコアパターンから画像を整理
    low_score_patterns = learning_data.get("low_score_patterns", [])
    print(f"\n[2] 低スコアパターンから画像を整理中... ({len(low_score_patterns)}件)")
    
    low_score_count = 0
    for i, pattern in enumerate(low_score_patterns, 1):
        if i % 10 == 0:
            print(f"  進捗: {i}/{len(low_score_patterns)}件")
        
        evaluation = pattern.get("evaluation", {})
        image_path_str = pattern.get("image_path", "")
        
        if not image_path_str:
            continue
        
        image_path = Path(image_path_str)
        if image_path.exists():
            if organize_image(image_path, evaluation, None):
                low_score_count += 1
    
    print(f"[OK] {low_score_count}件の画像を整理しました")
    
    # サマリー
    print(f"\n{'='*60}")
    print("[整理サマリー]")
    print(f"{'='*60}")
    print(f"改善提案から整理: {organized_count}件")
    print(f"低スコアパターンから整理: {low_score_count}件")
    print(f"合計: {organized_count + low_score_count}件")
    
    # フォルダごとの統計
    print(f"\n[フォルダ別統計]")
    for folder_name, config in FOLDER_STRUCTURE.items():
        folder_path = ORGANIZED_DIR / folder_name
        if folder_path.exists():
            png_count = len(list(folder_path.glob("*.png")))
            print(f"  {folder_name}: {png_count}件 ({config['description']})")
    
    print(f"\n{'='*60}")
    print(f"[完了] 画像の整理が完了しました！")
    print(f"整理先: {ORGANIZED_DIR.absolute()}")
    print(f"{'='*60}")

def find_all_images_in_system():
    """システム内のすべての画像を検索（広範囲検索）"""
    # 検索対象ディレクトリ（広範囲）
    image_dirs = [
        # プロジェクト内
        Path("gallery_images"),
        Path("generated_images"),
        Path("data/image_stock/generated"),
        Path("organized_images"),  # 既に整理済みのものは除外
        
        # ComfyUI関連
        Path("C:/ComfyUI/output"),
        Path("C:/ComfyUI/input"),
        Path("C:/ComfyUI/models"),
        
        # ワークスペース関連
        Path("C:/mana_workspace/generated_images"),
        Path("C:/mana_workspace"),
        
        # デスクトップ
        Path.home() / "Desktop",
        
        # ドキュメント
        Path.home() / "Documents",
        
        # ピクチャ
        Path.home() / "Pictures",
        
        # ダウンロード
        Path.home() / "Downloads",
        
        # その他の一般的な場所
        Path("D:/"),
        Path("E:/"),
        Path("F:/"),
    ]
    
    # 除外するディレクトリ（システムフォルダなど）
    exclude_dirs = {
        Path("C:/Windows"),
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
        Path("C:/ProgramData"),
        Path("C:/$Recycle.Bin"),
        Path("C:/System Volume Information"),
        Path("C:/Recovery"),
        ORGANIZED_DIR,  # 整理先フォルダは除外
    }
    
    all_images = []
    searched_dirs = set()
    
    def should_exclude(path: Path) -> bool:
        """除外すべきパスかチェック"""
        path_str = str(path).lower()
        # システムフォルダや一時ファイルを除外
        exclude_keywords = [
            "windows", "program files", "programdata", 
            "$recycle", "system volume", "recovery",
            "appdata\\local\\temp", "appdata\\local\\cache",
            "node_modules", ".git", "__pycache__"
        ]
        return any(keyword in path_str for keyword in exclude_keywords)
    
    def search_directory(dir_path: Path, max_depth: int = 3, current_depth: int = 0):
        """ディレクトリを再帰的に検索"""
        if current_depth > max_depth:
            return
        
        if not dir_path.exists() or not dir_path.is_dir():
            return
        
        # 除外チェック
        if dir_path in exclude_dirs or should_exclude(dir_path):
            return
        
        # 既に検索済みかチェック
        dir_str = str(dir_path.resolve())
        if dir_str in searched_dirs:
            return
        searched_dirs.add(dir_str)
        
        try:
            # PNGファイルを検索（再帰的）
            if current_depth == 0:
                # ルートレベル: 直接のPNGファイルとサブディレクトリ
                png_files = list(dir_path.glob("*.png"))
                subdirs = [d for d in dir_path.iterdir() if d.is_dir()]
            else:
                # サブディレクトリ: 直接のPNGファイルのみ
                png_files = list(dir_path.glob("*.png"))
                subdirs = []
            
            if png_files:
                print(f"  [{current_depth}] {dir_path}: {len(png_files)}件のPNGファイル")
            
            for png_file in png_files:
                # メタデータファイルを探す
                metadata_file = png_file.parent / f"{png_file.name}.json"
                metadata = {}
                
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    except:
                        pass
                
                all_images.append({
                    "path": png_file,
                    "metadata": metadata
                })
            
            # サブディレクトリを再帰的に検索
            for subdir in subdirs:
                try:
                    search_directory(subdir, max_depth, current_depth + 1)
                except (PermissionError, OSError):
                    # アクセス権限エラーは無視
                    continue
                    
        except (PermissionError, OSError) as e:
            # アクセス権限エラーは無視
            pass
        except Exception as e:
            # その他のエラーも無視（大量のファイルがある場合など）
            pass
    
    # 各ディレクトリを検索
    for dir_path in image_dirs:
        if dir_path.exists():
            print(f"[INFO] ディレクトリ検索中: {dir_path}")
            try:
                search_directory(dir_path, max_depth=3)
            except Exception as e:
                print(f"  [WARN] 検索エラー: {e}")
                continue
    
    print(f"\n[OK] 合計 {len(all_images)}件の画像を発見")
    print(f"  検索したディレクトリ数: {len(searched_dirs)}")
    return all_images

def evaluate_single_image(args):
    """単一画像を評価（並列処理用）"""
    image_info, auto_system_instance = args
    image_path = image_info["path"]
    metadata = image_info.get("metadata", {})
    
    if not image_path.exists():
        return None
    
    try:
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
        
        # 評価と改善提案を生成
        result = auto_system_instance.process_generated_image(
            image_path=str(image_path),
            prompt=prompt,
            negative_prompt=negative_prompt,
            model=model,
            parameters=parameters,
            auto_improve=True,
            threshold=0.75
        )
        
        if not result:
            return None
        
        evaluation = result.get("evaluation", {})
        improvement = result.get("improvement")
        
        return {
            "image_path": image_path,
            "evaluation": evaluation,
            "improvement": improvement,
            "metadata": metadata,
            "success": True
        }
        
    except Exception as e:
        return {
            "image_path": image_path,
            "error": str(e),
            "success": False
        }

def evaluate_and_organize_all_images():
    """すべての画像を評価して整理（並列処理版）"""
    try:
        from auto_reflection_improvement import get_auto_reflection_system
        auto_system = get_auto_reflection_system()
        print("[OK] 自動反省システムを初期化しました")
    except Exception as e:
        print(f"[ERROR] 自動反省システムの初期化に失敗: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # すべての画像を検索
    print("\n[1] システム内のすべての画像を検索中...")
    all_images = find_all_images_in_system()
    
    if not all_images:
        print("[ERROR] 画像が見つかりません")
        return
    
    # フォルダ構造を作成
    create_folder_structure()
    
    # 並列処理で評価・整理
    print(f"\n[2] 画像を評価・整理中（並列処理）...")
    print(f"  評価対象: {len(all_images)}件の画像")
    print(f"  並列数: 8スレッド")
    print(f"  進捗は100件ごとに表示されます...")
    
    organized_count = 0
    evaluated_count = 0
    error_count = 0
    
    # スレッドセーフなカウンター
    lock = threading.Lock()
    
    def update_counters(eval_inc=0, org_inc=0, err_inc=0):
        nonlocal evaluated_count, organized_count, error_count
        with lock:
            evaluated_count += eval_inc
            organized_count += org_inc
            error_count += err_inc
    
    # 並列処理で評価
    max_workers = 8  # 並列数
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # タスクを投入
        future_to_image = {
            executor.submit(evaluate_single_image, (img, auto_system)): img
            for img in all_images
        }
        
        # 完了したタスクを処理
        completed = 0
        for future in as_completed(future_to_image):
            completed += 1
            
            # 進捗表示（100件ごと）
            if completed % 100 == 0 or completed == 1:
                with lock:
                    print(f"  進捗: {completed}/{len(all_images)}件 (評価: {evaluated_count}, 整理: {organized_count}, エラー: {error_count})")
            
            try:
                result = future.result()
                
                if result is None:
                    continue
                
                if not result.get("success", False):
                    error_count += 1
                    if error_count <= 5:
                        print(f"  [WARN] 評価エラー: {result.get('error', 'Unknown')}")
                    continue
                
                evaluated_count += 1
                
                # 画像を整理
                image_path = result["image_path"]
                evaluation = result["evaluation"]
                improvement = result["improvement"]
                metadata = result["metadata"]
                
                if organize_image(image_path, evaluation, improvement, metadata):
                    organized_count += 1
                    
            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    print(f"  [WARN] 処理エラー: {e}")
                continue
    
    # サマリー
    print(f"\n{'='*60}")
    print("[評価・整理サマリー]")
    print(f"{'='*60}")
    print(f"評価した画像数: {evaluated_count}")
    print(f"整理した画像数: {organized_count}")
    print(f"エラー数: {error_count}")
    
    # フォルダごとの統計
    print(f"\n[フォルダ別統計]")
    for folder_name, config in FOLDER_STRUCTURE.items():
        folder_path = ORGANIZED_DIR / folder_name
        if folder_path.exists():
            png_count = len(list(folder_path.glob("*.png")))
            print(f"  {folder_name}: {png_count}件 ({config['description']})")
    
    print(f"\n{'='*60}")
    print(f"[完了] すべての画像の評価・整理が完了しました！")
    print(f"整理先: {ORGANIZED_DIR.absolute()}")
    print(f"{'='*60}")

def organize_from_database():
    """データベースから画像を整理"""
    try:
        import sqlite3
        
        db_path = Path("auto_improvement.db")
        if not db_path.exists():
            print(f"[ERROR] データベースファイルが見つかりません: {db_path}")
            return
        
        print(f"[INFO] データベースを読み込み中: {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 評価と改善提案を取得
        cursor.execute("""
            SELECT e.id, e.image_path, e.overall_score, e.anatomy_score, 
                   e.quality_score, e.prompt_match_score,
                   i.id as improvement_id, i.reason, i.expected_improvement
            FROM evaluations e
            LEFT JOIN improvements i ON e.id = i.evaluation_id
            ORDER BY e.timestamp DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        print(f"[OK] {len(results)}件の評価データを取得")
        
        # フォルダ構造を作成
        create_folder_structure()
        
        organized_count = 0
        print(f"\n[画像を整理中...]")
        
        for i, row in enumerate(results, 1):
            if i % 10 == 0:
                print(f"  進捗: {i}/{len(results)}件")
            
            eval_id, image_path_str, overall_score, anatomy_score, quality_score, prompt_match_score, improvement_id, reason, expected_improvement = row
            
            if not image_path_str:
                continue
            
            image_path = Path(image_path_str)
            if not image_path.exists():
                continue
            
            # 評価データを構築
            evaluation = {
                "overall_score": overall_score or 0,
                "anatomy_score": anatomy_score or 0,
                "quality_score": quality_score or 0,
                "prompt_match_score": prompt_match_score or 0
            }
            
            # 改善提案データを構築
            improvement = None
            if improvement_id:
                improvement = {
                    "reason": reason or "",
                    "expected_improvement": expected_improvement or 0
                }
            
            if organize_image(image_path, evaluation, improvement):
                organized_count += 1
        
        print(f"[OK] {organized_count}件の画像を整理しました")
        
        # フォルダごとの統計
        print(f"\n[フォルダ別統計]")
        for folder_name, config in FOLDER_STRUCTURE.items():
            folder_path = ORGANIZED_DIR / folder_name
            if folder_path.exists():
                png_count = len(list(folder_path.glob("*.png")))
                print(f"  {folder_name}: {png_count}件 ({config['description']})")
        
    except Exception as e:
        print(f"[ERROR] データベースからの整理エラー: {e}")
        import traceback
        traceback.print_exc()

def main():
    """メイン処理"""
    import sys
    
    # 既存の整理済み画像をクリアするかチェック
    clear_existing = "--clear" in sys.argv or "--fresh" in sys.argv
    
    # S/A/B/破綻フォルダ運用に切り替えるかチェック
    use_sab_structure = "--use-sab-structure" in sys.argv or "--sab" in sys.argv
    
    if use_sab_structure:
        # S/A/B/破綻フォルダ構造に変更
        global FOLDER_STRUCTURE
        FOLDER_STRUCTURE = {
            "S": {
                "min_score": 0.85,
                "description": "手元保存級（人間が即OK、スコア >= 0.85）"
            },
            "A": {
                "min_score": 0.75,
                "max_score": 0.85,
                "description": "使える（0.75 <= スコア < 0.85）"
            },
            "B": {
                "min_score": 0.65,
                "max_score": 0.75,
                "description": "素材（0.65 <= スコア < 0.75）"
            },
            "破綻": {
                "max_score": 0.65,
                "description": "捨て or 学習用（スコア < 0.65）"
            }
        }
        # get_image_category も更新
        global get_image_category
        def get_image_category_sab(evaluation: Dict[str, Any], improvement: Optional[Dict[str, Any]] = None) -> str:
            score = evaluation.get('overall_score', 0)
            if score >= 0.85:
                return "S"
            elif score >= 0.75:
                return "A"
            elif score >= 0.65:
                return "B"
            else:
                return "破綻"
        get_image_category = get_image_category_sab
        print("="*60)
        print("評価結果に応じた画像フォルダ分け（S/A/B/破綻運用）")
        print("="*60)
    else:
        print("="*60)
        print("評価結果に応じた画像フォルダ分け（マナより版）")
        print("="*60)
    
    print(f"整理先: {ORGANIZED_DIR.absolute()}")
    print("="*60)
    
    # 既存の整理済み画像をクリア（オプション）
    if clear_existing:
        print("\n[クリア] 既存の整理済み画像をクリア中...")
        if ORGANIZED_DIR.exists():
            for folder_name in FOLDER_STRUCTURE.keys():
                folder_path = ORGANIZED_DIR / folder_name
                if folder_path.exists():
                    import shutil
                    shutil.rmtree(folder_path)
                    print(f"  削除: {folder_path}")
        print("[OK] クリア完了")
    
    # すべての画像を評価して整理（新機能・マナより版）
    print("\n[方法1] システム内のすべての画像を評価・整理（マナより版）")
    print("  新しい評価基準で再評価します:")
    print("  - 品質スコア: 60%（最重要）")
    print("  - 生成安全スコア: 25%（足切り重視）")
    print("  - プロンプト一致度: 15%（オマケ扱い）")
    evaluate_and_organize_all_images()
    
    # 学習データから整理（既存データ）
    print("\n[方法2] 学習データ（JSON）から整理")
    organize_from_learning_data()
    
    # データベースから整理（既存データ）
    print("\n[方法3] データベースから整理")
    organize_from_database()
    
    print(f"\n{'='*60}")
    print("[完了] すべての画像整理が完了しました！")
    print(f"デスクトップの「画像評価整理」フォルダを確認してください")
    if not use_sab_structure:
        print(f"\n[オプション] S/A/B/破綻フォルダ運用に切り替える場合:")
        print(f"  python organize_images_by_evaluation.py --use-sab-structure")
    print(f"{'='*60}")

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
