"""Tests for render-settings templates — builtin + user-saved."""

from __future__ import annotations

import bpy

from stage.core.templates import (
    TEMPLATES,
    apply_template_to_studio,
    capture_template_dict_from_scene,
    user_template_to_dict,
    write_dict_to_user_template,
)
from stage.prefs import get_prefs


def _fresh_scene(name: str = "stage_template_test"):
    if name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[name], do_unlink=True)
    return bpy.data.scenes.new(name)


def _new_studio(scene, name: str = "Test"):
    s = scene.stage_data.studios.add()
    s.name = name
    s.uuid = f"tpl-test-{name}"
    return s


def _clear_user_templates(context):
    """Wipe user templates between tests so prefs state doesn't bleed."""
    prefs = get_prefs(context)
    if prefs is None:
        return
    while len(prefs.user_templates):
        prefs.user_templates.remove(0)


# --- builtin TEMPLATES dict -------------------------------------------------


def test_templates_has_default_and_social_examples():
    """v1.0 ships one neutral default plus four social-media examples."""
    assert "default" in TEMPLATES
    assert "instagram_square" in TEMPLATES
    assert "instagram_portrait" in TEMPLATES
    assert "instagram_story" in TEMPLATES
    assert "youtube_thumbnail" in TEMPLATES


def test_template_required_fields():
    required = {"display_name", "engine", "render_settings"}
    for tid, t in TEMPLATES.items():
        missing = required - set(t)
        assert not missing, f"{tid} missing keys: {missing}"


def test_instagram_square_resolution():
    t = TEMPLATES["instagram_square"]
    assert t["resolution_x"] == 1080
    assert t["resolution_y"] == 1080


def test_instagram_portrait_resolution():
    t = TEMPLATES["instagram_portrait"]
    assert t["resolution_x"] == 1080
    assert t["resolution_y"] == 1350


def test_instagram_story_resolution():
    t = TEMPLATES["instagram_story"]
    assert t["resolution_x"] == 1080
    assert t["resolution_y"] == 1920


# --- apply_template_to_studio ----------------------------------------------


def test_apply_default_sets_render_facet():
    scene = _fresh_scene()
    studio = _new_studio(scene)
    apply_template_to_studio(studio, TEMPLATES["default"])

    f = studio.facet_render
    assert f.captured is True
    assert f.engine == "BLENDER_EEVEE"
    assert f.resolution_x == 1920
    assert f.resolution_y == 1080
    paths = {e.data_path for e in f.settings}
    assert "eevee.taa_render_samples" in paths


def test_apply_template_replaces_settings_bag():
    """Applying a template clears any existing settings entries first."""
    scene = _fresh_scene()
    studio = _new_studio(scene)
    pre = studio.facet_render.settings.add()
    pre.data_path = "stale.path"
    pre.value_repr = "999"
    pre.value_type = 'INT'

    apply_template_to_studio(studio, TEMPLATES["default"])

    paths = {e.data_path for e in studio.facet_render.settings}
    assert "stale.path" not in paths


# --- builtin operator integration -----------------------------------------


def test_operator_creates_studio_from_builtin():
    scene = _fresh_scene()
    bpy.context.window.scene = scene

    with bpy.context.temp_override(scene=scene):
        result = bpy.ops.stage.studio_add_from_template(template_id="default")

    assert result == {'FINISHED'}
    s = scene.stage_data.studios[0]
    assert s.name == "Default"
    assert s.facet_render.engine == "BLENDER_EEVEE"
    assert s.facet_render.resolution_x == 1920


def test_operator_unknown_template_cancelled():
    scene = _fresh_scene()
    bpy.context.window.scene = scene

    raised = False
    try:
        with bpy.context.temp_override(scene=scene):
            bpy.ops.stage.studio_add_from_template(template_id="not_a_real_template")
    except RuntimeError:
        raised = True

    assert raised
    assert len(scene.stage_data.studios) == 0


# --- capture_template_dict_from_scene -------------------------------------


def test_capture_from_scene_records_engine_and_resolution():
    scene = _fresh_scene()
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 800
    scene.render.resolution_y = 600
    scene.render.resolution_percentage = 75

    template = capture_template_dict_from_scene(scene, "Snapshot")
    assert template["display_name"] == "Snapshot"
    assert template["engine"] == "BLENDER_EEVEE"
    assert template["resolution_x"] == 800
    assert template["resolution_y"] == 600
    assert template["resolution_percentage"] == 75


def test_capture_from_scene_records_engine_specific_settings():
    scene = _fresh_scene()
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = 32

    template = capture_template_dict_from_scene(scene, "Test")
    assert "eevee.taa_render_samples" in template["render_settings"]
    assert template["render_settings"]["eevee.taa_render_samples"] == 32


# --- user template round-trip --------------------------------------------


def test_user_template_dict_round_trip():
    """write_dict_to_user_template + user_template_to_dict round-trip cleanly."""
    bpy.context.window.scene = _fresh_scene()
    _clear_user_templates(bpy.context)
    prefs = get_prefs(bpy.context)
    assert prefs is not None, "prefs must be available for user-template tests"

    src = {
        "display_name": "RoundTrip",
        "engine": "BLENDER_EEVEE",
        "resolution_x": 1080,
        "resolution_y": 1350,
        "resolution_percentage": 100,
        "render_settings": {"eevee.taa_render_samples": 48},
    }
    ut = prefs.user_templates.add()
    write_dict_to_user_template(ut, src)
    out = user_template_to_dict(ut)

    assert out["display_name"] == src["display_name"]
    assert out["engine"] == src["engine"]
    assert out["resolution_x"] == src["resolution_x"]
    assert out["resolution_y"] == src["resolution_y"]
    assert out["render_settings"] == src["render_settings"]

    _clear_user_templates(bpy.context)


# --- save / delete operators ----------------------------------------------


def test_save_template_from_scene_creates_user_template():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    _clear_user_templates(bpy.context)

    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1080

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.save_template_from_scene(name="Insta Square Custom")

    prefs = get_prefs(bpy.context)
    assert prefs is not None
    assert len(prefs.user_templates) == 1
    saved = prefs.user_templates[0]
    assert saved.display_name == "Insta Square Custom"
    assert saved.engine == "BLENDER_EEVEE"
    assert saved.resolution_x == 1080
    assert saved.resolution_y == 1080

    _clear_user_templates(bpy.context)


def test_save_template_with_existing_name_overwrites():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    _clear_user_templates(bpy.context)

    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 100
    scene.render.resolution_y = 100

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.save_template_from_scene(name="Same")

    scene.render.resolution_x = 999
    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.save_template_from_scene(name="Same")

    prefs = get_prefs(bpy.context)
    assert len(prefs.user_templates) == 1, "should overwrite, not duplicate"
    assert prefs.user_templates[0].resolution_x == 999

    _clear_user_templates(bpy.context)


def test_save_template_empty_name_cancelled():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    _clear_user_templates(bpy.context)

    raised = False
    try:
        with bpy.context.temp_override(scene=scene):
            bpy.ops.stage.save_template_from_scene(name="   ")
    except RuntimeError:
        raised = True

    prefs = get_prefs(bpy.context)
    assert raised, "empty name must report ERROR"
    assert len(prefs.user_templates) == 0


def test_delete_user_template():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    _clear_user_templates(bpy.context)

    prefs = get_prefs(bpy.context)
    a = prefs.user_templates.add()
    a.display_name = "ToKeep"
    b = prefs.user_templates.add()
    b.display_name = "ToDrop"
    c = prefs.user_templates.add()
    c.display_name = "AlsoKeep"

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.delete_user_template(index=1)

    names = [ut.display_name for ut in prefs.user_templates]
    assert names == ["ToKeep", "AlsoKeep"]

    _clear_user_templates(bpy.context)


def test_delete_user_template_invalid_index_no_op():
    bpy.context.window.scene = _fresh_scene()
    _clear_user_templates(bpy.context)
    prefs = get_prefs(bpy.context)
    prefs.user_templates.add().display_name = "OnlyOne"

    with bpy.context.temp_override(scene=bpy.context.scene):
        bpy.ops.stage.delete_user_template(index=99)

    assert len(prefs.user_templates) == 1
    _clear_user_templates(bpy.context)


# --- add_from_template using user template path ---------------------------


def test_add_from_user_template_uses_prefs_entry():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    _clear_user_templates(bpy.context)

    prefs = get_prefs(bpy.context)
    ut = prefs.user_templates.add()
    write_dict_to_user_template(ut, {
        "display_name": "MyVerticalCustom",
        "engine": "BLENDER_EEVEE",
        "resolution_x": 720,
        "resolution_y": 1280,
        "resolution_percentage": 100,
        "render_settings": {"eevee.taa_render_samples": 24},
    })

    with bpy.context.temp_override(scene=scene):
        bpy.ops.stage.studio_add_from_template(user_template_name="MyVerticalCustom")

    s = scene.stage_data.studios[0]
    assert s.name == "MyVerticalCustom"
    assert s.facet_render.resolution_x == 720
    assert s.facet_render.resolution_y == 1280
    paths = {e.data_path for e in s.facet_render.settings}
    assert "eevee.taa_render_samples" in paths

    _clear_user_templates(bpy.context)


def test_add_from_unknown_user_template_cancelled():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    _clear_user_templates(bpy.context)

    raised = False
    try:
        with bpy.context.temp_override(scene=scene):
            bpy.ops.stage.studio_add_from_template(user_template_name="NeverSaved")
    except RuntimeError:
        raised = True

    assert raised
    assert len(scene.stage_data.studios) == 0
