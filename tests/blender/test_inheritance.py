"""Tests for Studio inheritance — v1.0.

Inheritance is a parent_name pointer plus apply-time chain walking.
Disabled facets on the child fall through to the parent because each
facet's apply step respects its enabled flag.
"""

from __future__ import annotations

import bpy

from stage.core.facets import capture_all
from stage.core.inheritance import apply_studio, resolve_parent_chain


def _fresh_scene(name: str = "stage_inheritance_test"):
    if name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[name], do_unlink=True)
    return bpy.data.scenes.new(name)


def _add_studio(scene, name: str, *, parent: str = ""):
    s = scene.stage_data.studios.add()
    s.name = name
    s.uuid = f"inh-{name}"
    s.parent_name = parent
    return s


# --- chain resolution -------------------------------------------------------


def test_chain_no_parent():
    scene = _fresh_scene()
    s = _add_studio(scene, "A")
    assert resolve_parent_chain(scene.stage_data, s) == []


def test_chain_single_parent():
    scene = _fresh_scene()
    _add_studio(scene, "A")
    b = _add_studio(scene, "B", parent="A")
    chain = resolve_parent_chain(scene.stage_data, b)
    assert [s.name for s in chain] == ["A"]


def test_chain_multi_level():
    """A → B → C: resolving C gives [A, B] (root first)."""
    scene = _fresh_scene()
    _add_studio(scene, "A")
    _add_studio(scene, "B", parent="A")
    c = _add_studio(scene, "C", parent="B")
    chain = resolve_parent_chain(scene.stage_data, c)
    assert [s.name for s in chain] == ["A", "B"]


def test_chain_missing_parent_truncated():
    """parent_name pointing to a non-existent Studio truncates the chain."""
    scene = _fresh_scene()
    s = _add_studio(scene, "A", parent="DoesNotExist")
    assert resolve_parent_chain(scene.stage_data, s) == []


def test_chain_cycle_broken():
    """A.parent=B and B.parent=A — cycle stops without hanging."""
    scene = _fresh_scene()
    a = _add_studio(scene, "A", parent="B")
    _add_studio(scene, "B", parent="A")
    chain = resolve_parent_chain(scene.stage_data, a)
    # Walking from A: append B (a's parent). B's parent is A (already seen).
    assert [s.name for s in chain] == ["B"]


def test_chain_capped_at_max_depth():
    """Pathologically long chain is capped at max_depth."""
    scene = _fresh_scene()
    prev = ""
    for i in range(10):
        _add_studio(scene, f"S{i}", parent=prev)
        prev = f"S{i}"
    leaf = scene.stage_data.studios.get("S9")
    chain = resolve_parent_chain(scene.stage_data, leaf, max_depth=3)
    assert len(chain) <= 3


# --- apply with inheritance -------------------------------------------------


def test_inheritance_disabled_facet_falls_through_to_parent():
    """Child with facet_render_enabled=False inherits parent's render settings."""
    scene = _fresh_scene()

    # Parent captures resolution=2560
    parent = _add_studio(scene, "Parent")
    scene.render.resolution_x = 2560
    capture_all(scene, parent)

    # Child captures something different, then disables its render facet
    # so the parent's value should win on apply.
    child = _add_studio(scene, "Child", parent="Parent")
    scene.render.resolution_x = 800
    capture_all(scene, child)
    child.facet_render_enabled = False

    # Mutate scene to confirm apply actually does something
    scene.render.resolution_x = 100

    apply_studio(scene, child)

    assert scene.render.resolution_x == 2560, (
        f"expected parent's 2560, got {scene.render.resolution_x}"
    )


def test_inheritance_enabled_facet_overrides_parent():
    """Child with facet enabled overrides parent's value."""
    scene = _fresh_scene()

    parent = _add_studio(scene, "Parent")
    scene.render.resolution_x = 2560
    capture_all(scene, parent)

    child = _add_studio(scene, "Child", parent="Parent")
    scene.render.resolution_x = 800
    capture_all(scene, child)
    # Both facets enabled — child's captured value wins

    scene.render.resolution_x = 100
    apply_studio(scene, child)

    assert scene.render.resolution_x == 800, (
        f"expected child's 800, got {scene.render.resolution_x}"
    )


def test_inheritance_no_parent_apply_matches_apply_all():
    """A Studio with no parent_name behaves identically to apply_all."""
    scene = _fresh_scene()
    s = _add_studio(scene, "Solo")
    scene.render.resolution_x = 1920
    capture_all(scene, s)

    scene.render.resolution_x = 100
    apply_studio(scene, s)

    assert scene.render.resolution_x == 1920
