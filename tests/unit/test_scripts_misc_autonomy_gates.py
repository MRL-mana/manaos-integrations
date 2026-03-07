"""
Unit tests for scripts/misc/autonomy_gates.py

Pure-function tests — no external deps, no mocking needed for most cases.
Tests: ActionClass enum, tool→class mapping, level gate logic, HMAC tokens,
quiet hours, degraded level, budget defaults, input hash.
"""
import sys
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "misc"))
import autonomy_gates as ag
from autonomy_gates import (
    ActionClass,
    get_action_class_for_tool,
    get_usage_key_for_tool,
    is_confirm_token_required,
    action_allowed_at_level,
    check_gate,
    _verify_confirm_token,
    generate_hmac_confirm_token,
    verify_hmac_confirm_token,
    _default_budget_usage,
    input_hash_for_audit,
    is_quiet_hours,
    get_degraded_level,
    get_budget_usage_path,
)


# ---------------------------------------------------------------------------
# ActionClass enum
# ---------------------------------------------------------------------------

class TestActionClass:
    def test_c0_value(self):
        assert ActionClass.C0.value == "C0"

    def test_c1_value(self):
        assert ActionClass.C1.value == "C1"

    def test_c2_value(self):
        assert ActionClass.C2.value == "C2"

    def test_c3_value(self):
        assert ActionClass.C3.value == "C3"

    def test_c4_value(self):
        assert ActionClass.C4.value == "C4"

    def test_five_members(self):
        assert len(list(ActionClass)) == 5

    def test_c3_in_require_confirm_token_classes(self):
        assert ActionClass.C3 in ag.REQUIRE_CONFIRM_TOKEN_CLASSES

    def test_c4_in_require_confirm_token_classes(self):
        assert ActionClass.C4 in ag.REQUIRE_CONFIRM_TOKEN_CLASSES

    def test_c0_not_in_require_confirm_token_classes(self):
        assert ActionClass.C0 not in ag.REQUIRE_CONFIRM_TOKEN_CLASSES


# ---------------------------------------------------------------------------
# get_action_class_for_tool
# ---------------------------------------------------------------------------

class TestGetActionClassForTool:
    def test_read_only_tool_is_c0(self):
        assert get_action_class_for_tool("device_get_status") == ActionClass.C0

    def test_search_tool_is_c0(self):
        assert get_action_class_for_tool("web_search") == ActionClass.C0

    def test_screenshot_is_c0(self):
        assert get_action_class_for_tool("pico_hid_screenshot") == ActionClass.C0

    def test_append_only_tool_is_c1(self):
        assert get_action_class_for_tool("memory_store") == ActionClass.C1

    def test_notification_is_c1(self):
        assert get_action_class_for_tool("notification_send") == ActionClass.C1

    def test_reversible_tool_is_c2(self):
        assert get_action_class_for_tool("file_secretary_organize") == ActionClass.C2

    def test_vscode_search_is_c0(self):
        assert get_action_class_for_tool("vscode_search_files") == ActionClass.C0

    def test_costly_llm_is_c3(self):
        assert get_action_class_for_tool("llm_chat") == ActionClass.C3

    def test_image_gen_is_c3(self):
        assert get_action_class_for_tool("comfyui_generate_image") == ActionClass.C3

    def test_destructive_tool_is_c4(self):
        assert get_action_class_for_tool("n8n_execute_workflow") == ActionClass.C4

    def test_vscode_execute_is_c4(self):
        assert get_action_class_for_tool("vscode_execute_command") == ActionClass.C4

    def test_unknown_tool_defaults_to_c4(self):
        assert get_action_class_for_tool("totally_unknown_tool") == ActionClass.C4


# ---------------------------------------------------------------------------
# get_usage_key_for_tool
# ---------------------------------------------------------------------------

class TestGetUsageKeyForTool:
    def test_llm_chat_returns_llm_calls(self):
        assert get_usage_key_for_tool("llm_chat") == "llm_calls"

    def test_base_ai_chat_returns_llm_calls(self):
        assert get_usage_key_for_tool("base_ai_chat") == "llm_calls"

    def test_brave_search_returns_llm_calls(self):
        assert get_usage_key_for_tool("brave_search") == "llm_calls"

    def test_comfyui_returns_image_jobs(self):
        assert get_usage_key_for_tool("comfyui_generate_image") == "image_jobs"

    def test_image_stock_add_returns_image_jobs(self):
        assert get_usage_key_for_tool("image_stock_add") == "image_jobs"

    def test_svi_generate_returns_video_jobs(self):
        assert get_usage_key_for_tool("svi_generate_video") == "video_jobs"

    def test_svi_extend_returns_video_jobs(self):
        assert get_usage_key_for_tool("svi_extend_video") == "video_jobs"

    def test_c0_tool_returns_none(self):
        assert get_usage_key_for_tool("device_get_status") is None

    def test_destructive_non_budget_tool_returns_none(self):
        assert get_usage_key_for_tool("n8n_execute_workflow") is None

    def test_unknown_tool_returns_none(self):
        assert get_usage_key_for_tool("not_a_real_tool") is None


# ---------------------------------------------------------------------------
# is_confirm_token_required
# ---------------------------------------------------------------------------

class TestIsConfirmTokenRequired:
    def test_c0_not_required(self):
        assert is_confirm_token_required(ActionClass.C0) is False

    def test_c1_not_required(self):
        assert is_confirm_token_required(ActionClass.C1) is False

    def test_c2_not_required(self):
        assert is_confirm_token_required(ActionClass.C2) is False

    def test_c3_required(self):
        assert is_confirm_token_required(ActionClass.C3) is True

    def test_c4_required(self):
        assert is_confirm_token_required(ActionClass.C4) is True


# ---------------------------------------------------------------------------
# action_allowed_at_level
# ---------------------------------------------------------------------------

class TestActionAllowedAtLevel:
    def test_level_0_nothing_allowed(self):
        for ac in ActionClass:
            assert action_allowed_at_level(0, ac) is False

    def test_level_1_c0_allowed(self):
        assert action_allowed_at_level(1, ActionClass.C0) is True

    def test_level_1_c1_not_allowed(self):
        assert action_allowed_at_level(1, ActionClass.C1) is False

    def test_level_2_c1_allowed(self):
        assert action_allowed_at_level(2, ActionClass.C1) is True

    def test_level_2_c2_not_allowed(self):
        assert action_allowed_at_level(2, ActionClass.C2) is False

    def test_level_3_c2_allowed(self):
        assert action_allowed_at_level(3, ActionClass.C2) is True

    def test_level_3_c3_not_allowed(self):
        assert action_allowed_at_level(3, ActionClass.C3) is False

    def test_level_5_c3_not_allowed(self):
        assert action_allowed_at_level(5, ActionClass.C3) is False

    def test_level_6_all_allowed(self):
        for ac in ActionClass:
            assert action_allowed_at_level(6, ac) is True

    def test_negative_level_returns_false(self):
        assert action_allowed_at_level(-1, ActionClass.C0) is False

    def test_level_7_returns_false(self):
        assert action_allowed_at_level(7, ActionClass.C0) is False


# ---------------------------------------------------------------------------
# check_gate
# ---------------------------------------------------------------------------

class TestCheckGate:
    def test_c0_tool_allowed_at_level_1(self):
        ok, reason = check_gate(1, "device_get_status")
        assert ok is True
        assert reason == ""

    def test_c4_tool_blocked_at_level_3(self):
        ok, reason = check_gate(3, "n8n_execute_workflow")
        assert ok is False
        assert "L3" in reason or "C4" in reason

    def test_c3_tool_requires_token_at_level_6(self):
        ok, reason = check_gate(6, "llm_chat", confirm_token=None,
                                config={"require_confirm_token_classes": ["C3", "C4"]})
        assert ok is False
        assert "Confirm Token" in reason

    def test_c3_tool_allowed_with_valid_allowlist_token(self):
        config = {
            "require_confirm_token_classes": ["C3", "C4"],
            "confirm_tokens_allowlist": ["abc123"],
        }
        ok, reason = check_gate(6, "llm_chat", confirm_token="abc123", config=config)
        assert ok is True

    def test_c1_tool_no_token_needed_at_level_3(self):
        ok, reason = check_gate(3, "memory_store")
        assert ok is True

    def test_c0_blocked_at_level_0(self):
        ok, reason = check_gate(0, "device_get_status")
        assert ok is False


# ---------------------------------------------------------------------------
# generate_hmac_confirm_token + verify_hmac_confirm_token
# ---------------------------------------------------------------------------

class TestGenerateHmacConfirmToken:
    def test_returns_hmac_prefix(self):
        token = generate_hmac_confirm_token("mysecret")
        assert token.startswith("hmac_")

    def test_format_is_hmac_window_sig(self):
        token = generate_hmac_confirm_token("mysecret")
        parts = token.split("_")
        assert len(parts) == 3
        assert parts[0] == "hmac"
        assert parts[1].isdigit()
        assert len(parts[2]) == 16

    def test_empty_secret_raises_value_error(self):
        with pytest.raises(ValueError):
            generate_hmac_confirm_token("")


class TestVerifyHmacConfirmToken:
    def test_roundtrip_valid(self):
        secret = "test_secret_key"
        token = generate_hmac_confirm_token(secret, window_seconds=300)
        assert verify_hmac_confirm_token(token, secret, window_seconds=300) is True

    def test_wrong_secret_returns_false(self):
        token = generate_hmac_confirm_token("secret_a", window_seconds=300)
        assert verify_hmac_confirm_token(token, "secret_b", window_seconds=300) is False

    def test_empty_token_returns_false(self):
        assert verify_hmac_confirm_token("", "secret") is False

    def test_no_hmac_prefix_returns_false(self):
        assert verify_hmac_confirm_token("not_a_token", "secret") is False

    def test_wrong_part_count_returns_false(self):
        assert verify_hmac_confirm_token("hmac_only", "secret") is False

    def test_non_numeric_window_returns_false(self):
        assert verify_hmac_confirm_token("hmac_abc_0123456789abcdef", "secret") is False

    def test_tampered_sig_returns_false(self):
        secret = "test_secret_key"
        token = generate_hmac_confirm_token(secret, window_seconds=300)
        tampered = token[:-4] + "xxxx"
        assert verify_hmac_confirm_token(tampered, secret, window_seconds=300) is False


# ---------------------------------------------------------------------------
# _verify_confirm_token
# ---------------------------------------------------------------------------

class TestVerifyConfirmToken:
    def test_allowlist_match(self):
        config = {"confirm_tokens_allowlist": ["token_abc"]}
        assert _verify_confirm_token("token_abc", config) is True

    def test_allowlist_no_match(self):
        config = {"confirm_tokens_allowlist": ["other_token"]}
        assert _verify_confirm_token("token_xyz", config) is False

    def test_empty_token_returns_false(self):
        assert _verify_confirm_token("", {}) is False

    def test_whitespace_only_returns_false(self):
        assert _verify_confirm_token("   ", {}) is False

    def test_hmac_roundtrip_via_verify(self):
        secret = "verify_test_secret"
        token = generate_hmac_confirm_token(secret, window_seconds=300)
        config = {"confirm_token_hmac_secret": secret, "confirm_token_hmac_window_seconds": 300}
        assert _verify_confirm_token(token, config) is True


# ---------------------------------------------------------------------------
# _default_budget_usage
# ---------------------------------------------------------------------------

class TestDefaultBudgetUsage:
    def test_has_per_hour_key(self):
        usage = _default_budget_usage()
        assert "per_hour" in usage

    def test_has_per_day_key(self):
        usage = _default_budget_usage()
        assert "per_day" in usage

    def test_per_hour_all_zero(self):
        usage = _default_budget_usage()
        for v in usage["per_hour"].values():
            assert v == 0

    def test_per_day_all_zero(self):
        usage = _default_budget_usage()
        for v in usage["per_day"].values():
            assert v == 0

    def test_has_hour_start(self):
        usage = _default_budget_usage()
        assert "hour_start" in usage

    def test_has_day_start(self):
        usage = _default_budget_usage()
        assert "day_start" in usage

    def test_per_hour_has_llm_calls(self):
        usage = _default_budget_usage()
        assert "llm_calls" in usage["per_hour"]


# ---------------------------------------------------------------------------
# input_hash_for_audit
# ---------------------------------------------------------------------------

class TestInputHashForAudit:
    def test_returns_16_char_hex(self):
        result = input_hash_for_audit("test input")
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self):
        assert input_hash_for_audit("same") == input_hash_for_audit("same")

    def test_different_input_different_hash(self):
        assert input_hash_for_audit("one") != input_hash_for_audit("two")

    def test_accepts_dict(self):
        result = input_hash_for_audit({"key": "value", "num": 42})
        assert len(result) == 16

    def test_dict_ordering_stable(self):
        h1 = input_hash_for_audit({"b": 2, "a": 1})
        h2 = input_hash_for_audit({"a": 1, "b": 2})
        assert h1 == h2  # sort_keys=True ensures stable serialization


# ---------------------------------------------------------------------------
# is_quiet_hours
# ---------------------------------------------------------------------------

class TestIsQuietHours:
    def test_no_config_returns_false(self):
        assert is_quiet_hours({}) is False

    def test_missing_start_returns_false(self):
        assert is_quiet_hours({"quiet_hours": {"end": "07:00"}}) is False

    def test_missing_end_returns_false(self):
        assert is_quiet_hours({"quiet_hours": {"start": "22:00"}}) is False

    def test_same_day_range_inside(self):
        config = {"quiet_hours": {"start": "10:00", "end": "18:00"}}
        with patch("autonomy_gates.datetime") as mock_dt:
            mock_dt.now.return_value = MagicMock(
                time=lambda: datetime(2024, 1, 1, 14, 0).time()
            )
            mock_dt.strptime = staticmethod(datetime.strptime)
            assert is_quiet_hours(config) is True

    def test_same_day_range_outside(self):
        config = {"quiet_hours": {"start": "10:00", "end": "18:00"}}
        with patch("autonomy_gates.datetime") as mock_dt:
            mock_dt.now.return_value = MagicMock(
                time=lambda: datetime(2024, 1, 1, 20, 0).time()
            )
            mock_dt.strptime = staticmethod(datetime.strptime)
            assert is_quiet_hours(config) is False

    def test_cross_midnight_inside(self):
        config = {"quiet_hours": {"start": "22:00", "end": "07:00"}}
        with patch("autonomy_gates.datetime") as mock_dt:
            mock_dt.now.return_value = MagicMock(
                time=lambda: datetime(2024, 1, 1, 23, 30).time()
            )
            mock_dt.strptime = staticmethod(datetime.strptime)
            assert is_quiet_hours(config) is True

    def test_cross_midnight_outside(self):
        config = {"quiet_hours": {"start": "22:00", "end": "07:00"}}
        with patch("autonomy_gates.datetime") as mock_dt:
            mock_dt.now.return_value = MagicMock(
                time=lambda: datetime(2024, 1, 1, 12, 0).time()
            )
            mock_dt.strptime = staticmethod(datetime.strptime)
            assert is_quiet_hours(config) is False


# ---------------------------------------------------------------------------
# get_degraded_level
# ---------------------------------------------------------------------------

class TestGetDegradedLevel:
    def test_on_budget_exceeded_default_is_2(self):
        assert get_degraded_level({}, "on_budget_exceeded") == 2

    def test_on_repeated_failures_default_is_3(self):
        assert get_degraded_level({}, "on_repeated_failures") == 3

    def test_on_budget_exceeded_custom_value(self):
        config = {"degrade_policy": {"on_budget_exceeded": 1}}
        assert get_degraded_level(config, "on_budget_exceeded") == 1

    def test_on_repeated_failures_custom_value(self):
        config = {"degrade_policy": {"on_repeated_failures": 2}}
        assert get_degraded_level(config, "on_repeated_failures") == 2

    def test_unknown_reason_returns_autonomy_level(self):
        config = {"autonomy_level": 5}
        assert get_degraded_level(config, "unknown_reason") == 5

    def test_unknown_reason_no_autonomy_level_returns_4(self):
        assert get_degraded_level({}, "unknown_reason") == 4


# ---------------------------------------------------------------------------
# get_budget_usage_path
# ---------------------------------------------------------------------------

class TestGetBudgetUsagePath:
    def test_returns_path_object(self):
        result = get_budget_usage_path({})
        assert isinstance(result, Path)

    def test_default_filename(self):
        result = get_budget_usage_path({})
        assert result.name == "autonomy_budget_usage.json"

    def test_custom_dir(self, tmp_path):
        config = {"budget_usage_dir": str(tmp_path)}
        result = get_budget_usage_path(config)
        assert result.parent == tmp_path
