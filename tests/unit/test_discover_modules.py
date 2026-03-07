"""Unit tests for tools/discover_modules.py — pure helper functions."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
import discover_modules as dm


# ─────────────────────────────────────────────────────────────────────────────
# _extract_docstring
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractDocstring:
    def test_triple_quote_docstring(self, tmp_path):
        f = tmp_path / "mod.py"
        f.write_text('"""My module description."""\nx = 1\n', encoding="utf-8")
        assert dm._extract_docstring(f) == "My module description."

    def test_hash_comment_fallback(self, tmp_path):
        f = tmp_path / "mod.py"
        f.write_text("# This is a helper script\nx = 1\n", encoding="utf-8")
        result = dm._extract_docstring(f)
        assert "This is a helper script" in result

    def test_empty_file_returns_empty_string(self, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("", encoding="utf-8")
        assert dm._extract_docstring(f) == ""

    def test_no_docstring_no_comment_returns_empty(self, tmp_path):
        f = tmp_path / "nocomment.py"
        f.write_text("x = 1\ny = 2\n", encoding="utf-8")
        assert dm._extract_docstring(f) == ""

    def test_single_quote_docstring(self, tmp_path):
        f = tmp_path / "sq.py"
        f.write_text("'''Single quote docstring'''\n", encoding="utf-8")
        result = dm._extract_docstring(f)
        assert "Single quote docstring" in result

    def test_non_existent_file_returns_empty(self, tmp_path):
        f = tmp_path / "missing.py"
        # ファイルが存在しなければ空文字
        assert dm._extract_docstring(f) == ""


# ─────────────────────────────────────────────────────────────────────────────
# _check_syntax
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckSyntax:
    def test_valid_python_returns_true_none(self, tmp_path):
        f = tmp_path / "valid.py"
        f.write_text("def foo():\n    return 42\n", encoding="utf-8")
        ok, err = dm._check_syntax(f)
        assert ok is True
        assert err is None

    def test_syntax_error_returns_false_with_message(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def broken(\n    pass\n", encoding="utf-8")
        ok, err = dm._check_syntax(f)
        assert ok is False
        assert err is not None
        assert "Line" in err

    def test_empty_file_is_valid_python(self, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("", encoding="utf-8")
        ok, err = dm._check_syntax(f)
        assert ok is True
        assert err is None

    def test_complex_valid_file(self, tmp_path):
        code = textwrap.dedent("""\
            from __future__ import annotations
            import os
            from typing import Optional

            class Foo:
                def bar(self, x: int) -> Optional[str]:
                    return str(x) if x else None
        """)
        f = tmp_path / "complex.py"
        f.write_text(code, encoding="utf-8")
        ok, err = dm._check_syntax(f)
        assert ok is True

    def test_indentation_error_returns_false(self, tmp_path):
        f = tmp_path / "indent_err.py"
        f.write_text("if True:\npass\n", encoding="utf-8")
        ok, err = dm._check_syntax(f)
        assert ok is False


# ─────────────────────────────────────────────────────────────────────────────
# _find_flask_routes
# ─────────────────────────────────────────────────────────────────────────────

class TestFindFlaskRoutes:
    def test_no_routes_returns_empty(self, tmp_path):
        f = tmp_path / "noroutes.py"
        f.write_text("x = 1\ndef foo(): pass\n", encoding="utf-8")
        assert dm._find_flask_routes(f) == []

    def test_single_route_found(self, tmp_path):
        f = tmp_path / "app.py"
        f.write_text('@app.route("/health")\ndef health(): pass\n', encoding="utf-8")
        routes = dm._find_flask_routes(f)
        assert routes == ["/health"]

    def test_multiple_routes_found(self, tmp_path):
        code = textwrap.dedent("""\
            @app.route("/health")
            def health(): pass

            @app.route("/status")
            def status(): pass

            @api.route("/generate")
            def generate(): pass
        """)
        f = tmp_path / "api.py"
        f.write_text(code, encoding="utf-8")
        routes = dm._find_flask_routes(f)
        assert "/health" in routes
        assert "/status" in routes
        assert "/generate" in routes
        assert len(routes) == 3

    def test_single_quote_route_found(self, tmp_path):
        f = tmp_path / "sq.py"
        f.write_text("@bp.route('/api/v1/data')\ndef data(): pass\n", encoding="utf-8")
        routes = dm._find_flask_routes(f)
        assert "/api/v1/data" in routes

    def test_non_existent_file_returns_empty(self, tmp_path):
        f = tmp_path / "missing.py"
        assert dm._find_flask_routes(f) == []
