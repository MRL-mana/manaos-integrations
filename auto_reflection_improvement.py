#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動反省・改善システム
生成された画像を自動的に評価し、問題があれば改善を試みる
"""

import os
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import logging

try:
    from manaos_logger import get_logger
except ImportError:
    logging.basicConfig(level=logging.INFO)
    get_logger = lambda name: logging.getLogger(name)

logger = get_logger(__name__)


@dataclass
class ImageEvaluation:
    """画像評価結果"""
    image_path: str
    prompt: str
    negative_prompt: str
    model: str
    parameters: Dict[str, Any]
    
    # 評価スコア（0.0-1.0）
    overall_score: float = 0.0
    anatomy_score: float = 0.0  # 生成安全スコア（旧：身体崩れスコア、設定チェック用）
    quality_score: float = 0.0  # 品質スコア
    prompt_match_score: float = 0.0  # プロンプト一致度
    
    # 問題点
    anatomy_issues: List[str] = None
    quality_issues: List[str] = None
    prompt_mismatches: List[str] = None
    
    # 改善提案
    improvements: List[str] = None
    
    # メタデータ
    timestamp: str = ""
    evaluation_method: str = "auto"
    
    def __post_init__(self):
        if self.anatomy_issues is None:
            self.anatomy_issues = []
        if self.quality_issues is None:
            self.quality_issues = []
        if self.prompt_mismatches is None:
            self.prompt_mismatches = []
        if self.improvements is None:
            self.improvements = []
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ImprovementPlan:
    """改善計画"""
    original_prompt: str
    improved_prompt: str
    original_negative_prompt: str
    improved_negative_prompt: str
    original_parameters: Dict[str, Any]
    improved_parameters: Dict[str, Any]
    reason: str
    expected_improvement: float  # 期待される改善度（0.0-1.0）
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class ImageEvaluator:
    """画像評価器"""
    
    def __init__(self):
        """初期化"""
        self.evaluation_history: List[ImageEvaluation] = []
    
    def evaluate_image(
        self,
        image_path: str,
        prompt: str,
        negative_prompt: str = "",
        model: str = "",
        parameters: Dict[str, Any] = None
    ) -> ImageEvaluation:
        """
        画像を評価
        
        Args:
            image_path: 画像パス
            prompt: プロンプト
            negative_prompt: ネガティブプロンプト
            model: モデル名
            parameters: 生成パラメータ
        
        Returns:
            評価結果
        """
        logger.info(f"[評価開始] {image_path}")
        
        evaluation = ImageEvaluation(
            image_path=image_path,
            prompt=prompt,
            negative_prompt=negative_prompt,
            model=model,
            parameters=parameters or {}
        )
        
        # 身体崩れの検出
        anatomy_result = self._detect_anatomy_issues(image_path, prompt)
        evaluation.anatomy_score = anatomy_result["score"]
        evaluation.anatomy_issues = anatomy_result["issues"]
        
        # 品質評価
        quality_result = self._evaluate_quality(image_path)
        evaluation.quality_score = quality_result["score"]
        evaluation.quality_issues = quality_result["issues"]
        
        # プロンプト一致度評価
        match_result = self._evaluate_prompt_match(image_path, prompt)
        evaluation.prompt_match_score = match_result["score"]
        evaluation.prompt_mismatches = match_result["mismatches"]
        
        # 総合スコア計算（マナより：品質重視の配分）
        # 旧: anatomy 0.4 / quality 0.3 / match 0.3
        # 新: safety(旧anatomy) 0.25 / quality 0.60 / match 0.15
        evaluation.overall_score = (
            evaluation.anatomy_score * 0.25 +      # 安全（設定チェック）は足切り重視
            evaluation.quality_score * 0.60 +       # 品質を最重要視
            evaluation.prompt_match_score * 0.15    # プロンプト一致度はオマケ扱い
        )
        
        # 改善提案の生成
        evaluation.improvements = self._generate_improvements(evaluation)
        
        self.evaluation_history.append(evaluation)
        logger.info(f"[評価完了] 総合スコア: {evaluation.overall_score:.2f}")
        
        return evaluation
    
    def _detect_anatomy_issues(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """
        身体崩れを検出（簡易版）
        
        実際の実装では、画像解析ライブラリやAIモデルを使用
        """
        issues = []
        score = 1.0  # デフォルトは完璧
        
        # 簡易チェック: ファイルサイズが小さすぎる場合は品質が低い可能性
        try:
            file_size = os.path.getsize(image_path)
            if file_size < 50000:  # 50KB未満
                issues.append("画像ファイルサイズが小さい（品質が低い可能性）")
                score -= 0.1
        except:
            pass
        
        # プロンプトから身体崩れの可能性を推測
        prompt_lower = prompt.lower()
        negative_lower = ""
        
        # 身体崩れ対策タグが不足している場合
        anatomy_keywords = ["perfect anatomy", "correct anatomy", "proper proportions"]
        has_anatomy_tags = any(keyword in prompt_lower for keyword in anatomy_keywords)
        
        if not has_anatomy_tags:
            issues.append("身体崩れ対策タグが不足している可能性")
            score -= 0.2
        
        # 解像度が低い場合
        if parameters := {}:
            width = parameters.get("width", 512)
            height = parameters.get("height", 512)
            if width < 1024 or height < 1024:
                issues.append(f"解像度が低い（{width}x{height}）。身体崩れが増える可能性")
                score -= 0.15
        
        # ステップ数が少ない場合
        steps = parameters.get("steps", 50) if parameters else 50
        if steps < 30:
            issues.append(f"ステップ数が少ない（{steps}）。身体崩れが増える可能性")
            score -= 0.1
        
        score = max(0.0, min(1.0, score))  # 0.0-1.0に制限
        
        return {
            "score": score,
            "issues": issues
        }
    
    def _evaluate_quality(self, image_path: str) -> Dict[str, Any]:
        """
        画像品質を評価（簡易版）
        """
        issues = []
        score = 0.8  # デフォルトスコア
        
        # ファイルサイズチェック（減点を弱体化：誤判定を減らす）
        try:
            file_size = os.path.getsize(image_path)
            if file_size < 100000:  # 100KB未満
                issues.append("ファイルサイズが小さい（圧縮や低品質の可能性）")
                score -= 0.05  # 旧: -0.2 → 新: -0.05（誤判定を減らす）
            elif file_size > 10000000:  # 10MB以上
                issues.append("ファイルサイズが大きい（最適化の余地あり）")
                score -= 0.02  # 旧: -0.05 → 新: -0.02
        except:
            pass
        
        score = max(0.0, min(1.0, score))
        
        return {
            "score": score,
            "issues": issues
        }
    
    def _evaluate_prompt_match(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """
        プロンプトとの一致度を評価（簡易版）
        
        実際の実装では、画像認識AIを使用
        """
        mismatches = []
        score = 0.7  # デフォルトスコア
        
        # 簡易チェック: プロンプトの長さと詳細度
        prompt_words = len(prompt.split())
        if prompt_words < 10:
            mismatches.append("プロンプトが短すぎる（詳細が不足）")
            score -= 0.1
        
        score = max(0.0, min(1.0, score))
        
        return {
            "score": score,
            "mismatches": mismatches
        }
    
    def _generate_improvements(self, evaluation: ImageEvaluation) -> List[str]:
        """改善提案を生成"""
        improvements = []
        
        # 身体崩れ対策
        if evaluation.anatomy_score < 0.7:
            improvements.append("身体崩れ対策タグを追加: perfect anatomy, correct anatomy")
            improvements.append("解像度を1024x1024以上に上げる")
            improvements.append("ステップ数を50以上に設定")
        
        # 品質改善
        if evaluation.quality_score < 0.7:
            improvements.append("品質タグを追加: masterpiece, best quality, ultra detailed")
            improvements.append("guidance_scaleを7.5に設定")
        
        # プロンプト改善
        if evaluation.prompt_match_score < 0.7:
            improvements.append("プロンプトをより詳細にする")
            improvements.append("具体的な描写を追加")
        
        return improvements


class AutoImprover:
    """自動改善器"""
    
    def __init__(self, evaluator: ImageEvaluator):
        """初期化"""
        self.evaluator = evaluator
        self.improvement_history: List[ImprovementPlan] = []
        self.learning_data: Dict[str, Any] = {
            "successful_prompts": [],
            "successful_parameters": [],
            "failed_patterns": []
        }
    
    def improve_generation(
        self,
        evaluation: ImageEvaluation,
        threshold: float = 0.7
    ) -> Optional[ImprovementPlan]:
        """
        生成を改善
        
        Args:
            evaluation: 評価結果
            threshold: 改善が必要なスコア閾値
        
        Returns:
            改善計画（改善不要の場合はNone）
        """
        if evaluation.overall_score >= threshold:
            logger.info(f"[改善不要] スコアが閾値以上: {evaluation.overall_score:.2f} >= {threshold}")
            return None
        
        logger.info(f"[改善開始] スコア: {evaluation.overall_score:.2f} < {threshold}")
        
        improvement = ImprovementPlan(
            original_prompt=evaluation.prompt,
            improved_prompt=self._improve_prompt(evaluation),
            original_negative_prompt=evaluation.negative_prompt,
            improved_negative_prompt=self._improve_negative_prompt(evaluation),
            original_parameters=evaluation.parameters,
            improved_parameters=self._improve_parameters(evaluation),
            reason=self._generate_improvement_reason(evaluation),
            expected_improvement=self._estimate_improvement(evaluation)
        )
        
        self.improvement_history.append(improvement)
        logger.info(f"[改善完了] 期待される改善度: {improvement.expected_improvement:.2f}")
        
        return improvement
    
    def _improve_prompt(self, evaluation: ImageEvaluation) -> str:
        """プロンプトを改善"""
        prompt = evaluation.prompt
        
        # 身体崩れ対策タグを追加
        if evaluation.anatomy_score < 0.7:
            from mufufu_config import ANATOMY_POSITIVE_TAGS
            if ANATOMY_POSITIVE_TAGS not in prompt:
                prompt = f"{ANATOMY_POSITIVE_TAGS}, {prompt}"
        
        # 品質タグを追加
        if evaluation.quality_score < 0.7:
            from mufufu_config import QUALITY_TAGS
            if QUALITY_TAGS not in prompt:
                prompt = f"{QUALITY_TAGS}, {prompt}"
        
        return prompt
    
    def _improve_negative_prompt(self, evaluation: ImageEvaluation) -> str:
        """ネガティブプロンプトを改善"""
        negative_prompt = evaluation.negative_prompt
        
        # 身体崩れ対策を強化
        if evaluation.anatomy_score < 0.7:
            from mufufu_config import MUFUFU_NEGATIVE_PROMPT
            if MUFUFU_NEGATIVE_PROMPT not in negative_prompt:
                if negative_prompt:
                    negative_prompt = f"{negative_prompt}, {MUFUFU_NEGATIVE_PROMPT}"
                else:
                    negative_prompt = MUFUFU_NEGATIVE_PROMPT
        
        return negative_prompt
    
    def _improve_parameters(self, evaluation: ImageEvaluation) -> Dict[str, Any]:
        """パラメータを改善"""
        params = evaluation.parameters.copy()
        
        # 身体崩れ対策
        if evaluation.anatomy_score < 0.7:
            from mufufu_config import OPTIMIZED_PARAMS
            params["steps"] = max(params.get("steps", 50), OPTIMIZED_PARAMS.get("steps", 50))
            params["guidance_scale"] = OPTIMIZED_PARAMS.get("guidance_scale", 7.5)
            params["width"] = max(params.get("width", 1024), OPTIMIZED_PARAMS.get("min_width", 1024))
            params["height"] = max(params.get("height", 1024), OPTIMIZED_PARAMS.get("min_height", 1024))
            params["sampler"] = OPTIMIZED_PARAMS.get("sampler", "dpmpp_2m")
            params["scheduler"] = OPTIMIZED_PARAMS.get("scheduler", "karras")
        
        return params
    
    def _generate_improvement_reason(self, evaluation: ImageEvaluation) -> str:
        """改善理由を生成"""
        reasons = []
        
        if evaluation.anatomy_score < 0.7:
            reasons.append(f"身体崩れスコアが低い（{evaluation.anatomy_score:.2f}）")
        
        if evaluation.quality_score < 0.7:
            reasons.append(f"品質スコアが低い（{evaluation.quality_score:.2f}）")
        
        if evaluation.prompt_match_score < 0.7:
            reasons.append(f"プロンプト一致度が低い（{evaluation.prompt_match_score:.2f}）")
        
        return "; ".join(reasons) if reasons else "総合スコアが低い"
    
    def _estimate_improvement(self, evaluation: ImageEvaluation) -> float:
        """期待される改善度を推定"""
        improvement = 0.0
        
        # 身体崩れ対策による改善
        if evaluation.anatomy_score < 0.7:
            improvement += 0.2
        
        # 品質改善による改善
        if evaluation.quality_score < 0.7:
            improvement += 0.15
        
        # プロンプト改善による改善
        if evaluation.prompt_match_score < 0.7:
            improvement += 0.1
        
        return min(1.0, improvement)
    
    def learn_from_result(
        self,
        evaluation: ImageEvaluation,
        improvement: Optional[ImprovementPlan],
        new_evaluation: Optional[ImageEvaluation] = None
    ):
        """
        結果から学習
        
        Args:
            evaluation: 元の評価
            improvement: 改善計画
            new_evaluation: 改善後の評価（あれば）
        """
        if not improvement:
            return
        
        # 改善が成功した場合
        if new_evaluation and new_evaluation.overall_score > evaluation.overall_score:
            logger.info(f"[学習] 改善成功: {evaluation.overall_score:.2f} -> {new_evaluation.overall_score:.2f}")
            
            # 成功パターンを記録
            self.learning_data["successful_prompts"].append({
                "original": evaluation.prompt,
                "improved": improvement.improved_prompt,
                "score_improvement": new_evaluation.overall_score - evaluation.overall_score
            })
            
            self.learning_data["successful_parameters"].append({
                "original": evaluation.parameters,
                "improved": improvement.improved_parameters,
                "score_improvement": new_evaluation.overall_score - evaluation.overall_score
            })
        else:
            # 失敗パターンを記録
            logger.info(f"[学習] 改善失敗または未検証")
            self.learning_data["failed_patterns"].append({
                "evaluation": asdict(evaluation),
                "improvement": asdict(improvement)
            })


class AutoReflectionImprovementSystem:
    """自動反省・改善システム"""
    
    def __init__(self, db_path: str = "auto_improvement.db"):
        """初期化"""
        self.evaluator = ImageEvaluator()
        self.improver = AutoImprover(self.evaluator)
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """データベースを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 評価履歴テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT,
                prompt TEXT,
                negative_prompt TEXT,
                model TEXT,
                parameters TEXT,
                overall_score REAL,
                anatomy_score REAL,
                quality_score REAL,
                prompt_match_score REAL,
                anatomy_issues TEXT,
                quality_issues TEXT,
                prompt_mismatches TEXT,
                improvements TEXT,
                timestamp TEXT
            )
        """)
        
        # 改善履歴テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS improvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluation_id INTEGER,
                original_prompt TEXT,
                improved_prompt TEXT,
                original_negative_prompt TEXT,
                improved_negative_prompt TEXT,
                original_parameters TEXT,
                improved_parameters TEXT,
                reason TEXT,
                expected_improvement REAL,
                actual_improvement REAL,
                timestamp TEXT,
                FOREIGN KEY (evaluation_id) REFERENCES evaluations(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def process_generated_image(
        self,
        image_path: str,
        prompt: str,
        negative_prompt: str = "",
        model: str = "",
        parameters: Dict[str, Any] = None,
        auto_improve: bool = True,
        threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        生成された画像を処理（評価→改善）
        
        Args:
            image_path: 画像パス
            prompt: プロンプト
            negative_prompt: ネガティブプロンプト
            model: モデル名
            parameters: 生成パラメータ
            auto_improve: 自動改善を実行するか
            threshold: 改善閾値
        
        Returns:
            処理結果
        """
        logger.info(f"[自動反省開始] {image_path}")
        
        # 1. 評価
        evaluation = self.evaluator.evaluate_image(
            image_path=image_path,
            prompt=prompt,
            negative_prompt=negative_prompt,
            model=model,
            parameters=parameters or {}
        )
        
        # データベースに保存
        self._save_evaluation(evaluation)
        
        result = {
            "evaluation": asdict(evaluation),
            "improvement": None,
            "should_regenerate": False
        }
        
        # 2. 改善（必要に応じて）
        if auto_improve:
            improvement = self.improver.improve_generation(evaluation, threshold)
            
            if improvement:
                result["improvement"] = asdict(improvement)
                result["should_regenerate"] = True
                
                # データベースに保存
                self._save_improvement(evaluation, improvement)
        
        logger.info(f"[自動反省完了] 総合スコア: {evaluation.overall_score:.2f}, 再生成推奨: {result['should_regenerate']}")
        
        return result
    
    def _save_evaluation(self, evaluation: ImageEvaluation):
        """評価をデータベースに保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO evaluations (
                image_path, prompt, negative_prompt, model, parameters,
                overall_score, anatomy_score, quality_score, prompt_match_score,
                anatomy_issues, quality_issues, prompt_mismatches, improvements, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            evaluation.image_path,
            evaluation.prompt,
            evaluation.negative_prompt,
            evaluation.model,
            json.dumps(evaluation.parameters),
            evaluation.overall_score,
            evaluation.anatomy_score,
            evaluation.quality_score,
            evaluation.prompt_match_score,
            json.dumps(evaluation.anatomy_issues),
            json.dumps(evaluation.quality_issues),
            json.dumps(evaluation.prompt_mismatches),
            json.dumps(evaluation.improvements),
            evaluation.timestamp
        ))
        
        conn.commit()
        conn.close()
    
    def _save_improvement(self, evaluation: ImageEvaluation, improvement: ImprovementPlan):
        """改善計画をデータベースに保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 最新の評価IDを取得
        cursor.execute("SELECT id FROM evaluations ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        evaluation_id = row[0] if row else None
        
        cursor.execute("""
            INSERT INTO improvements (
                evaluation_id, original_prompt, improved_prompt,
                original_negative_prompt, improved_negative_prompt,
                original_parameters, improved_parameters,
                reason, expected_improvement, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            evaluation_id,
            improvement.original_prompt,
            improvement.improved_prompt,
            improvement.original_negative_prompt,
            improvement.improved_negative_prompt,
            json.dumps(improvement.original_parameters),
            json.dumps(improvement.improved_parameters),
            improvement.reason,
            improvement.expected_improvement,
            improvement.timestamp
        ))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 評価数
        cursor.execute("SELECT COUNT(*) FROM evaluations")
        total_evaluations = cursor.fetchone()[0]
        
        # 平均スコア
        cursor.execute("SELECT AVG(overall_score) FROM evaluations")
        avg_score = cursor.fetchone()[0] or 0.0
        
        # 改善数
        cursor.execute("SELECT COUNT(*) FROM improvements")
        total_improvements = cursor.fetchone()[0]
        
        # 低スコア数（閾値以下）
        cursor.execute("SELECT COUNT(*) FROM evaluations WHERE overall_score < 0.7")
        low_score_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_evaluations": total_evaluations,
            "average_score": avg_score,
            "total_improvements": total_improvements,
            "low_score_count": low_score_count,
            "improvement_rate": total_improvements / total_evaluations if total_evaluations > 0 else 0.0
        }


# グローバルインスタンス
_auto_system = None

def get_auto_reflection_system() -> AutoReflectionImprovementSystem:
    """自動反省・改善システムのシングルトンインスタンスを取得"""
    global _auto_system
    if _auto_system is None:
        _auto_system = AutoReflectionImprovementSystem()
    return _auto_system
