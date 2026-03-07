"""
tests/unit/test_scripts_misc_playbook_auto_promotion.py

scripts/misc/playbook_auto_promotion.py の純粋ロジック単体テスト
- _clamp_rate()
- determine_tier()
- TIER_CRITERIA 定数
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "misc"))

import playbook_auto_promotion as pap
from playbook_auto_promotion import _clamp_rate, determine_tier, TIER_CRITERIA


# ===========================
# _clamp_rate()
# ===========================

class TestClampRate:
    def test_zero_returns_zero(self):
        assert _clamp_rate(0.0) == 0.0

    def test_one_returns_one(self):
        assert _clamp_rate(1.0) == 1.0

    def test_midpoint(self):
        assert _clamp_rate(0.5) == 0.5

    def test_negative_clamped_to_zero(self):
        assert _clamp_rate(-0.5) == 0.0

    def test_over_one_clamped_to_one(self):
        assert _clamp_rate(1.5) == 1.0

    def test_none_returns_zero(self):
        assert _clamp_rate(None) == 0.0

    def test_int_input_converted(self):
        assert _clamp_rate(1) == 1.0

    def test_small_float(self):
        import math
        assert math.isclose(_clamp_rate(0.123), 0.123)

    def test_large_value_clamped(self):
        assert _clamp_rate(100.0) == 1.0


# ===========================
# TIER_CRITERIA 定数
# ===========================

class TestTierCriteria:
    def test_all_tiers_present(self):
        assert {"tier1", "tier2", "tier3"} <= TIER_CRITERIA.keys()

    def test_tier1_auto_promote_true(self):
        assert TIER_CRITERIA["tier1"]["auto_promote"] is True

    def test_tier2_auto_promote_false(self):
        assert TIER_CRITERIA["tier2"]["auto_promote"] is False

    def test_tier3_auto_promote_false(self):
        assert TIER_CRITERIA["tier3"]["auto_promote"] is False

    def test_tier1_min_score_greatest(self):
        assert (
            TIER_CRITERIA["tier1"]["min_score"]
            > TIER_CRITERIA["tier2"]["min_score"]
            > TIER_CRITERIA["tier3"]["min_score"]
        )

    def test_tier1_min_approval_greatest(self):
        assert (
            TIER_CRITERIA["tier1"]["min_approval_rate"]
            > TIER_CRITERIA["tier2"]["min_approval_rate"]
            > TIER_CRITERIA["tier3"]["min_approval_rate"]
        )

    def test_tier1_min_execution_greatest(self):
        assert (
            TIER_CRITERIA["tier1"]["min_execution_rate"]
            > TIER_CRITERIA["tier2"]["min_execution_rate"]
            > TIER_CRITERIA["tier3"]["min_execution_rate"]
        )

    def test_tier1_max_noise_strictest(self):
        # tier1 は noise が最も低くなければならない
        assert (
            TIER_CRITERIA["tier1"]["max_noise_index"]
            < TIER_CRITERIA["tier2"]["max_noise_index"]
            < TIER_CRITERIA["tier3"]["max_noise_index"]
        )

    def test_tier1_min_days_active_greatest(self):
        assert (
            TIER_CRITERIA["tier1"]["min_days_active"]
            > TIER_CRITERIA["tier2"]["min_days_active"]
            > TIER_CRITERIA["tier3"]["min_days_active"]
        )


# ===========================
# determine_tier()
# ===========================

class TestDetermineTier:
    """determine_tier(metrics) のロジック検証"""

    def _tier1_metrics(self):
        """tier1 を満たす完全なメトリクス"""
        c = TIER_CRITERIA["tier1"]
        return {
            "score_avg": c["min_score"] + 1.0,
            "approval_rate": c["min_approval_rate"] + 0.05,
            "execution_rate": c["min_execution_rate"] + 0.05,
            "noise_index": c["max_noise_index"] - 0.05,
            "days_active": c["min_days_active"] + 1,
        }

    def _tier2_metrics(self):
        """tier2 を満たすが tier1 を満たさないメトリクス"""
        c2 = TIER_CRITERIA["tier2"]
        c1 = TIER_CRITERIA["tier1"]
        return {
            "score_avg": (c2["min_score"] + c1["min_score"]) / 2.0,
            "approval_rate": c2["min_approval_rate"] + 0.05,
            "execution_rate": c2["min_execution_rate"] + 0.05,
            "noise_index": c2["max_noise_index"] - 0.05,
            "days_active": c2["min_days_active"] + 1,
        }

    def test_perfect_metrics_returns_tier1(self):
        assert determine_tier(self._tier1_metrics()) == "tier1"

    def test_returns_tier2_when_score_below_tier1(self):
        m = self._tier1_metrics()
        m["score_avg"] = TIER_CRITERIA["tier1"]["min_score"] - 0.1
        # score_avg も tier2 以上に設定
        m["score_avg"] = max(m["score_avg"], TIER_CRITERIA["tier2"]["min_score"] + 0.5)
        result = determine_tier(m)
        assert result in ("tier2", "tier3")

    def test_returns_tier3_when_all_low(self):
        result = determine_tier({
            "score_avg": 1.0,
            "approval_rate": 0.1,
            "execution_rate": 0.1,
            "noise_index": 0.99,
            "days_active": 0,
        })
        assert result == "tier3"

    def test_zero_metrics_returns_tier3(self):
        assert determine_tier({
            "score_avg": 0.0,
            "approval_rate": 0.0,
            "execution_rate": 0.0,
            "noise_index": 0.0,
            "days_active": 0,
        }) == "tier3"

    def test_none_values_handled(self):
        # None は 0 として扱われるべき
        result = determine_tier({
            "score_avg": None,
            "approval_rate": None,
            "execution_rate": None,
            "noise_index": None,
            "days_active": None,
        })
        assert result == "tier3"

    def test_noise_too_high_fails_tier1(self):
        m = self._tier1_metrics()
        m["noise_index"] = TIER_CRITERIA["tier1"]["max_noise_index"] + 0.1
        assert determine_tier(m) != "tier1"

    def test_days_active_too_low_fails_tier1(self):
        m = self._tier1_metrics()
        m["days_active"] = TIER_CRITERIA["tier1"]["min_days_active"] - 1
        assert determine_tier(m) != "tier1"

    def test_approval_rate_just_meets_tier1(self):
        m = self._tier1_metrics()
        m["approval_rate"] = TIER_CRITERIA["tier1"]["min_approval_rate"]
        assert determine_tier(m) == "tier1"

    def test_approval_rate_just_below_tier1(self):
        m = self._tier1_metrics()
        m["approval_rate"] = TIER_CRITERIA["tier1"]["min_approval_rate"] - 0.01
        assert determine_tier(m) != "tier1"

    def test_execution_rate_just_meets_tier1(self):
        m = self._tier1_metrics()
        m["execution_rate"] = TIER_CRITERIA["tier1"]["min_execution_rate"]
        assert determine_tier(m) == "tier1"

    def test_score_just_meets_tier1(self):
        m = self._tier1_metrics()
        m["score_avg"] = float(TIER_CRITERIA["tier1"]["min_score"])
        assert determine_tier(m) == "tier1"

    def test_score_just_below_tier1(self):
        m = self._tier1_metrics()
        m["score_avg"] = TIER_CRITERIA["tier1"]["min_score"] - 0.01
        # need score >= tier2 to avoid tier3
        m["score_avg"] = max(m["score_avg"], TIER_CRITERIA["tier2"]["min_score"])
        result = determine_tier(m)
        assert result in ("tier2", "tier3")

    def test_out_of_range_noise_clamped(self):
        # noise_index > 1 → clamped to 1.0 internally → tier3
        result = determine_tier({
            "score_avg": 50.0,
            "approval_rate": 2.0,
            "execution_rate": 2.0,
            "noise_index": 5.0,
            "days_active": 10,
        })
        # noise_index clamped to 1.0 > max_noise of tier1/2/3
        assert result == "tier3"

    def test_returns_string(self):
        result = determine_tier(self._tier1_metrics())
        assert isinstance(result, str)

    def test_result_is_one_of_three_tiers(self):
        for m in [self._tier1_metrics(), self._tier2_metrics(),
                   {"score_avg": 0, "approval_rate": 0, "execution_rate": 0,
                    "noise_index": 1, "days_active": 0}]:
            assert determine_tier(m) in ("tier1", "tier2", "tier3")
