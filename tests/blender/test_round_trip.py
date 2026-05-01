"""Round-trip invariant tests — capture → mutate → apply → state-equal.

The central Phase 1 correctness check (per ADDON_PLAN.md §5).

Each facet must satisfy: capturing scene state into a Studio and then
applying that Studio back must restore the scene to its captured form.
"""

from __future__ import annotations

import bpy

from stage.core.facets import all_facets, apply_all, capture_all


# --- helpers ----------------------------------------------------------------


def _fresh_scene(name: str = "stage_test"):
    """Create a clean scene — no surprises from default loaded data."""
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


# --- registry ---------------------------------------------------------------


def test_registry_contains_output_path():
    facets = {f.facet_id for f in all_facets()}
    assert "output_path" in facets, f"Missing output_path facet; have: {sorted(facets)}"


# --- output_path facet ------------------------------------------------------


def test_output_path_round_trip():
    """capture → mutate → apply → state restored."""
    scene = _fresh_scene()
    studio = _new_studio(scene)

    scene.render.filepath = "/tmp/initial/"

    capture_all(scene, studio)

    scene.render.filepath = "/tmp/different/"

    apply_all(scene, studio)

    assert scene.render.filepath == "/tmp/initial/", (
        f"Output path round-trip failed: got {scene.render.filepath!r}"
    )


def test_output_path_disabled_facet_skips_apply():
    """When facet_output_path_enabled is False, apply leaves the scene alone."""
    scene = _fresh_scene()
    studio = _new_studio(scene)

    scene.render.filepath = "/tmp/captured/"
    capture_all(scene, studio)

    studio.facet_output_path_enabled = False

    scene.render.filepath = "/tmp/should_stay/"
    apply_all(scene, studio)

    assert scene.render.filepath == "/tmp/should_stay/", (
        f"Disabled facet still applied: got {scene.render.filepath!r}"
    )


def test_output_path_empty_capture_does_not_overwrite():
    """If output_override is empty (no captured value), apply is a no-op."""
    scene = _fresh_scene()
    studio = _new_studio(scene)

    # Studio has empty output_override (default)
    assert studio.output_override == ""

    scene.render.filepath = "/tmp/keep_this/"
    apply_all(scene, studio)

    assert scene.render.filepath == "/tmp/keep_this/"
