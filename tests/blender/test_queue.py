"""Tests for queue ops + UI registration — runs inside Blender.

We use a dedicated test DB path under tmp so we don't pollute the user's
real ~/Library/Application Support/Stage/queue.db.

The "is the .blend saved" check goes through stage.ops.queue._current_blend_filepath
which we monkeypatch per-test — bpy.data.filepath itself is read-only, and
read_homefile/save_as_mainfile have nasty session-wide side effects.

Subprocess execution is NOT exercised here — the worker spawns real
Blender instances, which is impractical in CI. The render_script.py is
tested by argument-parsing assertions only. Full e2e is a manual smoke
in the foreground addon.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import bpy

from stage.ops import queue as queue_ops
from stage.queue import db as queue_db
from stage.queue import paths as queue_paths


# --- helpers ---------------------------------------------------------------


_TEST_DB_DIR: Path | None = None
_REAL_QUEUE_DB_PATH = queue_paths.queue_db_path
_REAL_BLEND_FILEPATH_FN = queue_ops._current_blend_filepath


def _redirect_db_to_temp() -> Path:
    global _TEST_DB_DIR
    if _TEST_DB_DIR is None or not _TEST_DB_DIR.exists():
        _TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="stage_queue_test_"))
    db_path = _TEST_DB_DIR / "queue.db"
    queue_paths.queue_db_path = lambda: db_path  # type: ignore[assignment]
    return db_path


def _reset_test_db() -> Path:
    db_path = _redirect_db_to_temp()
    if db_path.exists():
        db_path.unlink()
    return db_path


def _restore_real_db_path() -> None:
    queue_paths.queue_db_path = _REAL_QUEUE_DB_PATH  # type: ignore[assignment]


def _stub_blend_path(value: str) -> None:
    queue_ops._current_blend_filepath = lambda: value  # type: ignore[assignment]


def _restore_blend_path() -> None:
    queue_ops._current_blend_filepath = _REAL_BLEND_FILEPATH_FN  # type: ignore[assignment]


def _fresh_scene(name: str = "stage_queue_test"):
    if name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[name], do_unlink=True)
    return bpy.data.scenes.new(name)


def _make_studio(scene, name: str, uuid: str):
    s = scene.stage_data.studios.add()
    s.name = name
    s.uuid = uuid
    return s


# --- registration sanity ---------------------------------------------------


def test_queue_panel_registered():
    from stage.ui.queue_panel import STAGE_PT_queue
    assert STAGE_PT_queue.bl_idname == "STAGE_PT_queue"
    assert STAGE_PT_queue.bl_category == "Stage"
    assert 'DEFAULT_CLOSED' in STAGE_PT_queue.bl_options


def test_queue_operators_registered():
    for op_id in (
        "stage.queue_active",
        "stage.queue_selected",
        "stage.queue_all_enabled",
        "stage.queue_remove",
        "stage.queue_cancel_active",
        "stage.queue_clear_completed",
        "stage.queue_kick",
    ):
        bl_idname = op_id.replace("stage.", "STAGE_OT_")
        assert hasattr(bpy.types, bl_idname), f"Missing {op_id}"


# --- queue_active operator -------------------------------------------------


def test_queue_active_requires_saved_blend():
    """When _current_blend_filepath() returns empty, the op must refuse."""
    _reset_test_db()
    _stub_blend_path("")
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    _make_studio(scene, "Hero", "uuid-hero")
    scene.stage_data.active_index = 0

    raised = False
    try:
        with bpy.context.temp_override(scene=scene):
            bpy.ops.stage.queue_active()
    except RuntimeError:
        raised = True

    try:
        assert raised, "expected ERROR + RuntimeError on unsaved blend"
        with queue_db.connect() as conn:
            assert len(queue_db.list_jobs(conn)) == 0
    finally:
        _restore_blend_path()
        _restore_real_db_path()


def test_queue_active_adds_pending_job_when_saved():
    _reset_test_db()
    _stub_blend_path("/tmp/fake.blend")
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    _make_studio(scene, "Hero", "uuid-hero")
    scene.stage_data.active_index = 0

    try:
        with bpy.context.temp_override(scene=scene):
            bpy.ops.stage.queue_active()

        with queue_db.connect() as conn:
            rows = queue_db.list_jobs(conn)
        assert len(rows) == 1
        row = rows[0]
        assert row["status"] == queue_db.STATUS_PENDING
        assert row["studio_uuid"] == "uuid-hero"
        assert row["studio_name_at_queue"] == "Hero"
        assert row["scene_name"] == scene.name
        assert row["blend_file_path"] == "/tmp/fake.blend"
    finally:
        _restore_blend_path()
        _restore_real_db_path()


# --- queue_selected operator ----------------------------------------------


def test_queue_selected_no_selection_warns():
    _reset_test_db()
    _stub_blend_path("/tmp/fake.blend")
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    _make_studio(scene, "Hero", "uuid-hero")  # not selected

    try:
        with bpy.context.temp_override(scene=scene):
            try:
                bpy.ops.stage.queue_selected()
            except RuntimeError:
                pass  # WARNING report → RuntimeError

        with queue_db.connect() as conn:
            assert len(queue_db.list_jobs(conn)) == 0
    finally:
        _restore_blend_path()
        _restore_real_db_path()


def test_queue_selected_only_picks_ticked_studios():
    _reset_test_db()
    _stub_blend_path("/tmp/fake.blend")
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _make_studio(scene, "A", "u-a")
    b = _make_studio(scene, "B", "u-b")
    c = _make_studio(scene, "C", "u-c")
    a.selected = True
    c.selected = True

    try:
        with bpy.context.temp_override(scene=scene):
            bpy.ops.stage.queue_selected()

        with queue_db.connect() as conn:
            rows = queue_db.list_jobs(conn)
        names = sorted(r["studio_name_at_queue"] for r in rows)
        assert names == ["A", "C"]
    finally:
        _restore_blend_path()
        _restore_real_db_path()


# --- queue_all_enabled ----------------------------------------------------


def test_queue_all_enabled_skips_disabled():
    _reset_test_db()
    _stub_blend_path("/tmp/fake.blend")
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _make_studio(scene, "A", "u-a")
    b = _make_studio(scene, "B", "u-b")
    c = _make_studio(scene, "C", "u-c")
    b.enabled = False

    try:
        with bpy.context.temp_override(scene=scene):
            bpy.ops.stage.queue_all_enabled()

        with queue_db.connect() as conn:
            rows = queue_db.list_jobs(conn)
        names = sorted(r["studio_name_at_queue"] for r in rows)
        assert names == ["A", "C"]
    finally:
        _restore_blend_path()
        _restore_real_db_path()


# --- queue_remove / clear_completed --------------------------------------


def test_queue_remove_drops_pending_job():
    _reset_test_db()
    try:
        with queue_db.connect() as conn:
            job_id = queue_db.add_job(
                conn,
                blend_file_path="/tmp/x.blend",
                scene_name="Scene",
                studio_uuid="u",
                studio_name="n",
            )
        with bpy.context.temp_override(scene=bpy.context.scene):
            bpy.ops.stage.queue_remove(job_id=job_id)
        with queue_db.connect() as conn:
            assert queue_db.get_job(conn, job_id) is None
    finally:
        _restore_real_db_path()


def test_queue_remove_refuses_running_job():
    _reset_test_db()
    try:
        with queue_db.connect() as conn:
            job_id = queue_db.add_job(
                conn,
                blend_file_path="/tmp/x.blend",
                scene_name="Scene",
                studio_uuid="u",
                studio_name="n",
            )
            queue_db.mark_running(conn, job_id, pid=12345)

        try:
            with bpy.context.temp_override(scene=bpy.context.scene):
                bpy.ops.stage.queue_remove(job_id=job_id)
        except RuntimeError:
            pass

        with queue_db.connect() as conn:
            assert queue_db.get_job(conn, job_id) is not None
    finally:
        _restore_real_db_path()


def test_queue_clear_completed():
    _reset_test_db()
    try:
        with queue_db.connect() as conn:
            a = queue_db.add_job(conn, blend_file_path="/x", scene_name="s", studio_uuid="ua", studio_name="A")
            b = queue_db.add_job(conn, blend_file_path="/x", scene_name="s", studio_uuid="ub", studio_name="B")
            queue_db.mark_done(conn, a, output_path=None)

        with bpy.context.temp_override(scene=bpy.context.scene):
            bpy.ops.stage.queue_clear_completed()

        with queue_db.connect() as conn:
            rows = queue_db.list_jobs(conn)
        assert [r["id"] for r in rows] == [b]
    finally:
        _restore_real_db_path()


# --- render_script arg parsing --------------------------------------------


def test_render_script_parses_job_id_and_db_path():
    from stage.queue.render_script import _parse_args
    job_id, db_path = _parse_args(
        ["blender", "-b", "x.blend", "-P", "render_script.py", "--",
         "--job-id=42", "--db-path=/tmp/queue.db"]
    )
    assert job_id == 42
    assert db_path == "/tmp/queue.db"


def test_render_script_requires_job_id():
    from stage.queue.render_script import _parse_args
    raised = False
    try:
        _parse_args(["foo", "--", "--db-path=/x"])
    except SystemExit:
        raised = True
    assert raised, "missing --job-id must SystemExit"
