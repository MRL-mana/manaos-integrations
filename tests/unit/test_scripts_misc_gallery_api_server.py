"""
tests/unit/test_scripts_misc_gallery_api_server.py

gallery_api_server.py の単体テスト
"""
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── 1. sys.modules に入れるべきモックは import より前に ──────────────────
_paths_mod = MagicMock()
_paths_mod.COMFYUI_PORT = 8188
_paths_mod.GALLERY_PORT = 7860
sys.modules["_paths"] = _paths_mod

_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

# auto_reflection_improvement をモックしておく → AUTO_REFLECTION_AVAILABLE = True になる
_auto_ref_mod = MagicMock()
_auto_ref_mod.get_auto_reflection_system.return_value.get_statistics.return_value = {
    "total_evaluations": 0,
    "average_score": 0.0,
}  # test_auto_reflection.py::test_statistics が isinstance(stats, dict) を検証するため
sys.modules["auto_reflection_improvement"] = _auto_ref_mod

# api_auth をモック → require_api_key をパススルーデコレータにする（401回避）
_api_auth_mod = MagicMock()
_dummy_auth_mgr = MagicMock()
_dummy_auth_mgr.require_api_key = lambda f: f  # passthrough decorator
_api_auth_mod.get_auth_manager.return_value = _dummy_auth_mgr
_real_api_auth_backup = sys.modules.pop("api_auth", None)  # save real module
sys.modules["api_auth"] = _api_auth_mod

# ── 2. SUT import ────────────────────────────────────────────────────────
import scripts.misc.gallery_api_server as _sut
from scripts.misc.gallery_api_server import app as flask_app

# Restore real api_auth so test_api_auth_rate_limit_state.py is not polluted
if _real_api_auth_backup is not None:
    sys.modules["api_auth"] = _real_api_auth_backup
else:
    sys.modules.pop("api_auth", None)


# ══════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def _clean_jobs():
    _sut.jobs.clear()
    yield
    _sut.jobs.clear()


# ══════════════════════════════════════════════════════════════════════════
# TestGetAvailableModels
# ══════════════════════════════════════════════════════════════════════════

class TestGetAvailableModels:
    def test_returns_empty_list_when_dirs_absent(self):
        with patch.object(_sut, "COMFYUI_MODELS_DIR", Path("/nonexistent/comfyui")):
            with patch.object(_sut, "MANA_MODELS_DIR", Path("/nonexistent/mana")):
                result = _sut.get_available_models()
        assert result == []

    def test_returns_safetensors_from_comfyui_dir(self, tmp_path):
        (tmp_path / "model_a.safetensors").touch()
        (tmp_path / "model_b.safetensors").touch()
        with patch.object(_sut, "COMFYUI_MODELS_DIR", tmp_path):
            with patch.object(_sut, "MANA_MODELS_DIR", Path("/nonexistent")):
                result = _sut.get_available_models()
        assert sorted(result) == ["model_a.safetensors", "model_b.safetensors"]

    def test_deduplicates_across_both_dirs(self, tmp_path):
        comfy = tmp_path / "comfy"
        mana = tmp_path / "mana"
        comfy.mkdir()
        mana.mkdir()
        (comfy / "shared.safetensors").touch()
        (mana / "shared.safetensors").touch()
        (mana / "extra.safetensors").touch()
        with patch.object(_sut, "COMFYUI_MODELS_DIR", comfy):
            with patch.object(_sut, "MANA_MODELS_DIR", mana):
                result = _sut.get_available_models()
        assert result.count("shared.safetensors") == 1
        assert "extra.safetensors" in result


# ══════════════════════════════════════════════════════════════════════════
# TestFindModelPath
# ══════════════════════════════════════════════════════════════════════════

class TestFindModelPath:
    def test_returns_none_when_not_found(self):
        with patch.object(_sut, "COMFYUI_MODELS_DIR", Path("/nonexistent")):
            with patch.object(_sut, "MANA_MODELS_DIR", Path("/nonexistent")):
                result = _sut.find_model_path("missing.safetensors")
        assert result is None

    def test_returns_model_name_when_in_comfyui_dir(self, tmp_path):
        (tmp_path / "real_model.safetensors").touch()
        with patch.object(_sut, "COMFYUI_MODELS_DIR", tmp_path):
            result = _sut.find_model_path("real_model.safetensors")
        assert result == "real_model.safetensors"

    def test_copies_and_returns_name_when_only_in_mana_dir(self, tmp_path):
        comfy = tmp_path / "comfy"
        mana = tmp_path / "mana"
        comfy.mkdir()
        mana.mkdir()
        (mana / "mana_only.safetensors").write_bytes(b"fake")
        with patch.object(_sut, "COMFYUI_MODELS_DIR", comfy):
            with patch.object(_sut, "MANA_MODELS_DIR", mana):
                result = _sut.find_model_path("mana_only.safetensors")
        assert result == "mana_only.safetensors"
        assert (comfy / "mana_only.safetensors").exists()


# ══════════════════════════════════════════════════════════════════════════
# TestCreateComfyuiWorkflow
# ══════════════════════════════════════════════════════════════════════════

class TestCreateComfyuiWorkflow:
    def test_raises_value_error_when_no_model_available(self):
        with patch.object(_sut, "COMFYUI_MODELS_DIR", Path("/nonexistent")):
            with patch.object(_sut, "MANA_MODELS_DIR", Path("/nonexistent")):
                with pytest.raises(ValueError, match="利用可能なモデルが見つかりません"):
                    _sut.create_comfyui_workflow("test prompt")

    def test_returns_dict_with_7_nodes(self, tmp_path):
        (tmp_path / "m.safetensors").touch()
        with patch.object(_sut, "COMFYUI_MODELS_DIR", tmp_path):
            wf = _sut.create_comfyui_workflow("hello", model="m.safetensors")
        assert set(wf.keys()) == {"1", "2", "3", "4", "5", "6", "7"}

    def test_prompt_and_negative_set_correctly(self, tmp_path):
        (tmp_path / "m.safetensors").touch()
        with patch.object(_sut, "COMFYUI_MODELS_DIR", tmp_path):
            wf = _sut.create_comfyui_workflow(
                "my_prompt", negative_prompt="ugly", model="m.safetensors"
            )
        assert wf["2"]["inputs"]["text"] == "my_prompt"
        assert wf["3"]["inputs"]["text"] == "ugly"

    def test_given_seed_is_used(self, tmp_path):
        (tmp_path / "m.safetensors").touch()
        with patch.object(_sut, "COMFYUI_MODELS_DIR", tmp_path):
            wf = _sut.create_comfyui_workflow("p", model="m.safetensors", seed=42)
        assert wf["4"]["inputs"]["seed"] == 42

    def test_output_subfolder_included_when_specified(self, tmp_path):
        (tmp_path / "m.safetensors").touch()
        with patch.object(_sut, "COMFYUI_MODELS_DIR", tmp_path):
            wf = _sut.create_comfyui_workflow(
                "p", model="m.safetensors", output_subfolder="lab"
            )
        assert wf["7"]["inputs"].get("subfolder") == "lab"

    def test_no_subfolder_key_by_default(self, tmp_path):
        (tmp_path / "m.safetensors").touch()
        with patch.object(_sut, "COMFYUI_MODELS_DIR", tmp_path):
            wf = _sut.create_comfyui_workflow("p", model="m.safetensors")
        assert "subfolder" not in wf["7"]["inputs"]


# ══════════════════════════════════════════════════════════════════════════
# TestSubmitToComfyui
# ══════════════════════════════════════════════════════════════════════════

class TestSubmitToComfyui:
    def test_returns_prompt_id_on_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"prompt_id": "abc-123"}
        with patch.object(_sut, "requests") as mr:
            mr.post.return_value = mock_resp
            result = _sut.submit_to_comfyui({"1": {}})
        assert result == "abc-123"

    def test_returns_none_on_http_error_status(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "server error"
        mock_resp.json.side_effect = ValueError("no json")
        with patch.object(_sut, "requests") as mr:
            mr.post.return_value = mock_resp
            result = _sut.submit_to_comfyui({"1": {}})
        assert result is None

    def test_returns_none_on_exception(self):
        import requests as _real_requests
        with patch.object(_sut, "requests") as mr:
            # SUT uses `except requests.exceptions.RequestException` → set real class
            mr.exceptions.RequestException = _real_requests.exceptions.RequestException
            mr.post.side_effect = Exception("network error")
            result = _sut.submit_to_comfyui({"1": {}})
        assert result is None


# ══════════════════════════════════════════════════════════════════════════
# TestHealthEndpoint
# ══════════════════════════════════════════════════════════════════════════

class TestHealthEndpoint:
    def test_returns_ok_and_service_name(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.object(_sut, "requests") as mr:
            mr.get.return_value = mock_resp
            r = client.get("/health")
        data = r.get_json()
        assert r.status_code == 200
        assert data["status"] == "ok"
        assert data["service"] == "gallery_api"

    def test_comfyui_available_when_request_200(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.object(_sut, "requests") as mr:
            mr.get.return_value = mock_resp
            r = client.get("/health")
        assert r.get_json()["comfyui_available"] is True

    def test_comfyui_unavailable_when_request_raises(self, client):
        with patch.object(_sut, "requests") as mr:
            mr.get.side_effect = Exception("unreachable")
            r = client.get("/health")
        assert r.get_json()["comfyui_available"] is False

    def test_health_includes_jobs_count(self, client):
        _sut.jobs["x"] = {"status": "processing"}
        with patch.object(_sut, "requests") as mr:
            mr.get.side_effect = Exception("down")
            r = client.get("/health")
        assert r.get_json()["jobs_count"] == 1


# ══════════════════════════════════════════════════════════════════════════
# TestApiGenerateEndpoint
# ══════════════════════════════════════════════════════════════════════════

class TestApiGenerateEndpoint:
    def test_returns_400_when_no_prompt(self, client):
        r = client.post("/api/generate", json={})
        assert r.status_code == 400
        assert "プロンプトが指定されていません" in r.get_json()["error"]

    def test_returns_200_with_job_id(self, client):
        with patch.object(_sut, "submit_to_comfyui", return_value="pid-1"):
            with patch.object(_sut, "create_comfyui_workflow", return_value={}):
                r = client.post("/api/generate", json={"prompt": "girl"})
        data = r.get_json()
        assert r.status_code == 200
        assert data["success"] is True
        assert "job_id" in data
        assert data["prompt_id"] == "pid-1"

    def test_job_stored_in_jobs_dict_with_processing_status(self, client):
        with patch.object(_sut, "submit_to_comfyui", return_value="pid-2"):
            with patch.object(_sut, "create_comfyui_workflow", return_value={}):
                r = client.post("/api/generate", json={"prompt": "scenery"})
        job_id = r.get_json()["job_id"]
        assert job_id in _sut.jobs
        assert _sut.jobs[job_id]["status"] == "processing"

    def test_returns_500_when_submit_fails(self, client):
        with patch.object(_sut, "submit_to_comfyui", return_value=None):
            with patch.object(_sut, "create_comfyui_workflow", return_value={}):
                r = client.post("/api/generate", json={"prompt": "test"})
        assert r.status_code == 500
        assert r.get_json()["success"] is False

    def test_japanese_tags_added_when_no_japanese_keyword(self, client):
        captured = {}

        def fake_wf(prompt, **kw):
            captured["prompt"] = prompt
            return {}

        with patch.object(_sut, "submit_to_comfyui", return_value="pid-3"):
            with patch.object(_sut, "create_comfyui_workflow", side_effect=fake_wf):
                client.post("/api/generate", json={"prompt": "beautiful sunset"})
        assert "Japanese" in captured.get("prompt", "")

    def test_japanese_tags_not_added_again_when_keyword_present(self, client):
        captured = {}

        def fake_wf(prompt, **kw):
            captured["prompt"] = prompt
            return {}

        with patch.object(_sut, "submit_to_comfyui", return_value="pid-4"):
            with patch.object(_sut, "create_comfyui_workflow", side_effect=fake_wf):
                client.post("/api/generate", json={"prompt": "japanese woman in kimono"})
        # japanese keyword present → DEFAULT_JAPANESE_PROMPT prefix NOT prepended
        prefix_count = captured.get("prompt", "").lower().count("japanese,")
        assert prefix_count <= 1


# ══════════════════════════════════════════════════════════════════════════
# TestJobStatusEndpoint
# ══════════════════════════════════════════════════════════════════════════

class TestJobStatusEndpoint:
    def test_unknown_job_returns_404(self, client):
        r = client.get("/api/job/nonexistent-id")
        assert r.status_code == 404
        assert "ジョブが見つかりません" in r.get_json()["error"]

    def test_known_job_returns_200_with_data(self, client):
        _sut.jobs["job-abc"] = {"job_id": "job-abc", "status": "completed"}
        r = client.get("/api/job/job-abc")
        assert r.status_code == 200
        data = r.get_json()
        assert data["job_id"] == "job-abc"
        assert data["status"] == "completed"

    def test_processing_job_contents_returned(self, client):
        _sut.jobs["j1"] = {"job_id": "j1", "status": "processing", "filename": None}
        r = client.get("/api/job/j1")
        assert r.get_json()["status"] == "processing"


# ══════════════════════════════════════════════════════════════════════════
# TestReflectionEndpoints
# ══════════════════════════════════════════════════════════════════════════

class TestReflectionEndpoints:
    def test_statistics_returns_503_when_unavailable(self, client):
        with patch.object(_sut, "AUTO_REFLECTION_AVAILABLE", new=False):
            r = client.get("/api/reflection/statistics")
        assert r.status_code == 503

    def test_evaluate_returns_503_when_unavailable(self, client):
        with patch.object(_sut, "AUTO_REFLECTION_AVAILABLE", new=False):
            r = client.post("/api/reflection/evaluate", json={"image_path": "x.png"})
        assert r.status_code == 503

    def test_evaluate_returns_400_when_no_image_path(self, client):
        fake_sys = MagicMock()
        with patch.object(_sut, "AUTO_REFLECTION_AVAILABLE", new=True):
            with patch.object(_sut, "get_auto_reflection_system", return_value=fake_sys):
                r = client.post("/api/reflection/evaluate", json={})
        assert r.status_code == 400
        assert "image_path" in r.get_json()["error"]

    def test_evaluate_returns_200_on_success(self, client):
        fake_sys = MagicMock()
        fake_sys.process_generated_image.return_value = {"overall_score": 0.9}
        with patch.object(_sut, "AUTO_REFLECTION_AVAILABLE", new=True):
            with patch.object(_sut, "get_auto_reflection_system", return_value=fake_sys):
                r = client.post(
                    "/api/reflection/evaluate",
                    json={"image_path": "img.png", "prompt": "test"},
                )
        assert r.status_code == 200
        assert r.get_json()["success"] is True

    def test_statistics_returns_200_when_available(self, client):
        fake_sys = MagicMock()
        fake_sys.get_statistics.return_value = {"total": 5}
        with patch.object(_sut, "AUTO_REFLECTION_AVAILABLE", new=True):
            with patch.object(_sut, "get_auto_reflection_system", return_value=fake_sys):
                r = client.get("/api/reflection/statistics")
        assert r.status_code == 200
        assert r.get_json()["success"] is True


# ══════════════════════════════════════════════════════════════════════════
# TestApiImagesEndpoint
# ══════════════════════════════════════════════════════════════════════════

class TestApiImagesEndpoint:
    def test_returns_empty_list_when_no_png_files(self, client, tmp_path):
        with patch.object(_sut, "IMAGES_DIR", tmp_path):
            r = client.get("/api/images")
        data = r.get_json()
        assert r.status_code == 200
        assert data["images"] == []
        assert data["count"] == 0

    def test_returns_list_with_one_item_for_one_png(self, client, tmp_path):
        (tmp_path / "test.png").touch()
        with patch.object(_sut, "IMAGES_DIR", tmp_path):
            r = client.get("/api/images")
        data = r.get_json()
        assert isinstance(data["images"], list)
        assert len(data["images"]) == 1
        assert data["images"][0]["filename"] == "test.png"

    def test_includes_metadata_from_json_file(self, client, tmp_path):
        (tmp_path / "out.png").touch()
        meta = {"prompt": "test prompt", "model": "my_model.safetensors"}
        (tmp_path / "out.png.json").write_text(json.dumps(meta), encoding="utf-8")
        with patch.object(_sut, "IMAGES_DIR", tmp_path):
            r = client.get("/api/images")
        item = r.get_json()["images"][0]
        assert item["prompt"] == "test prompt"
        assert item["model"] == "my_model.safetensors"

    def test_non_png_files_excluded(self, client, tmp_path):
        (tmp_path / "image.jpg").touch()
        (tmp_path / "image.png").touch()
        with patch.object(_sut, "IMAGES_DIR", tmp_path):
            r = client.get("/api/images")
        filenames = [item["filename"] for item in r.get_json()["images"]]
        assert "image.png" in filenames
        assert "image.jpg" not in filenames


# ══════════════════════════════════════════════════════════════════════════
# TestIndexEndpoint
# ══════════════════════════════════════════════════════════════════════════

class TestIndexEndpoint:
    def test_index_returns_success_response(self, client, tmp_path):
        with patch.object(_sut, "IMAGES_DIR", tmp_path):
            r = client.get("/")
        assert r.status_code == 200
        assert r.get_json()["success"] is True

    def test_index_reflects_images_in_dir(self, client, tmp_path):
        (tmp_path / "a.png").touch()
        with patch.object(_sut, "IMAGES_DIR", tmp_path):
            r = client.get("/")
        assert r.get_json()["count"] == 1
