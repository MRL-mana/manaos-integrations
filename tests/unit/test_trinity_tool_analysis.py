"""Unit tests for tools/trinity_tool_analysis.py."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
from trinity_tool_analysis import ToolAnalysis


# ─────────────────────────────────────────────────────────────────────────────
# analyze_implementation_method — pure dict-return, no I/O
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyzeImplementationMethod:
    def setup_method(self):
        self.ta = ToolAnalysis()

    def test_returns_four_sections(self):
        result = self.ta.analyze_implementation_method()
        assert set(result.keys()) == {
            "image_generation", "ai_generation", "web_interface", "model_management"
        }

    def test_all_sections_have_method_key(self):
        result = self.ta.analyze_implementation_method()
        for key, section in result.items():
            assert "method" in section, f"section '{key}' missing 'method'"

    def test_all_sections_have_tools_used_list(self):
        result = self.ta.analyze_implementation_method()
        for key, section in result.items():
            assert isinstance(section["tools_used"], list), \
                f"section '{key}' tools_used should be list"

    def test_tools_used_nonempty(self):
        result = self.ta.analyze_implementation_method()
        for key, section in result.items():
            assert len(section["tools_used"]) > 0, f"section '{key}' tools_used empty"

    def test_external_tools_marked_none_string(self):
        result = self.ta.analyze_implementation_method()
        for key, section in result.items():
            assert section["external_tools"] == "None", \
                f"section '{key}' external_tools should be 'None'"

    def test_image_generation_references_pillow(self):
        result = self.ta.analyze_implementation_method()
        tools_text = " ".join(result["image_generation"]["tools_used"])
        assert "PIL" in tools_text or "Pillow" in tools_text

    def test_ai_generation_references_diffusers(self):
        result = self.ta.analyze_implementation_method()
        tools_text = " ".join(result["ai_generation"]["tools_used"])
        assert "Diffusers" in tools_text or "diffusers" in tools_text.lower()

    def test_web_interface_references_flask(self):
        result = self.ta.analyze_implementation_method()
        tools_text = " ".join(result["web_interface"]["tools_used"])
        assert "Flask" in tools_text or "flask" in tools_text.lower()

    def test_model_management_references_requests_or_civitai(self):
        result = self.ta.analyze_implementation_method()
        tools_text = " ".join(result["model_management"]["tools_used"])
        assert "Requests" in tools_text or "CivitAI" in tools_text


# ─────────────────────────────────────────────────────────────────────────────
# check_python_packages — dynamic import; use sys.modules mock to control
# ─────────────────────────────────────────────────────────────────────────────

def _fake_module(version: str = "9.9.9") -> ModuleType:
    m = MagicMock()
    m.__version__ = version
    return m


class TestCheckPythonPackages:
    def setup_method(self):
        self.ta = ToolAnalysis()

    def test_returns_dict(self):
        result = self.ta.check_python_packages()
        assert isinstance(result, dict)

    def test_expected_packages_present(self):
        result = self.ta.check_python_packages()
        for pkg in ("PIL", "numpy", "flask", "torch"):
            assert pkg in result, f"'{pkg}' missing from result"

    def test_each_entry_has_installed_bool(self):
        result = self.ta.check_python_packages()
        for pkg, info in result.items():
            assert isinstance(info["installed"], bool), \
                f"package '{pkg}' installed field is not bool"

    def test_each_entry_has_version_key(self):
        result = self.ta.check_python_packages()
        for pkg, info in result.items():
            assert "version" in info, f"package '{pkg}' missing 'version'"

    def test_each_entry_has_description(self):
        result = self.ta.check_python_packages()
        for pkg, info in result.items():
            assert isinstance(info["description"], str)
            assert len(info["description"]) > 0

    def test_mock_installed_package_via_sys_modules(self):
        """sys.modules に fake モジュールを挿入するとインストール済みと判定される"""
        fake = _fake_module("3.1.4")
        with patch.dict(sys.modules, {"flask": fake}, clear=False):
            result = self.ta.check_python_packages()
        assert result["flask"]["installed"] is True

    def test_mock_uninstalled_package_via_sys_modules(self):
        """sys.modules から削除すると未インストール扱いになる"""
        # diffusers は通常このシステムには存在しない
        with patch.dict(sys.modules, {}, clear=False):
            if "diffusers" in sys.modules:
                with patch.dict(sys.modules, {"diffusers": None}, clear=False):
                    result = self.ta.check_python_packages()
            else:
                result = self.ta.check_python_packages()
        assert result["diffusers"]["installed"] is False
