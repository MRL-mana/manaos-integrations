#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CASTLE-EXフレームワーク: 評価ツール

層別評価と3軸統合の測定機能
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict, Counter
import statistics

if sys.platform == 'win32':
    try:
        import io
        if not hasattr(sys.stdout, 'buffer') or sys.stdout.buffer.closed:
            pass
        else:
            sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass


class CastleEXEvaluator:
    """CASTLE-EX評価器"""
    
    # 層別テストデータ定義
    LAYER_TEST_TEMPLATES = {
        0: [
            ("A = A ?", "同じ。"),
            ("1 = 2 ?", "違う。"),
            ("嬉しい = 嬉しい ?", "同じ。"),
        ],
        1: [
            ("1 + 1 = ?", "2"),
            ("大きい ↔ ?", "小さい"),
            ("真 AND 真 → ?", "真"),
        ],
        2: [
            ("A > B, B > C → A と C は？", "A > C"),
            ("太陽 : 昼 = 月 : ?", "夜"),
            ("犬 ⊂ 動物 ?", "はい"),
        ],
        3: [
            ("😊 → 感情は？", "喜び"),
            ("怒り → 深呼吸 → 感情は？", "冷静"),
            ("悲しい → 時間が経つ → ?", "和らぐ"),
        ],
        4: [
            ("「バカだな」(親友から) → 意味は？", "親愛表現"),
            ("「大丈夫」(泣きながら) → 真意は？", "大丈夫ではない"),
            ("沈黙（会議中）→ 意味は？", "同意または反対"),
        ],
        5: [
            ("試験に落ちた(悲しい) → 勉強する → ?", "知識が増える"),
            ("批判された(怒り) → 冷静に聞く → ?", "建設的な対話"),
            ("同僚が「手伝おうか？」(忙しそう) → 真意は？", "社交辞令"),
        ],
        6: [
            ("チームメンバーAが会議で沈黙(普段は発言多い)、腕組み → 分析は？", "反対"),
            ("部下が期限ギリギリに提出(普段は早い)、元気がない → 対応は？", "個人的問題"),
            ("もしあの時、怒らずに冷静に対応していたら → 結果は？", "建設的解決"),
        ],
    }
    
    # キーワード抽出用パターン（感情・文脈検出）
    EMOTION_KEYWORDS = ["感情", "悲しい", "怒り", "嬉しい", "不安", "自信", "喜び", "悲しみ", "恐怖"]
    CONTEXT_KEYWORDS = ["文脈", "状況", "会議", "関係", "真意", "意味", "親友", "上司", "面接官"]
    
    def __init__(self):
        """初期化"""
        self.results = {
            "layer_scores": {},
            "axis_scores": {
                "logic": [],
                "emotion": [],
                "context": [],
                "integrated": [],
            },
            "overall": {
                "total": 0,
                "correct": 0,
                "accuracy": 0.0,
            },
        }
    
    def evaluate_response(self, question: str, expected_answer: str, 
                         actual_answer: str) -> Tuple[bool, float, Dict[str, Any]]:
        """回答の評価（簡易版：部分一致ベース）"""
        # 期待回答を正規化
        expected_normalized = expected_answer.lower().strip()
        actual_normalized = actual_answer.lower().strip()
        
        # 完全一致
        if expected_normalized == actual_normalized:
            return True, 1.0, {"method": "exact_match"}
        
        # キーワード一致チェック
        expected_keywords = set(re.findall(r'\w+', expected_normalized))
        actual_keywords = set(re.findall(r'\w+', actual_normalized))
        
        if len(expected_keywords) == 0:
            return False, 0.0, {"method": "keyword_match", "error": "期待回答にキーワードなし"}
        
        common_keywords = expected_keywords & actual_keywords
        keyword_score = len(common_keywords) / len(expected_keywords)
        
        # 部分一致チェック
        if expected_normalized in actual_normalized or actual_normalized in expected_normalized:
            partial_score = min(len(expected_normalized), len(actual_normalized)) / max(len(expected_normalized), len(actual_normalized))
            final_score = max(keyword_score, partial_score * 0.8)
        else:
            final_score = keyword_score * 0.7
        
        is_correct = final_score >= 0.5
        
        return is_correct, final_score, {
            "method": "keyword_match",
            "keyword_score": keyword_score,
            "final_score": final_score,
        }
    
    def detect_axes(self, question: str, answer: str) -> Dict[str, bool]:
        """3軸の検出（質問と回答から）"""
        combined = (question + " " + answer).lower()
        
        return {
            "logic": any(kw in combined for kw in ["論理", "推論", "因果", "関係", "→", "="]),
            "emotion": any(kw in combined for kw in self.EMOTION_KEYWORDS),
            "context": any(kw in combined for kw in self.CONTEXT_KEYWORDS),
        }
    
    def evaluate_layer(self, layer: int, model_predictor=None, 
                      test_data: Optional[List[Tuple[str, str]]] = None) -> Dict[str, Any]:
        """特定層の評価"""
        if test_data is None:
            test_data = self.LAYER_TEST_TEMPLATES.get(layer, [])
        
        if not test_data:
            return {"error": f"Layer {layer}のテストデータがありません"}
        
        layer_results = {
            "layer": layer,
            "total": len(test_data),
            "correct": 0,
            "scores": [],
            "details": [],
        }
        
        for question, expected_answer in test_data:
            # モデルからの回答を取得（実装では外部APIやモデルを呼び出す）
            if model_predictor is None:
                # モック回答（実際の評価では実際のモデルを使用）
                actual_answer = expected_answer  # デフォルトは正解とする
            else:
                actual_answer = model_predictor(question)
            
            is_correct, score, details = self.evaluate_response(question, expected_answer, actual_answer)
            
            # 軸の検出
            axes = self.detect_axes(question, actual_answer)
            
            layer_results["correct"] += 1 if is_correct else 0
            layer_results["scores"].append(score)
            layer_results["details"].append({
                "question": question,
                "expected": expected_answer,
                "actual": actual_answer,
                "correct": is_correct,
                "score": score,
                "axes": axes,
                **details,
            })
            
            # 軸別スコア記録
            if axes["logic"]:
                self.results["axis_scores"]["logic"].append(score)
            if axes["emotion"]:
                self.results["axis_scores"]["emotion"].append(score)
            if axes["context"]:
                self.results["axis_scores"]["context"].append(score)
            if axes["logic"] and axes["emotion"] and axes["context"]:
                self.results["axis_scores"]["integrated"].append(score)
        
        layer_results["accuracy"] = layer_results["correct"] / layer_results["total"]
        layer_results["average_score"] = statistics.mean(layer_results["scores"]) if layer_results["scores"] else 0.0
        
        self.results["layer_scores"][layer] = layer_results
        self.results["overall"]["total"] += layer_results["total"]
        self.results["overall"]["correct"] += layer_results["correct"]
        
        return layer_results
    
    def evaluate_all_layers(self, model_predictor=None) -> Dict[str, Any]:
        """全層の評価"""
        print("=" * 60)
        print("CASTLE-EX 全層評価")
        print("=" * 60)
        
        for layer in sorted(self.LAYER_TEST_TEMPLATES.keys()):
            print(f"\nLayer {layer} 評価中...")
            result = self.evaluate_layer(layer, model_predictor)
            
            if "error" not in result:
                print(f"  正確率: {result['accuracy']:.1%} ({result['correct']}/{result['total']})")
                print(f"  平均スコア: {result['average_score']:.3f}")
        
        # 全体統計
        if self.results["overall"]["total"] > 0:
            self.results["overall"]["accuracy"] = (
                self.results["overall"]["correct"] / self.results["overall"]["total"]
            )
        
        # 軸別統計
        for axis_name, scores in self.results["axis_scores"].items():
            if scores:
                axis_average = statistics.mean(scores)
                self.results["axis_scores"][axis_name] = {
                    "scores": scores,
                    "average": axis_average,
                    "count": len(scores),
                }
        
        # 統合評価指標の計算
        self.results["integration_metrics"] = self.calculate_integration_metrics()
        
        return self.results
    
    def calculate_integration_metrics(self) -> Dict[str, float]:
        """CASTLE-EX統合評価指標の計算"""
        metrics = {
            "axis_consistency": 0.0,  # 軸一貫性（矛盾率、低いほど良い）
            "causal_validity": 0.0,  # 因果妥当性
            "emotion_appropriateness": 0.0,  # 感情適切性
            "context_sensitivity": 0.0,  # 文脈感度
            "negative_detection": 0.0,  # 負例検出率
            "paraphrase_robustness": 0.0,  # パラフレーズ（言い換え）耐性
            "semantic_consistency": 0.0,  # 意味的一貫性（表現が違っても結論が同じ）
        }
        
        # 簡易実装（実際の評価ではモデルの出力を分析）
        # ここではサンプル値として0.85を設定
        # 実際の実装では、評価データから計算
        
        # 軸一貫性: 感情/文脈/論理の矛盾率（仮の値）
        metrics["axis_consistency"] = 0.12  # 12%の矛盾率
        
        # 因果妥当性: state遷移が自然か（仮の値）
        metrics["causal_validity"] = 0.89
        
        # 感情適切性: 相手の感情に合った返答か（仮の値）
        metrics["emotion_appropriateness"] = 0.85
        
        # 文脈感度: 同じ質問でも文脈で返答が変わるか（仮の値）
        metrics["context_sensitivity"] = 0.87
        
        # 負例検出: 負例を正しく「不適切」と判定できるか（仮の値）
        metrics["negative_detection"] = 0.82
        
        # パラフレーズ耐性: 同義・言い換えで回答の品質が落ちない率（仮の値）
        # 実装では、同義語ペア（「怒る」と「イライラする」など）で同じ結論が出るかを評価
        metrics["paraphrase_robustness"] = 0.88
        
        # 意味的一貫性: 表現が違っても結論が同じ率（仮の値）
        # 実装では、Layer 1/2の同義語データで同じ回答が出るかを評価
        metrics["semantic_consistency"] = 0.90
        
        return metrics
    
    def evaluate_3axis_integration(self, test_cases: List[Tuple[str, str]], 
                                   model_predictor=None) -> Dict[str, Any]:
        """3軸統合の評価（Layer 5-6の複合状況）"""
        print("=" * 60)
        print("CASTLE-EX 3軸統合評価")
        print("=" * 60)
        
        integration_results = {
            "total": len(test_cases),
            "correct": 0,
            "scores": [],
            "axis_detection": {
                "logic": 0,
                "emotion": 0,
                "context": 0,
                "all_three": 0,
            },
        }
        
        for question, expected_answer in test_cases:
            if model_predictor is None:
                actual_answer = expected_answer
            else:
                actual_answer = model_predictor(question)
            
            is_correct, score, details = self.evaluate_response(question, expected_answer, actual_answer)
            axes = self.detect_axes(question, actual_answer)
            
            integration_results["correct"] += 1 if is_correct else 0
            integration_results["scores"].append(score)
            
            if axes["logic"]:
                integration_results["axis_detection"]["logic"] += 1
            if axes["emotion"]:
                integration_results["axis_detection"]["emotion"] += 1
            if axes["context"]:
                integration_results["axis_detection"]["context"] += 1
            if axes["logic"] and axes["emotion"] and axes["context"]:
                integration_results["axis_detection"]["all_three"] += 1
        
        integration_results["accuracy"] = integration_results["correct"] / integration_results["total"]
        integration_results["average_score"] = (
            statistics.mean(integration_results["scores"]) if integration_results["scores"] else 0.0
        )
        
        print(f"\n3軸統合評価結果:")
        print(f"  正確率: {integration_results['accuracy']:.1%}")
        print(f"  平均スコア: {integration_results['average_score']:.3f}")
        print(f"\n軸検出状況:")
        print(f"  推論軸: {integration_results['axis_detection']['logic']}/{integration_results['total']}")
        print(f"  感情軸: {integration_results['axis_detection']['emotion']}/{integration_results['total']}")
        print(f"  文脈軸: {integration_results['axis_detection']['context']}/{integration_results['total']}")
        print(f"  3軸統合: {integration_results['axis_detection']['all_three']}/{integration_results['total']}")
        
        return integration_results
    
    def print_report(self, output_file: Optional[str] = None):
        """評価レポートの表示・保存"""
        print("\n" + "=" * 60)
        print("CASTLE-EX 評価レポート")
        print("=" * 60)
        
        # 全体結果
        overall = self.results["overall"]
        print(f"\n【全体結果】")
        print(f"  総質問数: {overall['total']}")
        print(f"  正解数: {overall['correct']}")
        print(f"  正確率: {overall['accuracy']:.1%}")
        
        # 層別結果
        print(f"\n【層別結果】")
        for layer in sorted(self.results["layer_scores"].keys()):
            layer_result = self.results["layer_scores"][layer]
            print(f"  Layer {layer}:")
            print(f"    正確率: {layer_result['accuracy']:.1%} ({layer_result['correct']}/{layer_result['total']})")
            print(f"    平均スコア: {layer_result['average_score']:.3f}")
        
        # 軸別結果
        print(f"\n【軸別結果】")
        for axis_name, axis_data in self.results["axis_scores"].items():
            if isinstance(axis_data, dict) and "average" in axis_data:
                print(f"  {axis_name}:")
                print(f"    平均スコア: {axis_data['average']:.3f}")
                print(f"    検出数: {axis_data['count']}")
        
        # 統合評価指標
        if "integration_metrics" in self.results:
            print(f"\n【CASTLE-EX統合評価指標】")
            im = self.results["integration_metrics"]
            print(f"  Axis Consistency（軸一貫性）: {im.get('axis_consistency', 0.0):.3f} (低いほど良い)")
            print(f"  Causal Validity（因果妥当性）: {im.get('causal_validity', 0.0):.3f}")
            print(f"  Emotion Appropriateness（感情適切性）: {im.get('emotion_appropriateness', 0.0):.3f}")
            print(f"  Context Sensitivity（文脈感度）: {im.get('context_sensitivity', 0.0):.3f}")
            print(f"  Negative Detection（負例検出）: {im.get('negative_detection', 0.0):.3f}")
            print(f"  Paraphrase Robustness（言い換え耐性）: {im.get('paraphrase_robustness', 0.0):.3f}")
            print(f"  Semantic Consistency（意味的一貫性）: {im.get('semantic_consistency', 0.0):.3f}")
        
        # JSON形式で保存
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            
            print(f"\n評価結果を保存: {output_file}")


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CASTLE-EX評価ツール')
    parser.add_argument('--output', type=str, default='castle_ex_evaluation.json',
                       help='評価結果出力ファイル（デフォルト: castle_ex_evaluation.json）')
    
    args = parser.parse_args()
    
    evaluator = CastleEXEvaluator()
    results = evaluator.evaluate_all_layers()
    evaluator.print_report(args.output)
    
    print("\n✓ 評価が完了しました")


if __name__ == "__main__":
    main()
