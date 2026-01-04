"""
画像ストック機能
生成された画像を自動で整理し、次回の精度が上がる仕組み
"""

import os
import json
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from PIL import Image
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 標準APIをインポート
try:
    import manaos_core_api as manaos
    MANAOS_API_AVAILABLE = True
except ImportError:
    MANAOS_API_AVAILABLE = False
    logger.warning("manaOS標準APIが利用できません")


class ImageStock:
    """画像ストックシステム"""
    
    def __init__(self, stock_dir: Optional[str] = None, metadata_dir: Optional[str] = None):
        """
        初期化
        
        Args:
            stock_dir: ストックディレクトリ（Noneの場合はデフォルト）
            metadata_dir: メタデータディレクトリ（Noneの場合はデフォルト）
        """
        if stock_dir is None:
            stock_dir = Path(__file__).parent.parent / "data" / "image_stock"
        self.stock_dir = Path(stock_dir)
        self.stock_dir.mkdir(parents=True, exist_ok=True)
        
        # メタデータディレクトリ
        if metadata_dir is None:
            metadata_dir = self.stock_dir / "metadata"
        self.metadata_dir = Path(metadata_dir)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # 分類ディレクトリ
        self.categories = {
            "generated": self.stock_dir / "generated",
            "lora": self.stock_dir / "lora",
            "flyer": self.stock_dir / "flyer",
            "other": self.stock_dir / "other"
        }
        
        for category_dir in self.categories.values():
            category_dir.mkdir(parents=True, exist_ok=True)
    
    def _calculate_image_hash(self, image_path: Path) -> str:
        """画像のハッシュを計算（重複検出用）"""
        try:
            with open(image_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"ハッシュ計算エラー: {e}")
            return ""
    
    def _extract_metadata_from_image(self, image_path: Path) -> Dict[str, Any]:
        """画像からメタデータを抽出"""
        metadata = {
            "file_path": str(image_path),
            "file_name": image_path.name,
            "file_size": image_path.stat().st_size,
            "image_hash": self._calculate_image_hash(image_path)
        }
        
        try:
            with Image.open(image_path) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["format"] = img.format
                metadata["mode"] = img.mode
                
                # EXIFデータがあれば取得
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    metadata["exif"] = dict(exif) if exif else {}
        except Exception as e:
            logger.warning(f"メタデータ抽出エラー: {e}")
        
        return metadata
    
    def _classify_image(self, metadata: Dict[str, Any], prompt: Optional[str] = None) -> str:
        """画像を分類"""
        # プロンプトから分類
        if prompt:
            prompt_lower = prompt.lower()
            if "lora" in prompt_lower or "training" in prompt_lower:
                return "lora"
            elif "flyer" in prompt_lower or "poster" in prompt_lower:
                return "flyer"
            elif "generate" in prompt_lower or "create" in prompt_lower:
                return "generated"
        
        # ファイル名から分類
        file_name = metadata.get("file_name", "").lower()
        if "lora" in file_name:
            return "lora"
        elif "flyer" in file_name or "poster" in file_name:
            return "flyer"
        elif "generated" in file_name or "gen" in file_name:
            return "generated"
        
        return "other"
    
    def store(
        self,
        image_path: Path,
        prompt: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        model: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        画像をストック（自動整理）
        
        Args:
            image_path: 画像ファイルのパス
            prompt: プロンプト
            negative_prompt: ネガティブプロンプト
            model: 使用したモデル
            parameters: 生成パラメータ
            category: カテゴリ（Noneの場合は自動分類）
        
        Returns:
            ストック情報
        """
        if not image_path.exists():
            raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")
        
        # メタデータを抽出
        image_metadata = self._extract_metadata_from_image(image_path)
        
        # カテゴリを決定
        if category is None:
            category = self._classify_image(image_metadata, prompt)
        
        # ストックIDを生成
        stock_id = str(uuid.uuid4())
        
        # ストック先のパスを決定
        category_dir = self.categories.get(category, self.categories["other"])
        timestamp = datetime.now().strftime("%Y%m%d")
        date_dir = category_dir / timestamp
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # ファイル名を生成
        safe_prompt = ""
        if prompt:
            safe_prompt = "".join(c for c in prompt[:30] if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_prompt = safe_prompt.replace(' ', '_')
        
        file_extension = image_path.suffix
        stock_filename = f"{stock_id}_{safe_prompt}{file_extension}"
        stock_path = date_dir / stock_filename
        
        # 画像をコピー
        shutil.copy2(image_path, stock_path)
        
        # ストック情報を作成
        stock_info = {
            "stock_id": stock_id,
            "original_path": str(image_path),
            "stock_path": str(stock_path),
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "image_metadata": image_metadata,
            "generation_metadata": {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "model": model,
                "parameters": parameters or {}
            },
            "evaluation": {
                "score": None,  # 1-5のスコア（None=未評価）
                "is_hit": False,  # 「刺さった」フラグ
                "evaluated_at": None,
                "feedback": None  # ユーザーフィードバック
            }
        }
        
        # メタデータを保存
        metadata_file = self.metadata_dir / f"{stock_id}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(stock_info, f, ensure_ascii=False, indent=2)
        
        # 統一記憶システムに保存
        if MANAOS_API_AVAILABLE:
            try:
                manaos.remember({
                    "type": "system",
                    "content": f"画像をストック: {stock_id}",
                    "metadata": {
                        "stock_id": stock_id,
                        "category": category,
                        "prompt": prompt,
                        "model": model
                    }
                }, format_type="system")
            except Exception as e:
                logger.warning(f"記憶保存エラー: {e}")
        
        logger.info(f"[ImageStock] 画像をストック: {stock_id} ({category})")
        
        return stock_info
    
    def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        model: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        画像を検索
        
        Args:
            query: 検索クエリ（プロンプトなど）
            category: カテゴリ
            model: モデル名
            date_from: 開始日（YYYY-MM-DD）
            date_to: 終了日（YYYY-MM-DD）
            limit: 取得件数
        
        Returns:
            検索結果のリスト
        """
        results = []
        
        # メタデータファイルを検索
        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    stock_info = json.load(f)
                
                # フィルタ
                if category and stock_info.get("category") != category:
                    continue
                
                if model and stock_info.get("generation_metadata", {}).get("model") != model:
                    continue
                
                # 日付フィルタ
                timestamp = stock_info.get("timestamp", "")
                if date_from and timestamp < date_from:
                    continue
                if date_to and timestamp > date_to:
                    continue
                
                # クエリ検索
                if query:
                    query_lower = query.lower()
                    prompt = stock_info.get("generation_metadata", {}).get("prompt", "")
                    if query_lower not in prompt.lower():
                        continue
                
                results.append(stock_info)
            
            except Exception as e:
                logger.warning(f"メタデータ読み込みエラー: {e}")
                continue
        
        # タイムスタンプでソート（新しい順）
        results.sort(
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        return results[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        stats = {
            "total": 0,
            "by_category": {},
            "by_model": {},
            "by_date": {}
        }
        
        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    stock_info = json.load(f)
                
                stats["total"] += 1
                
                # カテゴリ別
                category = stock_info.get("category", "other")
                stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
                
                # モデル別
                model = stock_info.get("generation_metadata", {}).get("model", "unknown")
                stats["by_model"][model] = stats["by_model"].get(model, 0) + 1
                
                # 日付別
                timestamp = stock_info.get("timestamp", "")
                date = timestamp[:10] if timestamp else "unknown"
                stats["by_date"][date] = stats["by_date"].get(date, 0) + 1
            
            except Exception as e:
                logger.warning(f"統計情報取得エラー: {e}")
                continue
        
        return stats
    
    def mark_as_hit(self, stock_id: str, score: Optional[int] = None, feedback: Optional[str] = None) -> bool:
        """
        画像を「刺さった」とマーク（評価スコアを記録）
        
        Args:
            stock_id: ストックID
            score: 評価スコア（1-5、Noneの場合は自動で5）
            feedback: フィードバック
        
        Returns:
            成功時True
        """
        metadata_file = self.metadata_dir / f"{stock_id}.json"
        if not metadata_file.exists():
            logger.warning(f"ストックIDが見つかりません: {stock_id}")
            return False
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                stock_info = json.load(f)
            
            # 評価を更新
            stock_info["evaluation"] = {
                "score": score if score is not None else 5,
                "is_hit": True,
                "evaluated_at": datetime.now().isoformat(),
                "feedback": feedback
            }
            
            # 保存
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(stock_info, f, ensure_ascii=False, indent=2)
            
            logger.info(f"画像を「刺さった」とマーク: {stock_id} (score: {stock_info['evaluation']['score']})")
            return True
        
        except Exception as e:
            logger.error(f"評価マークエラー: {e}")
            return False
    
    def suggest_for_generation(self, prompt: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        次回生成時の自動提案（過去に似たプロンプトで成功した画像を検索）
        
        Args:
            prompt: 新しいプロンプト
            limit: 提案する最大件数
        
        Returns:
            提案画像のリスト（プロンプト差分、パラメータ等を含む）
        """
        # 「刺さった」画像を検索
        hit_images = []
        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    stock_info = json.load(f)
                
                # 「刺さった」画像のみ
                if not stock_info.get("evaluation", {}).get("is_hit", False):
                    continue
                
                # プロンプトの類似度を簡易計算（キーワードマッチ）
                stored_prompt = stock_info.get("generation_metadata", {}).get("prompt", "").lower()
                new_prompt_lower = prompt.lower()
                
                # 共通キーワード数をカウント
                stored_words = set(stored_prompt.split())
                new_words = set(new_prompt_lower.split())
                common_words = stored_words & new_words
                similarity = len(common_words) / max(len(stored_words), len(new_words), 1)
                
                if similarity > 0.3:  # 30%以上類似
                    hit_images.append({
                        "stock_info": stock_info,
                        "similarity": similarity,
                        "score": stock_info.get("evaluation", {}).get("score", 0)
                    })
            
            except Exception as e:
                logger.warning(f"メタデータ読み込みエラー: {e}")
                continue
        
        # 類似度とスコアでソート
        hit_images.sort(
            key=lambda x: (x["similarity"], x["score"]),
            reverse=True
        )
        
        # 提案を生成
        suggestions = []
        for item in hit_images[:limit]:
            stock_info = item["stock_info"]
            gen_meta = stock_info.get("generation_metadata", {})
            
            # プロンプト差分を計算（簡易版）
            stored_prompt = gen_meta.get("prompt", "")
            prompt_diff = self._calculate_prompt_diff(stored_prompt, prompt)
            
            suggestions.append({
                "stock_id": stock_info.get("stock_id"),
                "image_path": stock_info.get("stock_path"),
                "similarity": item["similarity"],
                "score": item["score"],
                "original_prompt": stored_prompt,
                "prompt_diff": prompt_diff,
                "recommended_prompt": self._generate_recommended_prompt(stored_prompt, prompt, prompt_diff),
                "parameters": gen_meta.get("parameters", {}),
                "model": gen_meta.get("model"),
                "negative_prompt": gen_meta.get("negative_prompt")
            })
        
        return suggestions
    
    def _calculate_prompt_diff(self, stored_prompt: str, new_prompt: str) -> Dict[str, List[str]]:
        """プロンプト差分を計算"""
        stored_words = set(stored_prompt.lower().split())
        new_words = set(new_prompt.lower().split())
        
        return {
            "added": list(new_words - stored_words),
            "removed": list(stored_words - new_words),
            "common": list(stored_words & new_words)
        }
    
    def _generate_recommended_prompt(self, stored_prompt: str, new_prompt: str, prompt_diff: Dict[str, List[str]]) -> str:
        """推奨プロンプトを生成（成功したプロンプトをベースに、新しい要素を追加）"""
        # 簡易版：成功したプロンプトのキーワードを保持しつつ、新しい要素を追加
        recommended = stored_prompt
        
        # 新しいキーワードがあれば追加
        if prompt_diff["added"]:
            recommended += ", " + ", ".join(prompt_diff["added"][:5])  # 最大5個
        
        return recommended
    
    def get_success_patterns(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        成功パターンを学習（どのプロンプト/パラメータの組み合わせが「刺さる」か）
        
        Args:
            category: カテゴリ（Noneの場合は全カテゴリ）
        
        Returns:
            成功パターンの統計
        """
        patterns = {
            "total_hits": 0,
            "avg_score": 0.0,
            "common_keywords": {},
            "common_parameters": {},
            "top_models": {},
            "top_negative_prompts": []
        }
        
        hit_count = 0
        total_score = 0
        
        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    stock_info = json.load(f)
                
                # カテゴリフィルタ
                if category and stock_info.get("category") != category:
                    continue
                
                # 「刺さった」画像のみ
                evaluation = stock_info.get("evaluation", {})
                if not evaluation.get("is_hit", False):
                    continue
                
                hit_count += 1
                score = evaluation.get("score", 0)
                total_score += score
                
                # キーワード分析
                prompt = stock_info.get("generation_metadata", {}).get("prompt", "")
                for word in prompt.lower().split():
                    if len(word) > 3:  # 3文字以上の単語のみ
                        patterns["common_keywords"][word] = patterns["common_keywords"].get(word, 0) + score
                
                # パラメータ分析
                params = stock_info.get("generation_metadata", {}).get("parameters", {})
                for key, value in params.items():
                    if key not in patterns["common_parameters"]:
                        patterns["common_parameters"][key] = {}
                    value_str = str(value)
                    patterns["common_parameters"][key][value_str] = patterns["common_parameters"][key].get(value_str, 0) + score
                
                # モデル分析
                model = stock_info.get("generation_metadata", {}).get("model", "unknown")
                patterns["top_models"][model] = patterns["top_models"].get(model, 0) + score
                
                # ネガティブプロンプト分析
                neg_prompt = stock_info.get("generation_metadata", {}).get("negative_prompt", "")
                if neg_prompt:
                    patterns["top_negative_prompts"].append(neg_prompt)
            
            except Exception as e:
                logger.warning(f"パターン分析エラー: {e}")
                continue
        
        patterns["total_hits"] = hit_count
        patterns["avg_score"] = (total_score / hit_count) if hit_count > 0 else 0.0
        
        # トップキーワードを取得
        patterns["top_keywords"] = sorted(
            patterns["common_keywords"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # トップモデルを取得
        patterns["top_models"] = sorted(
            patterns["top_models"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return patterns


# 使用例
if __name__ == "__main__":
    stock = ImageStock()
    
    # 画像をストック
    test_image = Path("test_image.png")
    if test_image.exists():
        stock_info = stock.store(
            image_path=test_image,
            prompt="test prompt",
            model="stable-diffusion-v1-5"
        )
        print(f"ストック完了: {stock_info['stock_id']}")
    
    # 検索
    results = stock.search(query="test", limit=10)
    print(f"検索結果: {len(results)}件")
    
    # 統計情報
    stats = stock.get_statistics()
    print(f"総数: {stats['total']}件")






