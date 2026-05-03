"""Tests for starter templates — v1.0."""

from __future__ import annotations

import bpy

from stage.core.templates import TEMPLATES, apply_template_to_studio


def _fresh_scene(name: str = "stage_template_test"):
    if name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[name], do_unlink=True)
    return bpy.data.scenes.new(name)


def _new_studio(scene, name: str = "Test"):
    s = scene.stage_data.studios.add()
    s.name = name
    s.uuid = f"tpl-test-{name}"
    return s


# --- TEMPLATES dict --------------------------------------------------------


def test_templates_has_three_entries():
    """v1.0 ships with the documented three render-settings templates."""
    assert "cycles_quality" in TEMPLATES
    assert "eevee_preview" in TEMPLATES
    assert "print_4k" in TEMPLATES


def test_template_required_fields():
    """Every template has the keys apply_template_to_studio relies on."""
    required = {"display_name", "engine", "render_settings"}
    for tid, t in TEMPLATES.items():
        missing = required - set(t)
        assert not missing, f"{tid} missing keys: {missing}"


# --- apply_template_to_studio ----------------------------------------------


def test_apply_cycles_quality_sets_render_facet():
    scene = _fresh_scene()
    studio = _new_studio(scene)

    apply_template_to_studio(studio, TEMPLATES["cycles_quality"])

    f = studio.facet_render
    assert f.captured is True
    assert f.engine == "CYCLES"
    assert f.resolution_x == 1920
    assert f.resolution_y == 1080
    # Engine-specific bag populated with each render_settings entry
    paths = {e.data_path for e in f.settings}
    assert "cycles.samples" in paths
    assert "cycles.use_denoising" in paths
    assert "cycles.max_bounces" in paths


def test_apply_eevee_preview_sets_engine():
    scene = _fresh_scene()
    studio = _new_studio(scene)
    apply_template_to_studio(studio, TEMPLATES["eevee_preview"])
    assert studio.facet_render.engine == "BLENDER_EEVEE"
    assert studio.facet_render.resolution_x == 1280


def test_apply_print_4k_resolution():
    scene = _fresh_scene()
    studio = _new_studio(scene)
    apply_template_to_studio(studio, TEMPLATES["print_4k"])
    assert studio.facet_render.resolution_x == 3840
    assert studio.facet_render.resolution_y == 2160


def test_apply_template_replaces_settings_bag():
    """Applying a template clears any existing settings entries first."""
    scene = _fresh_scene()
    studio = _new_studio(scene)

    # Pre-populate with stale data
    pre = studio.facet_render.settings.add()
    pre.data_path = "stale.path"
    pre.value_repr = "999"
    pre.value_type = 'INT'

    apply_template_to_studio(studio, TEMPLATES["cycles_quality"])

    paths = {e.data_path for e in studio.facet_render.settings}
    assert "stale.path" not in paths, "stale entries should be cleared"
    assert "cycles.samples" in paths


# --- operator integration --------------------------------------------------


def test_operator_creates_studio_with_template_settings():
    scene = _fresh_scene()
    bpy.context.window.scene = scene

    with bpy.context.temp_override(scene=scene):
        result = bpy.ops.stage.studio_add_from_template(template_id="cycles_quality")

    assert result == {'FINISHED'}
    studios = scene.stage_data.studios
    assert len(studios) == 1
    s = studios[0]
    assert s.name == "Cycles Quality"
    assert s.facet_render.engine == "CYCLES"
    assert s.facet_render.resolution_x == 1920


def test_operator_unknown_template_cancelled():
    scene = _fresh_scene()
    bpy.context.window.scene = scene

    raised = False
    try:
        with bpy.context.temp_override(scene=scene):
            bpy.ops.stage.studio_add_from_template(template_id="not_a_real_template")
    except RuntimeError:
        # bpy.ops raises when the operator reports {'ERROR'} — expected.
        raised = True

    assert raised, "expected RuntimeError on unknown template"
    assert len(scene.stage_data.studios) == 0
