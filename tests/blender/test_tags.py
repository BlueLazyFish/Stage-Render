"""Tests for tag-based filtering in the UIList — v1.0."""

from __future__ import annotations

import bpy

from stage.ui.studio_uilist import matches_filter


def _fresh_scene(name: str = "stage_tags_test"):
    if name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[name], do_unlink=True)
    return bpy.data.scenes.new(name)


def _make_studio(scene, name: str, tags: str = ""):
    s = scene.stage_data.studios.add()
    s.name = name
    s.uuid = f"tag-test-{name}"
    s.tags = tags
    return s


# --- matches_filter helper --------------------------------------------------


def test_empty_needle_matches_all():
    scene = _fresh_scene()
    s = _make_studio(scene, "Hero", "")
    assert matches_filter("", s) is True


def test_match_by_name_substring():
    scene = _fresh_scene()
    s = _make_studio(scene, "Hero")
    assert matches_filter("hero", s) is True
    assert matches_filter("HERO", s) is True  # case-insensitive
    assert matches_filter("er", s) is True    # substring
    assert matches_filter("wide", s) is False


def test_match_by_tag_substring():
    scene = _fresh_scene()
    s = _make_studio(scene, "Hero", "wip, client-a")
    assert matches_filter("wip", s) is True
    assert matches_filter("client", s) is True
    assert matches_filter("final", s) is False


def test_match_combines_name_and_tags():
    scene = _fresh_scene()
    name_only = _make_studio(scene, "WipShot", "")
    tag_only = _make_studio(scene, "Detail", "wip")
    neither = _make_studio(scene, "Hero", "final")

    assert matches_filter("wip", name_only) is True
    assert matches_filter("wip", tag_only) is True
    assert matches_filter("wip", neither) is False


def test_match_case_insensitive_on_tags():
    scene = _fresh_scene()
    s = _make_studio(scene, "Hero", "WIP, Client-A")
    assert matches_filter("wip", s) is True
    assert matches_filter("client", s) is True
