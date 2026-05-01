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


# --- world facet ------------------------------------------------------------


def _world(name: str):
    """Get or create a World datablock for testing — idempotent."""
    if name in bpy.data.worlds:
        return bpy.data.worlds[name]
    return bpy.data.worlds.new(name)


def test_world_facet_in_registry():
    facets = {f.facet_id for f in all_facets()}
    assert "world" in facets, f"Missing world facet; have: {sorted(facets)}"


def test_world_round_trip_with_existing_world():
    scene = _fresh_scene()
    studio = _new_studio(scene)

    world_a = _world("stage_test_world_a")
    world_b = _world("stage_test_world_b")

    scene.world = world_a
    scene.render.film_transparent = True

    capture_all(scene, studio)

    scene.world = world_b
    scene.render.film_transparent = False

    apply_all(scene, studio)

    assert scene.world == world_a, f"world not restored: got {scene.world}"
    assert scene.render.film_transparent is True


def test_world_round_trip_with_no_world():
    """A Studio that captured 'no world' restores scene.world to None on apply."""
    scene = _fresh_scene()
    studio = _new_studio(scene)

    scene.world = None
    capture_all(scene, studio)

    scene.world = _world("stage_test_world_a")
    apply_all(scene, studio)

    assert scene.world is None, f"expected None, got {scene.world}"


def test_world_disabled_facet_skips_apply():
    scene = _fresh_scene()
    studio = _new_studio(scene)

    world_a = _world("stage_test_world_a")
    world_c = _world("stage_test_world_c")

    scene.world = world_a
    capture_all(scene, studio)

    studio.facet_world_enabled = False

    scene.world = world_c
    apply_all(scene, studio)

    assert scene.world == world_c, "disabled facet still applied"


def test_world_missing_world_does_not_raise():
    """If captured world was deleted before apply, log + skip rather than crash."""
    scene = _fresh_scene()
    studio = _new_studio(scene)

    name = "stage_test_world_temp"
    if name in bpy.data.worlds:
        bpy.data.worlds.remove(bpy.data.worlds[name])
    world = bpy.data.worlds.new(name)
    scene.world = world

    capture_all(scene, studio)

    # Delete the world after capture
    bpy.data.worlds.remove(world)

    # Apply should not raise
    apply_all(scene, studio)


# --- camera facet -----------------------------------------------------------


def _camera_obj(name: str):
    """Get or create a camera Object — idempotent."""
    if name in bpy.data.objects:
        obj = bpy.data.objects[name]
        if obj.type == 'CAMERA':
            return obj
        bpy.data.objects.remove(obj, do_unlink=True)
    cam_data = bpy.data.cameras.new(f"{name}_data")
    return bpy.data.objects.new(name, cam_data)


def _vec_close(a, b, eps=1e-5):
    return all(abs(x - y) < eps for x, y in zip(a, b))


def test_camera_facet_in_registry():
    facets = {f.facet_id for f in all_facets()}
    assert "camera" in facets, f"Missing camera facet; have: {sorted(facets)}"


def test_camera_round_trip():
    """Capture transform + lens + DoF, mutate, apply, verify restored."""
    scene = _fresh_scene()
    studio = _new_studio(scene)

    cam_obj = _camera_obj("stage_test_camera")
    if cam_obj.name not in scene.collection.objects:
        scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # Distinctive captured state
    cam_obj.location = (1.5, 2.5, 3.5)
    cam_obj.rotation_euler = (0.1, 0.2, 0.3)
    cam_data = cam_obj.data
    cam_data.lens = 85.0
    cam_data.clip_start = 0.5
    cam_data.clip_end = 500.0
    cam_data.shift_x = 0.05
    cam_data.shift_y = -0.05
    cam_data.dof.use_dof = True
    cam_data.dof.aperture_fstop = 1.8
    cam_data.dof.focus_distance = 5.0

    capture_all(scene, studio)

    # Mutate
    cam_obj.location = (0.0, 0.0, 0.0)
    cam_obj.rotation_euler = (0.0, 0.0, 0.0)
    cam_data.lens = 24.0
    cam_data.dof.use_dof = False
    cam_data.dof.aperture_fstop = 8.0
    cam_data.dof.focus_distance = 100.0

    apply_all(scene, studio)

    assert _vec_close(cam_obj.location, (1.5, 2.5, 3.5)), (
        f"location not restored: {tuple(cam_obj.location)}"
    )
    assert _vec_close(cam_obj.rotation_euler, (0.1, 0.2, 0.3)), (
        f"rotation not restored: {tuple(cam_obj.rotation_euler)}"
    )
    assert abs(cam_data.lens - 85.0) < 1e-5, f"lens: {cam_data.lens}"
    assert abs(cam_data.shift_x - 0.05) < 1e-5
    assert abs(cam_data.shift_y - (-0.05)) < 1e-5
    assert cam_data.dof.use_dof is True
    assert abs(cam_data.dof.aperture_fstop - 1.8) < 1e-5
    assert abs(cam_data.dof.focus_distance - 5.0) < 1e-5


def test_camera_round_trip_with_no_camera():
    scene = _fresh_scene()
    studio = _new_studio(scene)

    scene.camera = None
    capture_all(scene, studio)

    cam_obj = _camera_obj("stage_test_camera")
    if cam_obj.name not in scene.collection.objects:
        scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    apply_all(scene, studio)

    assert scene.camera is None, f"expected None, got {scene.camera}"


def test_camera_disabled_facet_skips_apply():
    scene = _fresh_scene()
    studio = _new_studio(scene)

    cam_a = _camera_obj("stage_test_camera_a")
    cam_b = _camera_obj("stage_test_camera_b")
    for c in (cam_a, cam_b):
        if c.name not in scene.collection.objects:
            scene.collection.objects.link(c)
    scene.camera = cam_a

    capture_all(scene, studio)

    studio.facet_camera_enabled = False

    scene.camera = cam_b
    apply_all(scene, studio)

    assert scene.camera == cam_b, "disabled facet still applied"


def test_camera_missing_camera_does_not_raise():
    scene = _fresh_scene()
    studio = _new_studio(scene)

    name = "stage_test_camera_temp"
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    cam_data = bpy.data.cameras.new(f"{name}_data")
    cam_obj = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    capture_all(scene, studio)

    # Delete the camera object after capture
    bpy.data.objects.remove(cam_obj, do_unlink=True)

    # Apply should not raise
    apply_all(scene, studio)
