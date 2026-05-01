"""Unit tests for stage.core.paths.

Pure-Python — does not require Blender. Run with:
    pytest tests/unit

These exercise the path-variable expansion and sanitization logic, which
is the single source of truth for output paths across the addon.
"""

from __future__ import annotations

import datetime

from stage.core.paths import build_default_context, expand_path, sanitize_name


# --- sanitize_name ----------------------------------------------------------


def test_sanitize_name_replaces_slashes():
    assert sanitize_name("foo/bar") == "foo_bar"
    assert sanitize_name("a\\b") == "a_b"


def test_sanitize_name_replaces_other_unsafe():
    assert sanitize_name("a:b*c?d") == "a_b_c_d"
    assert sanitize_name('q"x<y>z|w') == "q_x_y_z_w"


def test_sanitize_name_handles_reserved_windows():
    assert sanitize_name("CON") == "_CON"
    assert sanitize_name("nul") == "_nul"
    assert sanitize_name("COM1") == "_COM1"
    assert sanitize_name("LPT9") == "_LPT9"


def test_sanitize_name_handles_empty_or_dots():
    assert sanitize_name("") == "_"
    assert sanitize_name("...") == "_"
    assert sanitize_name("  ") == "_"


def test_sanitize_name_strips_trailing_dots_and_whitespace():
    assert sanitize_name("foo.") == "foo"
    assert sanitize_name(" Hero Shot ") == "Hero Shot"


# --- expand_path ------------------------------------------------------------


def test_expand_path_basic():
    assert expand_path("{a}/{b}", {"a": "x", "b": "y"}) == "x/y"


def test_expand_path_unknown_var_left_literal():
    assert expand_path("{a}/{b}", {"a": "x"}) == "x/{b}"


def test_expand_path_format_spec():
    """{frame:04d} produces zero-padded output."""
    assert expand_path("frame_{frame:04d}", {"frame": 5}) == "frame_0005"


def test_expand_path_sanitizes_string_values():
    """String values pass through sanitize_name to keep paths safe."""
    assert expand_path("{studio}/x", {"studio": "Hero/Shot"}) == "Hero_Shot/x"


def test_expand_path_passes_int_values_through():
    assert expand_path("{frame}", {"frame": 42}) == "42"


def test_expand_path_empty_template():
    assert expand_path("", {"a": "x"}) == ""


def test_expand_path_no_vars():
    assert expand_path("static/path/here", {"a": "x"}) == "static/path/here"


def test_expand_path_unknown_var_with_format_spec_left_literal():
    """Unknown var with a format spec also stays literal."""
    assert expand_path("{frame:04d}", {}) == "{frame:04d}"


# --- build_default_context --------------------------------------------------


def test_build_default_context_includes_required_vars():
    ctx = build_default_context(
        studio_name="Test",
        blend_path="/foo/scene.blend",
        frame=42,
    )
    assert ctx["studio"] == "Test"
    assert ctx["blendname"] == "scene"
    assert ctx["blend_filename"] == "scene"
    assert ctx["blend_full_path"] == "/foo/scene.blend"
    assert ctx["frame"] == 42
    # Date components always present
    for k in ("year", "month", "day", "hour", "minute", "second", "date_time"):
        assert k in ctx, f"missing {k!r} in context"


def test_build_default_context_freeze_time():
    """Two builds with the same frozen_now share a timestamp.

    This is the 'Freeze time' trick from the plan — batch renders share
    one {date_time} so outputs group as a coherent batch.
    """
    frozen = datetime.datetime(2026, 5, 1, 12, 30, 45)
    a = build_default_context(studio_name="A", frozen_now=frozen)
    b = build_default_context(studio_name="B", frozen_now=frozen)
    assert a["date_time"] == b["date_time"] == "2026-05-01T12-30-45"
    assert a["year"] == "2026"
    assert a["month"] == "05"
    assert a["day"] == "01"


def test_build_default_context_render_type():
    ctx = build_default_context(render_type="animation")
    assert ctx["context_render_type"] == "animation"


def test_build_default_context_empty_blend_path():
    ctx = build_default_context()
    assert ctx["blendname"] == ""
    assert ctx["blend_full_path"] == ""
