"""Tests for scripts/misc/calculate_training_time.py"""
import sys
import types
import json
import os
from unittest.mock import MagicMock, patch, mock_open
import pytest
from datetime import datetime, timedelta
from pathlib import Path


_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _fake_trainer_state(steps=500, epoch=2.0):
    return json.dumps({"global_step": steps, "epoch": epoch})


class TestCalculateTrainingTime:
    def test_import_with_mocked_fs(self, monkeypatch, tmp_path):
        """ファイルシステムをモックしてインポートできる"""
        sys.modules.pop("calculate_training_time", None)
        monkeypatch.syspath_prepend(str(_MISC))

        checkpoint_dir = tmp_path / "castle_ex_v1_0"
        (checkpoint_dir / "checkpoint-500").mkdir(parents=True)
        trainer_path = checkpoint_dir / "checkpoint-500" / "trainer_state.json"
        trainer_path.write_text(_fake_trainer_state(500, 2.0))

        monkeypatch.setenv("CHECKPOINT_DIR_OVERRIDE", str(checkpoint_dir))

        with patch("os.listdir", return_value=["checkpoint-500"]), \
             patch("os.path.isdir", return_value=True), \
             patch("builtins.open", mock_open(read_data=_fake_trainer_state(500, 2.0))), \
             patch("builtins.print"):
            import calculate_training_time  # noqa

    def test_elapsed_hours_positive(self, monkeypatch):
        """経過時間が正の値"""
        sys.modules.pop("calculate_training_time", None)
        monkeypatch.syspath_prepend(str(_MISC))

        with patch("os.listdir", return_value=["checkpoint-500"]), \
             patch("os.path.isdir", return_value=True), \
             patch("builtins.open", mock_open(read_data=_fake_trainer_state(500, 2.0))), \
             patch("builtins.print"):
            import calculate_training_time as m
        # elapsed_hours is set at module level
        assert hasattr(m, "elapsed_hours")
        assert m.elapsed_hours >= 0

    def test_current_step_set(self, monkeypatch):
        """current_step が設定される"""
        sys.modules.pop("calculate_training_time", None)
        monkeypatch.syspath_prepend(str(_MISC))

        with patch("os.listdir", return_value=["checkpoint-500"]), \
             patch("os.path.isdir", return_value=True), \
             patch("builtins.open", mock_open(read_data=_fake_trainer_state(500, 2.0))), \
             patch("builtins.print"):
            import calculate_training_time as m
        assert m.current_step == 500

    def test_current_epoch_set(self, monkeypatch):
        """current_epoch が設定される"""
        sys.modules.pop("calculate_training_time", None)
        monkeypatch.syspath_prepend(str(_MISC))

        with patch("os.listdir", return_value=["checkpoint-500"]), \
             patch("os.path.isdir", return_value=True), \
             patch("builtins.open", mock_open(read_data=_fake_trainer_state(500, 2.0))), \
             patch("builtins.print"):
            import calculate_training_time as m
        assert m.current_epoch == 2.0

    def test_total_epochs_is_25(self, monkeypatch):
        """total_epochs が25"""
        sys.modules.pop("calculate_training_time", None)
        monkeypatch.syspath_prepend(str(_MISC))

        with patch("os.listdir", return_value=["checkpoint-500"]), \
             patch("os.path.isdir", return_value=True), \
             patch("builtins.open", mock_open(read_data=_fake_trainer_state(500, 2.0))), \
             patch("builtins.print"):
            import calculate_training_time as m
        assert m.total_epochs == 25
