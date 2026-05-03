"""Unit tests for stage.queue.db — the SQLite render queue layer.

Pure-Python — does not require Blender. Each test gets its own
on-disk SQLite file via tmp_path so the schema migration path runs
fresh and tests don't pollute each other.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from stage.queue import db as queue_db


def _add(conn, *, name="StudioA", uuid="uuid-a", scene="Scene"):
    return queue_db.add_job(
        conn,
        blend_file_path="/tmp/fake.blend",
        scene_name=scene,
        studio_uuid=uuid,
        studio_name=name,
    )


# --- schema ----------------------------------------------------------------


def test_init_creates_meta_and_jobs(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    names = {r["name"] for r in rows}
    assert {"meta", "jobs"}.issubset(names)


def test_schema_version_recorded(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        v = conn.execute(
            "SELECT value FROM meta WHERE key='schema_version'"
        ).fetchone()
    assert v["value"] == str(queue_db.SCHEMA_VERSION)


def test_double_init_idempotent(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        _add(conn)
    # Second connect must not duplicate schema rows / wipe data
    with queue_db.connect(db) as conn:
        rows = queue_db.list_jobs(conn)
    assert len(rows) == 1


# --- add / get -------------------------------------------------------------


def test_add_job_returns_id_and_pending_status(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        job_id = _add(conn)
        row = queue_db.get_job(conn, job_id)
    assert row["id"] == job_id
    assert row["status"] == queue_db.STATUS_PENDING
    assert row["studio_name_at_queue"] == "StudioA"
    assert row["submitted_at"] > 0
    assert row["started_at"] is None
    assert row["completed_at"] is None


def test_get_job_returns_none_for_missing_id(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        assert queue_db.get_job(conn, 999) is None


# --- list / next pending ---------------------------------------------------


def test_list_jobs_orders_by_submitted_ascending(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        a = _add(conn, name="A", uuid="u-a")
        b = _add(conn, name="B", uuid="u-b")
        c = _add(conn, name="C", uuid="u-c")
        rows = queue_db.list_jobs(conn)
    assert [r["id"] for r in rows] == [a, b, c]


def test_list_jobs_status_filter(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        a = _add(conn, name="A", uuid="u-a")
        b = _add(conn, name="B", uuid="u-b")
        queue_db.mark_done(conn, a, output_path="/x/a.png")
        only_pending = queue_db.list_jobs(
            conn, statuses=(queue_db.STATUS_PENDING,)
        )
    assert [r["id"] for r in only_pending] == [b]


def test_next_pending_picks_oldest(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        first = _add(conn, name="A", uuid="u-a")
        _add(conn, name="B", uuid="u-b")
        n = queue_db.next_pending_job(conn)
    assert n["id"] == first


def test_next_pending_returns_none_when_empty(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        assert queue_db.next_pending_job(conn) is None


def test_next_pending_skips_completed(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        a = _add(conn, name="A", uuid="u-a")
        queue_db.mark_done(conn, a, output_path=None)
        assert queue_db.next_pending_job(conn) is None


# --- status transitions ----------------------------------------------------


def test_mark_running_sets_pid_and_started_at(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        j = _add(conn)
        queue_db.mark_running(conn, j, pid=12345)
        row = queue_db.get_job(conn, j)
    assert row["status"] == queue_db.STATUS_RUNNING
    assert row["pid"] == 12345
    assert row["started_at"] > 0


def test_mark_done_records_output_path(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        j = _add(conn)
        queue_db.mark_done(conn, j, output_path="/tmp/r.png")
        row = queue_db.get_job(conn, j)
    assert row["status"] == queue_db.STATUS_DONE
    assert row["output_path"] == "/tmp/r.png"
    assert row["completed_at"] > 0


def test_mark_failed_records_error(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        j = _add(conn)
        queue_db.mark_failed(conn, j, error_message="boom")
        row = queue_db.get_job(conn, j)
    assert row["status"] == queue_db.STATUS_FAILED
    assert row["error_message"] == "boom"


def test_mark_cancelled(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        j = _add(conn)
        queue_db.mark_cancelled(conn, j)
        assert queue_db.get_job(conn, j)["status"] == queue_db.STATUS_CANCELLED


def test_has_running_job(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        assert queue_db.has_running_job(conn) is False
        j = _add(conn)
        queue_db.mark_running(conn, j, pid=1)
        assert queue_db.has_running_job(conn) is True


# --- delete / clear --------------------------------------------------------


def test_delete_job(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        j = _add(conn)
        queue_db.delete_job(conn, j)
        assert queue_db.get_job(conn, j) is None


def test_clear_completed_drops_terminal_only(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        a = _add(conn, name="A", uuid="u-a")
        b = _add(conn, name="B", uuid="u-b")
        c = _add(conn, name="C", uuid="u-c")
        d = _add(conn, name="D", uuid="u-d")
        queue_db.mark_done(conn, a, output_path=None)
        queue_db.mark_failed(conn, b, error_message="oops")
        queue_db.mark_cancelled(conn, c)
        # d stays PENDING

        deleted = queue_db.clear_completed(conn)
        rows = queue_db.list_jobs(conn)

    assert deleted == 3
    assert [r["id"] for r in rows] == [d]


# --- orphan recovery -------------------------------------------------------


def test_reset_orphaned_running_marks_failed(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        a = _add(conn, name="A", uuid="u-a")
        b = _add(conn, name="B", uuid="u-b")
        queue_db.mark_running(conn, a, pid=999)
        queue_db.mark_running(conn, b, pid=998)

        n = queue_db.reset_orphaned_running(conn)
        rows = {r["id"]: r for r in queue_db.list_jobs(conn)}

    assert n == 2
    assert rows[a]["status"] == queue_db.STATUS_FAILED
    assert rows[b]["status"] == queue_db.STATUS_FAILED
    assert "Worker process did not finish" in rows[a]["error_message"]


def test_reset_orphaned_running_leaves_other_statuses_alone(tmp_path: Path):
    db = tmp_path / "q.db"
    with queue_db.connect(db) as conn:
        a = _add(conn, name="A", uuid="u-a")
        b = _add(conn, name="B", uuid="u-b")
        queue_db.mark_done(conn, a, output_path="/x.png")
        # b stays PENDING

        n = queue_db.reset_orphaned_running(conn)

    assert n == 0
    with queue_db.connect(db) as conn:
        rows = {r["id"]: r for r in queue_db.list_jobs(conn)}
    assert rows[a]["status"] == queue_db.STATUS_DONE
    assert rows[b]["status"] == queue_db.STATUS_PENDING
