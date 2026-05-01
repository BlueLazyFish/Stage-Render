"""Dirty-state tracking — the UX win over Renderset.

Tests the state machine (handler flag, last_applied tracking) plus the
operator-level integration (apply / update clearing dirty). Cannot reliably
test depsgraph firing in headless mode, so we call the handler directly.
"""

from __future__ import annotations

import bpy

from stage import handlers
from stage.core.facets import capture_all


def _fresh_scene(name: str = "stage_dirty_test"):
    if name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[name], do_unlink=True)
    return bpy.data.scenes.new(name)


def _new_studio(scene, name: str = "Test"):
    data = scene.stage_data
    while len(data.studios):
        data.studios.remove(0)
    s = data.studios.add()
    s.name = name
    s.uuid = f"test-{name}"
    return s


# --- defaults ---------------------------------------------------------------


def test_dirty_starts_false():
    scene = _fresh_scene()
    assert scene.stage_data.dirty is False
    assert scene.stage_data.last_applied_studio_uuid == ""


# --- handler behavior -------------------------------------------------------


def test_handler_skips_when_no_studio_applied():
    """Without last_applied_studio_uuid, the handler is a no-op."""
    scene = _fresh_scene()
    _new_studio(scene)

    handlers.depsgraph_update_post(scene, None)

    assert scene.stage_data.dirty is False


def test_handler_sets_dirty_when_studio_applied():
    """With last_applied set, the handler flips dirty=True."""
    scene = _fresh_scene()
    studio = _new_studio(scene)

    scene.stage_data.last_applied_studio_uuid = studio.uuid
    scene.stage_data.dirty = False

    handlers.depsgraph_update_post(scene, None)

    assert scene.stage_data.dirty is True


def test_handler_skips_when_apply_in_progress():
    """set_apply_in_progress(True) suppresses the handler — keeps Apply / Update
    from self-triggering as they write to the scene."""
    scene = _fresh_scene()
    studio = _new_studio(scene)
    scene.stage_data.last_applied_studio_uuid = studio.uuid
    scene.stage_data.dirty = False

    handlers.set_apply_in_progress(True)
    try:
        handlers.depsgraph_update_post(scene, None)
        assert scene.stage_data.dirty is False, (
            "handler fired while apply was in progress"
        )
    finally:
        handlers.set_apply_in_progress(False)


# --- operator integration ---------------------------------------------------


def test_apply_clears_dirty_and_stamps_last_applied():
    scene = _fresh_scene()
    studio = _new_studio(scene)
    capture_all(scene, studio)  # so apply has something coherent to do

    # Force pre-conditions
    scene.stage_data.dirty = True
    scene.stage_data.last_applied_studio_uuid = ""

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.studio_apply()

    assert scene.stage_data.dirty is False
    assert scene.stage_data.last_applied_studio_uuid == studio.uuid


def test_update_clears_dirty_and_stamps_last_applied():
    scene = _fresh_scene()
    studio = _new_studio(scene)

    scene.stage_data.dirty = True
    scene.stage_data.last_applied_studio_uuid = ""

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.studio_update_from_scene()

    assert scene.stage_data.dirty is False
    assert scene.stage_data.last_applied_studio_uuid == studio.uuid
