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

if sys.platform == "win32":
    try:
        import io

        if not hasattr(sys.stdout, "buffer") or sys.stdout.buffer.closed:
            pass
        else:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def _extract_question_entities_layer2(user_content: str) -> List[str]:
    """Layer 2 用：問いから A/B 相当のトークンを簡易抽出（評価の invalid_label 検出用）"""
    stop = {
        "は",
        "の",
        "と",
        "？",
        "?",
        "か",
        "どっちが",
        "の一部",
        "です",
        "で",
        "に",
        "を",
        "が",
        "も",
    }
    tokens = re.split(r"[\s　、。？?]+", user_content)
    return [t for t in tokens if len(t) >= 1 and t not in stop]


def _classify_invalid_reason_layer2(user_content: str, gold_answer: str) -> str:
    """
    Layer 2 で invalid の場合の理由を分類（generator のどのテンプレが壊れたか切り分け用）。
    Returns: "missing_subject" | "missing_object" | "missing_slot" | "parse_failed"
    """
    entities = _extract_question_entities_layer2(user_content)
    if not entities:
        return "parse_failed"
    # どっちが → A, B 両方必須
    if "どっちが" in user_content and len(entities) >= 2:
        a_in, b_in = entities[0] in gold_answer, entities[1] in gold_answer
        if not a_in and not b_in:
            return "missing_object"
        if not a_in or not b_in:
            return "missing_subject"
    # 「A は B」型 → 両方
    if " は " in user_content and len(entities) >= 2:
        if entities[0] not in gold_answer and entities[1] not in gold_answer:
            return "missing_object"
        if entities[0] not in gold_answer or entities[1] not in gold_answer:
            return "missing_subject"
    # 属性（危険度/大きさ等）→ slot 語が正解に含まれるか
    slot_terms = ["危険度", "重要度", "大きさ", "色", "役割", "優先度", "難易度", "重要", "効率的"]
    for slot in slot_terms:
        if slot in user_content and slot not in gold_answer:
            if not any(e in gold_answer for e in entities):
                return "missing_slot"
    # 役割の仕事は
    if "の仕事は" in user_content or "の役割は" in user_content:
        if not any(e in gold_answer for e in entities):
            return "missing_subject"
    # フォールバック：1語も含まれていない
    if not any(e in gold_answer for e in entities):
        return "missing_object"
    return "parse_failed"


def _is_invalid_layer4(user_content: str, gold_answer: str) -> Tuple[bool, Optional[str]]:
    """
    Layer 4: 制約・例外の壊れ検知（バリデータと同一思想）。
    Returns: (invalid, reason)
    """
    if not user_content or not gold_answer:
        return False, None
    constraint_in_q = any(
        k in user_content for k in ("禁止", "しない", "のみ", "必須", "だけ", "のみ可")
    )
    if constraint_in_q:
        if not any(
            k in gold_answer
            for k in ("禁止", "しない", "のみ", "必須", "守", "従う", "反映", "考慮", "だけ")
        ):
            return True, "missing_constraint"
    exception_in_q = any(k in user_content for k in ("ただし", "例外", "しかし"))
    if exception_in_q:
        if not any(k in gold_answer for k in ("ただし", "例外", "しかし")):
            return True, "missing_exception"
    return False, None


def _is_invalid_layer6(item: Dict, gold_answer: str) -> Tuple[bool, Optional[str]]:
    """
    Layer 6: 正例で長い答えの構造壊れ検知（バリデータと同一思想）。
    Returns: (invalid, reason)
    """
    if item.get("layer") != 6 or not item.get("positive", True):
        return False, None
    if not gold_answer or len(gold_answer) < 80:
        return False, None
    structure_words = (
        "結論",
        "理由",
        "対策",
        "リスク",
        "感情",
        "状況",
        "優先",
        "対応",
        "理解",
        "重要",
        "考慮",
        "共感",
        "解決",
        "整理",
    )
    if not any(k in gold_answer for k in structure_words):
        return True, "missing_structure"
    return False, None


def format_prompt_phi3(item: Dict) -> str:
    """
    messages形式をPhi-3チャット形式に変換（assistantの手前まで＝モデル入力用）
    学習時の format_messages_for_training と同一形式。
    """
    messages = item.get("messages", [])
    if not messages:
        return ""
    parts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            parts.append(f"<|system|>\n{content}<|end|>\n")
        elif role == "user":
            parts.append(f"<|user|>\n{content}<|end|>\n")
        elif role == "assistant":
            parts.append("<|assistant|>\n")  # ここまでが入力、以降が生成対象
            break
    return "".join(parts)


class CastleEXEvaluator:
    """CASTLE-EX評価器（修正版：実際のモデル評価対応）"""

    def __init__(
        self,
        model_predictor: Optional[Callable[[str], str]] = None,
        prompt_format: str = "role_content",
    ):
        """
        初期化

        Args:
            model_predictor: モデル予測関数（prompt文字列を受け取り、予測テキストを返す）
                            Noneの場合はデバッグモード（goldをそのまま返す）
            prompt_format: "role_content"（デフォルト）または "phi3"（Phi-3チャット形式）
        """
        self.model_predictor = model_predictor
        self.prompt_format = (prompt_format or "role_content").lower()
        self.results = {
            "dataset": "",
            "seed": "castle_ex_v1_0",
            "overall": {
                "negative_detection": 0.0,
                "axis_consistency": 0.0,
                "context_sensitivity": 0.0,
                "emotion_appropriateness": 0.0,
                "paraphrase_robustness": 0.0,
                "causal_validity": 0.0,
            },
            "by_layer": {},
            "by_axes_combo": {},
            "negative_by_error_type": {},
            "debug_samples": [],  # デバッグ用：最初の5サンプルのgold/pred
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
            ユーザープロンプト（assistantを除いたmessagesをテキスト化、またはPhi-3形式）
        """
        if self.prompt_format == "phi3":
            return format_prompt_phi3(item)
        messages = item.get("messages", [])
        if not messages:
            return ""
        prompt_parts = []
        for msg in messages:
            if msg.get("role") == "assistant":
                break
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
            return {"error": "gold_answer not found", "item_index": item_index}

        # User promptを抽出
        user_prompt = self.extract_user_prompt(item)
        if not user_prompt:
            return {"error": "user_prompt not found", "item_index": item_index}

        # モデルで予測
        pred_answer = self.predict_with_model(user_prompt)

        # デバッグ用：最初の5サンプルを保存
        if len(self.results["debug_samples"]) < 5:
            self.results["debug_samples"].append(
                {
                    "item_index": item_index,
                    "layer": item.get("layer", -1),
                    "user_prompt": (
                        user_prompt[:100] + "..." if len(user_prompt) > 100 else user_prompt
                    ),
                    "gold_answer": (
                        gold_answer[:100] + "..." if len(gold_answer) > 100 else gold_answer
                    ),
                    "pred_answer": (
                        pred_answer[:100] + "..." if len(pred_answer) > 100 else pred_answer
                    ),
                    "pred_empty": len(pred_answer) == 0,
                }
            )

        # 評価（簡易版：部分一致ベース）
        is_correct, score = self.evaluate_response(gold_answer, pred_answer)

        # メタデータを取得
        layer = item.get("layer", -1)
        axes = item.get("axes", [])
        positive = item.get("positive", True)
        error_type = item.get("error_type")

        # Layer 2/4/6: 正解が問いの語・制約・構造を満たさない場合はデータ不正としてマーク（accuracy に混ぜない）
        invalid_label = False
        invalid_reason: Optional[str] = None
        if user_prompt:
            user_content = user_prompt.replace("<|user|>\n", "").replace("<|end|>\n", "").strip()
            if self.prompt_format != "phi3":
                user_content = user_prompt
            if layer == 2:
                entities = _extract_question_entities_layer2(user_content)
                if entities and not any(e in gold_answer for e in entities):
                    invalid_label = True
                    invalid_reason = _classify_invalid_reason_layer2(user_content, gold_answer)
            elif layer == 4:
                inv, reason = _is_invalid_layer4(user_content, gold_answer)
                if inv:
                    invalid_label = True
                    invalid_reason = reason
            elif layer == 6:
                inv, reason = _is_invalid_layer6(item, gold_answer)
                if inv:
                    invalid_label = True
                    invalid_reason = reason
        return {
            "item_index": item_index,
            "layer": layer,
            "axes": axes,
            "positive": positive,
            "error_type": error_type,
            "template_id": item.get("template_id"),  # Layer2 template_id 別サマリ用
            "gold_answer": gold_answer,
            "pred_answer": pred_answer,
            "is_correct": is_correct,
            "score": score,
            "invalid_label": invalid_label,
            "invalid_reason": invalid_reason,
            "user_prompt_snippet": (user_prompt[:400] if user_prompt and layer == 2 else None),  # Layer2誤答分析用
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
        gold_keywords = set(re.findall(r"\w+", gold_normalized))
        pred_keywords = set(re.findall(r"\w+", pred_normalized))

        if len(gold_keywords) == 0:
            return False, 0.0

        common_keywords = gold_keywords & pred_keywords
        keyword_score = len(common_keywords) / len(gold_keywords)

        # 部分一致チェック
        if gold_normalized in pred_normalized or pred_normalized in gold_normalized:
            partial_score = min(len(gold_normalized), len(pred_normalized)) / max(
                len(gold_normalized), len(pred_normalized)
            )
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
        with open(eval_path, "r", encoding="utf-8") as f:
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

        # Layer別統計（Layer 2 は invalid_label を accuracy に混ぜず別カウント）
        layer_stats = defaultdict(
            lambda: {"total": 0, "correct": 0, "scores": [], "invalid_label": 0}
        )
        for result in item_results:
            layer = result.get("layer", -1)
            invalid = result.get("invalid_label", False)
            if invalid:
                layer_stats[layer]["invalid_label"] += 1
            else:
                layer_stats[layer]["total"] += 1
                if result.get("is_correct", False):
                    layer_stats[layer]["correct"] += 1
                layer_stats[layer]["scores"].append(result.get("score", 0.0))

        self.results["by_layer"] = {
            str(layer): {
                "acc": (
                    layer_stats[layer]["correct"] / layer_stats[layer]["total"]
                    if layer_stats[layer]["total"] > 0
                    else 0.0
                ),
                "invalid_label_count": layer_stats[layer]["invalid_label"],
            }
            for layer in sorted(layer_stats.keys())
        }
        # 全体の invalid_label 件数（主に Layer 2）
        total_invalid_label = sum(layer_stats[l]["invalid_label"] for l in layer_stats)
        if total_invalid_label > 0:
            self.results["invalid_label_count"] = total_invalid_label

        # invalid_reason 別集計（generator のどのテンプレが壊れたか切り分け用）
        invalid_reason_counts: Dict[str, int] = defaultdict(int)
        for r in item_results:
            if r.get("invalid_label") and r.get("invalid_reason"):
                invalid_reason_counts[r["invalid_reason"]] += 1
        if invalid_reason_counts:
            self.results["invalid_reason_counts"] = dict(invalid_reason_counts)

        # Layer2 template_id 別正答率（v1.2 増強方針用）
        layer2_results = [r for r in item_results if r.get("layer") == 2]
        if layer2_results:
            tid_stats: Dict[str, Dict[str, int]] = defaultdict(
                lambda: {"total": 0, "correct": 0, "invalid_label": 0}
            )
            for r in layer2_results:
                tid = r.get("template_id") or "unknown"
                if r.get("invalid_label"):
                    tid_stats[tid]["invalid_label"] += 1
                else:
                    tid_stats[tid]["total"] += 1
                    if r.get("is_correct"):
                        tid_stats[tid]["correct"] += 1
            self.results["layer2_by_template_id"] = {
                tid: {
                    "acc": (s["correct"] / s["total"] if s["total"] > 0 else 0.0),
                    "total": s["total"],
                    "correct": s["correct"],
                    "invalid_label_count": s["invalid_label"],
                }
                for tid, s in sorted(tid_stats.items())
            }
            # Layer2 全件詳細（誤答分析用）
            self.results["layer2_details"] = [
                {
                    k: r.get(k)
                    for k in (
                        "item_index",
                        "template_id",
                        "user_prompt_snippet",
                        "gold_answer",
                        "pred_answer",
                        "is_correct",
                        "score",
                    )
                }
                for r in layer2_results
            ]

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
                "acc": (
                    axes_stats[axes_key]["correct"] / axes_stats[axes_key]["total"]
                    if axes_stats[axes_key]["total"] > 0
                    else 0.0
                )
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
                "precision": (
                    error_type_stats[error_type]["correct"] / error_type_stats[error_type]["total"]
                    if error_type_stats[error_type]["total"] > 0
                    else 0.0
                ),
                "recall": (
                    error_type_stats[error_type]["correct"] / error_type_stats[error_type]["total"]
                    if error_type_stats[error_type]["total"] > 0
                    else 0.0
                ),
            }
            for error_type in sorted(error_type_stats.keys())
        }

        # Overall指標の計算（簡易版）
        total = len(item_results)
        correct = sum(1 for r in item_results if r.get("is_correct", False))
        avg_score = (
            statistics.mean([r.get("score", 0.0) for r in item_results]) if item_results else 0.0
        )

        # Negative Detection: 負例の正解率
        negative_total = len(negative_results)
        negative_correct = sum(1 for r in negative_results if r.get("is_correct", False))
        self.results["overall"]["negative_detection"] = (
            negative_correct / negative_total if negative_total > 0 else 0.0
        )

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

        # v1.1 評価サマリ（貼り用：次の打ち手即決用）
        self._print_v11_summary(total, correct)

    def _print_v11_summary(self, total: int, correct: int):
        """v1.1 学習後の評価サマリを貼り用フォーマットで表示"""
        overall_acc = correct / total if total > 0 else 0.0
        inv_total = self.results.get("invalid_label_count", 0)
        by_layer = self.results.get("by_layer", {})
        inv_reason = self.results.get("invalid_reason_counts", {})
        l2_by_tid = self.results.get("layer2_by_template_id", {})

        print("\n" + "=" * 50)
        print("【v1.1 評価サマリ（貼り用）】")
        print("=" * 50)
        for layer in sorted(
            by_layer.keys(), key=lambda x: int(x) if x.lstrip("-").isdigit() else 999
        ):
            s = by_layer[layer]
            acc = s.get("acc", 0.0)
            inv = s.get("invalid_label_count", 0)
            print(f"  layer{layer}: acc={acc:.3f}, invalid={inv}")
        print(f"  全体: acc={overall_acc:.3f}, invalid_total={inv_total}")
        if inv_reason:
            print("  invalid_reason_counts:", dict(inv_reason))
        if l2_by_tid:
            print("  Layer2 template_id別:")
            for tid, s in sorted(l2_by_tid.items()):
                print(
                    f"    {tid}: acc={s['acc']:.3f}, n={s['total']}, invalid={s['invalid_label_count']}"
                )
        print("=" * 50)

    def save_results(self, output_file: str):
        """
        評価結果を標準フォーマットで保存

        Args:
            output_file: 出力ファイル名
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] 評価結果を保存: {output_file}")

        # Layer2 誤答のみ別ファイル（誤答分析用）
        layer2_details = self.results.get("layer2_details", [])
        if layer2_details:
            errors = [r for r in layer2_details if not r.get("is_correct", True)]
            err_path = output_path.parent / f"{output_path.stem}_layer2_errors.json"
            with open(err_path, "w", encoding="utf-8") as f:
                json.dump({"count": len(errors), "items": errors}, f, ensure_ascii=False, indent=2)
            print(f"[OK] Layer2誤答一覧: {err_path} ({len(errors)}件)")

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

    parser = argparse.ArgumentParser(description="CASTLE-EX評価ツール（修正版）")
    parser.add_argument(
        "--eval-data", type=str, required=True, help="評価データセットJSONLファイル"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evaluation_v1_0.json",
        help="評価結果出力ファイル（デフォルト: evaluation_v1_0.json）",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="モデルパス/チェックポイント（Ollama: モデル名、Transformers: モデルパス）",
    )
    parser.add_argument(
        "--model-type",
        type=str,
        default="dummy",
        choices=["dummy", "ollama", "transformers"],
        help="モデルタイプ（デフォルト: dummy）",
    )
    parser.add_argument(
        "--ollama-url",
        type=str,
        default="http://localhost:11434/api/generate",
        help="Ollama API URL（model-type=ollamaの場合）",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="最大評価サンプル数（デバッグ用、Noneの場合は全件）",
    )
    parser.add_argument(
        "--prompt-format",
        type=str,
        default="role_content",
        choices=["role_content", "phi3"],
        help="プロンプト形式（phi3=Phi-3チャット形式、学習済みPhi-3用）",
    )
    parser.add_argument(
        "--lora",
        type=str,
        default=None,
        help="LoRAアダプタのパス（指定時は base model の上に PeftModel としてロード）",
    )

    args = parser.parse_args()

    # モデル予測関数を取得
    model_predictor = None

    if args.model_type == "dummy":
        print("[WARN] ダミーモデルを使用します（実際の評価には使用しないでください）")
        model_predictor = create_dummy_model_predictor()
    elif args.model_type == "ollama":
        # Ollama統合
        try:
            import requests

            ollama_url = args.ollama_url
            model_name = args.model if args.model else "qwen2.5:14b"

            def ollama_predict(prompt: str) -> str:
                try:
                    response = requests.post(
                        ollama_url,
                        json={"model": model_name, "prompt": prompt, "stream": False},
                        timeout=60,
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
    elif args.model_type == "transformers":
        # Transformers統合（Phi-3等の学習済みモデル対応）
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch

            model_path = args.model if args.model else "microsoft/DialoGPT-medium"
            print(f"[INFO] モデル読み込み中: {model_path}")

            tokenizer = AutoTokenizer.from_pretrained(
                model_path, trust_remote_code=True, local_files_only=True
            )
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            # 学習済み保存先に modeling_phi3.py を配置済みの場合は local_files_only=True で可
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                trust_remote_code=True,
                local_files_only=True,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            )
            if getattr(args, "lora", None):
                try:
                    from peft import PeftModel
                    model = PeftModel.from_pretrained(model, args.lora)
                    print(f"[OK] LoRAをロード: {args.lora}")
                except Exception as e:
                    print(f"[WARN] LoRAロード失敗（ベースのみ使用）: {e}")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = model.to(device)
            model.eval()
            max_new_tokens = 512
            use_phi3 = args.prompt_format == "phi3"

            def transformers_predict(prompt: str) -> str:
                try:
                    inputs = tokenizer(
                        prompt, return_tensors="pt", truncation=True, max_length=2048, padding=False
                    )
                    input_len = inputs["input_ids"].shape[1]
                    inputs = {k: v.to(device) for k, v in inputs.items()}
                    with torch.no_grad():
                        outputs = model.generate(
                            **inputs,
                            max_new_tokens=max_new_tokens,
                            num_return_sequences=1,
                            pad_token_id=tokenizer.eos_token_id,
                            do_sample=False,
                            use_cache=False,  # DynamicCache API差異によるエラー回避
                        )
                    # 入力トークン数以降だけをデコード（生成部分のみ）
                    generated_ids = outputs[0][input_len:]
                    generated_text = tokenizer.decode(generated_ids, skip_special_tokens=False)
                    if use_phi3 and "<|end|>" in generated_text:
                        generated_text = generated_text.split("<|end|>")[0]
                    return generated_text.strip()
                except Exception as e:
                    print(f"[ERROR] Transformers生成エラー: {e}", file=sys.stderr)
                    return ""

            model_predictor = transformers_predict
            print(
                f"[OK] Transformersモデルを使用: {model_path} (device: {device}, prompt_format: {args.prompt_format})"
            )
        except ImportError:
            print("[ERROR] transformersライブラリがインストールされていません", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"[ERROR] モデル読み込みエラー: {e}", file=sys.stderr)
            return 1

    # 評価実行
    evaluator = CastleEXEvaluator(model_predictor=model_predictor, prompt_format=args.prompt_format)

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
