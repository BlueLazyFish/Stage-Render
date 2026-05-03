"""Tests for post-render actions — v1.0.

Real network / audio output is mocked / skipped; the file-system runners
work against tempdirs.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import bpy

from stage.core.post_render import (
    copy_file,
    delete_folder,
    move_file,
    play_sound,
    run_actions,
    slack_webhook,
)


def _fresh_scene(name: str = "stage_post_render_test"):
    if name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[name], do_unlink=True)
    return bpy.data.scenes.new(name)


def _new_studio(scene, name: str = "Hero"):
    s = scene.stage_data.studios.add()
    s.name = name
    s.uuid = f"pra-{name}"
    return s


def _make_render_output(tmp: Path, name: str = "render.png") -> Path:
    out = tmp / name
    out.write_bytes(b"PNG-stub")
    return out


# --- model registration ----------------------------------------------------


def test_studio_has_post_render_actions_collection():
    scene = _fresh_scene()
    s = _new_studio(scene)
    assert hasattr(s, "post_render_actions")
    assert len(s.post_render_actions) == 0


def test_post_render_action_default_type_is_copy_file():
    scene = _fresh_scene()
    s = _new_studio(scene)
    action = s.post_render_actions.add()
    assert action.action_type == 'COPY_FILE'


# --- copy_file -------------------------------------------------------------


def test_copy_file_creates_destination_with_template_expansion():
    scene = _fresh_scene()
    studio = _new_studio(scene, name="Hero")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = _make_render_output(tmp_path)
        action = studio.post_render_actions.add()
        action.action_type = 'COPY_FILE'
        action.target = str(tmp_path / "out" / "{studio}.png")

        copy_file(action, scene, studio, str(src))

        dst = tmp_path / "out" / "Hero.png"
        assert dst.exists(), "destination not created"
        assert src.exists(), "source should still be there after COPY"


def test_copy_file_missing_source_logs_and_skips():
    scene = _fresh_scene()
    studio = _new_studio(scene)
    with tempfile.TemporaryDirectory() as tmp:
        action = studio.post_render_actions.add()
        action.action_type = 'COPY_FILE'
        action.target = str(Path(tmp) / "dst.png")
        # Should not raise, just log warning
        copy_file(action, scene, studio, str(Path(tmp) / "missing.png"))


# --- move_file -------------------------------------------------------------


def test_move_file_relocates_source():
    scene = _fresh_scene()
    studio = _new_studio(scene)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = _make_render_output(tmp_path)
        action = studio.post_render_actions.add()
        action.action_type = 'MOVE_FILE'
        action.target = str(tmp_path / "moved" / "out.png")

        move_file(action, scene, studio, str(src))

        dst = tmp_path / "moved" / "out.png"
        assert dst.exists()
        assert not src.exists(), "source should be gone after MOVE"


# --- delete_folder ---------------------------------------------------------


def test_delete_folder_removes_directory():
    scene = _fresh_scene()
    studio = _new_studio(scene)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        target_dir = tmp_path / "trash"
        target_dir.mkdir()
        (target_dir / "file.txt").write_text("x")

        action = studio.post_render_actions.add()
        action.action_type = 'DELETE_FOLDER'
        action.target = str(target_dir)

        delete_folder(action, scene, studio, "")

        assert not target_dir.exists()


def test_delete_folder_missing_target_no_op():
    scene = _fresh_scene()
    studio = _new_studio(scene)
    with tempfile.TemporaryDirectory() as tmp:
        action = studio.post_render_actions.add()
        action.action_type = 'DELETE_FOLDER'
        action.target = str(Path(tmp) / "does_not_exist")
        # Should not raise
        delete_folder(action, scene, studio, "")


# --- play_sound (mock subprocess so no actual audio) -----------------------


def test_play_sound_default_writes_bell():
    """'default' target writes a bell to stdout — best-effort cross-platform."""
    scene = _fresh_scene()
    studio = _new_studio(scene)
    action = studio.post_render_actions.add()
    action.action_type = 'PLAY_SOUND'
    action.target = "default"
    # Should not raise
    play_sound(action, scene, studio, "")


def test_play_sound_missing_file_no_op():
    scene = _fresh_scene()
    studio = _new_studio(scene)
    with tempfile.TemporaryDirectory() as tmp:
        action = studio.post_render_actions.add()
        action.action_type = 'PLAY_SOUND'
        action.target = str(Path(tmp) / "no_such_file.wav")
        play_sound(action, scene, studio, "")


# --- slack_webhook (mock urllib so no network) -----------------------------


def test_slack_webhook_posts_payload_with_template_expansion():
    scene = _fresh_scene()
    studio = _new_studio(scene, name="Hero")
    action = studio.post_render_actions.add()
    action.action_type = 'SLACK_WEBHOOK'
    action.target = "https://hooks.slack.com/services/FAKE"
    action.message = "Done: {studio} at {output_path}"

    with patch("stage.core.post_render.urlrequest.urlopen") as mock_open:
        slack_webhook(action, scene, studio, "/tmp/out.png")
        assert mock_open.called
        req = mock_open.call_args[0][0]
        assert req.full_url == "https://hooks.slack.com/services/FAKE"
        body = req.data.decode("utf-8")
        assert "Hero" in body
        assert "/tmp/out.png" in body


def test_slack_webhook_empty_url_no_op():
    scene = _fresh_scene()
    studio = _new_studio(scene)
    action = studio.post_render_actions.add()
    action.action_type = 'SLACK_WEBHOOK'
    action.target = ""

    with patch("stage.core.post_render.urlrequest.urlopen") as mock_open:
        slack_webhook(action, scene, studio, "/tmp/x.png")
        assert not mock_open.called


# --- run_actions chain -----------------------------------------------------


def test_run_actions_executes_in_order():
    """Two actions in declared order; both must run."""
    scene = _fresh_scene()
    studio = _new_studio(scene)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = _make_render_output(tmp_path)

        a1 = studio.post_render_actions.add()
        a1.action_type = 'COPY_FILE'
        a1.target = str(tmp_path / "a" / "{studio}.png")
        a2 = studio.post_render_actions.add()
        a2.action_type = 'COPY_FILE'
        a2.target = str(tmp_path / "b" / "{studio}.png")

        run_actions(scene, studio, str(src))

        assert (tmp_path / "a" / "Hero.png").exists()
        assert (tmp_path / "b" / "Hero.png").exists()


def test_run_actions_continues_after_action_error():
    """A failing action shouldn't abort the rest of the chain."""
    scene = _fresh_scene()
    studio = _new_studio(scene)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        src = _make_render_output(tmp_path)

        bad = studio.post_render_actions.add()
        bad.action_type = 'COPY_FILE'
        bad.target = "/nonexistent_root_dir/cannot_write_here/x.png"

        good = studio.post_render_actions.add()
        good.action_type = 'COPY_FILE'
        good.target = str(tmp_path / "good" / "{studio}.png")

        run_actions(scene, studio, str(src))

        # Despite the first one failing, the second should have run
        assert (tmp_path / "good" / "Hero.png").exists()
