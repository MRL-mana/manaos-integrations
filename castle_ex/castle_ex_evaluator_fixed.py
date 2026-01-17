#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CASTLE-EXフレームワーク: 評価ツール（修正版）
実際のモデルを評価し、標準フォーマット（evaluation_v1_0.json）で出力
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Callable
from collections import defaultdict, Counter
import statistics

if sys.platform == 'win32':
    try:
        import io
        if not hasattr(sys.stdout, 'buffer') or sys.stdout.buffer.closed:
            pass
        else:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except (AttributeError, ValueError):
        pass


class CastleEXEvaluator:
    """CASTLE-EX評価器（修正版：実際のモデル評価対応）"""
    
    def __init__(self, model_predictor: Optional[Callable[[str], str]] = None):
        """
        初期化
        
        Args:
            model_predictor: モデル予測関数（prompt文字列を受け取り、予測テキストを返す）
                            Noneの場合はデバッグモード（goldをそのまま返す）
        """
        self.model_predictor = model_predictor
        self.results = {
            "dataset": "",
            "seed": "castle_ex_v1_0",
            "overall": {
                "negative_detection": 0.0,
                "axis_consistency": 0.0,
                "context_sensitivity": 0.0,
                "emotion_appropriateness": 0.0,
                "paraphrase_robustness": 0.0,
                "causal_validity": 0.0
            },
            "by_layer": {},
            "by_axes_combo": {},
            "negative_by_error_type": {},
            "debug_samples": []  # デバッグ用：最初の5サンプルのgold/pred
        }
    
    def extract_gold_answer(self, item: Dict) -> Optional[str]:
        """
        JSONLアイテムから正解（gold answer）を抽出
        
        Args:
            item: JSONLアイテム（messages形式）
        
        Returns:
            正解テキスト（assistantの最後のメッセージ）、見つからない場合はNone
        """
        messages = item.get("messages", [])
        if not messages:
            return None
        
        # messagesの最後のassistantメッセージを取得
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                return msg.get("content", "")
        
        return None
    
    def extract_user_prompt(self, item: Dict) -> str:
        """
        JSONLアイテムからユーザープロンプトを抽出（モデル入力用）
        
        Args:
            item: JSONLアイテム（messages形式）
        
        Returns:
            ユーザープロンプト（assistantを除いたmessagesをテキスト化）
        """
        messages = item.get("messages", [])
        if not messages:
            return ""
        
        # assistantを除いたmessagesを結合
        prompt_parts = []
        for msg in messages:
            if msg.get("role") == "assistant":
                break  # assistant以降は無視
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                prompt_parts.append(f"{role}: {content}")
        
        return "\n".join(prompt_parts)
    
    def predict_with_model(self, prompt: str) -> str:
        """
        モデルで予測を生成
        
        Args:
            prompt: 入力プロンプト
        
        Returns:
            予測テキスト（失敗時は空文字列）
        """
        if self.model_predictor is None:
            # デバッグモード：空文字列を返す（評価が動いてるか確認用）
            return ""
        
        try:
            prediction = self.model_predictor(prompt)
            if prediction is None:
                return ""
            return str(prediction).strip()
        except Exception as e:
            print(f"[ERROR] モデル予測エラー: {e}", file=sys.stderr)
            return ""
    
    def evaluate_item(self, item: Dict, item_index: int) -> Dict[str, Any]:
        """
        1アイテムを評価
        
        Args:
            item: JSONLアイテム
            item_index: アイテムのインデックス（デバッグ用）
        
        Returns:
            評価結果辞書
        """
        # Gold answerを抽出
        gold_answer = self.extract_gold_answer(item)
        if gold_answer is None:
            return {
                "error": "gold_answer not found",
                "item_index": item_index
            }
        
        # User promptを抽出
        user_prompt = self.extract_user_prompt(item)
        if not user_prompt:
            return {
                "error": "user_prompt not found",
                "item_index": item_index
            }
        
        # モデルで予測
        pred_answer = self.predict_with_model(user_prompt)
        
        # デバッグ用：最初の5サンプルを保存
        if len(self.results["debug_samples"]) < 5:
            self.results["debug_samples"].append({
                "item_index": item_index,
                "layer": item.get("layer", -1),
                "user_prompt": user_prompt[:100] + "..." if len(user_prompt) > 100 else user_prompt,
                "gold_answer": gold_answer[:100] + "..." if len(gold_answer) > 100 else gold_answer,
                "pred_answer": pred_answer[:100] + "..." if len(pred_answer) > 100 else pred_answer,
                "pred_empty": len(pred_answer) == 0
            })
        
        # 評価（簡易版：部分一致ベース）
        is_correct, score = self.evaluate_response(gold_answer, pred_answer)
        
        # メタデータを取得
        layer = item.get("layer", -1)
        axes = item.get("axes", [])
        positive = item.get("positive", True)
        error_type = item.get("error_type")
        
        return {
            "item_index": item_index,
            "layer": layer,
            "axes": axes,
            "positive": positive,
            "error_type": error_type,
            "gold_answer": gold_answer,
            "pred_answer": pred_answer,
            "is_correct": is_correct,
            "score": score
        }
    
    def evaluate_response(self, gold: str, pred: str) -> Tuple[bool, float]:
        """
        回答の評価（簡易版：部分一致ベース）
        
        Args:
            gold: 正解テキスト
            pred: 予測テキスト
        
        Returns:
            (is_correct, score) のタプル
        """
        if not pred:
            return False, 0.0
        
        # 正規化
        gold_normalized = gold.lower().strip()
        pred_normalized = pred.lower().strip()
        
        # 完全一致
        if gold_normalized == pred_normalized:
            return True, 1.0
        
        # キーワード一致チェック
        gold_keywords = set(re.findall(r'\w+', gold_normalized))
        pred_keywords = set(re.findall(r'\w+', pred_normalized))
        
        if len(gold_keywords) == 0:
            return False, 0.0
        
        common_keywords = gold_keywords & pred_keywords
        keyword_score = len(common_keywords) / len(gold_keywords)
        
        # 部分一致チェック
        if gold_normalized in pred_normalized or pred_normalized in gold_normalized:
            partial_score = min(len(gold_normalized), len(pred_normalized)) / max(len(gold_normalized), len(pred_normalized))
            final_score = max(keyword_score, partial_score * 0.8)
        else:
            final_score = keyword_score * 0.7
        
        is_correct = final_score >= 0.5
        
        return is_correct, final_score
    
    def evaluate_dataset(self, eval_file: str, max_samples: Optional[int] = None) -> Dict[str, Any]:
        """
        評価データセット全体を評価
        
        Args:
            eval_file: 評価データセットJSONLファイル
            max_samples: 最大評価サンプル数（Noneの場合は全件、デバッグ用）
        
        Returns:
            評価結果辞書（標準フォーマット）
        """
        eval_path = Path(eval_file)
        if not eval_path.exists():
            raise FileNotFoundError(f"評価データセットが見つかりません: {eval_file}")
        
        self.results["dataset"] = eval_file
        
        # データセット読み込み
        print(f"評価データセット読み込み: {eval_file}")
        all_items = []
        with open(eval_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    all_items.append(json.loads(line))
        
        if max_samples:
            all_items = all_items[:max_samples]
            print(f"  デバッグモード: 最初の{max_samples}件のみ評価")
        
        print(f"  総データ数: {len(all_items)}件")
        
        # 各アイテムを評価
        print(f"\n評価実行中...")
        item_results = []
        for i, item in enumerate(all_items):
            if (i + 1) % 50 == 0:
                print(f"  進捗: {i + 1}/{len(all_items)}件")
            
            result = self.evaluate_item(item, i)
            if "error" not in result:
                item_results.append(result)
            else:
                print(f"  [WARN] アイテム{i}: {result.get('error')}")
        
        print(f"  評価完了: {len(item_results)}件")
        
        # 統計を計算
        self.calculate_statistics(item_results)
        
        return self.results
    
    def calculate_statistics(self, item_results: List[Dict[str, Any]]):
        """
        評価結果から統計を計算（標準フォーマットに変換）
        
        Args:
            item_results: 評価結果のリスト
        """
        if not item_results:
            print("[WARN] 評価結果が空です")
            return
        
        # Layer別統計
        layer_stats = defaultdict(lambda: {"total": 0, "correct": 0, "scores": []})
        for result in item_results:
            layer = result.get("layer", -1)
            layer_stats[layer]["total"] += 1
            if result.get("is_correct", False):
                layer_stats[layer]["correct"] += 1
            layer_stats[layer]["scores"].append(result.get("score", 0.0))
        
        self.results["by_layer"] = {
            str(layer): {
                "acc": layer_stats[layer]["correct"] / layer_stats[layer]["total"] if layer_stats[layer]["total"] > 0 else 0.0
            }
            for layer in sorted(layer_stats.keys())
        }
        
        # Axes組み合わせ別統計
        axes_stats = defaultdict(lambda: {"total": 0, "correct": 0, "scores": []})
        for result in item_results:
            axes = result.get("axes", [])
            axes_key = ",".join(sorted(axes)) if axes else "unknown"
            axes_stats[axes_key]["total"] += 1
            if result.get("is_correct", False):
                axes_stats[axes_key]["correct"] += 1
            axes_stats[axes_key]["scores"].append(result.get("score", 0.0))
        
        self.results["by_axes_combo"] = {
            axes_key: {
                "acc": axes_stats[axes_key]["correct"] / axes_stats[axes_key]["total"] if axes_stats[axes_key]["total"] > 0 else 0.0
            }
            for axes_key in sorted(axes_stats.keys())
        }
        
        # Negative by error_type統計
        negative_results = [r for r in item_results if not r.get("positive", True)]
        error_type_stats = defaultdict(lambda: {"total": 0, "correct": 0, "scores": []})
        for result in negative_results:
            error_type = result.get("error_type")
            if error_type:
                error_type_stats[error_type]["total"] += 1
                if result.get("is_correct", False):
                    error_type_stats[error_type]["correct"] += 1
                error_type_stats[error_type]["scores"].append(result.get("score", 0.0))
        
        # Precision/Recall計算（簡易版：correct/totalをprecisionとして使用）
        self.results["negative_by_error_type"] = {
            error_type: {
                "precision": error_type_stats[error_type]["correct"] / error_type_stats[error_type]["total"] if error_type_stats[error_type]["total"] > 0 else 0.0,
                "recall": error_type_stats[error_type]["correct"] / error_type_stats[error_type]["total"] if error_type_stats[error_type]["total"] > 0 else 0.0
            }
            for error_type in sorted(error_type_stats.keys())
        }
        
        # Overall指標の計算（簡易版）
        total = len(item_results)
        correct = sum(1 for r in item_results if r.get("is_correct", False))
        avg_score = statistics.mean([r.get("score", 0.0) for r in item_results]) if item_results else 0.0
        
        # Negative Detection: 負例の正解率
        negative_total = len(negative_results)
        negative_correct = sum(1 for r in negative_results if r.get("is_correct", False))
        self.results["overall"]["negative_detection"] = negative_correct / negative_total if negative_total > 0 else 0.0
        
        # その他の指標は簡易版（実際の評価ではより詳細な計算が必要）
        self.results["overall"]["axis_consistency"] = avg_score  # 簡易版
        self.results["overall"]["context_sensitivity"] = avg_score  # 簡易版
        self.results["overall"]["emotion_appropriateness"] = avg_score  # 簡易版
        self.results["overall"]["paraphrase_robustness"] = avg_score  # 簡易版
        self.results["overall"]["causal_validity"] = avg_score  # 簡易版
        
        print(f"\n統計計算完了:")
        print(f"  総数: {total}件")
        print(f"  正解: {correct}件 ({correct/total*100:.1f}%)")
        print(f"  平均スコア: {avg_score:.3f}")
        print(f"  負例検出: {self.results['overall']['negative_detection']:.3f}")
    
    def save_results(self, output_file: str):
        """
        評価結果を標準フォーマットで保存
        
        Args:
            output_file: 出力ファイル名
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n[OK] 評価結果を保存: {output_file}")
        
        # デバッグサンプルを表示
        if self.results.get("debug_samples"):
            print(f"\n[デバッグ] 最初の5サンプル:")
            for sample in self.results["debug_samples"]:
                print(f"  サンプル{sample['item_index']}:")
                print(f"    Layer: {sample['layer']}")
                print(f"    Gold: {sample['gold_answer']}")
                print(f"    Pred: {sample['pred_answer']}")
                print(f"    Pred空: {sample['pred_empty']}")


def create_dummy_model_predictor() -> Callable[[str], str]:
    """
    ダミーモデル予測関数（デバッグ用）
    実際のモデルがない場合のテスト用
    
    Returns:
        予測関数
    """
    def dummy_predict(prompt: str) -> str:
        # デバッグ用：プロンプトの一部を返す
        return "ダミー予測: " + prompt[:50] + "..."
    
    return dummy_predict


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CASTLE-EX評価ツール（修正版）')
    parser.add_argument('--eval-data', type=str, required=True, help='評価データセットJSONLファイル')
    parser.add_argument('--output', type=str, default='evaluation_v1_0.json', help='評価結果出力ファイル（デフォルト: evaluation_v1_0.json）')
    parser.add_argument('--model', type=str, default=None, help='モデルパス/チェックポイント（Ollama: モデル名、Transformers: モデルパス）')
    parser.add_argument('--model-type', type=str, default='dummy', choices=['dummy', 'ollama', 'transformers'], help='モデルタイプ（デフォルト: dummy）')
    parser.add_argument('--ollama-url', type=str, default='http://localhost:11434/api/generate', help='Ollama API URL（model-type=ollamaの場合）')
    parser.add_argument('--max-samples', type=int, default=None, help='最大評価サンプル数（デバッグ用、Noneの場合は全件）')
    
    args = parser.parse_args()
    
    # モデル予測関数を取得
    model_predictor = None
    
    if args.model_type == 'dummy':
        print("[WARN] ダミーモデルを使用します（実際の評価には使用しないでください）")
        model_predictor = create_dummy_model_predictor()
    elif args.model_type == 'ollama':
        # Ollama統合
        try:
            import requests
            ollama_url = args.ollama_url
            model_name = args.model if args.model else "qwen2.5:14b"
            
            def ollama_predict(prompt: str) -> str:
                try:
                    response = requests.post(
                        ollama_url,
                        json={
                            "model": model_name,
                            "prompt": prompt,
                            "stream": False
                        },
                        timeout=60
                    )
                    if response.status_code == 200:
                        result = response.json()
                        return result.get("response", "").strip()
                    else:
                        print(f"[ERROR] Ollama API エラー: {response.status_code}", file=sys.stderr)
                        return ""
                except Exception as e:
                    print(f"[ERROR] Ollama呼び出しエラー: {e}", file=sys.stderr)
                    return ""
            
            model_predictor = ollama_predict
            print(f"[OK] Ollamaモデルを使用: {model_name}")
        except ImportError:
            print("[ERROR] requestsライブラリがインストールされていません", file=sys.stderr)
            return 1
    elif args.model_type == 'transformers':
        # Transformers統合
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            model_path = args.model if args.model else "microsoft/DialoGPT-medium"
            print(f"[INFO] モデル読み込み中: {model_path}")
            
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForCausalLM.from_pretrained(model_path)
            
            # GPU使用可能な場合は使用
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = model.to(device)
            model.eval()
            
            def transformers_predict(prompt: str) -> str:
                try:
                    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
                    inputs = {k: v.to(device) for k, v in inputs.items()}
                    
                    with torch.no_grad():
                        outputs = model.generate(
                            **inputs,
                            max_length=512,
                            num_return_sequences=1,
                            pad_token_id=tokenizer.eos_token_id
                        )
                    
                    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
                    # プロンプト部分を除去
                    if generated_text.startswith(prompt):
                        generated_text = generated_text[len(prompt):].strip()
                    return generated_text
                except Exception as e:
                    print(f"[ERROR] Transformers生成エラー: {e}", file=sys.stderr)
                    return ""
            
            model_predictor = transformers_predict
            print(f"[OK] Transformersモデルを使用: {model_path} (device: {device})")
        except ImportError:
            print("[ERROR] transformersライブラリがインストールされていません", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"[ERROR] モデル読み込みエラー: {e}", file=sys.stderr)
            return 1
    
    # 評価実行
    evaluator = CastleEXEvaluator(model_predictor=model_predictor)
    
    try:
        results = evaluator.evaluate_dataset(args.eval_data, max_samples=args.max_samples)
        evaluator.save_results(args.output)
        
        print("\n[OK] 評価が完了しました")
        print(f"\n次のステップ:")
        print(f"  1. デバッグサンプルを確認（pred_emptyがtrueならモデル呼び出しに問題）")
        print(f"  2. 実際のモデルを接続（--model-typeを変更）")
        print(f"  3. 評価結果を分析してv1.1データを生成")
        
        return 0
    except Exception as e:
        print(f"[ERROR] 評価エラー: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
