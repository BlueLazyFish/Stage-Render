"""Tests for multi-selection + bulk-edit operators — v1.0."""

from __future__ import annotations

import bpy


def _fresh_scene(name: str = "stage_multi_edit_test"):
    if name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[name], do_unlink=True)
    return bpy.data.scenes.new(name)


def _add_studio(scene, name: str, *, selected: bool = False, locked: bool = False, tags: str = "", group: str = ""):
    s = scene.stage_data.studios.add()
    s.name = name
    s.uuid = f"me-{name}"
    s.selected = selected
    s.locked = locked
    s.tags = tags
    s.group_name = group
    return s


# --- model -----------------------------------------------------------------


def test_studio_has_selected_field():
    scene = _fresh_scene()
    s = _add_studio(scene, "A")
    assert hasattr(s, "selected")
    assert s.selected is False


# --- selection operators ---------------------------------------------------


def test_select_all():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    for i in range(3):
        _add_studio(scene, f"S{i}")

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.select_all()

    assert all(s.selected for s in scene.stage_data.studios)


def test_select_none():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    for i in range(3):
        _add_studio(scene, f"S{i}", selected=True)

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.select_none()

    assert not any(s.selected for s in scene.stage_data.studios)


def test_select_invert():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _add_studio(scene, "A", selected=True)
    b = _add_studio(scene, "B", selected=False)
    c = _add_studio(scene, "C", selected=True)

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.select_invert()

    assert a.selected is False
    assert b.selected is True
    assert c.selected is False


def test_select_by_group():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _add_studio(scene, "A", group="Cameras")
    b = _add_studio(scene, "B", group="Cameras")
    c = _add_studio(scene, "C", group="Lighting")

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.select_by_group(group_name="Cameras")

    assert a.selected and b.selected
    assert not c.selected


def test_select_by_tag_substring_case_insensitive():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _add_studio(scene, "A", tags="wip, hero")
    b = _add_studio(scene, "B", tags="WIP, detail")
    c = _add_studio(scene, "C", tags="final")

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.select_by_tag(tag="wip")

    assert a.selected and b.selected
    assert not c.selected


def test_select_by_tag_empty_cancelled():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _add_studio(scene, "A", tags="wip")

    with bpy.context.temp_override(scene=scene):
        try:
            bpy.ops.stage.select_by_tag(tag="")
        except RuntimeError:
            pass  # operator reports {'WARNING'} + returns CANCELLED

    assert a.selected is False, "empty tag must not change selection"


# --- bulk edit: group / parent ---------------------------------------------


def test_bulk_set_group_only_touches_selected():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _add_studio(scene, "A", selected=True)
    b = _add_studio(scene, "B", selected=False)
    c = _add_studio(scene, "C", selected=True)

    g = scene.stage_data.groups.add()
    g.name = "Cameras"

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.bulk_set_group(group_name="Cameras")

    assert a.group_name == "Cameras"
    assert b.group_name == ""
    assert c.group_name == "Cameras"


def test_bulk_set_group_skips_locked():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _add_studio(scene, "A", selected=True)
    b = _add_studio(scene, "B", selected=True, locked=True)

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.bulk_set_group(group_name="X")

    assert a.group_name == "X"
    assert b.group_name == "", "locked Studio must not be touched by bulk edit"


def test_bulk_set_parent_skips_self_reference():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    parent = _add_studio(scene, "Parent", selected=True)
    child = _add_studio(scene, "Child", selected=True)

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.bulk_set_parent(parent_name="Parent")

    assert child.parent_name == "Parent"
    assert parent.parent_name == "", "Studio must not become its own parent"


# --- bulk edit: color / locked ---------------------------------------------


def test_bulk_set_color():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _add_studio(scene, "A", selected=True)
    b = _add_studio(scene, "B", selected=False)

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.bulk_set_color(color=(1.0, 0.0, 0.0, 1.0))

    assert tuple(a.color) == (1.0, 0.0, 0.0, 1.0)
    assert tuple(b.color) != (1.0, 0.0, 0.0, 1.0)


def test_bulk_lock_can_target_unlocked():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _add_studio(scene, "A", selected=True)

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.bulk_set_locked(locked=True)

    assert a.locked is True


def test_bulk_unlock_targets_locked_studios():
    """Lock op intentionally bypasses the skip-locked rule, so you can
    bulk-unlock a batch of locked deliverables."""
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _add_studio(scene, "A", selected=True, locked=True)
    b = _add_studio(scene, "B", selected=True, locked=True)
    c = _add_studio(scene, "C", selected=False, locked=True)

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.bulk_set_locked(locked=False)

    assert a.locked is False
    assert b.locked is False
    assert c.locked is True, "unselected locked Studio must not be unlocked"


# --- bulk edit: tags -------------------------------------------------------


def test_bulk_add_tag_appends_unique():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _add_studio(scene, "A", selected=True, tags="wip")
    b = _add_studio(scene, "B", selected=True, tags="")

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.bulk_add_tag(tag="hero")

    assert "hero" in a.tags and "wip" in a.tags
    assert b.tags == "hero"


def test_bulk_add_tag_skips_duplicate():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _add_studio(scene, "A", selected=True, tags="wip, hero")

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.bulk_add_tag(tag="hero")

    # Should not double up — exact tag set unchanged
    parts = sorted(t.strip() for t in a.tags.split(","))
    assert parts == ["hero", "wip"]


def test_bulk_remove_tag():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _add_studio(scene, "A", selected=True, tags="wip, hero, detail")
    b = _add_studio(scene, "B", selected=True, tags="final")

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.bulk_remove_tag(tag="hero")

    assert "hero" not in a.tags
    assert "wip" in a.tags and "detail" in a.tags
    assert b.tags == "final"  # didn't have hero, no-op


# --- bulk edit: output / facet --------------------------------------------


def test_bulk_set_output_override():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _add_studio(scene, "A", selected=True)
    b = _add_studio(scene, "B", selected=False)

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.bulk_set_output(output_override="/tmp/renders/")

    assert a.output_override == "/tmp/renders/"
    assert b.output_override == ""


def test_bulk_set_facet_disables_camera():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _add_studio(scene, "A", selected=True)
    b = _add_studio(scene, "B", selected=False)

    assert a.facet_camera_enabled is True

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.bulk_set_facet(facet='camera', enabled=False)

    assert a.facet_camera_enabled is False
    assert b.facet_camera_enabled is True


def test_bulk_set_facet_enables_render():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    a = _add_studio(scene, "A", selected=True)
    a.facet_render_enabled = False

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.bulk_set_facet(facet='render', enabled=True)

    assert a.facet_render_enabled is True


# --- panel registration ----------------------------------------------------


def test_bulk_edit_panel_registered():
    from stage.ui.n_panel import STAGE_PT_bulk_edit
    assert STAGE_PT_bulk_edit.bl_idname == "STAGE_PT_bulk_edit"
    assert STAGE_PT_bulk_edit.bl_category == "Stage"
    assert 'DEFAULT_CLOSED' in STAGE_PT_bulk_edit.bl_options
