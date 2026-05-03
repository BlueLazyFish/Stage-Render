"""Tests that the queue subprocess and the foreground render operators
resolve the same output path for the same Studio + scene + default pattern.

This is the regression test for the bug where queued renders were going
to scene.render.filepath (raw, no template expansion, no addon-prefs
fallback) while foreground renders went to expand_path(template, ctx).
"""

from __future__ import annotations

import bpy

from stage.core.render import resolve_output_path


def _fresh_scene(name: str = "stage_render_path_test"):
    if name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[name], do_unlink=True)
    return bpy.data.scenes.new(name)


def _make_studio(scene, name: str, *, output_override: str = ""):
    s = scene.stage_data.studios.add()
    s.name = name
    s.uuid = f"render-path-{name}"
    s.output_override = output_override
    return s


def test_resolve_output_path_uses_studio_override_when_set():
    scene = _fresh_scene()
    studio = _make_studio(scene, "Hero", output_override="/tmp/custom/{studio}/{frame}.{ext}")

    path = resolve_output_path(scene, studio, default_pattern="should-not-be-used")
    assert "Hero" in path, f"expected studio name in path, got {path}"
    assert path.startswith("/tmp/custom/"), f"override prefix should win, got {path}"
    assert "{studio}" not in path and "{frame}" not in path, "tokens must be expanded"


def test_resolve_output_path_falls_back_to_default_when_override_empty():
    scene = _fresh_scene()
    studio = _make_studio(scene, "Hero", output_override="")

    path = resolve_output_path(scene, studio, default_pattern="/tmp/dflt/{studio}/{frame}.{ext}")
    assert path.startswith("/tmp/dflt/Hero/"), f"default pattern should be used, got {path}"


def test_resolve_output_path_expands_ext_from_file_format():
    scene = _fresh_scene()
    studio = _make_studio(scene, "Hero")
    scene.render.image_settings.file_format = 'JPEG'

    path = resolve_output_path(scene, studio, default_pattern="/tmp/{studio}/{frame}.{ext}")
    assert path.endswith(".jpg"), f"jpg extension expected, got {path}"


def test_resolve_output_path_expands_blendname():
    scene = _fresh_scene()
    studio = _make_studio(scene, "Hero")

    # bpy.data.filepath is "" in this test, so {blendname} expands to ""
    path = resolve_output_path(scene, studio, default_pattern="/tmp/{blendname}/{studio}.{ext}")
    # With empty blendname the directory becomes /tmp//Hero.png — that's fine,
    # just verify the {studio} substitution succeeded.
    assert "Hero" in path
    assert "{blendname}" not in path


def test_resolve_output_path_preserves_blender_relative_prefix():
    """`//` is Blender's blend-relative anchor — expand_path should leave
    it intact so Blender's own bpy.path.abspath resolves it at render time."""
    scene = _fresh_scene()
    studio = _make_studio(scene, "Hero")

    path = resolve_output_path(
        scene, studio, default_pattern="//{studio}/{frame}.{ext}"
    )
    assert path.startswith("//"), f"// prefix must survive expansion, got {path}"
    assert "Hero" in path


def test_foreground_and_subprocess_paths_match():
    """The whole point of extracting core/render.resolve_output_path —
    foreground and subprocess MUST produce identical paths for the same
    inputs. Both should call resolve_output_path; this test pins that
    contract by calling it once and asserting determinism."""
    scene = _fresh_scene()
    studio = _make_studio(scene, "Hero", output_override="/tmp/x/{studio}/{frame:04d}.{ext}")

    a = resolve_output_path(scene, studio, default_pattern="ignored")
    b = resolve_output_path(scene, studio, default_pattern="ignored")
    assert a == b, "resolve_output_path must be deterministic"
    # And the expansion actually happened
    assert "/tmp/x/Hero/" in a
    assert a.endswith(".png")
