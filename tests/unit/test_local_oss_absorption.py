import asyncio
from pathlib import Path

import pytest

from local_oss_absorption import LocalOSSAbsorption


class _FakeResult:
    def __init__(self):
        self.task_id = "task-1"
        self.status = "success"
        self.cost = 0.12
        self.execution_time = 1.7
        self.iterations = 2
        self.error = None
        self.result = {"summary": "ok"}


class _FakeOH:
    async def execute_task(self, task_description, mode=None, task_type=None, use_trinity=None):
        assert "本番移行手順を更新" in task_description
        assert "NOTE:" in task_description
        return _FakeResult()


@pytest.fixture
def orchestrator(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "local_oss_profile.json").write_text(
        """
        {
          "profile_name": "test_profile",
          "notes": {
            "directory": "notes",
            "glob": "**/*.md",
            "max_context_files": 3,
            "max_chars_per_file": 400
          },
          "oh_my_opencode": {
            "default_mode": "normal",
            "default_task_type": "general",
            "use_trinity": true
          }
        }
        """,
        encoding="utf-8",
    )
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    (notes_dir / "deploy.md").write_text("本番移行手順を更新。rollback も追記。", encoding="utf-8")
    return LocalOSSAbsorption(base_dir=str(tmp_path))


def test_status_reads_profile(orchestrator: LocalOSSAbsorption):
    status = orchestrator.get_status()
    assert status["available"] is True
    assert status["profile_name"] == "test_profile"
    assert status["notes_files"] >= 1


def test_execute_with_context_and_note(orchestrator: LocalOSSAbsorption):
    integrations = {"oh_my_opencode": _FakeOH()}
    out = asyncio.run(
        orchestrator.execute(
            task_description="本番移行手順を更新",
            integrations=integrations,
            context_query="rollback",
            write_note=True,
            note_title="deploy_update",
        )
    )

    assert out["status"] == "success"
    assert out["task_id"] == "task-1"
    assert out.get("note_path")


def test_execute_returns_unavailable_when_oh_missing(orchestrator: LocalOSSAbsorption):
    out = asyncio.run(
        orchestrator.execute(
            task_description="ローカル検証",
            integrations={},
            write_note=False,
        )
    )
    assert out["status"] == "unavailable"
