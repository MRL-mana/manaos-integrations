"""tests/unit/test_scripts_misc_demo_llm_routing.py

demo_llm_routing.py の単体テスト
"""
import json
import pytest
import scripts.misc.demo_llm_routing as _mod


class TestPrintSection:
    def test_prints_title(self, capsys):
        _mod.print_section("テストタイトル")
        out = capsys.readouterr().out
        assert "テストタイトル" in out

    def test_prints_separator(self, capsys):
        _mod.print_section("X")
        out = capsys.readouterr().out
        assert "=" in out

    def test_returns_none(self):
        assert _mod.print_section("test") is None


class TestPrintResult:
    def test_prints_title(self, capsys):
        _mod.print_result({"key": "value"}, title="テスト結果")
        out = capsys.readouterr().out
        assert "テスト結果" in out

    def test_prints_json_content(self, capsys):
        _mod.print_result({"score": 42}, title="結果")
        out = capsys.readouterr().out
        assert "42" in out

    def test_default_title(self, capsys):
        _mod.print_result({"a": 1})
        out = capsys.readouterr().out
        assert "結果" in out

    def test_returns_none(self):
        assert _mod.print_result({"x": 1}) is None

    def test_nested_dict(self, capsys):
        data = {"outer": {"inner": "hello"}}
        _mod.print_result(data)
        out = capsys.readouterr().out
        assert "hello" in out
