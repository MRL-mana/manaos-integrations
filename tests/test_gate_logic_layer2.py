"""
Layer2 gate ロジックの回帰テスト
-----------------------------------------------
evaluator の is_correct_negative_v2 が error_type 別に正しく判定するかを検証する。

実行:
    py.exe -3.10 -m pytest tests/test_gate_logic_layer2.py -v
"""
import sys
from pathlib import Path

# パス追加（プロジェクトルートから実行前提）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from castle_ex.castle_ex_evaluator_fixed import (
    is_correct_negative_v2,
    _normalize_text_v2,
)


# ------------------------------------------------------------------ #
# aizuchi_tail: 正解の後ろに「はい/いいえ」が付く悪パターン
# ------------------------------------------------------------------ #
class TestAizuchiTail:
    def test_pred_without_hai_is_ok(self):
        """正しい応答（はい なし）→ OK（True）"""
        gold = "ピットの危険度は中です。 はい。"
        pred = "ピット の 危険度 は？ ピットの危険度は中です。"
        assert is_correct_negative_v2(
            _normalize_text_v2(gold), _normalize_text_v2(pred), error_type="aizuchi_tail"
        ) is True

    def test_pred_with_hai_is_ng(self):
        """悪パターン（はい 付き）→ NG（False）"""
        gold = "ピットの危険度は中です。 はい。"
        pred = "ピットの危険度は中です。 はい。"
        assert is_correct_negative_v2(
            _normalize_text_v2(gold), _normalize_text_v2(pred), error_type="aizuchi_tail"
        ) is False

    def test_attribute_value_in_pred_not_penalized(self):
        """属性値（中/高/低等）が pred に含まれていても aizuchi_tail では減点しない"""
        gold = "レジの色は低いです。 はい。"
        pred = "レジの色は低いです。"  # はい なし → OK
        assert is_correct_negative_v2(
            _normalize_text_v2(gold), _normalize_text_v2(pred), error_type="aizuchi_tail"
        ) is True


# ------------------------------------------------------------------ #
# repeat_phrase: 同じフレーズを繰り返す悪パターン
# ------------------------------------------------------------------ #
class TestRepeatPhrase:
    def test_no_repeat_is_ok(self):
        """繰り返しなし → OK"""
        gold = "レジの色は低いです。 レジの色は低いです。"
        pred = "レジ の 色 は？ レジの色は低いです。"
        assert is_correct_negative_v2(
            _normalize_text_v2(gold), _normalize_text_v2(pred), error_type="repeat_phrase"
        ) is True

    def test_two_repeat_is_ok(self):
        """2回繰り返し（閾値未満）→ OK"""
        gold = "レジの色は低いです。 レジの色は低いです。"
        pred = "レジの色は低いです。 レジの色は低いです。"  # 2回のみ
        assert is_correct_negative_v2(
            _normalize_text_v2(gold), _normalize_text_v2(pred), error_type="repeat_phrase"
        ) is True

    def test_three_repeat_is_ng(self):
        """同一トークン3回以上 → NG"""
        gold = "レジの色は低いです。 レジの色は低いです。"
        pred = "低いです。 低いです。 低いです。"  # 3回
        assert is_correct_negative_v2(
            _normalize_text_v2(gold), _normalize_text_v2(pred), error_type="repeat_phrase"
        ) is False


# ------------------------------------------------------------------ #
# verbose_echo: 質問文をそのままエコーする悪パターン
# ------------------------------------------------------------------ #
class TestVerboseEcho:
    def test_echo_without_question_is_ok(self):
        """質問コピーなし → OK（verbose_echo は signals ベース判定）"""
        gold = "オイル の 大きさ は？ オイルの大きさは赤です。"
        pred = "オイルの大きさは赤です。"  # 短く正確 → signals に引っかからない
        assert is_correct_negative_v2(
            _normalize_text_v2(gold), _normalize_text_v2(pred), error_type="verbose_echo"
        ) is True


# ------------------------------------------------------------------ #
# 後方互換: error_type=None でも動作する
# ------------------------------------------------------------------ #
class TestBackwardCompat:
    def test_none_error_type_works(self):
        """error_type=None でも例外が起きない"""
        gold = "オイル交換の優先度は小さいです。 はい。"
        pred = "オイル交換の優先度は小さいです。"
        result = is_correct_negative_v2(
            _normalize_text_v2(gold), _normalize_text_v2(pred), error_type=None
        )
        assert isinstance(result, bool)

    def test_empty_pred_is_ng(self):
        """空 pred → 常に NG"""
        assert is_correct_negative_v2("何でも", "", error_type="aizuchi_tail") is False
