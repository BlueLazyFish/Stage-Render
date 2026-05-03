"""Tests for Studio Groups — v1.0."""

from __future__ import annotations

import bpy

from stage.ui.studio_uilist import matches_filter


def _fresh_scene(name: str = "stage_groups_test"):
    if name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[name], do_unlink=True)
    return bpy.data.scenes.new(name)


def _add_studio(scene, name: str, *, group: str = ""):
    s = scene.stage_data.studios.add()
    s.name = name
    s.uuid = f"grp-{name}"
    s.group_name = group
    return s


# --- model -----------------------------------------------------------------


def test_studio_has_group_name_field():
    scene = _fresh_scene()
    s = _add_studio(scene, "A")
    assert hasattr(s, "group_name")
    assert s.group_name == ""


def test_studio_collection_has_groups():
    scene = _fresh_scene()
    assert hasattr(scene.stage_data, "groups")
    assert len(scene.stage_data.groups) == 0


# --- add_group operator ----------------------------------------------------


def test_add_group_creates_with_default_name():
    scene = _fresh_scene()
    bpy.context.window.scene = scene

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.add_group()

    assert len(scene.stage_data.groups) == 1
    assert scene.stage_data.groups[0].name == "Group"


def test_add_group_disambiguates_duplicate_names():
    scene = _fresh_scene()
    bpy.context.window.scene = scene

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.add_group()
        bpy.ops.stage.add_group()
        bpy.ops.stage.add_group()

    names = [g.name for g in scene.stage_data.groups]
    # Blender's standard convention: Foo, Foo.001, Foo.002 (no skipped index).
    assert names == ["Group", "Group.001", "Group.002"], (
        f"unexpected disambiguation: {names}"
    )


def test_add_group_with_custom_name():
    scene = _fresh_scene()
    bpy.context.window.scene = scene

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.add_group(name="Cameras")

    assert scene.stage_data.groups[0].name == "Cameras"


# --- remove_group operator -------------------------------------------------


def test_remove_group_drops_entry():
    scene = _fresh_scene()
    bpy.context.window.scene = scene

    g = scene.stage_data.groups.add()
    g.name = "ToRemove"

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.remove_group(index=0)

    assert len(scene.stage_data.groups) == 0


def test_remove_group_detaches_member_studios():
    """Studios that referenced the removed group should become ungrouped."""
    scene = _fresh_scene()
    bpy.context.window.scene = scene

    g = scene.stage_data.groups.add()
    g.name = "Cameras"

    s1 = _add_studio(scene, "Hero", group="Cameras")
    s2 = _add_studio(scene, "Wide", group="Cameras")
    s3 = _add_studio(scene, "Detail", group="Other")  # different group

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.remove_group(index=0)

    assert s1.group_name == "", "member Studio should be detached"
    assert s2.group_name == "", "member Studio should be detached"
    assert s3.group_name == "Other", "non-member Studio shouldn't be touched"


def test_remove_group_invalid_index_no_op():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    g = scene.stage_data.groups.add()
    g.name = "OnlyOne"

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.remove_group(index=99)

    assert len(scene.stage_data.groups) == 1, "invalid index should be no-op"


# --- filter integration ----------------------------------------------------


def test_matches_filter_matches_group_name():
    scene = _fresh_scene()
    s = _add_studio(scene, "Hero", group="Cameras")
    assert matches_filter("camera", s) is True
    assert matches_filter("CAMERAS", s) is True
    assert matches_filter("lighting", s) is False


def test_matches_filter_combines_name_tags_and_group():
    scene = _fresh_scene()
    name_only = _add_studio(scene, "WipShot", group="")
    tag_only = _add_studio(scene, "A", group="")
    tag_only.tags = "wip"
    group_only = _add_studio(scene, "B", group="WipBatch")

    for studio in (name_only, tag_only, group_only):
        assert matches_filter("wip", studio) is True


# --- panel registration ----------------------------------------------------


def test_groups_panel_registered():
    from stage.ui.n_panel import STAGE_PT_groups
    assert STAGE_PT_groups.bl_idname == "STAGE_PT_groups"
    assert STAGE_PT_groups.bl_category == "Stage"
    assert 'DEFAULT_CLOSED' in STAGE_PT_groups.bl_options
