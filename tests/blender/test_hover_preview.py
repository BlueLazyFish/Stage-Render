"""Tests for click-to-preview (auto-apply on active-index change) — v1.0."""

from __future__ import annotations

import bpy

from stage.core.auto_apply import maybe_auto_apply
from stage.core.facets import capture_all


def _fresh_scene(name: str = "stage_hover_test"):
    if name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[name], do_unlink=True)
    return bpy.data.scenes.new(name)


def _add_studio_with_resolution(scene, name: str, resolution_x: int):
    s = scene.stage_data.studios.add()
    s.name = name
    s.uuid = f"hp-{name}"
    scene.render.resolution_x = resolution_x
    capture_all(scene, s)
    return s


def test_auto_apply_off_does_nothing():
    scene = _fresh_scene()
    _add_studio_with_resolution(scene, "A", 1920)
    _add_studio_with_resolution(scene, "B", 800)

    scene.stage_data.active_index = 0
    scene.render.resolution_x = 100  # mutate

    applied = maybe_auto_apply(scene.stage_data, scene, auto_apply=False)

    assert applied is False
    assert scene.render.resolution_x == 100, "auto_apply=False should not touch the scene"


def test_auto_apply_on_applies_active_studio():
    scene = _fresh_scene()
    _add_studio_with_resolution(scene, "A", 1920)
    b = _add_studio_with_resolution(scene, "B", 800)

    scene.stage_data.active_index = 1  # select B
    scene.render.resolution_x = 100  # mutate scene away from B's captured 800

    applied = maybe_auto_apply(scene.stage_data, scene, auto_apply=True)

    assert applied is True
    assert scene.render.resolution_x == 800, (
        f"expected B's 800, got {scene.render.resolution_x}"
    )
    assert scene.stage_data.last_applied_studio_uuid == b.uuid
    assert scene.stage_data.dirty is False


def test_auto_apply_with_invalid_index_is_no_op():
    scene = _fresh_scene()
    # No Studios at all
    applied = maybe_auto_apply(scene.stage_data, scene, auto_apply=True)
    assert applied is False


def test_active_index_callback_fires_with_auto_apply_off_default():
    """Default behavior: changing active_index does NOT mutate scene (no prefs in test)."""
    scene = _fresh_scene()
    _add_studio_with_resolution(scene, "A", 1920)
    _add_studio_with_resolution(scene, "B", 800)
    scene.stage_data.active_index = 0
    scene.render.resolution_x = 100

    # Trigger the callback by changing active_index — get_prefs returns None
    # in this script-registered context, so auto_apply defaults to False.
    scene.stage_data.active_index = 1

    assert scene.render.resolution_x == 100, (
        "scene should not change when prefs aren't installed (default off)"
    )
