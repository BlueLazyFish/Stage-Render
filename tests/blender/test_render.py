"""Tests for render_one and render_all operators.

These tests do real Workbench renders, so each adds ~100ms. Kept to a
small handful — three tests covering the must-work cases.
"""

from __future__ import annotations

from pathlib import Path

import bpy

from stage.core.facets import capture_all


_OUT_DIR = Path("/tmp/stage_render_test")
_PATTERN = str(_OUT_DIR / "{studio}.png")


def _fresh_scene(name: str = "stage_render_test"):
    if name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[name], do_unlink=True)
    return bpy.data.scenes.new(name)


def _setup_renderable(scene):
    mesh = bpy.data.meshes.new(f"{scene.name}_mesh")
    obj = bpy.data.objects.new(f"{scene.name}_cube", mesh)
    scene.collection.objects.link(obj)
    cam_data = bpy.data.cameras.new(f"{scene.name}_cam_data")
    cam_obj = bpy.data.objects.new(f"{scene.name}_cam", cam_data)
    cam_obj.location = (5, -5, 5)
    cam_obj.rotation_euler = (0.9, 0, 0.78)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    # Workbench keeps tests fast — Cycles would multiply runtime by 10x+
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x = 64
    scene.render.resolution_y = 64


def _add_studio(scene, name: str, *, enabled: bool = True):
    data = scene.stage_data
    s = data.studios.add()
    s.name = name
    s.uuid = f"render-test-{name}"
    s.enabled = enabled
    # Capture first — OutputPathFacet.capture would otherwise overwrite
    # whatever we set on output_override with scene.render.filepath.
    capture_all(scene, s)
    s.output_override = _PATTERN
    return s


def _expected_path(studio_name: str) -> Path:
    return _OUT_DIR / f"{studio_name}.png"


def _cleanup_outputs(*names):
    for n in names:
        _expected_path(n).unlink(missing_ok=True)


def test_render_one_writes_to_expanded_path():
    scene = _fresh_scene()
    _setup_renderable(scene)
    bpy.context.window.scene = scene

    _add_studio(scene, "Hero")

    with bpy.context.temp_override(scene=scene):
        result = bpy.ops.stage.studio_render_one()

    try:
        assert result == {'FINISHED'}, f"operator returned {result}"
        assert _expected_path("Hero").exists(), (
            f"render output not at {_expected_path('Hero')}"
        )
    finally:
        _cleanup_outputs("Hero")


def test_render_all_writes_each_enabled():
    scene = _fresh_scene()
    _setup_renderable(scene)
    bpy.context.window.scene = scene

    data = scene.stage_data
    while len(data.studios):
        data.studios.remove(0)
    _add_studio(scene, "AllHero")
    _add_studio(scene, "AllWide")

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.studio_render_all()

    try:
        assert _expected_path("AllHero").exists()
        assert _expected_path("AllWide").exists()
    finally:
        _cleanup_outputs("AllHero", "AllWide")


def test_render_all_skips_disabled():
    scene = _fresh_scene()
    _setup_renderable(scene)
    bpy.context.window.scene = scene

    data = scene.stage_data
    while len(data.studios):
        data.studios.remove(0)
    _add_studio(scene, "EnabledStudio", enabled=True)
    _add_studio(scene, "DisabledStudio", enabled=False)

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.studio_render_all()

    try:
        assert _expected_path("EnabledStudio").exists(), (
            "enabled studio should have been rendered"
        )
        assert not _expected_path("DisabledStudio").exists(), (
            "disabled studio should have been skipped"
        )
    finally:
        _cleanup_outputs("EnabledStudio", "DisabledStudio")
