"""
tests/unit/test_scripts_misc_sla_slo_monitoring.py

scripts/misc/sla_slo_monitoring.py の純粋ロジック単体テスト
- SLO dataclass
- ManaOSSLOs 定数
- SLAViolation 定数
- SLOCalculator.calculate_downtime / check_slo_violation
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "misc"))

from sla_slo_monitoring import SLO, ManaOSSLOs, SLAViolation, SLOCalculator


# ===========================
# SLO dataclass
# ===========================

class TestSLODataclass:
    def test_field_name(self):
        slo = SLO(name="Test", description="desc", target=99.9,
                  threshold=99.5, window="30d", metric="uptime")
        assert slo.name == "Test"

    def test_field_description(self):
        slo = SLO(name="X", description="explanation",
                  target=90.0, threshold=80.0, window="7d", metric="m")
        assert slo.description == "explanation"

    def test_field_target(self):
        slo = SLO(name="X", description="", target=99.9,
                  threshold=99.0, window="30d", metric="uptime")
        assert slo.target == 99.9

    def test_field_threshold(self):
        slo = SLO(name="X", description="", target=99.9,
                  threshold=99.5, window="30d", metric="uptime")
        assert slo.threshold == 99.5

    def test_field_window(self):
        slo = SLO(name="X", description="", target=99.9,
                  threshold=99.5, window="24h", metric="m")
        assert slo.window == "24h"

    def test_field_metric(self):
        slo = SLO(name="X", description="", target=99.9,
                  threshold=99.5, window="7d", metric="cache_hit_ratio")
        assert slo.metric == "cache_hit_ratio"

    def test_is_dataclass_with_six_fields(self):
        from dataclasses import fields
        assert len(fields(SLO)) == 6

    def test_equality(self):
        s1 = SLO("A", "d", 99.0, 90.0, "7d", "m")
        s2 = SLO("A", "d", 99.0, 90.0, "7d", "m")
        assert s1 == s2

    def test_inequality(self):
        s1 = SLO("A", "d", 99.0, 90.0, "7d", "m")
        s2 = SLO("B", "d", 99.0, 90.0, "7d", "m")
        assert s1 != s2

    def test_target_can_be_less_than_threshold(self):
        # SLO doesn't validate ordering; just stores values
        slo = SLO("X", "", target=10.0, threshold=20.0, window="7d", metric="m")
        assert slo.target == 10.0


# ===========================
# ManaOSSLOs 定数
# ===========================

class TestManaOSSLOs:
    def test_api_availability_type(self):
        assert isinstance(ManaOSSLOs.API_AVAILABILITY, SLO)

    def test_api_availability_target_99_9(self):
        assert ManaOSSLOs.API_AVAILABILITY.target == 99.9

    def test_api_availability_threshold_99_5(self):
        assert ManaOSSLOs.API_AVAILABILITY.threshold == 99.5

    def test_api_availability_window_30d(self):
        assert ManaOSSLOs.API_AVAILABILITY.window == "30d"

    def test_api_availability_metric_uptime(self):
        assert ManaOSSLOs.API_AVAILABILITY.metric == "uptime"

    def test_response_time_p99_type(self):
        assert isinstance(ManaOSSLOs.RESPONSE_TIME_P99, SLO)

    def test_response_time_p99_target_200(self):
        assert ManaOSSLOs.RESPONSE_TIME_P99.target == 200

    def test_response_time_p99_threshold_300(self):
        assert ManaOSSLOs.RESPONSE_TIME_P99.threshold == 300

    def test_response_time_p99_window_7d(self):
        assert ManaOSSLOs.RESPONSE_TIME_P99.window == "7d"

    def test_error_rate_type(self):
        assert isinstance(ManaOSSLOs.ERROR_RATE, SLO)

    def test_error_rate_target_0_1(self):
        assert ManaOSSLOs.ERROR_RATE.target == 0.1

    def test_error_rate_metric(self):
        assert ManaOSSLOs.ERROR_RATE.metric == "error_rate"

    def test_memory_service_availability_type(self):
        assert isinstance(ManaOSSLOs.MEMORY_SERVICE_AVAILABILITY, SLO)

    def test_memory_service_availability_target_99_5(self):
        assert ManaOSSLOs.MEMORY_SERVICE_AVAILABILITY.target == 99.5

    def test_memory_service_availability_threshold_99(self):
        assert ManaOSSLOs.MEMORY_SERVICE_AVAILABILITY.threshold == 99.0

    def test_cache_hit_rate_type(self):
        assert isinstance(ManaOSSLOs.CACHE_HIT_RATE, SLO)

    def test_cache_hit_rate_target_85(self):
        assert ManaOSSLOs.CACHE_HIT_RATE.target == 85.0

    def test_cache_hit_rate_threshold_75(self):
        assert ManaOSSLOs.CACHE_HIT_RATE.threshold == 75.0

    def test_cache_hit_rate_window_7d(self):
        assert ManaOSSLOs.CACHE_HIT_RATE.window == "7d"

    def test_backup_success_rate_type(self):
        assert isinstance(ManaOSSLOs.BACKUP_SUCCESS_RATE, SLO)

    def test_backup_success_rate_target_99_9(self):
        assert ManaOSSLOs.BACKUP_SUCCESS_RATE.target == 99.9

    def test_backup_success_rate_window_30d(self):
        assert ManaOSSLOs.BACKUP_SUCCESS_RATE.window == "30d"

    def test_all_six_are_slo_instances(self):
        for slo in (
            ManaOSSLOs.API_AVAILABILITY,
            ManaOSSLOs.RESPONSE_TIME_P99,
            ManaOSSLOs.ERROR_RATE,
            ManaOSSLOs.MEMORY_SERVICE_AVAILABILITY,
            ManaOSSLOs.CACHE_HIT_RATE,
            ManaOSSLOs.BACKUP_SUCCESS_RATE,
        ):
            assert isinstance(slo, SLO)


# ===========================
# SLAViolation 定数
# ===========================

class TestSLAViolation:
    def test_unified_api_sla_is_dict(self):
        assert isinstance(SLAViolation.UNIFIED_API_SLA, dict)

    def test_unified_api_tier_standard(self):
        assert SLAViolation.UNIFIED_API_SLA["tier"] == "Standard"

    def test_unified_api_availability_99_5(self):
        assert SLAViolation.UNIFIED_API_SLA["availability"] == 99.5

    def test_unified_api_has_response_time(self):
        rt = SLAViolation.UNIFIED_API_SLA["response_time"]
        assert {"p50", "p95", "p99"} <= rt.keys()

    def test_unified_api_response_time_p50_50ms(self):
        assert SLAViolation.UNIFIED_API_SLA["response_time"]["p50"] == 50

    def test_unified_api_incident_p1_15min(self):
        assert SLAViolation.UNIFIED_API_SLA["incident_response"]["p1"] == 15

    def test_unified_api_incident_p2_60min(self):
        assert SLAViolation.UNIFIED_API_SLA["incident_response"]["p2"] == 60

    def test_unified_api_credit_policy_exists(self):
        assert "credit_policy" in SLAViolation.UNIFIED_API_SLA

    def test_premium_sla_is_dict(self):
        assert isinstance(SLAViolation.PREMIUM_SLA, dict)

    def test_premium_tier(self):
        assert SLAViolation.PREMIUM_SLA["tier"] == "Premium"

    def test_premium_availability_99_99(self):
        assert SLAViolation.PREMIUM_SLA["availability"] == 99.99

    def test_premium_dedicated_support(self):
        assert SLAViolation.PREMIUM_SLA["dedicated_support"] is True

    def test_premium_p1_faster_than_standard(self):
        standard = SLAViolation.UNIFIED_API_SLA["incident_response"]["p1"]
        premium = SLAViolation.PREMIUM_SLA["incident_response"]["p1"]
        assert premium < standard

    def test_premium_availability_higher_than_standard(self):
        assert (
            SLAViolation.PREMIUM_SLA["availability"]
            > SLAViolation.UNIFIED_API_SLA["availability"]
        )


# ===========================
# SLOCalculator
# ===========================

class TestSLOCalculatorDowntime:
    def test_returns_string(self):
        result = SLOCalculator.calculate_downtime(99.9)
        assert isinstance(result, str)

    def test_format_has_h_and_m(self):
        result = SLOCalculator.calculate_downtime(99.9)
        assert "h" in result and "m" in result

    def test_100_percent_zero_downtime(self):
        assert SLOCalculator.calculate_downtime(100.0) == "0h 0m"

    def test_0_percent_all_downtime_1day(self):
        # 0% availability, 1 day = 1440 min = 24h 0m
        assert SLOCalculator.calculate_downtime(0.0, days=1) == "24h 0m"

    def test_50_percent_30days(self):
        # 30 days * 24 * 60 = 43200 min, 50% down = 21600 min = 360h 0m
        assert SLOCalculator.calculate_downtime(50.0, days=30) == "360h 0m"

    def test_different_days_give_different_results(self):
        r30 = SLOCalculator.calculate_downtime(99.9, days=30)
        r7 = SLOCalculator.calculate_downtime(99.9, days=7)
        assert r30 != r7

    def test_99_9_30days_small_downtime(self):
        # 99.9% → 0.1% down = 43.2 min over 30 days = 0h 43m
        assert SLOCalculator.calculate_downtime(99.9, days=30) == "0h 43m"


class TestSLOCalculatorViolation:
    @pytest.fixture
    def api_slo(self):
        return ManaOSSLOs.API_AVAILABILITY  # target=99.9, threshold=99.5

    @pytest.fixture
    def custom_slo(self):
        return SLO("Test", "d", target=100.0, threshold=90.0, window="7d", metric="m")

    def test_returns_dict(self, api_slo):
        result = SLOCalculator.check_slo_violation(99.8, api_slo)
        assert isinstance(result, dict)

    def test_not_violated_above_threshold(self, api_slo):
        result = SLOCalculator.check_slo_violation(99.8, api_slo)
        assert result["is_violated"] is False

    def test_violated_below_threshold(self, api_slo):
        result = SLOCalculator.check_slo_violation(99.0, api_slo)
        assert result["is_violated"] is True

    def test_at_threshold_not_violated(self, api_slo):
        # actual == threshold → not violated (actual < threshold is False)
        result = SLOCalculator.check_slo_violation(99.5, api_slo)
        assert result["is_violated"] is False

    def test_status_ok_when_not_violated(self, api_slo):
        result = SLOCalculator.check_slo_violation(99.9, api_slo)
        assert "OK" in result["status"]

    def test_status_violated_when_violated(self, api_slo):
        result = SLOCalculator.check_slo_violation(99.0, api_slo)
        assert "VIOLATED" in result["status"]

    def test_required_keys_present(self, custom_slo):
        result = SLOCalculator.check_slo_violation(95.0, custom_slo)
        for key in ("slo_name", "target", "actual", "threshold",
                    "is_violated", "health_percentage", "status",
                    "error_budget_remaining"):
            assert key in result

    def test_actual_stored_correctly(self, custom_slo):
        result = SLOCalculator.check_slo_violation(75.5, custom_slo)
        assert result["actual"] == 75.5

    def test_target_stored_correctly(self, api_slo):
        result = SLOCalculator.check_slo_violation(99.0, api_slo)
        assert result["target"] == 99.9

    def test_error_budget_zero_when_not_violated(self, custom_slo):
        result = SLOCalculator.check_slo_violation(95.0, custom_slo)
        assert result["error_budget_remaining"] == 0

    def test_error_budget_nonzero_when_violated(self, custom_slo):
        # target=100.0, actual=80.0 → budget = 100.0 - 80.0
        result = SLOCalculator.check_slo_violation(80.0, custom_slo)
        assert result["error_budget_remaining"] == pytest.approx(20.0)

    def test_health_percentage_calculation(self, custom_slo):
        # actual=80.0, target=100.0 → 80%
        result = SLOCalculator.check_slo_violation(80.0, custom_slo)
        assert result["health_percentage"] == pytest.approx(80.0)

    def test_zero_target_health_percentage_zero(self):
        slo = SLO("Z", "", target=0.0, threshold=0.0, window="7d", metric="m")
        result = SLOCalculator.check_slo_violation(0.0, slo)
        assert result["health_percentage"] == 0

    def test_slo_name_from_slo_object(self, api_slo):
        result = SLOCalculator.check_slo_violation(99.0, api_slo)
        assert result["slo_name"] == api_slo.name
