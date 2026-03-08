"""
Unit tests for scripts/misc/openapi_generator.py
（外部依存なし - 純粋なPythonクラス）
"""
import json
import sys
from pathlib import Path

import pytest

from scripts.misc.openapi_generator import OpenAPISpecBuilder, FlaskOpenAPIExtractor


# ─── OpenAPISpecBuilder ────────────────────────────────────────────────────────
class TestOpenAPISpecBuilderInit:
    def test_default_values(self):
        builder = OpenAPISpecBuilder()
        assert builder.title == "ManaOS Unified API"
        assert builder.version == "1.0.0"
        assert builder.endpoints == []

    def test_custom_values(self):
        builder = OpenAPISpecBuilder(
            title="My API", description="desc", version="2.0", base_url="http://x.com"
        )
        assert builder.title == "My API"
        assert builder.version == "2.0"
        assert builder.base_url == "http://x.com"


class TestOpenAPISpecBuilderAddEndpoint:
    def test_add_single_endpoint(self):
        builder = OpenAPISpecBuilder()
        builder.add_endpoint("/health", "GET", summary="Health check")
        assert len(builder.endpoints) == 1
        assert builder.endpoints[0]["path"] == "/health"
        assert builder.endpoints[0]["method"] == "get"

    def test_add_multiple_endpoints(self):
        builder = OpenAPISpecBuilder()
        builder.add_endpoint("/a", "GET")
        builder.add_endpoint("/b", "POST")
        builder.add_endpoint("/c", "DELETE")
        assert len(builder.endpoints) == 3

    def test_method_lowercased(self):
        builder = OpenAPISpecBuilder()
        builder.add_endpoint("/x", "POST")
        assert builder.endpoints[0]["method"] == "post"

    def test_requires_auth_adds_security(self):
        builder = OpenAPISpecBuilder()
        builder.add_endpoint("/secure", "GET", requires_auth=True)
        assert builder.endpoints[0]["security"] != []

    def test_no_auth_empty_security(self):
        builder = OpenAPISpecBuilder()
        builder.add_endpoint("/open", "GET", requires_auth=False)
        assert builder.endpoints[0]["security"] == []

    def test_default_responses_added(self):
        builder = OpenAPISpecBuilder()
        builder.add_endpoint("/ep", "GET")
        resp = builder.endpoints[0]["responses"]
        assert "200" in resp

    def test_tags_set_correctly(self):
        builder = OpenAPISpecBuilder()
        builder.add_endpoint("/tagged", "GET", tags=["Health", "API"])
        assert builder.endpoints[0]["tags"] == ["Health", "API"]

    def test_summary_defaults_to_method_path(self):
        builder = OpenAPISpecBuilder()
        builder.add_endpoint("/ep", "GET")
        assert "GET" in builder.endpoints[0]["summary"] or "/ep" in builder.endpoints[0]["summary"]


class TestOpenAPISpecBuilderBuild:
    def test_build_returns_dict(self):
        builder = OpenAPISpecBuilder()
        builder.add_endpoint("/health", "GET")
        spec = builder.build()
        assert isinstance(spec, dict)

    def test_build_has_openapi_version(self):
        builder = OpenAPISpecBuilder()
        spec = builder.build()
        assert spec.get("openapi") == "3.0.3"

    def test_build_has_info(self):
        builder = OpenAPISpecBuilder(title="Test API", version="3.0")
        spec = builder.build()
        assert spec["info"]["title"] == "Test API"
        assert spec["info"]["version"] == "3.0"

    def test_build_has_paths(self):
        builder = OpenAPISpecBuilder()
        builder.add_endpoint("/health", "GET")
        builder.add_endpoint("/data", "POST")
        spec = builder.build()
        assert "/health" in spec["paths"]
        assert "/data" in spec["paths"]

    def test_build_has_components(self):
        builder = OpenAPISpecBuilder()
        spec = builder.build()
        assert "components" in spec
        assert "securitySchemes" in spec["components"]

    def test_build_has_servers(self):
        builder = OpenAPISpecBuilder(base_url="http://myapi.com")
        spec = builder.build()
        assert spec["servers"][0]["url"] == "http://myapi.com"

    def test_request_body_included_when_set(self):
        builder = OpenAPISpecBuilder()
        builder.add_endpoint(
            "/data", "POST",
            request_body={"required": True, "content": {"application/json": {}}}
        )
        spec = builder.build()
        assert "requestBody" in spec["paths"]["/data"]["post"]

    def test_request_body_not_included_when_none(self):
        builder = OpenAPISpecBuilder()
        builder.add_endpoint("/data", "GET")
        spec = builder.build()
        assert "requestBody" not in spec["paths"]["/data"]["get"]


class TestOpenAPISpecBuilderToJSON:
    def test_to_json_returns_valid_json(self):
        builder = OpenAPISpecBuilder()
        builder.add_endpoint("/x", "GET")
        json_str = builder.to_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_to_json_has_openapi_key(self):
        builder = OpenAPISpecBuilder()
        json_str = builder.to_json()
        parsed = json.loads(json_str)
        assert "openapi" in parsed


class TestOpenAPISpecBuilderSaveToFile:
    def test_save_creates_file(self, tmp_path: Path):
        builder = OpenAPISpecBuilder()
        builder.add_endpoint("/health", "GET")
        out = str(tmp_path / "spec.json")
        result = builder.save_to_file(out)
        assert Path(result).exists()

    def test_save_creates_parent_dirs(self, tmp_path: Path):
        builder = OpenAPISpecBuilder()
        out = str(tmp_path / "nested" / "dir" / "spec.json")
        builder.save_to_file(out)
        assert Path(out).exists()

    def test_saved_content_is_valid_json(self, tmp_path: Path):
        builder = OpenAPISpecBuilder()
        builder.add_endpoint("/ep", "POST")
        out = str(tmp_path / "spec.json")
        builder.save_to_file(out)
        content = Path(out).read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert "openapi" in parsed


# ─── FlaskOpenAPIExtractor ────────────────────────────────────────────────────
class TestFlaskOpenAPIExtractor:
    def test_extract_from_app_returns_builder(self):
        from unittest.mock import MagicMock
        # Build a minimal Flask mock
        fake_rule = MagicMock()
        fake_rule.endpoint = "health"
        fake_rule.methods = {"GET", "OPTIONS", "HEAD"}
        fake_rule.__str__ = lambda self: "/health"
        fake_app = MagicMock()
        fake_app.url_map.iter_rules.return_value = [fake_rule]
        fake_view = MagicMock(__doc__="Health check endpoint\nReturns status.")
        fake_app.view_functions = {"health": fake_view}

        builder = FlaskOpenAPIExtractor.extract_from_app(fake_app)
        assert isinstance(builder, OpenAPISpecBuilder)
