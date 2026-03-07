"""Unit tests for tools/file_secretary_engine.py."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
import file_secretary_engine as fse
from file_secretary_engine import Rule


# ─────────────────────────────────────────────────────────────────────────────
# to_list
# ─────────────────────────────────────────────────────────────────────────────

class TestToList:
    def test_none_returns_empty(self):
        assert fse.to_list(None) == []

    def test_single_string(self):
        assert fse.to_list("hello") == ["hello"]

    def test_list_preserved(self):
        assert fse.to_list(["a", "b", "c"]) == ["a", "b", "c"]

    def test_list_items_converted_to_str(self):
        assert fse.to_list([1, 2]) == ["1", "2"]

    def test_scalar_converted_to_str(self):
        assert fse.to_list(42) == ["42"]


# ─────────────────────────────────────────────────────────────────────────────
# file_matches  (uses tmp_path for real file stat)
# ─────────────────────────────────────────────────────────────────────────────

def _make_rule(name: str = "r", **match_kwargs) -> Rule:
    return Rule(name=name, match=match_kwargs, action={"type": "none"})


class TestFileMatches:
    def test_no_constraints_always_matches(self, tmp_path):
        f = tmp_path / "anything.txt"
        f.write_bytes(b"data")
        rule = _make_rule()
        assert fse.file_matches(rule, f) is True

    def test_extension_match(self, tmp_path):
        f = tmp_path / "report.pdf"
        f.write_bytes(b"data")
        rule = _make_rule(extension=".pdf")
        assert fse.file_matches(rule, f) is True

    def test_extension_no_match(self, tmp_path):
        f = tmp_path / "report.txt"
        f.write_bytes(b"data")
        rule = _make_rule(extension=".pdf")
        assert fse.file_matches(rule, f) is False

    def test_extension_case_insensitive(self, tmp_path):
        f = tmp_path / "PHOTO.JPG"
        f.write_bytes(b"data")
        rule = _make_rule(extension=".jpg")
        assert fse.file_matches(rule, f) is True

    def test_filename_contains_match(self, tmp_path):
        f = tmp_path / "invoice_2026.pdf"
        f.write_bytes(b"data")
        rule = _make_rule(filename_contains="invoice")
        assert fse.file_matches(rule, f) is True

    def test_filename_contains_no_match(self, tmp_path):
        f = tmp_path / "receipt_2026.pdf"
        f.write_bytes(b"data")
        rule = _make_rule(filename_contains="invoice")
        assert fse.file_matches(rule, f) is False

    def test_max_size_excludes_small_file(self, tmp_path):
        # max_size_bytes → file must be LARGER than threshold to match
        f = tmp_path / "small.bin"
        f.write_bytes(b"hi")  # 2 bytes
        rule = _make_rule(max_size_bytes=100)
        # st_size (2) <= 100 → does NOT match
        assert fse.file_matches(rule, f) is False

    def test_max_size_matches_large_file(self, tmp_path):
        f = tmp_path / "big.bin"
        f.write_bytes(b"x" * 200)
        rule = _make_rule(max_size_bytes=100)
        # st_size (200) > 100 → matches
        assert fse.file_matches(rule, f) is True

    def test_combined_ext_and_contains_both_must_match(self, tmp_path):
        f = tmp_path / "invoice.pdf"
        f.write_bytes(b"data")
        # Both constraints satisfied
        rule = _make_rule(extension=".pdf", filename_contains="invoice")
        assert fse.file_matches(rule, f) is True

    def test_combined_ext_ok_but_contains_fails(self, tmp_path):
        f = tmp_path / "receipt.pdf"
        f.write_bytes(b"data")
        rule = _make_rule(extension=".pdf", filename_contains="invoice")
        assert fse.file_matches(rule, f) is False


# ─────────────────────────────────────────────────────────────────────────────
# safe_target_path
# ─────────────────────────────────────────────────────────────────────────────

class TestSafeTargetPath:
    def test_relative_target_under_inbox(self, tmp_path):
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        result = fse.safe_target_path(inbox, "archive", "file.pdf")
        assert result.parent == (inbox / "archive").resolve()
        assert result.name == "file.pdf"

    def test_dot_target_stays_in_inbox(self, tmp_path):
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        result = fse.safe_target_path(inbox, ".", "new_name.txt")
        assert result.parent == inbox.resolve()

    def test_path_traversal_raises(self, tmp_path):
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        with pytest.raises(ValueError, match="escapes inbox"):
            fse.safe_target_path(inbox, "../outside", "evil.txt")


# ─────────────────────────────────────────────────────────────────────────────
# apply_action
# ─────────────────────────────────────────────────────────────────────────────

class TestApplyAction:
    def test_none_action_returns_skip(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_bytes(b"data")
        kind, dest, status = fse.apply_action(tmp_path, f, {"type": "none"}, dry_run=True)
        assert kind == "none"
        assert status == "SKIP"

    def test_move_dry_run_no_actual_move(self, tmp_path):
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        src = inbox / "report.pdf"
        src.write_bytes(b"data")
        kind, dest, status = fse.apply_action(
            inbox, src, {"type": "move", "target": "archive"}, dry_run=True
        )
        assert status == "OK"
        assert src.exists()  # dry_run: file not moved

    def test_move_actually_moves_file(self, tmp_path):
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        src = inbox / "report.pdf"
        src.write_bytes(b"data")
        kind, dest, status = fse.apply_action(
            inbox, src, {"type": "move", "target": "archive"}, dry_run=False
        )
        assert status == "OK"
        assert not src.exists()
        assert Path(dest).exists()

    def test_move_missing_target_returns_fail(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_bytes(b"data")
        kind, dest, status = fse.apply_action(tmp_path, f, {"type": "move"}, dry_run=True)
        assert "FAIL" in status

    def test_tag_action_returns_tag_value(self, tmp_path):
        f = tmp_path / "photo.jpg"
        f.write_bytes(b"data")
        kind, dest, status = fse.apply_action(
            tmp_path, f, {"type": "tag", "tag": "personal"}, dry_run=True
        )
        assert kind == "tag"
        assert dest == "personal"
        assert status == "OK"

    def test_tag_missing_value_returns_fail(self, tmp_path):
        f = tmp_path / "photo.jpg"
        f.write_bytes(b"data")
        kind, dest, status = fse.apply_action(
            tmp_path, f, {"type": "tag"}, dry_run=True
        )
        assert "FAIL" in status

    def test_unsupported_action_returns_fail(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_bytes(b"data")
        kind, dest, status = fse.apply_action(
            tmp_path, f, {"type": "upload_s3"}, dry_run=True
        )
        assert "FAIL" in status


# ─────────────────────────────────────────────────────────────────────────────
# load_rules
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadRules:
    def test_basic_rule_parsed(self, tmp_path):
        yaml_text = textwrap.dedent("""\
            rules:
              - name: move_pdfs
                match:
                  extension: .pdf
                action:
                  type: move
                  target: docs
        """)
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text(yaml_text, encoding="utf-8")
        rules, _ = fse.load_rules(rules_file)
        assert len(rules) == 1
        assert rules[0].name == "move_pdfs"
        assert rules[0].match["extension"] == ".pdf"

    def test_defaults_parsed(self, tmp_path):
        yaml_text = textwrap.dedent("""\
            defaults:
              dry_run: true
            rules: []
        """)
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text(yaml_text, encoding="utf-8")
        _, defaults = fse.load_rules(rules_file)
        assert defaults.get("dry_run") is True

    def test_empty_rules_list(self, tmp_path):
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("rules: []\n", encoding="utf-8")
        rules, _ = fse.load_rules(rules_file)
        assert rules == []

    def test_non_dict_root_raises(self, tmp_path):
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="root must be mapping"):
            fse.load_rules(rules_file)

    def test_unnamed_rule_gets_default_name(self, tmp_path):
        yaml_text = textwrap.dedent("""\
            rules:
              - match:
                  extension: .tmp
                action:
                  type: none
        """)
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text(yaml_text, encoding="utf-8")
        rules, _ = fse.load_rules(rules_file)
        assert rules[0].name == "unnamed_rule"
