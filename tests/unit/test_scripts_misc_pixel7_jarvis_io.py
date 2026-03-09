"""
tests/unit/test_scripts_misc_pixel7_jarvis_io.py
pixel7_jarvis_io.py のユニットテスト
 - ADB処理はすべて subprocess.run をモックして実機不要
"""
from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import types

import pytest

# ---------------------------------------------------------------------------
# sys.path / 外部依存モックを setup_module で整える
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
MISC_DIR = REPO_ROOT / "scripts" / "misc"

# manaos_logger スタブ（実機なし環境用）
if "manaos_logger" not in sys.modules:
    stub_logger = types.ModuleType("manaos_logger")
    import logging
    stub_logger.get_service_logger = lambda name: logging.getLogger(name)  # type: ignore[attr-defined]
    sys.modules["manaos_logger"] = stub_logger

# _paths スタブ
if "_paths" not in sys.modules:
    stub_paths = types.ModuleType("_paths")
    stub_paths.UNIFIED_API_PORT = 9510  # type: ignore[attr-defined]
    stub_paths.LLM_ROUTING_PORT = 5117  # type: ignore[attr-defined]
    sys.modules["_paths"] = stub_paths

if str(MISC_DIR) not in sys.path:
    sys.path.insert(0, str(MISC_DIR))

import importlib
import pixel7_jarvis_io as m  # noqa: E402


# ---------------------------------------------------------------------------
# ヘルパー: subprocess.CompletedProcess を簡単に作れる factory
# ---------------------------------------------------------------------------

def _ok(stdout: str = "", stderr: str = "") -> object:
    import subprocess
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr=stderr)


def _ng(stderr: str = "error") -> object:
    import subprocess
    return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=stderr)


# ---------------------------------------------------------------------------
# _get_device_serial
# ---------------------------------------------------------------------------

class TestGetDeviceSerial:
    def test_from_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(m, "_load_adb_config", lambda: {"device_ip": "10.0.0.1", "device_port": "5555"})
        assert m._get_device_serial() == "10.0.0.1:5555"

    def test_no_ip_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(m, "_load_adb_config", lambda: {})
        monkeypatch.delenv("ANDROID_SERIAL", raising=False)
        assert m._get_device_serial() == ""


# ---------------------------------------------------------------------------
# check_connection
# ---------------------------------------------------------------------------

class TestCheckConnection:
    def test_ok_when_device(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(m, "_run_adb", lambda *a, **kw: _ok(stdout="device"))
        assert m.check_connection() is True

    def test_ok_via_ssh_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ADB 失敗でも SSH で繋がれば True"""
        monkeypatch.setattr(m, "_run_adb", lambda *a, **kw: _ng())
        monkeypatch.setattr(m, "_check_ssh_connection", lambda: True)
        assert m.check_connection() is True

    def test_ng_when_offline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(m, "_run_adb", lambda *a, **kw: _ng())
        monkeypatch.setattr(m, "_check_ssh_connection", lambda: False)
        assert m.check_connection() is False

    def test_ng_on_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def raise_exc(*a, **kw):
            raise RuntimeError("adb not found")
        monkeypatch.setattr(m, "_run_adb", raise_exc)
        monkeypatch.setattr(m, "_check_ssh_connection", lambda: False)
        assert m.check_connection() is False


# ---------------------------------------------------------------------------
# record_audio_on_pixel7
# ---------------------------------------------------------------------------

class TestRecordAudio:
    def test_returns_none_when_disconnected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(m, "check_connection", lambda: False)
        assert m.record_audio_on_pixel7() is None

    def test_termux_rec_path(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """SSH 経由 rec コマンドで録音成功するパス"""
        monkeypatch.setattr(m, "check_connection", lambda: True)

        out_wav = tmp_path / "mic.wav"

        def fake_ssh(cmd: str, **kw):
            # SSH 経由 rec 成功
            return _ok(stdout="")

        def fake_adb(args: list, **kw):
            # pull → ファイルを手動で作成してから返す
            if "pull" in args:
                out_wav.write_bytes(b"\x00" * 5000)
                return _ok()
            return _ok()

        monkeypatch.setattr(m, "_run_ssh", fake_ssh)
        monkeypatch.setattr(m, "_run_adb", fake_adb)
        result = m.record_audio_on_pixel7(duration_sec=2, local_out=out_wav)
        assert result == out_wav
        assert result.exists()

    def test_pull_failure_returns_none(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(m, "check_connection", lambda: True)
        out_wav = tmp_path / "mic.wav"

        def fake_ssh(cmd: str, **kw):
            # SSH rec 失敗
            return _ng("audio device not found")

        def fake_adb(args: list, **kw):
            # termux-microphone-record → 失敗
            if "termux-microphone-record" in " ".join(str(a) for a in args):
                return _ng("not found")
            return _ok()

        monkeypatch.setattr(m, "_run_ssh", fake_ssh)
        monkeypatch.setattr(m, "_run_adb", fake_adb)
        assert m.record_audio_on_pixel7(local_out=out_wav) is None


# ---------------------------------------------------------------------------
# play_audio_on_pixel7
# ---------------------------------------------------------------------------

class TestPlayAudio:
    def test_returns_false_when_disconnected(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(m, "check_connection", lambda: False)
        wav = tmp_path / "tts.wav"
        wav.write_bytes(b"\x00")
        assert m.play_audio_on_pixel7(wav) is False

    def test_returns_false_missing_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(m, "check_connection", lambda: True)
        assert m.play_audio_on_pixel7(tmp_path / "ghost.wav") is False

    def test_success_via_termux(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(m, "check_connection", lambda: True)
        monkeypatch.setattr(m.time, "sleep", lambda _: None)  # type: ignore[attr-defined]

        wav = tmp_path / "tts.wav"
        wav.write_bytes(b"\x00" * 32000)  # 1秒分

        monkeypatch.setattr(m, "_run_ssh", lambda *a, **kw: _ok())
        monkeypatch.setattr(m, "_run_adb", lambda *a, **kw: _ok())
        assert m.play_audio_on_pixel7(wav) is True

    def test_fallback_intent_when_termux_fails(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(m, "check_connection", lambda: True)
        monkeypatch.setattr(m.time, "sleep", lambda _: None)

        wav = tmp_path / "tts.wav"
        wav.write_bytes(b"\x00" * 100)

        calls: list[list[str]] = []

        def fake_adb(args: list, **kw):
            calls.append(args)
            if "termux-media-player" in " ".join(args):
                return _ng("not found")
            return _ok()

        # SSH play 失敗
        monkeypatch.setattr(m, "_run_ssh", lambda *a, **kw: _ng("ssh error"))
        monkeypatch.setattr(m, "_run_adb", fake_adb)
        result = m.play_audio_on_pixel7(wav)
        assert result is True
        # Intent フォールバックが呼ばれた
        assert any("am" in str(c) for c in calls)


# ---------------------------------------------------------------------------
# capture_photo_from_pixel7
# ---------------------------------------------------------------------------

class TestCapturePhoto:
    def test_returns_none_when_disconnected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(m, "check_connection", lambda: False)
        assert m.capture_photo_from_pixel7() is None

    def test_termux_camera_photo(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(m, "check_connection", lambda: True)

        out_jpg = tmp_path / "photo.jpg"

        def fake_adb(args: list, **kw):
            if "pull" in args:
                out_jpg.write_bytes(b"\xff\xd8\xff" + b"\x00" * 50)
                return _ok()
            return _ok()

        monkeypatch.setattr(m, "_run_adb", fake_adb)
        result = m.capture_photo_from_pixel7(local_out=out_jpg)
        assert result == out_jpg
        assert result.exists()

    def test_fallback_intent_when_termux_fails(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(m, "check_connection", lambda: True)

        out_jpg = tmp_path / "photo.jpg"
        call_count = {"n": 0}

        def fake_adb(args: list, **kw):
            call_count["n"] += 1
            # termux-camera-photo → 失敗
            if "termux-camera-photo" in " ".join(args):
                return _ng("no termux")
            # find 最新写真
            if "find" in " ".join(args):
                return _ok(stdout="/sdcard/DCIM/camera.jpg\n")
            # pull
            if "pull" in args:
                out_jpg.write_bytes(b"\xff\xd8" + b"\x00")
                return _ok()
            return _ok()

        monkeypatch.setattr(m, "_run_adb", fake_adb)
        monkeypatch.setattr(m.time, "sleep", lambda _: None)
        result = m.capture_photo_from_pixel7(local_out=out_jpg)
        assert result is not None


# ---------------------------------------------------------------------------
# Pixel7JarvisIO クラス
# ---------------------------------------------------------------------------

class TestPixel7JarvisIO:
    def test_is_connected_delegates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(m, "check_connection", lambda: True)
        io = m.Pixel7JarvisIO()
        assert io.is_connected() is True

    def test_listen_returns_wav(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        wav = tmp_path / "listen.wav"
        wav.write_bytes(b"\x00")
        monkeypatch.setattr(m, "record_audio_on_pixel7", lambda **kw: wav)
        io = m.Pixel7JarvisIO(record_duration=3)
        assert io.listen() == wav

    def test_speak_delegates(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(m, "play_audio_on_pixel7", lambda p: True)
        io = m.Pixel7JarvisIO()
        wav = tmp_path / "tts.wav"
        wav.write_bytes(b"\x00")
        assert io.speak(wav) is True

    def test_shoot_returns_description(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        photo = tmp_path / "shot.jpg"
        photo.write_bytes(b"\xff\xd8")
        monkeypatch.setattr(m, "capture_photo_from_pixel7", lambda **kw: photo)
        monkeypatch.setattr(m, "describe_image", lambda p, prompt: "テスト画像の説明")
        io = m.Pixel7JarvisIO()
        assert io.shoot() == "テスト画像の説明"

    def test_shoot_failed_capture(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(m, "capture_photo_from_pixel7", lambda **kw: None)
        io = m.Pixel7JarvisIO()
        assert "失敗" in io.shoot()

    # run_voice_turn
    def test_run_voice_turn_disconnected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(m, "check_connection", lambda: False)
        io = m.Pixel7JarvisIO()
        result = io.run_voice_turn(lambda p: "hello", lambda t: "ok", lambda t: None)
        assert result["success"] is False

    def test_run_voice_turn_listen_fail(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(m, "check_connection", lambda: True)
        monkeypatch.setattr(m, "record_audio_on_pixel7", lambda **kw: None)
        io = m.Pixel7JarvisIO()
        result = io.run_voice_turn(lambda p: "hello", lambda t: "ok", lambda t: None)
        assert result["success"] is False

    def test_run_voice_turn_empty_stt(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        wav = tmp_path / "empty.wav"
        wav.write_bytes(b"\x00")
        monkeypatch.setattr(m, "check_connection", lambda: True)
        monkeypatch.setattr(m, "record_audio_on_pixel7", lambda **kw: wav)
        io = m.Pixel7JarvisIO()
        result = io.run_voice_turn(lambda p: "   ", lambda t: "ok", lambda t: None)
        assert result["success"] is False
        assert "無音" in result["assistant"]

    def test_run_voice_turn_success(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        wav_in = tmp_path / "in.wav"
        wav_in.write_bytes(b"\x00")
        wav_out = tmp_path / "out.wav"
        wav_out.write_bytes(b"\x00")

        monkeypatch.setattr(m, "check_connection", lambda: True)
        monkeypatch.setattr(m, "record_audio_on_pixel7", lambda **kw: wav_in)
        monkeypatch.setattr(m, "play_audio_on_pixel7", lambda p: True)

        io = m.Pixel7JarvisIO()
        result = io.run_voice_turn(
            stt_fn=lambda p: "こんにちは",
            llm_fn=lambda t: "どうぞよろしく",
            tts_fn=lambda t: wav_out,
        )
        assert result["success"] is True
        assert result["user"] == "こんにちは"
        assert result["assistant"] == "どうぞよろしく"

    def test_run_voice_turn_llm_error(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        wav_in = tmp_path / "in.wav"
        wav_in.write_bytes(b"\x00")
        monkeypatch.setattr(m, "check_connection", lambda: True)
        monkeypatch.setattr(m, "record_audio_on_pixel7", lambda **kw: wav_in)

        def explode(t: str) -> str:
            raise RuntimeError("LLM dead")

        io = m.Pixel7JarvisIO()
        result = io.run_voice_turn(
            stt_fn=lambda p: "質問",
            llm_fn=explode,
            tts_fn=lambda t: None,
        )
        assert result["success"] is True  # LLMエラーでも success=True (assistant=エラーメッセージ)
        assert "できませんでした" in result["assistant"]


# ---------------------------------------------------------------------------
# ensure_sshd_running
# ---------------------------------------------------------------------------

class TestEnsureSshdRunning:
    def test_returns_false_when_disconnected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(m, "check_connection", lambda: False)
        assert m.ensure_sshd_running() is False

    def test_returns_true_when_ssh_ok(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(m, "check_connection", lambda: True)
        monkeypatch.setattr(m, "_run_ssh", lambda cmd, **kw: _ok(stdout="SSHD_OK"))
        assert m.ensure_sshd_running() is True

    def test_starts_sshd_when_ssh_fails_first(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SSH 初回失敗 → ADB 経由で起動 → 2回目成功"""
        monkeypatch.setattr(m, "check_connection", lambda: True)
        monkeypatch.setattr(m.time, "sleep", lambda _: None)

        call_count = {"n": 0}

        def fake_ssh(cmd: str, **kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return _ng("Connection refused")
            return _ok(stdout="SSHD_OK")

        monkeypatch.setattr(m, "_run_ssh", fake_ssh)
        monkeypatch.setattr(m, "_run_adb", lambda *a, **kw: _ok())
        result = m.ensure_sshd_running()
        assert result is True
        assert call_count["n"] == 2  # 2回 SSH 試行

    def test_returns_false_when_sshd_never_starts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ADB 経由で起動しても SSH に応答しない"""
        monkeypatch.setattr(m, "check_connection", lambda: True)
        monkeypatch.setattr(m.time, "sleep", lambda _: None)
        monkeypatch.setattr(m, "_run_ssh", lambda *a, **kw: _ng("refused"))
        monkeypatch.setattr(m, "_run_adb", lambda *a, **kw: _ok())
        assert m.ensure_sshd_running() is False


# ---------------------------------------------------------------------------
# Pixel7JarvisIO.__init__ auto_ensure_sshd
# ---------------------------------------------------------------------------

class TestPixel7JarvisIOAutoSshd:
    def test_auto_ensure_called_when_connected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        called = {"n": 0}
        monkeypatch.setattr(m, "check_connection", lambda: True)
        monkeypatch.setattr(m, "ensure_sshd_running", lambda: called.update({"n": called["n"] + 1}) or True)
        m.Pixel7JarvisIO(auto_ensure_sshd=True)
        assert called["n"] == 1

    def test_auto_ensure_skipped_when_disconnected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        called = {"n": 0}
        monkeypatch.setattr(m, "check_connection", lambda: False)
        monkeypatch.setattr(m, "ensure_sshd_running", lambda: called.update({"n": called["n"] + 1}) or True)
        m.Pixel7JarvisIO(auto_ensure_sshd=True)
        assert called["n"] == 0

    def test_auto_ensure_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        called = {"n": 0}
        monkeypatch.setattr(m, "check_connection", lambda: True)
        monkeypatch.setattr(m, "ensure_sshd_running", lambda: called.update({"n": called["n"] + 1}) or True)
        m.Pixel7JarvisIO(auto_ensure_sshd=False)
        assert called["n"] == 0
