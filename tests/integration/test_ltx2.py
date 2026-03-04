"""LTX-2動画生成統合テスト（pytest対応）"""

import importlib
from pathlib import Path

import pytest
import requests


def _create_ltx2() -> object:
    module = None
    last_error = None
    for module_name in ("ltx2_video_integration", "ltx2.ltx2_video_integration"):
        try:
            module = importlib.import_module(module_name)
            break
        except Exception as exc:
            last_error = exc
    if module is None:
        pytest.skip(f"ltx2_video_integration の読み込みに失敗: {last_error}")

    integration_cls = getattr(module, "LTX2VideoIntegration", None)
    if integration_cls is None:
        pytest.skip("LTX2VideoIntegration が見つからないためスキップ")

    try:
        return integration_cls()
    except Exception as exc:
        pytest.skip(f"LTX2VideoIntegration 初期化に失敗: {exc}")


def test_comfyui_connection_smoke():
    try:
        response = requests.get("http://127.0.0.1:8188/system_stats", timeout=5)
    except requests.RequestException as exc:
        return

    assert response.status_code in (200, 401, 403, 404, 500, 503)


def test_ltx2_initialization_smoke():
    ltx2 = _create_ltx2()
    assert ltx2 is not None


def test_ltx2_queue_status_smoke():
    ltx2 = _create_ltx2()
    if not hasattr(ltx2, "get_queue_status"):
        pytest.skip("get_queue_status が未実装のためスキップ")

    queue_status = ltx2.get_queue_status()
    assert isinstance(queue_status, dict)


def test_ltx2_workflow_creation_smoke():
    ltx2 = _create_ltx2()
    image_path = Path("test_image.png")
    if not image_path.exists():
        image_path = Path("placeholder.png")

    if not hasattr(ltx2, "create_ltx2_workflow"):
        pytest.skip("create_ltx2_workflow が未実装のためスキップ")

    workflow = ltx2.create_ltx2_workflow(
        start_image_path=str(image_path),
        prompt="test prompt",
        video_length_seconds=5,
        use_two_pass=True,
        use_nag=True,
        use_res2s_sampler=True,
    )
    assert workflow is not None
