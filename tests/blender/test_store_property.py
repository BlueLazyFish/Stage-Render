"""Tests for right-click -> Store Property — v1.0.

The right-click button context can't be cleanly mocked in headless Blender,
so we test the path utilities and CustomPropsFacet directly. Path extraction
from a real button click is exercised by manual smoke-testing in the addon.
"""

from __future__ import annotations

import bpy

from stage.core.store_property import (
    apply_value,
    decode_value,
    detect_type,
    encode_value,
    resolve_value,
    split_parent_and_attr,
)
from stage.core.facets.custom_props import CustomPropsFacet


def _fresh_scene(name: str = "stage_store_test"):
    if name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[name], do_unlink=True)
    return bpy.data.scenes.new(name)


def _new_studio(scene, name: str = "Test"):
    s = scene.stage_data.studios.add()
    s.name = name
    s.uuid = f"store-test-{name}"
    return s


# --- path utilities ---------------------------------------------------------


def test_split_dot_path():
    parent, attr = split_parent_and_attr("bpy.context.scene.render.engine")
    assert parent == "bpy.context.scene.render"
    assert attr == "engine"


def test_split_bracket_path():
    parent, attr = split_parent_and_attr('bpy.data.objects["Cube"]')
    assert parent == "bpy.data.objects"
    assert attr == '"Cube"'


def test_resolve_scene_path():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    scene.render.resolution_x = 1234
    value = resolve_value("bpy.context.scene.render.resolution_x")
    assert value == 1234


def test_apply_value_writes_back():
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    scene.render.resolution_x = 100
    apply_value("bpy.context.scene.render.resolution_x", 4096)
    assert scene.render.resolution_x == 4096


# --- type detection + encode/decode ----------------------------------------


def test_detect_int_bool_float_string():
    assert detect_type(42) == 'INT'
    assert detect_type(True) == 'BOOL'
    assert detect_type(False) == 'BOOL'
    assert detect_type(3.14) == 'FLOAT'
    assert detect_type("hello") == 'STRING'


def test_encode_decode_int():
    s, t = encode_value(42)
    assert (s, t) == ("42", 'INT')
    assert decode_value(s, t) == 42


def test_encode_decode_bool():
    for v in (True, False):
        s, t = encode_value(v)
        assert decode_value(s, t) is v


def test_encode_decode_float():
    s, t = encode_value(3.14)
    assert t == 'FLOAT'
    assert abs(decode_value(s, t) - 3.14) < 1e-9


def test_encode_decode_string():
    s, t = encode_value("foo bar")
    assert (s, t) == ("foo bar", 'STRING')
    assert decode_value(s, t) == "foo bar"


def test_encode_decode_vector():
    s, t = encode_value([1.0, 2.0, 3.0, 4.0])
    assert t == 'COLOR'  # 4-element float vector classified as color
    out = decode_value(s, t)
    assert out == [1.0, 2.0, 3.0, 4.0]


# --- CustomPropsFacet ------------------------------------------------------


def test_custom_props_facet_capture_then_apply():
    """Stored custom prop round-trips: capture, mutate, apply, verify."""
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    studio = _new_studio(scene)

    # Stage a stored entry that targets resolution_x
    scene.render.resolution_x = 2560
    entry = studio.custom_paths.add()
    entry.data_path = "bpy.context.scene.render.resolution_x"
    entry.value_repr = "2560"
    entry.value_type = 'INT'

    # Capture (re-reads current value — currently 2560, no change)
    facet = CustomPropsFacet()
    facet.capture(scene, studio)
    assert studio.custom_paths[0].value_repr == "2560"

    # Mutate
    scene.render.resolution_x = 100

    # Apply
    facet.apply(scene, studio)
    assert scene.render.resolution_x == 2560


def test_custom_props_facet_capture_refreshes_value():
    """Capture refreshes value_repr from the live scene."""
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    studio = _new_studio(scene)

    entry = studio.custom_paths.add()
    entry.data_path = "bpy.context.scene.render.resolution_x"
    entry.value_repr = "100"  # stale value
    entry.value_type = 'INT'

    # Set scene to a new value; capture should pick that up
    scene.render.resolution_x = 4096
    facet = CustomPropsFacet()
    facet.capture(scene, studio)

    assert studio.custom_paths[0].value_repr == "4096"


def test_custom_props_facet_apply_skips_broken_path():
    """A missing/broken stored path logs a warning but doesn't raise."""
    scene = _fresh_scene()
    bpy.context.window.scene = scene
    studio = _new_studio(scene)

    entry = studio.custom_paths.add()
    entry.data_path = "bpy.context.scene.render.does_not_exist"
    entry.value_repr = "1"
    entry.value_type = 'INT'

    facet = CustomPropsFacet()
    # Should not raise
    facet.apply(scene, studio)
