"""router.py の商用エンドポイント定義を依存なしで検証するテスト。"""

from pathlib import Path

import pytest


ROUTER_PATH = (
    Path(__file__).resolve().parents[2]
    / "image_generation_service"
    / "router.py"
)


def _router_text() -> str:
    return ROUTER_PATH.read_text(encoding="utf-8")


class TestCommercialRouterSource:

    def test_payment_endpoints_declared(self):
        content = _router_text()
        assert '@router.post("/payment/stripe"' in content
        assert '@router.post("/payment/komoju"' in content

    def test_signup_endpoint_declared(self):
        content = _router_text()
        assert '@router.post("/signup"' in content
        assert "class SignupRequest(BaseModel):" in content

    def test_dashboard_endpoint_declared(self):
        content = _router_text()
        assert '@router.get(\n    "/dashboard"' in content

    def test_dynamic_job_route_is_after_dashboard(self):
        content = _router_text()
        dashboard_pos = content.find('@router.get(\n    "/dashboard"')
        job_pos = content.find('@router.get(\n    "/{job_id}"')
        assert dashboard_pos != -1
        assert job_pos != -1
        assert dashboard_pos < job_pos

    def test_dynamic_result_route_is_after_dashboard(self):
        content = _router_text()
        dashboard_pos = content.find('@router.get(\n    "/dashboard"')
        result_pos = content.find('@router.get(\n    "/{job_id}/result"')
        assert dashboard_pos != -1
        assert result_pos != -1
        assert dashboard_pos < result_pos

    def test_file_exists(self):
        assert ROUTER_PATH.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
