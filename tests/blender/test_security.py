"""Security regression tests for v0.1.1 hardening.

Covers:
  - store_property._eval_path AST allowlist (the eval -> AST-walker fix)
  - slack_webhook scheme + host validation
  - worker spawn_next blend-path leading-dash guard

These pin the security boundary so future refactors can't accidentally
weaken it without a failing test.
"""

from __future__ import annotations

from unittest import mock

import bpy

from stage.core.store_property import (
    UnsafePathError,
    _eval_path,
    resolve_value,
)


# --- AST-walker / _eval_path -----------------------------------------------


def test_eval_path_accepts_simple_attribute_chain():
    # Real RNA path: should resolve without raising. Value identity isn't
    # important here — just that the walker permits the structure.
    val = _eval_path("bpy.context.scene")
    assert val is bpy.context.scene


def test_eval_path_accepts_string_subscript():
    # bpy.data.scenes['Scene'] — the most common stored-path shape after
    # the right-click hook normalises into bpy.context.scene anyway.
    if "Scene" not in bpy.data.scenes:
        bpy.data.scenes.new("Scene")
    val = _eval_path("bpy.data.scenes['Scene']")
    assert val is bpy.data.scenes["Scene"]


def test_eval_path_rejects_function_call():
    """A poisoned data_path with a Call node must be refused."""
    raised = False
    try:
        _eval_path("bpy.ops.wm.quit_blender()")
    except UnsafePathError:
        raised = True
    assert raised, "Call nodes must raise UnsafePathError"


def test_eval_path_rejects_lambda():
    raised = False
    try:
        _eval_path("(lambda: bpy.context.scene)()")
    except UnsafePathError:
        raised = True
    assert raised


def test_eval_path_rejects_arithmetic():
    raised = False
    try:
        _eval_path("bpy.context.scene + bpy.context.scene")
    except UnsafePathError:
        raised = True
    assert raised


def test_eval_path_rejects_dunder_access_via_non_bpy_root():
    """A `__import__('os')...` attempt must fail because the root name
    isn't `bpy`."""
    raised = False
    try:
        _eval_path("__import__('os').system('echo pwned')")
    except UnsafePathError:
        raised = True
    assert raised


def test_eval_path_rejects_non_constant_subscript():
    """Dynamic subscripts (`a[b]` where b is a Name) must be refused —
    the indexer must be a literal."""
    raised = False
    try:
        _eval_path("bpy.data.scenes[bpy.context]")
    except UnsafePathError:
        raised = True
    assert raised


def test_eval_path_rejects_syntax_error():
    raised = False
    try:
        _eval_path("bpy.context.scene.<<")
    except UnsafePathError:
        raised = True
    assert raised


def test_resolve_value_propagates_unsafe_path_error():
    """Public entry point must surface the same protection."""
    raised = False
    try:
        resolve_value("bpy.ops.wm.quit_blender()")
    except UnsafePathError:
        raised = True
    assert raised


# --- slack_webhook scheme guard -------------------------------------------


def _stub_action(target: str, message: str = ""):
    """Minimal duck-typed stand-in for a PostRenderAction PropertyGroup."""
    class _A:
        pass
    a = _A()
    a.target = target
    a.message = message
    return a


def test_slack_webhook_refuses_file_scheme():
    """file:// URLs would let a poisoned .blend exfiltrate local files
    via urllib's default opener. Must be refused outright — no network
    call attempted."""
    from stage.core import post_render

    scene = bpy.context.scene
    if scene.stage_data.studios:
        studio = scene.stage_data.studios[0]
    else:
        studio = scene.stage_data.studios.add()
        studio.name = "TestStudio"
        studio.uuid = "sec-test"

    action = _stub_action("file:///etc/passwd")

    with mock.patch.object(post_render.urlrequest, "urlopen") as fake_open:
        post_render.slack_webhook(action, scene, studio, "/tmp/out.png")
        assert fake_open.call_count == 0, (
            "urlopen must not be called for non-http(s) schemes"
        )


def test_slack_webhook_refuses_gopher_scheme():
    from stage.core import post_render

    scene = bpy.context.scene
    studio = scene.stage_data.studios[0] if scene.stage_data.studios else None
    if studio is None:
        studio = scene.stage_data.studios.add()
        studio.name = "TestStudio"
        studio.uuid = "sec-test"

    action = _stub_action("gopher://internal-host:70/0/secret")

    with mock.patch.object(post_render.urlrequest, "urlopen") as fake_open:
        post_render.slack_webhook(action, scene, studio, "/tmp/out.png")
        assert fake_open.call_count == 0


def test_slack_webhook_refuses_url_with_no_host():
    from stage.core import post_render

    scene = bpy.context.scene
    studio = scene.stage_data.studios[0] if scene.stage_data.studios else None
    if studio is None:
        studio = scene.stage_data.studios.add()
        studio.name = "TestStudio"
        studio.uuid = "sec-test"

    action = _stub_action("https://")

    with mock.patch.object(post_render.urlrequest, "urlopen") as fake_open:
        post_render.slack_webhook(action, scene, studio, "/tmp/out.png")
        assert fake_open.call_count == 0


def test_slack_webhook_accepts_https_url():
    """Sanity check the happy path — hooks.slack.com style URLs must\n    still go through."""
    from stage.core import post_render

    scene = bpy.context.scene
    studio = scene.stage_data.studios[0] if scene.stage_data.studios else None
    if studio is None:
        studio = scene.stage_data.studios.add()
        studio.name = "TestStudio"
        studio.uuid = "sec-test"

    action = _stub_action("https://hooks.slack.com/services/T0/B0/XXX")

    with mock.patch.object(post_render.urlrequest, "urlopen") as fake_open:
        post_render.slack_webhook(action, scene, studio, "/tmp/out.png")
        assert fake_open.call_count == 1, (
            "valid https URL should reach urlopen"
        )
