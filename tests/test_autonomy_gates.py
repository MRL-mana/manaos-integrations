#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_autonomy_gates.py
autonomy_gates.py の単体テスト
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# プロジェクトルートを sys.path に追加
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT / "scripts" / "misc") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "scripts" / "misc"))

from autonomy_gates import (
    ActionClass,
    LEVEL_ALLOWED_ACTION_CLASSES,
    TOOL_ACTION_CLASS,
    action_allowed_at_level,
    audit_log,
    check_budget,
    check_gate,
    generate_hmac_confirm_token,
    get_action_class_for_tool,
    get_audit_log_path,
    get_budget_usage_path,
    get_degraded_level,
    get_usage_key_for_tool,
    increment_budget_usage,
    input_hash_for_audit,
    is_confirm_token_required,
    is_quiet_hours,
    load_budget_usage,
    verify_hmac_confirm_token,
)

# ─────────────────────────────────────────────
# テスト用ヘルパー
# ─────────────────────────────────────────────


def _config_with_tmpdir(tmp_path: Path) -> dict:
    return {
        "budget_usage_dir": str(tmp_path),
        "audit_log_dir": str(tmp_path),
    }


# ─────────────────────────────────────────────
# ActionClass マッピング
# ─────────────────────────────────────────────


class TestActionClassMapping:
    def test_c0_readonly_tools(self):
        assert get_action_class_for_tool("device_get_status") == ActionClass.C0
        assert get_action_class_for_tool("brave_search") == ActionClass.C0
        assert get_action_class_for_tool("obsidian_search_notes") == ActionClass.C0

    def test_c1_append_tools(self):
        assert get_action_class_for_tool("obsidian_create_note") == ActionClass.C1
        assert get_action_class_for_tool("memory_store") == ActionClass.C1
        assert get_action_class_for_tool("notification_send") == ActionClass.C1

    def test_c2_reversible_tools(self):
        assert get_action_class_for_tool("file_secretary_organize") == ActionClass.C2
        assert get_action_class_for_tool("personality_update") == ActionClass.C2

    def test_c3_costly_tools(self):
        assert get_action_class_for_tool("llm_chat") == ActionClass.C3
        assert get_action_class_for_tool("comfyui_generate_image") == ActionClass.C3
        assert get_action_class_for_tool("svi_generate_video") == ActionClass.C3

    def test_c4_destructive_tools(self):
        assert get_action_class_for_tool("pixel7_execute") == ActionClass.C4
        assert get_action_class_for_tool("n8n_execute_workflow") == ActionClass.C4
        assert get_action_class_for_tool("mothership_execute") == ActionClass.C4

    def test_unknown_tool_defaults_to_c4(self):
        """未定義ツールは安全側に C4"""
        assert get_action_class_for_tool("totally_unknown_tool_xyz") == ActionClass.C4

    def test_pico_hid_read_is_c0(self):
        assert get_action_class_for_tool("pico_hid_screenshot") == ActionClass.C0
        assert get_action_class_for_tool("pico_hid_mouse_position") == ActionClass.C0

    def test_pico_hid_write_is_c4(self):
        assert get_action_class_for_tool("pico_hid_key_press") == ActionClass.C4
        assert get_action_class_for_tool("pico_hid_mouse_click") == ActionClass.C4


# ─────────────────────────────────────────────
# レベル別許可
# ─────────────────────────────────────────────


class TestLevelPermissions:
    def test_l0_denies_everything(self):
        for cls in ActionClass:
            assert action_allowed_at_level(0, cls) is False

    def test_l1_allows_only_c0(self):
        assert action_allowed_at_level(1, ActionClass.C0) is True
        assert action_allowed_at_level(1, ActionClass.C1) is False
        assert action_allowed_at_level(1, ActionClass.C2) is False

    def test_l2_allows_c0_c1(self):
        assert action_allowed_at_level(2, ActionClass.C0) is True
        assert action_allowed_at_level(2, ActionClass.C1) is True
        assert action_allowed_at_level(2, ActionClass.C2) is False

    def test_l3_allows_c0_c1_c2(self):
        assert action_allowed_at_level(3, ActionClass.C2) is True
        assert action_allowed_at_level(3, ActionClass.C3) is False

    def test_l6_allows_all(self):
        for cls in ActionClass:
            assert action_allowed_at_level(6, cls) is True

    def test_out_of_range_level(self):
        assert action_allowed_at_level(-1, ActionClass.C0) is False
        assert action_allowed_at_level(99, ActionClass.C0) is False


# ─────────────────────────────────────────────
# Gate A + B (check_gate)
# ─────────────────────────────────────────────


class TestCheckGate:
    def test_l0_always_denied(self):
        allowed, reason = check_gate(0, "device_get_status")
        assert allowed is False
        assert "L0" in reason

    def test_l1_readonly_allowed(self):
        allowed, reason = check_gate(1, "device_get_status")
        assert allowed is True
        assert reason == ""

    def test_l1_costly_denied(self):
        allowed, reason = check_gate(1, "llm_chat")
        assert allowed is False

    def test_l3_c2_allowed(self):
        allowed, reason = check_gate(3, "file_secretary_organize")
        assert allowed is True

    def test_l3_c3_denied(self):
        allowed, reason = check_gate(3, "llm_chat")
        assert allowed is False

    def test_l5_c3_denied_level_mismatch(self):
        """L5 は C3 を許可しない（LEVEL_ALLOWED_ACTION_CLASSES の定義通り）"""
        allowed, reason = check_gate(
            5,
            "llm_chat",
            confirm_token=None,
            config={"require_confirm_token_classes": ["C3", "C4"]},
        )
        assert allowed is False
        # レベル不一致か Confirm Token のどちらかのメッセージが含まれる
        assert "L5" in reason or "C3" in reason or "Confirm" in reason

    def test_l6_c3_needs_confirm_token(self):
        """L6 は C3 を許可するが Confirm Token が必要"""
        allowed, reason = check_gate(
            6,
            "llm_chat",
            confirm_token=None,
            config={"require_confirm_token_classes": ["C3", "C4"]},
        )
        assert allowed is False
        assert "Confirm Token" in reason

    def test_l6_c4_allowed_with_valid_token(self, tmp_path):
        token = generate_hmac_confirm_token("testsecret", 300)
        config = {
            "confirm_token_hmac_secret": "testsecret",
            "confirm_token_hmac_window_seconds": 300,
            "require_confirm_token_classes": ["C3", "C4"],
        }
        allowed, reason = check_gate(6, "pixel7_execute", confirm_token=token, config=config)
        assert allowed is True, reason

    def test_l6_c4_denied_with_invalid_token(self):
        config = {
            "confirm_token_hmac_secret": "testsecret",
            "confirm_token_hmac_window_seconds": 300,
            "require_confirm_token_classes": ["C3", "C4"],
        }
        allowed, reason = check_gate(6, "pixel7_execute", confirm_token="invalid_token", config=config)
        assert allowed is False
        assert "無効" in reason or "Confirm" in reason

    def test_no_token_required_below_c3_by_default(self):
        """C2 以下はトークン不要（デフォルト設定）"""
        config = {"require_confirm_token_classes": ["C3", "C4"]}
        allowed, reason = check_gate(6, "file_secretary_organize", confirm_token=None, config=config)
        assert allowed is True


# ─────────────────────────────────────────────
# HMAC Confirm Token
# ─────────────────────────────────────────────


class TestHmacConfirmToken:
    def test_generate_and_verify(self):
        secret = "my_secret"
        token = generate_hmac_confirm_token(secret, 300)
        assert token.startswith("hmac_")
        assert verify_hmac_confirm_token(token, secret, 300)

    def test_wrong_secret_fails(self):
        token = generate_hmac_confirm_token("secret_a", 300)
        assert not verify_hmac_confirm_token(token, "secret_b", 300)

    def test_invalid_format_fails(self):
        assert not verify_hmac_confirm_token("not_a_token", "secret", 300)
        assert not verify_hmac_confirm_token("", "secret", 300)

    def test_no_secret_raises(self):
        with pytest.raises(ValueError):
            generate_hmac_confirm_token("")


# ─────────────────────────────────────────────
# Gate C: 予算管理
# ─────────────────────────────────────────────


class TestBudgetManagement:
    def test_load_empty_budget(self, tmp_path):
        config = _config_with_tmpdir(tmp_path)
        usage = load_budget_usage(config)
        # 空か既定値が返ってくる
        assert isinstance(usage, dict)

    def test_increment_and_reload(self, tmp_path):
        config = _config_with_tmpdir(tmp_path)
        increment_budget_usage(config, "llm_calls", "per_hour", 3)
        usage = load_budget_usage(config)
        assert isinstance(usage, dict)

    def test_check_budget_within_limit(self, tmp_path):
        config = _config_with_tmpdir(tmp_path)
        config["budget"] = {"per_hour": {"llm_calls": 100}}
        ok, _ = check_budget(config, "llm_calls", "per_hour")
        assert ok is True

    def test_check_budget_exceeded(self, tmp_path):
        config = _config_with_tmpdir(tmp_path)
        config["budget"] = {"per_hour": {"llm_calls": 2}}
        # 2回使用して上限に達する
        increment_budget_usage(config, "llm_calls", "per_hour", 2)
        ok, _ = check_budget(config, "llm_calls", "per_hour")
        assert ok is False

    def test_check_budget_no_limit_returns_ok(self, tmp_path):
        config = _config_with_tmpdir(tmp_path)
        ok, _ = check_budget(config, "llm_calls", "per_hour")
        assert ok is True

    def test_increment_multiple_keys(self, tmp_path):
        config = _config_with_tmpdir(tmp_path)
        config["budget"] = {"per_hour": {"image_jobs": 5, "video_jobs": 3}}
        increment_budget_usage(config, "image_jobs", "per_hour", 2)
        increment_budget_usage(config, "video_jobs", "per_hour", 1)
        ok_img, _ = check_budget(config, "image_jobs", "per_hour")
        ok_vid, _ = check_budget(config, "video_jobs", "per_hour")
        assert ok_img is True
        assert ok_vid is True


# ─────────────────────────────────────────────
# usage_key マッピング
# ─────────────────────────────────────────────


class TestUsageKeyMapping:
    def test_llm_tools(self):
        assert get_usage_key_for_tool("llm_chat") == "llm_calls"
        assert get_usage_key_for_tool("openwebui_send_message") == "llm_calls"
        assert get_usage_key_for_tool("brave_search") == "llm_calls"

    def test_image_tools(self):
        assert get_usage_key_for_tool("comfyui_generate_image") == "image_jobs"

    def test_video_tools(self):
        assert get_usage_key_for_tool("svi_generate_video") == "video_jobs"
        assert get_usage_key_for_tool("svi_extend_video") == "video_jobs"

    def test_no_cost_tools(self):
        assert get_usage_key_for_tool("device_get_status") is None
        assert get_usage_key_for_tool("pixel7_execute") is None


# ─────────────────────────────────────────────
# Gate D: 監査ログ
# ─────────────────────────────────────────────


class TestAuditLog:
    def test_audit_log_writes_jsonl(self, tmp_path):
        config = _config_with_tmpdir(tmp_path)
        audit_log(
            config,
            plan_id="plan_001",
            action_id="act_001",
            tool_name="llm_chat",
            action_class="C3",
            input_hash="abc123",
            result="success",
            message="test",
            level=4,
        )
        log_path = get_audit_log_path(config)
        assert log_path.exists()
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["tool"] == "llm_chat"
        assert entry["result"] == "success"
        assert entry["level"] == 4

    def test_audit_log_appends_multiple(self, tmp_path):
        config = _config_with_tmpdir(tmp_path)
        for i in range(3):
            audit_log(
                config,
                plan_id=f"plan_{i}",
                action_id=f"act_{i}",
                tool_name="llm_chat",
                action_class="C3",
                input_hash=f"hash{i}",
                result="success",
                level=4,
            )
        lines = get_audit_log_path(config).read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3

    def test_input_hash_for_audit(self):
        h1 = input_hash_for_audit({"tool": "llm_chat", "prompt": "hello"})
        h2 = input_hash_for_audit({"tool": "llm_chat", "prompt": "hello"})
        h3 = input_hash_for_audit({"tool": "llm_chat", "prompt": "world"})
        assert h1 == h2  # 同じ入力は同じハッシュ
        assert h1 != h3  # 異なる入力は異なるハッシュ
        assert len(h1) == 16  # 16文字

    def test_audit_log_path(self, tmp_path):
        config = _config_with_tmpdir(tmp_path)
        path = get_audit_log_path(config)
        assert path.name == "autonomy_audit.jsonl"
        assert str(tmp_path) in str(path)


# ─────────────────────────────────────────────
# 降格ポリシー
# ─────────────────────────────────────────────


class TestDegradePolicy:
    def test_budget_exceeded_degrades(self):
        config = {"degrade_policy": {"on_budget_exceeded": 2}}
        assert get_degraded_level(config, "on_budget_exceeded") == 2

    def test_repeated_failures_degrades(self):
        config = {"degrade_policy": {"on_repeated_failures": 3}}
        assert get_degraded_level(config, "on_repeated_failures") == 3

    def test_no_policy_returns_default(self):
        config = {}
        # デフォルト: on_budget_exceeded=2, on_repeated_failures=3
        assert get_degraded_level(config, "on_budget_exceeded") == 2
        assert get_degraded_level(config, "on_repeated_failures") == 3


# ─────────────────────────────────────────────
# 静音時間
# ─────────────────────────────────────────────


class TestQuietHours:
    def test_no_quiet_hours_config_returns_false(self):
        assert is_quiet_hours({}) is False

    def test_empty_quiet_hours_returns_false(self):
        assert is_quiet_hours({"quiet_hours": {}}) is False

    def test_always_quiet_22_to_07(self):
        """22:00〜07:00 → 時刻によって変わる（境界値外ではなく論理確認）"""
        from datetime import datetime as _dt
        import unittest.mock as mock

        with mock.patch("autonomy_gates.datetime") as mock_dt:
            mock_dt.now.return_value = _dt(2024, 1, 1, 23, 0, 0)
            mock_dt.strptime = _dt.strptime
            config = {"quiet_hours": {"start": "22:00", "end": "07:00"}}
            assert is_quiet_hours(config) is True

    def test_outside_quiet_hours(self):
        from datetime import datetime as _dt
        import unittest.mock as mock

        with mock.patch("autonomy_gates.datetime") as mock_dt:
            mock_dt.now.return_value = _dt(2024, 1, 1, 12, 0, 0)
            mock_dt.strptime = _dt.strptime
            config = {"quiet_hours": {"start": "22:00", "end": "07:00"}}
            assert is_quiet_hours(config) is False


# ─────────────────────────────────────────────
# confirm_token_required
# ─────────────────────────────────────────────


class TestConfirmTokenRequired:
    def test_c3_requires_token(self):
        assert is_confirm_token_required(ActionClass.C3) is True

    def test_c4_requires_token(self):
        assert is_confirm_token_required(ActionClass.C4) is True

    def test_c0_no_token(self):
        assert is_confirm_token_required(ActionClass.C0) is False

    def test_c1_no_token(self):
        assert is_confirm_token_required(ActionClass.C1) is False

    def test_c2_no_token(self):
        assert is_confirm_token_required(ActionClass.C2) is False
