#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CASTLE-EXフレームワーク: データ検証ツール

生成データの品質チェック機能
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from collections import Counter

if sys.platform == "win32":
    try:
        import io

        if not hasattr(sys.stdout, "buffer") or sys.stdout.buffer.closed:
            pass
        else:
            sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass


class CastleEXDataValidator:
    """CASTLE-EXデータ検証器"""

    # 回答長の基準（文字数）
    LAYER_LENGTH_LIMITS = {
        0: (1, 5),  # 公理層: 1-5文字
        1: (1, 20),  # 操作層: 1-20文字
        2: (5, 40),  # 関係層: 5-40文字
        3: (10, 40),  # 感情基礎層: 10-40文字
        4: (20, 60),  # 文脈基礎層: 20-60文字
        5: (40, 100),  # 因果層: 40-100文字
        6: (80, 200),  # 統合層: 80-200文字
    }

    def __init__(self):
        """初期化"""
        self.errors = []
        self.warnings = []
        self.stats = {
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "by_layer": {},
            "error_types": Counter(),
            "invalid_reason": Counter(),  # Layer 2 ペアリング不正の理由別
        }
        self.message_hashes = {}  # 重複検知用

    def validate_format(self, item: Dict) -> Tuple[bool, Optional[str]]:
        """基本的なフォーマット検証"""
        if "messages" not in item:
            return False, "messagesキーが存在しません"

        messages = item["messages"]
        if not isinstance(messages, list) or len(messages) < 2:
            return False, "messagesは少なくとも2つの要素が必要です"

        if messages[0].get("role") != "user":
            return False, "最初のメッセージのroleは'user'である必要があります"

        if messages[-1].get("role") != "assistant":
            return False, "最後のメッセージのroleは'assistant'である必要があります"

        if "content" not in messages[0] or "content" not in messages[-1]:
            return False, "userとassistantのメッセージにcontentが必要です"

        return True, None

    def validate_answer_length(
        self, item: Dict, layer: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """回答長の検証"""
        if layer is None:
            layer = item.get("layer")

        if layer is None:
            # 層情報がない場合は推定を試みる
            assistant_content = item["messages"][-1]["content"]
            length = len(assistant_content)

            # 長さから層を推定
            for l, (min_len, max_len) in self.LAYER_LENGTH_LIMITS.items():
                if min_len <= length <= max_len:
                    return True, None

            return False, f"回答長({length}文字)がどの層の基準にも合致しません"

        if layer not in self.LAYER_LENGTH_LIMITS:
            return True, None  # 層が不明な場合は警告のみ

        assistant_content = item["messages"][-1]["content"]
        length = len(assistant_content)
        min_len, max_len = self.LAYER_LENGTH_LIMITS[layer]

        if length < min_len:
            return False, f"Layer {layer}: 回答が短すぎます ({length}文字 < {min_len}文字)"

        if length > max_len:
            return False, f"Layer {layer}: 回答が長すぎます ({length}文字 > {max_len}文字)"

        return True, None

    def validate_content_quality(self, item: Dict) -> Tuple[bool, List[str]]:
        """内容品質の検証"""
        warnings = []

        user_content = item["messages"][0]["content"]
        assistant_content = item["messages"][-1]["content"]

        # 曖昧な回答チェック（Layer 0-2では禁止）
        ambiguous_phrases = ["場合による", "文脈次第", "場合により", "時と場合により"]
        layer = item.get("layer")

        if layer is not None and layer <= 2:
            for phrase in ambiguous_phrases:
                if phrase in assistant_content:
                    warnings.append(f"Layer {layer}で曖昧な表現「{phrase}」が使用されています")

        # 空の回答チェック
        if not assistant_content.strip():
            return False, ["回答が空です"]

        # 回答が短すぎる場合（公理層以外）
        if layer is not None and layer > 0 and len(assistant_content.strip()) < 2:
            warnings.append("回答が非常に短いです")

        # ユーザーメッセージが空
        if not user_content.strip():
            return False, ["ユーザーメッセージが空です"]

        return True, warnings

    def validate_3axis_integration(self, item: Dict) -> Tuple[bool, List[str]]:
        """3軸統合の検証（Layer 5-6）"""
        warnings = []
        layer = item.get("layer")

        if layer is None or layer < 5:
            return True, []  # Layer 5-6以外はチェックしない

        user_content = item["messages"][0]["content"]
        assistant_content = item["messages"][-1]["content"]

        # Layer 5-6では感情・文脈要素が含まれるべき
        emotion_keywords = ["感情", "悲しい", "怒り", "嬉しい", "不安", "自信"]
        context_keywords = ["文脈", "状況", "会議", "関係", "真意", "意味"]

        has_emotion = any(
            keyword in user_content or keyword in assistant_content for keyword in emotion_keywords
        )
        has_context = any(
            keyword in user_content or keyword in assistant_content for keyword in context_keywords
        )

        if layer >= 5 and not has_emotion and not has_context:
            warnings.append(f"Layer {layer}では感情または文脈要素が推奨されます")

        return True, warnings

    def _extract_question_entities_layer2(self, user_content: str) -> List[str]:
        """Layer 2 用：問いから A/B 相当のトークンを簡易抽出（バリデータ用）"""
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

    def _parse_layer2_question_type(
        self, user_content: str
    ) -> Tuple[str, List[str], Optional[str]]:
        """
        Layer 2 用：問いの型と必須語を簡易パース。
        Returns: (question_type, required_entities, slot_term or None)
        question_type: "a_wa_b" | "a_to_b" | "role_job" | "attr" | "unknown"
        """
        entities = self._extract_question_entities_layer2(user_content)
        if not entities:
            return "unknown", [], None
        # 「A と B、どっちが」→ A, B 両方必須
        if "どっちが" in user_content and len(entities) >= 2:
            return "a_to_b", entities[:2], None
        # 「A は B の一部」「A は B？」→ A, B 両方必須
        if " は " in user_content and ("の一部" in user_content or "？" in user_content):
            parts = re.split(r"\s+は\s+", user_content, 1)
            if len(parts) == 2:
                a_candidates = self._extract_question_entities_layer2(parts[0])
                b_candidates = self._extract_question_entities_layer2(parts[1])
                required = (a_candidates[:1] or []) + (b_candidates[:1] or [])
                if required:
                    return "a_wa_b", required, None
        # 「role の仕事は」→ role と「仕事」相当の語が正解に含まれること
        if "の仕事は" in user_content or "の役割は" in user_content:
            return "role_job", entities[:1], "仕事" if "仕事" in user_content else "役割"
        # 「A の attr は」→ A と attr 語（危険度/大きさ等）が正解に含まれること
        slot_terms = ["危険度", "重要度", "大きさ", "色", "役割", "優先度", "難易度"]
        for slot in slot_terms:
            if slot in user_content:
                return "attr", entities[:1], slot
        # フォールバック：抽出したエンティティのいずれか1つ以上
        return "unknown", entities[:2] if len(entities) >= 2 else entities, None

    def validate_layer2_pairing(self, item: Dict) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Layer 2 用：問いと正解のペアリング整合性（強化版）。
        A/B 形式は両方、属性質問は slot 語も正解に含まれることを要求。壊れていれば INVALID。
        Returns: (ok, error_message, invalid_reason)
        """
        if item.get("layer") != 2:
            return True, None, None
        messages = item.get("messages", [])
        if len(messages) < 2:
            return True, None, None
        user_content = messages[0].get("content", "")
        assistant_content = messages[-1].get("content", "")
        if not user_content or not assistant_content:
            return True, None, None

        q_type, required, slot_term = self._parse_layer2_question_type(user_content)
        if not required:
            return True, None, None

        missing = []
        for e in required:
            if e not in assistant_content:
                missing.append(e)
        if slot_term and slot_term not in assistant_content:
            missing.append(f"slot:{slot_term}")

        if not missing:
            return True, None, None
        reason = "missing_object" if len(missing) > 1 else "missing_subject"
        if slot_term and f"slot:{slot_term}" in missing:
            reason = "missing_slot"
        msg = (
            f"Layer 2 ペアリング不正 [{reason}]: 正解に問いの必須語が含まれていません "
            f"(不足: {missing[:3]})"
        )
        return False, msg, reason

    def validate_layer4_pairing(self, item: Dict) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Layer 4 用：制約・例外の壊れ検知（最低限）。
        問いに制約語（禁止/のみ/必須）があれば答えに反映、例外語（ただし/例外/しかし）があれば答えに含まれること。
        Returns: (ok, error_message, invalid_reason)
        """
        if item.get("layer") != 4:
            return True, None, None
        messages = item.get("messages", [])
        if len(messages) < 2:
            return True, None, None
        user_content = messages[0].get("content", "")
        assistant_content = messages[-1].get("content", "")
        if not user_content or not assistant_content:
            return True, None, None

        # 制約型：問いに「禁止」「しない」「のみ」「必須」→ 答えに制約反映語が欲しい
        constraint_in_q = any(
            k in user_content for k in ("禁止", "しない", "のみ", "必須", "だけ", "のみ可")
        )
        if constraint_in_q:
            constraint_in_a = any(
                k in assistant_content
                for k in ("禁止", "しない", "のみ", "必須", "守", "従う", "反映", "考慮", "だけ")
            )
            if not constraint_in_a:
                return (
                    False,
                    "Layer 4 制約型: 問いの制約が答えに反映されていません",
                    "missing_constraint",
                )

        # 例外型：問いに「ただし」「例外」「しかし」→ 答えに例外語が欲しい
        exception_in_q = any(k in user_content for k in ("ただし", "例外", "しかし"))
        if exception_in_q:
            exception_in_a = any(k in assistant_content for k in ("ただし", "例外", "しかし"))
            if not exception_in_a:
                return (
                    False,
                    "Layer 4 例外型: 問いの例外が答えに含まれていません",
                    "missing_exception",
                )

        return True, None, None

    def validate_layer6_pairing(self, item: Dict) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Layer 6 用：文章構造の壊れ検知（最低限）。
        正例で長い答えの場合、結論/理由/対策/リスク/感情/状況のいずれかが含まれること。
        Returns: (ok, error_message, invalid_reason)
        """
        if item.get("layer") != 6:
            return True, None, None
        if not item.get("positive", True):
            return True, None, None  # 負例はチェックしない
        messages = item.get("messages", [])
        if len(messages) < 2:
            return True, None, None
        assistant_content = messages[-1].get("content", "")
        if not assistant_content:
            return True, None, None

        # Layer 6 正例で 80 文字以上なら構造語が欲しい（tradeoff/risk_mgmt の最低限）
        if len(assistant_content) >= 80:
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
            if not any(k in assistant_content for k in structure_words):
                return (
                    False,
                    "Layer 6 正例: 長い答えに結論/理由/対策等の構造がありません",
                    "missing_structure",
                )
        return True, None, None

    def validate_axis_evidence(self, item: Dict) -> Tuple[bool, List[str]]:
        """axis_evidenceの必須チェック（Layer3+で60%以上必須）"""
        warnings = []
        layer = item.get("layer")
        axes = item.get("axes", [])
        axis_evidence = item.get("axis_evidence", {})

        # Layer 3+ではaxis_evidenceが推奨（統計で60%以上必要）
        if layer is not None and layer >= 3:
            if not axis_evidence:
                warnings.append(
                    f"Layer {layer}ではaxis_evidenceが推奨されます（Layer 3+で60%以上必要）"
                )
            else:
                # axesに含まれる軸に対してevidenceがあるかチェック
                for axis in axes:
                    if axis not in axis_evidence:
                        warnings.append(
                            f"axesに'{axis}'が含まれていますが、axis_evidenceに'{axis}'の証拠がありません"
                        )

        # axis_evidenceがあるのにaxesに含まれていない軸がある場合
        if axis_evidence:
            for axis in axis_evidence.keys():
                if axis not in axes:
                    warnings.append(
                        f"axis_evidenceに'{axis}'の証拠がありますが、axesに'{axis}'が含まれていません"
                    )

        return True, warnings

    def validate_axis_evidence_coverage(self, all_items: List[Dict]) -> Tuple[bool, str]:
        """axis_evidenceカバレッジの検証（Layer 3+で60%以上必須）"""
        layer3_plus_items = [item for item in all_items if item.get("layer", 0) >= 3]
        if not layer3_plus_items:
            return True, ""

        with_evidence = sum(1 for item in layer3_plus_items if item.get("axis_evidence"))
        coverage_ratio = with_evidence / len(layer3_plus_items)

        if coverage_ratio < 0.6:
            return (
                False,
                f"Layer 3+のaxis_evidenceカバレッジが{coverage_ratio:.1%}と低すぎます（60%以上必要）",
            )

        return True, ""

    def validate_item(self, item: Dict, index: int) -> bool:
        """単一データ項目の検証"""
        self.stats["total"] += 1

        # フォーマット検証
        is_valid, error = self.validate_format(item)
        if not is_valid:
            self.errors.append(f"行{index+1}: {error}")
            self.stats["error_types"][error] += 1
            self.stats["invalid"] += 1
            return False

        # Layer 2 ペアリング整合性（問いの A/B が正解に含まれるか）
        is_valid, error, invalid_reason = self.validate_layer2_pairing(item)
        if not is_valid:
            self.errors.append(f"行{index+1}: {error}")
            self.stats["error_types"]["Layer2ペアリング不正"] += 1
            if invalid_reason:
                self.stats["invalid_reason"][invalid_reason] += 1
            self.stats["invalid"] += 1
            return False

        # Layer 4 制約・例外の壊れ検知
        is_valid, error, invalid_reason = self.validate_layer4_pairing(item)
        if not is_valid:
            self.errors.append(f"行{index+1}: {error}")
            self.stats["error_types"]["Layer4ペアリング不正"] += 1
            if invalid_reason:
                self.stats["invalid_reason"][invalid_reason] += 1
            self.stats["invalid"] += 1
            return False

        # Layer 6 構造の壊れ検知
        is_valid, error, invalid_reason = self.validate_layer6_pairing(item)
        if not is_valid:
            self.errors.append(f"行{index+1}: {error}")
            self.stats["error_types"]["Layer6ペアリング不正"] += 1
            if invalid_reason:
                self.stats["invalid_reason"][invalid_reason] += 1
            self.stats["invalid"] += 1
            return False

        # 内容品質検証
        is_valid, warnings = self.validate_content_quality(item)
        if not is_valid:
            for warning in warnings:
                self.errors.append(f"行{index+1}: {warning}")
                self.stats["error_types"][warning] += 1
            self.stats["invalid"] += 1
            return False

        # 回答長検証
        is_valid, error = self.validate_answer_length(item)
        if not is_valid:
            self.warnings.append(f"行{index+1}: {error}")

        # 3軸統合検証
        is_valid, warnings = self.validate_3axis_integration(item)
        for warning in warnings:
            self.warnings.append(f"行{index+1}: {warning}")

        # axis_evidence検証
        is_valid, warnings = self.validate_axis_evidence(item)
        for warning in warnings:
            self.warnings.append(f"行{index+1}: {warning}")

        # 重複検知（messagesのハッシュ）
        import hashlib

        messages = item.get("messages", [])
        if messages:
            messages_str = json.dumps(messages, sort_keys=True, ensure_ascii=False)
            msg_hash = hashlib.md5(messages_str.encode("utf-8")).hexdigest()
            if msg_hash in self.message_hashes:
                self.warnings.append(
                    f"行{index+1}: 重複メッセージを検出（行{self.message_hashes[msg_hash]}と同一）"
                )
            else:
                self.message_hashes[msg_hash] = index + 1

        # 層統計
        layer = item.get("layer")
        if layer is not None:
            if layer not in self.stats["by_layer"]:
                self.stats["by_layer"][layer] = {"total": 0, "valid": 0, "invalid": 0}
            self.stats["by_layer"][layer]["total"] += 1

        self.stats["valid"] += 1
        if layer is not None:
            self.stats["by_layer"][layer]["valid"] += 1

        return True

    def validate_file(self, file_path: str) -> Dict[str, Any]:
        """JSONLファイル全体の検証"""
        print("=" * 60)
        print("CASTLE-EX データ検証")
        print("=" * 60)
        print(f"検証ファイル: {file_path}")

        path = Path(file_path)
        if not path.exists():
            print(f"✗ ファイルが存在しません: {file_path}")
            return {"valid": False, "error": "ファイルが存在しません"}

        # ファイル読み込み
        items = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                        items.append(item)
                    except json.JSONDecodeError as e:
                        self.errors.append(f"行{line_num}: JSON解析エラー - {e}")
                        self.stats["error_types"]["JSON解析エラー"] += 1
        except Exception as e:
            print(f"✗ ファイル読み込みエラー: {e}")
            return {"valid": False, "error": str(e)}

        print(f"読み込み完了: {len(items)}件")
        print("\n検証中...")

        # 各項目を検証
        for i, item in enumerate(items):
            self.validate_item(item, i)

        # axis_evidenceカバレッジの検証（Layer 3+で60%以上必須）
        is_valid_coverage, coverage_error = self.validate_axis_evidence_coverage(items)
        if not is_valid_coverage:
            self.errors.append(coverage_error)
            self.stats["invalid"] += 1

        # 結果レポート
        self.print_report()

        return {
            "valid": len(self.errors) == 0,
            "stats": self.stats,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def print_report(self):
        """検証結果レポートの表示"""
        print("\n" + "=" * 60)
        print("検証結果")
        print("=" * 60)

        total = self.stats["total"]
        valid = self.stats["valid"]
        invalid = self.stats["invalid"]

        print(f"総データ数: {total}")
        print(f"有効: {valid} ({valid/total*100:.1f}%)")
        print(f"無効: {invalid} ({invalid/total*100:.1f}%)")
        print(f"警告: {len(self.warnings)}件")

        if self.stats["by_layer"]:
            print("\n層別統計:")
            for layer in sorted(self.stats["by_layer"].keys()):
                layer_stats = self.stats["by_layer"][layer]
                total_l = layer_stats["total"]
                valid_l = layer_stats["valid"]
                print(f"  Layer {layer}: {valid_l}/{total_l} 有効 ({valid_l/total_l*100:.1f}%)")

        if self.errors:
            print(f"\n✗ エラー ({len(self.errors)}件):")
            for error in self.errors[:10]:  # 最初の10件のみ表示
                print(f"  - {error}")
            if len(self.errors) > 10:
                print(f"  ... 他{len(self.errors)-10}件")

        if self.warnings:
            print(f"\n⚠ 警告 ({len(self.warnings)}件):")
            for warning in self.warnings[:10]:  # 最初の10件のみ表示
                print(f"  - {warning}")
            if len(self.warnings) > 10:
                print(f"  ... 他{len(self.warnings)-10}件")

        if self.stats["error_types"]:
            print("\nエラータイプ別集計:")
            for error_type, count in self.stats["error_types"].most_common(5):
                print(f"  - {error_type}: {count}件")
        if self.stats.get("invalid_reason"):
            print("\nLayer 2/4/6 invalid_reason 別:")
            for reason, count in self.stats["invalid_reason"].most_common():
                print(f"  - {reason}: {count}件")


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="CASTLE-EXデータ検証ツール")
    parser.add_argument("file", type=str, help="検証するJSONLファイルパス")

    args = parser.parse_args()

    validator = CastleEXDataValidator()
    result = validator.validate_file(args.file)

    if result["valid"]:
        print("\n✓ すべてのデータが有効です")
        sys.exit(0)
    else:
        print("\n✗ 検証エラーが検出されました")
        sys.exit(1)


if __name__ == "__main__":
    main()
