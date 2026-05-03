"""Tests for Studio name auto-disambiguation on add / duplicate / template."""

from __future__ import annotations

import bpy

from stage.utils.naming import unique_name


def _fresh_scene(name: str = "stage_naming_test"):
    if name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[name], do_unlink=True)
    return bpy.data.scenes.new(name)


# --- helper ----------------------------------------------------------------


def test_unique_name_returns_base_when_free():
    assert unique_name("Studio", []) == "Studio"
    assert unique_name("Studio", ["Other"]) == "Studio"


def test_unique_name_appends_001_then_002():
    assert unique_name("Studio", ["Studio"]) == "Studio.001"
    assert unique_name("Studio", ["Studio", "Studio.001"]) == "Studio.002"


def test_unique_name_fills_first_gap():
    """Skipped indexes get reused — Studio.001 is free even though .005 exists."""
    assert unique_name("Studio", ["Studio", "Studio.005"]) == "Studio.001"


def test_unique_name_empty_base_falls_back():
    assert unique_name("", []) == "_"
    assert unique_name("   ", []) == "_"


# --- studio_add operator --------------------------------------------------


def test_studio_add_disambiguates_back_to_back_clicks():
    scene = _fresh_scene()
    bpy.context.window.scene = scene

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.studio_add()
        bpy.ops.stage.studio_add()
        bpy.ops.stage.studio_add()

    names = [s.name for s in scene.stage_data.studios]
    assert names == ["Studio", "Studio.001", "Studio.002"], (
        f"unexpected disambiguation: {names}"
    )


def test_studio_add_with_custom_name_disambiguates_too():
    scene = _fresh_scene()
    bpy.context.window.scene = scene

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.studio_add(name="Hero")
        bpy.ops.stage.studio_add(name="Hero")

    names = [s.name for s in scene.stage_data.studios]
    assert names == ["Hero", "Hero.001"]


# --- studio_duplicate operator -------------------------------------------


def test_studio_duplicate_disambiguates_copy_suffix():
    scene = _fresh_scene()
    bpy.context.window.scene = scene

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.studio_add(name="Hero")
        scene.stage_data.active_index = 0
        bpy.ops.stage.studio_duplicate()
        scene.stage_data.active_index = 0  # duplicate again from the original
        bpy.ops.stage.studio_duplicate()

    names = sorted(s.name for s in scene.stage_data.studios)
    assert names == ["Hero", "Hero Copy", "Hero Copy.001"], (
        f"unexpected: {names}"
    )


# --- template add -------------------------------------------------------


def test_template_add_disambiguates_repeated_use():
    scene = _fresh_scene()
    bpy.context.window.scene = scene

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.studio_add_from_template(template_id="default")
        bpy.ops.stage.studio_add_from_template(template_id="default")

    names = [s.name for s in scene.stage_data.studios]
    assert names == ["Default", "Default.001"], f"unexpected: {names}"
