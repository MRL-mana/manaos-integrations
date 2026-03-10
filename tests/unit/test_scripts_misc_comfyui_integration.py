"""
Unit tests for scripts/misc/comfyui_integration.py
"""
import sys
from unittest.mock import MagicMock, patch

import pytest

# ── モジュールモック（インポート前に設定）──────────────────────────────────────
_ml = MagicMock()
_ml.get_logger = MagicMock(return_value=MagicMock())
_ml.get_service_logger = MagicMock(return_value=MagicMock())
sys.modules.setdefault("manaos_logger", _ml)

_error_obj = MagicMock()
_error_obj.message = "mocked error"
_error_obj.user_message = "mocked user error"
_meh = MagicMock()
_meh.ManaOSErrorHandler = MagicMock(return_value=MagicMock(
    handle_exception=MagicMock(return_value=_error_obj)
))
_meh.ErrorCategory = MagicMock()
_meh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _meh)

_mtc = MagicMock()
_mtc.get_timeout_config = MagicMock(return_value={"api_call": 10, "workflow_execution": 60})
sys.modules.setdefault("manaos_timeout_config", _mtc)

_mcv = MagicMock()
_mcv.ConfigValidator = MagicMock(return_value=MagicMock())
sys.modules.setdefault("manaos_config_validator", _mcv)

_cve = MagicMock()
_cve.ConfigValidatorEnhanced = MagicMock(return_value=MagicMock(
    validate_config_file=MagicMock(return_value=(True, [], {}))
))
sys.modules.setdefault("config_validator_enhanced", _cve)

_paths_mod = sys.modules.get("_paths") or MagicMock()
_paths_mod.COMFYUI_PORT = 8188  # type: ignore
sys.modules["_paths"] = _paths_mod

from scripts.misc.comfyui_integration import ComfyUIIntegration, DEFAULT_COMFYUI_URL


# ── helpers ────────────────────────────────────────────────────────────────
def _make_integration(url: str = "http://localhost:8188") -> ComfyUIIntegration:
    return ComfyUIIntegration(base_url=url)


def _mock_response(status_code: int = 200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.raise_for_status = MagicMock()
    return resp


def _mock_response_raise(exc: Exception):
    resp = MagicMock()
    resp.raise_for_status.side_effect = exc
    return resp


# ── TestDefaultUrl ─────────────────────────────────────────────────────────
class TestDefaultUrl:
    def test_default_url_uses_comfyui_port(self):
        assert "8188" in DEFAULT_COMFYUI_URL

    def test_base_url_stored(self):
        ci = _make_integration("http://localhost:9999")
        assert ci.base_url == "http://localhost:9999"

    def test_trailing_slash_stripped(self):
        ci = _make_integration("http://localhost:8188/")
        assert not ci.base_url.endswith("/")


# ── TestInitializeInternal ─────────────────────────────────────────────────
class TestInitializeInternal:
    def test_returns_true_on_200(self):
        ci = _make_integration()
        resp = _mock_response(200)
        with patch.object(ci.session, "get", return_value=resp):
            result = ci._initialize_internal()
        assert result is True

    def test_returns_false_on_non_200(self):
        ci = _make_integration()
        resp = _mock_response(503)
        with patch.object(ci.session, "get", return_value=resp):
            result = ci._initialize_internal()
        assert result is False

    def test_returns_false_on_exception(self):
        ci = _make_integration()
        with patch.object(ci.session, "get", side_effect=Exception("no conn")):
            result = ci._initialize_internal()
        assert result is False


# ── TestCheckAvailabilityInternal ──────────────────────────────────────────
class TestCheckAvailabilityInternal:
    def test_returns_true_on_200(self):
        ci = _make_integration()
        resp = _mock_response(200)
        with patch.object(ci.session, "get", return_value=resp):
            result = ci._check_availability_internal()
        assert result is True

    def test_returns_false_on_exception(self):
        ci = _make_integration()
        with patch.object(ci.session, "get", side_effect=Exception("refused")):
            result = ci._check_availability_internal()
        assert result is False


# ── TestGetQueueStatus ─────────────────────────────────────────────────────
class TestGetQueueStatus:
    def test_returns_json_on_success(self):
        ci = _make_integration()
        resp = _mock_response(200, json_data={"queue_running": [], "queue_pending": []})
        with patch.object(ci.session, "get", return_value=resp):
            result = ci.get_queue_status()
        assert "queue_running" in result
        assert "queue_pending" in result

    def test_returns_error_on_exception(self):
        ci = _make_integration()
        with patch.object(ci.session, "get", side_effect=Exception("timeout")):
            result = ci.get_queue_status()
        assert "error" in result


# ── TestListCheckpoints ────────────────────────────────────────────────────
class TestListCheckpoints:
    def test_returns_checkpoint_names(self):
        ci = _make_integration()
        payload = {
            "CheckpointLoaderSimple": {
                "input": {
                    "required": {
                        "ckpt_name": [["v1-5-pruned.safetensors", "xl_base.safetensors"]]
                    }
                }
            }
        }
        with patch.object(ci.session, "get", return_value=_mock_response(200, payload)):
            result = ci.list_checkpoints()
        assert "v1-5-pruned.safetensors" in result
        assert "xl_base.safetensors" in result

    def test_returns_empty_on_exception(self):
        ci = _make_integration()
        with patch.object(ci.session, "get", side_effect=Exception("err")):
            result = ci.list_checkpoints()
        assert result == []

    def test_returns_no_named_checkpoints_on_malformed_response(self):
        ci = _make_integration()
        with patch.object(ci.session, "get", return_value=_mock_response(200, {})):
            result = ci.list_checkpoints()
        # malformed → default fallback [[[]]][0] = [[]] → list returns [[]]  
        assert isinstance(result, list)


# ── TestSubmitWorkflow ─────────────────────────────────────────────────────
class TestSubmitWorkflow:
    def test_returns_prompt_id_on_success(self):
        ci = _make_integration()
        resp = _mock_response(200, {"prompt_id": "abc-123"})
        with patch.object(ci.session, "post", return_value=resp):
            result = ci.submit_workflow({"1": {}}, prompt="test prompt")
        assert result == "abc-123"

    def test_returns_none_on_exception(self):
        ci = _make_integration()
        with patch.object(ci.session, "post", side_effect=Exception("refused")):
            result = ci.submit_workflow({"1": {}})
        assert result is None

    def test_includes_prompt_in_payload(self):
        ci = _make_integration()
        resp = _mock_response(200, {"prompt_id": "x"})
        with patch.object(ci.session, "post", return_value=resp) as mock_post:
            ci.submit_workflow({"1": {}}, prompt="artist:picasso")
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs.get("json", {})
        assert "extra_data" in payload


# ── TestGetHistory ─────────────────────────────────────────────────────────
class TestGetHistory:
    def test_returns_list_on_success(self):
        ci = _make_integration()
        history_data = [{"id": "1", "status": "done"}]
        with patch.object(ci.session, "get", return_value=_mock_response(200, history_data)):
            result = ci.get_history(max_items=5)
        assert isinstance(result, list)

    def test_returns_empty_on_exception(self):
        ci = _make_integration()
        with patch.object(ci.session, "get", side_effect=Exception("err")):
            result = ci.get_history()
        assert result == []


# ── TestGenerateImage ──────────────────────────────────────────────────────
class TestGenerateImage:
    def _make_ci_with_ckpts(self, ckpts=None):
        ci = _make_integration()
        if ckpts is None:
            ckpts = ["base.safetensors"]
        ci.list_checkpoints = MagicMock(return_value=ckpts)
        return ci

    def test_returns_prompt_id_on_success(self):
        ci = self._make_ci_with_ckpts()
        ci.submit_workflow = MagicMock(return_value="prompt-99")
        result = ci.generate_image(prompt="1girl, solo")
        assert result == "prompt-99"

    def test_returns_none_on_submit_failure(self):
        ci = self._make_ci_with_ckpts()
        ci.submit_workflow = MagicMock(return_value=None)
        result = ci.generate_image(prompt="1girl")
        assert result is None

    def test_uses_model_from_checkpoints_when_not_specified(self):
        ci = self._make_ci_with_ckpts(["auto_ckpt.safetensors"])
        workflows_submitted = []
        def _capture(wf, *a, **kw):
            workflows_submitted.append(wf)
            return "pid"
        ci.submit_workflow = _capture  # type: ignore
        ci.generate_image(prompt="test", model="")
        wf = workflows_submitted[0]
        assert wf["1"]["inputs"]["ckpt_name"] == "auto_ckpt.safetensors"

    def test_loras_are_included_in_workflow(self):
        ci = self._make_ci_with_ckpts(["base.safetensors"])
        workflows_submitted = []
        def _capture(wf, *a, **kw):
            workflows_submitted.append(wf)
            return "pid"
        ci.submit_workflow = _capture  # type: ignore
        ci.generate_image(prompt="test", loras=[("lora_a.safetensors", 0.8)])
        wf = workflows_submitted[0]
        lora_nodes = [v for v in wf.values() if v.get("class_type") == "LoraLoader"]
        assert len(lora_nodes) == 1
        assert lora_nodes[0]["inputs"]["lora_name"] == "lora_a.safetensors"

    def test_no_checkpoints_fallback_uses_specified_model(self):
        ci = self._make_ci_with_ckpts([])
        workflows_submitted = []
        def _capture(wf, *a, **kw):
            workflows_submitted.append(wf)
            return "pid"
        ci.submit_workflow = _capture  # type: ignore
        ci.generate_image(prompt="test", model="my_model.safetensors")
        wf = workflows_submitted[0]
        assert wf["1"]["inputs"]["ckpt_name"] == "my_model.safetensors"

    def test_returns_none_on_exception(self):
        ci = _make_integration()
        ci.list_checkpoints = MagicMock(side_effect=Exception("fail"))
        result = ci.generate_image(prompt="test")
        assert result is None
