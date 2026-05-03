"""Tests for the Stored-Properties Lister filter — v1.0."""

from __future__ import annotations

import bpy

from stage.ui.lister import matches_lister_filter, STAGE_PT_lister


def test_empty_needle_matches_all():
    assert matches_lister_filter("", "Hero", "bpy.context.scene.x", "1") is True


def test_match_studio_name():
    assert matches_lister_filter("hero", "Hero", "bpy.context.scene.x", "1") is True
    assert matches_lister_filter("hero", "Wide", "bpy.context.scene.x", "1") is False


def test_match_data_path():
    assert matches_lister_filter(
        "samples", "Hero", "bpy.context.scene.cycles.samples", "256"
    ) is True
    assert matches_lister_filter(
        "samples", "Hero", "bpy.context.scene.render.engine", "CYCLES"
    ) is False


def test_match_value():
    assert matches_lister_filter(
        "256", "Hero", "bpy.context.scene.cycles.samples", "256"
    ) is True
    assert matches_lister_filter(
        "1024", "Hero", "bpy.context.scene.cycles.samples", "256"
    ) is False


def test_case_insensitive():
    assert matches_lister_filter("HERO", "hero", "x", "y") is True
    assert matches_lister_filter("hero", "HERO", "x", "y") is True
    assert matches_lister_filter("CYCLES", "Hero", "x", "cycles") is True


def test_panel_class_registered():
    """Sanity: the Lister panel class is registered with the right metadata."""
    cls = STAGE_PT_lister
    assert cls.bl_idname == "STAGE_PT_lister"
    assert cls.bl_category == "Stage"
    assert 'DEFAULT_CLOSED' in cls.bl_options


def test_window_manager_filter_prop_exists():
    """Filter property is attached to WindowManager after register."""
    assert hasattr(bpy.types.WindowManager, "stage_lister_filter")
