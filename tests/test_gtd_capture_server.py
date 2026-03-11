"""
GTD Capture Server のユニットテスト

テスト対象エンドポイント:
  GET  /health
  GET  /api/gtd/status
  POST /api/gtd/capture
  GET  /api/gtd/morning
  GET  /api/gtd/inbox/list
  POST /api/gtd/process
  DELETE /api/gtd/inbox/{filename}
"""

import importlib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixture: GTD ディレクトリをすべて tmp_path に向けて副作用を排除
# ---------------------------------------------------------------------------

@pytest.fixture()
def gtd_client(tmp_path, monkeypatch):
    """tmp_path 内に GTD ディレクトリを作り、モジュールを再ロードして TestClient を返す"""
    inbox_dir = tmp_path / "gtd" / "inbox"
    na_dir = tmp_path / "gtd" / "next-actions" / "items"
    logs_dir = tmp_path / "gtd" / "daily-logs"
    inbox_dir.mkdir(parents=True)
    na_dir.mkdir(parents=True)
    logs_dir.mkdir(parents=True)

    import gtd_capture_server as gtd_mod

    # モジュールレベル変数をモンキーパッチ
    monkeypatch.setattr(gtd_mod, "GTD_INBOX", inbox_dir)
    monkeypatch.setattr(gtd_mod, "GTD_NA", na_dir)
    monkeypatch.setattr(gtd_mod, "GTD_LOGS", logs_dir)

    client = TestClient(gtd_mod.app)
    return client, inbox_dir, na_dir, logs_dir


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _make_inbox_file(inbox_dir: Path, name: str = "20990101_0000_test.md") -> Path:
    p = inbox_dir / name
    p.write_text("# Test\n\n内容\n", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health(gtd_client):
    client, *_ = gtd_client
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["service"] == "gtd-capture"


# ---------------------------------------------------------------------------
# /api/gtd/status
# ---------------------------------------------------------------------------

def test_status_empty(gtd_client):
    client, *_ = gtd_client
    res = client.get("/api/gtd/status")
    assert res.status_code == 200
    body = res.json()
    assert body["inbox_count"] == 0
    assert body["next_actions_count"] == 0


def test_status_counts_items(gtd_client):
    client, inbox_dir, na_dir, _ = gtd_client
    _make_inbox_file(inbox_dir)
    _make_inbox_file(inbox_dir, "20990101_0001_another.md")
    res = client.get("/api/gtd/status")
    assert res.json()["inbox_count"] == 2


# ---------------------------------------------------------------------------
# /api/gtd/capture
# ---------------------------------------------------------------------------

def test_capture_creates_file(gtd_client):
    client, inbox_dir, *_ = gtd_client
    before = list(inbox_dir.glob("*.md"))
    res = client.post(
        "/api/gtd/capture",
        json={"text": "テストタスク", "type": "タスク", "source": "test"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "file" in body
    after = list(inbox_dir.glob("*.md"))
    assert len(after) == len(before) + 1


def test_capture_file_content(gtd_client):
    client, inbox_dir, *_ = gtd_client
    res = client.post(
        "/api/gtd/capture",
        json={"text": "サンプルメモ", "source": "unit_test", "note": "補足"},
    )
    fname = res.json()["file"]
    content = (inbox_dir / fname).read_text(encoding="utf-8")
    assert "サンプルメモ" in content
    assert "unit_test" in content
    assert "補足" in content


def test_capture_increments_inbox_count(gtd_client):
    client, *_ = gtd_client
    for i in range(3):
        client.post("/api/gtd/capture", json={"text": f"item {i}"})
    res = client.post("/api/gtd/capture", json={"text": "last item"})
    assert res.json()["inbox_count"] == 4


# ---------------------------------------------------------------------------
# /api/gtd/morning
# ---------------------------------------------------------------------------

def test_morning_returns_date(gtd_client):
    client, *_ = gtd_client
    res = client.get("/api/gtd/morning")
    assert res.status_code == 200
    body = res.json()
    assert "date" in body
    assert "inbox_count" in body
    assert "next_actions_count" in body
    assert "summary" in body


def test_morning_no_log(gtd_client):
    client, *_ = gtd_client
    res = client.get("/api/gtd/morning")
    body = res.json()
    # ログが存在しない場合でも 200 を返す
    assert res.status_code == 200
    assert body["full_log_exists"] is False


# ---------------------------------------------------------------------------
# /api/gtd/inbox/list
# ---------------------------------------------------------------------------

def test_inbox_list_empty(gtd_client):
    client, *_ = gtd_client
    res = client.get("/api/gtd/inbox/list")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 0
    assert body["items"] == []


def test_inbox_list_with_items(gtd_client):
    client, inbox_dir, *_ = gtd_client
    _make_inbox_file(inbox_dir, "20990101_0000_a.md")
    _make_inbox_file(inbox_dir, "20990101_0001_b.md")
    res = client.get("/api/gtd/inbox/list")
    body = res.json()
    assert body["count"] == 2
    assert "20990101_0000_a.md" in body["items"]


# ---------------------------------------------------------------------------
# /api/gtd/process
# ---------------------------------------------------------------------------

def test_process_moves_to_next_actions(gtd_client):
    client, inbox_dir, na_dir, _ = gtd_client
    fname = "20990101_0000_proc.md"
    _make_inbox_file(inbox_dir, fname)

    res = client.post(
        "/api/gtd/process",
        json={"filename": fname, "next_action": "やること", "project": "プロジェクトX"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["processed"] == fname

    # Inbox から削除されている
    assert not (inbox_dir / fname).exists()
    # Next-Actions に新規ファイルが出来ている
    na_files = list(na_dir.glob("*.md"))
    assert len(na_files) == 1
    content = na_files[0].read_text(encoding="utf-8")
    assert "やること" in content
    assert "プロジェクトX" in content


def test_process_not_found(gtd_client):
    client, *_ = gtd_client
    res = client.post(
        "/api/gtd/process", json={"filename": "nonexistent.md"}
    )
    assert res.status_code == 404


def test_process_path_traversal(gtd_client):
    """パストラバーサルを拒否する"""
    client, *_ = gtd_client
    res = client.post(
        "/api/gtd/process", json={"filename": "../../etc/passwd"}
    )
    # 404 (ファイルなし) か 400 (invalid) のどちらかで弾く
    assert res.status_code in (400, 404)


# ---------------------------------------------------------------------------
# DELETE /api/gtd/inbox/{filename}
# ---------------------------------------------------------------------------

def test_delete_removes_file(gtd_client):
    client, inbox_dir, *_ = gtd_client
    fname = "20990101_0000_del.md"
    _make_inbox_file(inbox_dir, fname)

    res = client.delete(f"/api/gtd/inbox/{fname}")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["deleted"] == fname
    assert not (inbox_dir / fname).exists()


def test_delete_not_found(gtd_client):
    client, *_ = gtd_client
    res = client.delete("/api/gtd/inbox/nonexistent.md")
    assert res.status_code == 404


def test_delete_rejects_non_md(gtd_client):
    """拡張子 .md 以外は弾く"""
    client, inbox_dir, *_ = gtd_client
    # .sh ファイルが実際に存在しても拒否されること
    (inbox_dir / "bad.sh").write_text("rm -rf /", encoding="utf-8")
    res = client.delete("/api/gtd/inbox/bad.sh")
    assert res.status_code == 400


def test_delete_path_traversal(gtd_client):
    """パストラバーサルがある場合も安全に弾く"""
    client, *_ = gtd_client
    res = client.delete("/api/gtd/inbox/../../../etc/passwd.md")
    # 400 (invalid) か 404 のどちらかで弾く
    assert res.status_code in (400, 404)


def test_delete_decrements_count(gtd_client):
    client, inbox_dir, *_ = gtd_client
    f1 = _make_inbox_file(inbox_dir, "20990101_0000_x.md")
    f2 = _make_inbox_file(inbox_dir, "20990101_0001_y.md")

    res = client.delete(f"/api/gtd/inbox/{f1.name}")
    assert res.json()["inbox_count"] == 1
