"""
tests/unit/test_scripts_misc_api_documentation_generator.py

scripts/misc/api_documentation_generator.py の単体テスト
- generate_openapi_spec() — 静的 dict の構造検証
- save_openapi_spec(output_path) — ファイル I/O
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "misc"))

import api_documentation_generator as adg


# ===========================
# generate_openapi_spec()
# ===========================

class TestGenerateOpenApiSpec:
    def _spec(self):
        return adg.generate_openapi_spec()

    def test_returns_dict(self):
        assert isinstance(self._spec(), dict)

    def test_openapi_version_3(self):
        spec = self._spec()
        assert spec["openapi"].startswith("3.")

    def test_info_section_present(self):
        assert "info" in self._spec()

    def test_info_title_manaos(self):
        assert "ManaOS" in self._spec()["info"]["title"]

    def test_info_version_present(self):
        assert "version" in self._spec()["info"]

    def test_servers_is_list(self):
        assert isinstance(self._spec()["servers"], list)

    def test_servers_not_empty(self):
        assert len(self._spec()["servers"]) > 0

    def test_servers_have_url(self):
        for s in self._spec()["servers"]:
            assert "url" in s

    def test_tags_is_list(self):
        assert isinstance(self._spec()["tags"], list)

    def test_tags_include_health(self):
        names = {t["name"] for t in self._spec()["tags"]}
        assert "Health" in names

    def test_tags_include_services(self):
        names = {t["name"] for t in self._spec()["tags"]}
        assert "Services" in names

    def test_tags_include_llm(self):
        names = {t["name"] for t in self._spec()["tags"]}
        assert "LLM" in names

    def test_tags_include_metrics(self):
        names = {t["name"] for t in self._spec()["tags"]}
        assert "Metrics" in names

    def test_paths_is_dict(self):
        assert isinstance(self._spec()["paths"], dict)

    def test_paths_not_empty(self):
        assert len(self._spec()["paths"]) > 0

    def test_health_endpoint_present(self):
        assert "/health" in self._spec()["paths"]

    def test_health_has_get(self):
        assert "get" in self._spec()["paths"]["/health"]

    def test_llm_chat_endpoint_present(self):
        assert "/api/llm/chat" in self._spec()["paths"]

    def test_llm_chat_has_post(self):
        assert "post" in self._spec()["paths"]["/api/llm/chat"]

    def test_metrics_endpoint_present(self):
        assert "/api/metrics" in self._spec()["paths"]

    def test_components_present(self):
        assert "components" in self._spec()

    def test_security_schemes_present(self):
        assert "securitySchemes" in self._spec()["components"]

    def test_api_key_auth_defined(self):
        schemes = self._spec()["components"]["securitySchemes"]
        assert "ApiKeyAuth" in schemes

    def test_bearer_auth_defined(self):
        schemes = self._spec()["components"]["securitySchemes"]
        assert "BearerAuth" in schemes

    def test_api_key_auth_type(self):
        scheme = self._spec()["components"]["securitySchemes"]["ApiKeyAuth"]
        assert scheme["type"] == "apiKey"

    def test_api_key_header_name(self):
        scheme = self._spec()["components"]["securitySchemes"]["ApiKeyAuth"]
        assert scheme["name"] == "X-API-Key"

    def test_bearer_scheme(self):
        scheme = self._spec()["components"]["securitySchemes"]["BearerAuth"]
        assert scheme["scheme"] == "bearer"

    def test_error_schema_defined(self):
        schemas = self._spec()["components"].get("schemas", {})
        assert "Error" in schemas

    def test_spec_is_json_serializable(self):
        spec = self._spec()
        dumped = json.dumps(spec)
        assert isinstance(dumped, str)
        reloaded = json.loads(dumped)
        assert reloaded["openapi"] == spec["openapi"]

    def test_returns_new_dict_each_call(self):
        s1 = adg.generate_openapi_spec()
        s2 = adg.generate_openapi_spec()
        # Both should have same content but different objects
        assert s1 == s2


# ===========================
# save_openapi_spec(output_path)
# ===========================

class TestSaveOpenApiSpec:
    def test_saves_file(self, tmp_path):
        out = tmp_path / "openapi.json"
        adg.save_openapi_spec(out)
        assert out.exists()

    def test_saved_file_is_valid_json(self, tmp_path):
        out = tmp_path / "openapi.json"
        adg.save_openapi_spec(out)
        content = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(content, dict)

    def test_saved_spec_openapi_version(self, tmp_path):
        out = tmp_path / "openapi.json"
        adg.save_openapi_spec(out)
        content = json.loads(out.read_text(encoding="utf-8"))
        assert content["openapi"].startswith("3.")

    def test_creates_parent_directory(self, tmp_path):
        out = tmp_path / "subdir" / "docs" / "openapi.json"
        adg.save_openapi_spec(out)
        assert out.exists()

    def test_returns_path(self, tmp_path):
        out = tmp_path / "openapi.json"
        result = adg.save_openapi_spec(out)
        assert result == out

    def test_saved_paths_not_empty(self, tmp_path):
        out = tmp_path / "openapi.json"
        adg.save_openapi_spec(out)
        content = json.loads(out.read_text(encoding="utf-8"))
        assert len(content["paths"]) > 0
