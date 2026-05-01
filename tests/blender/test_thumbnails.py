"""Tests for thumbnail rendering and preview cache integration."""

from __future__ import annotations

from pathlib import Path

import bpy

from stage import handlers
from stage.core.thumbnails import render_thumbnail, thumbnail_path_for


def _fresh_scene(name: str = "stage_thumb_test"):
    if name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[name], do_unlink=True)
    return bpy.data.scenes.new(name)


def _new_studio(scene, name: str = "Test"):
    data = scene.stage_data
    while len(data.studios):
        data.studios.remove(0)
    s = data.studios.add()
    s.name = name
    s.uuid = f"thumb-test-{name}"
    return s


def _setup_minimal_renderable(scene):
    """Cube + camera so Workbench has something to render."""
    mesh = bpy.data.meshes.new(f"{scene.name}_mesh")
    obj = bpy.data.objects.new(f"{scene.name}_cube", mesh)
    scene.collection.objects.link(obj)
    cam_data = bpy.data.cameras.new(f"{scene.name}_cam_data")
    cam_obj = bpy.data.objects.new(f"{scene.name}_cam", cam_data)
    cam_obj.location = (5, -5, 5)
    cam_obj.rotation_euler = (0.9, 0, 0.78)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj


def test_thumbnail_path_format():
    p = thumbnail_path_for("test-uuid-1234")
    assert p.name == "test-uuid-1234.png"
    assert "stage" in str(p)
    assert "thumbnails" in str(p)


def test_thumbnail_path_no_uuid():
    """Empty uuid still returns a path (caller is responsible for guarding)."""
    p = thumbnail_path_for("")
    assert p.name == ".png"


def test_render_thumbnail_creates_file():
    scene = _fresh_scene()
    _setup_minimal_renderable(scene)
    studio = _new_studio(scene)

    handlers.set_apply_in_progress(True)
    try:
        result = render_thumbnail(scene, studio)
    finally:
        handlers.set_apply_in_progress(False)

    assert result is not None, "render_thumbnail returned None"
    assert result.exists(), f"thumbnail file not at {result}"
    assert result.stat().st_size > 0, "thumbnail file empty"
    assert studio.thumbnail_path == str(result)

    # Cleanup
    result.unlink(missing_ok=True)


def test_render_thumbnail_no_uuid_returns_none():
    scene = _fresh_scene()
    data = scene.stage_data
    while len(data.studios):
        data.studios.remove(0)
    s = data.studios.add()
    # Don't set uuid — empty by default
    assert s.uuid == ""

    result = render_thumbnail(scene, s)
    assert result is None


def test_render_thumbnail_restores_render_settings():
    """Engine / resolution / filepath / file_format / use_lock_interface
    must all be restored after render."""
    scene = _fresh_scene()
    _setup_minimal_renderable(scene)
    studio = _new_studio(scene)

    scene.render.engine = 'CYCLES'
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 50
    scene.render.filepath = "/tmp/user_set_path/"
    scene.render.image_settings.file_format = 'JPEG'
    scene.render.use_lock_interface = True

    handlers.set_apply_in_progress(True)
    try:
        result = render_thumbnail(scene, studio)
    finally:
        handlers.set_apply_in_progress(False)

    assert result is not None
    assert scene.render.engine == 'CYCLES', f"engine: {scene.render.engine}"
    assert scene.render.resolution_x == 1920
    assert scene.render.resolution_y == 1080
    assert scene.render.resolution_percentage == 50
    assert scene.render.filepath == "/tmp/user_set_path/"
    assert scene.render.image_settings.file_format == 'JPEG'
    assert scene.render.use_lock_interface is True

    result.unlink(missing_ok=True)


def test_studio_add_renders_thumbnail():
    """The stage.studio_add operator renders a thumbnail as a side effect."""
    scene = _fresh_scene()
    _setup_minimal_renderable(scene)
    bpy.context.window.scene = scene  # make active so operator targets it

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.studio_add(name="ThumbProbe")

    studio = scene.stage_data.studios[0]
    assert studio.thumbnail_path != "", "thumbnail_path not set on add"
    assert Path(studio.thumbnail_path).exists(), (
        f"thumbnail file missing: {studio.thumbnail_path}"
    )

    # Cleanup
    Path(studio.thumbnail_path).unlink(missing_ok=True)
