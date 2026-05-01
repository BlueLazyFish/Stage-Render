"""Visibility facet — captures collection and object visibility flags.

Walks the scene's collection tree (skipping the master scene collection)
and object list. Captures Collection.hide_viewport / hide_render plus
LayerCollection.exclude in the first view layer, and Object.hide_viewport /
hide_render.

The view-layer-scoped EYE icon (Object.hide_get()) is the known Blender
limitation we surface honestly to users; we don't capture it.

Multi-view-layer support is v1.x — Phase 1 captures from view_layers[0]
only.
"""

from __future__ import annotations

import bpy

from ...utils.logger import get_logger
from . import register_facet


_log = get_logger()


def _walk_collections(coll, seen, callback) -> None:
    """Recursively walk a Collection tree. Calls callback(coll) once per unique."""
    if coll.name in seen:
        return
    seen.add(coll.name)
    callback(coll)
    for child in coll.children:
        _walk_collections(child, seen, callback)


def _build_layer_collection_lookup(layer_coll, lookup: dict) -> None:
    """Map collection name → its LayerCollection in this view layer."""
    lookup[layer_coll.collection.name] = layer_coll
    for child in layer_coll.children:
        _build_layer_collection_lookup(child, lookup)


def _first_view_layer(scene):
    return scene.view_layers[0] if scene.view_layers else None


class VisibilityFacet:
    facet_id = "visibility"

    def is_enabled(self, studio) -> bool:
        return studio.facet_visibility_enabled

    def capture(self, scene, studio) -> None:
        f = studio.facet_visibility
        f.captured = True
        f.collections.clear()
        f.objects.clear()

        # Build a lookup so we can read LayerCollection.exclude per Collection.name
        view_layer = _first_view_layer(scene)
        layer_coll_lookup: dict = {}
        if view_layer is not None:
            _build_layer_collection_lookup(view_layer.layer_collection, layer_coll_lookup)

        # Walk the scene's collection tree (children of master only — master itself is skipped)
        seen: set = set()

        def add_collection(coll):
            entry = f.collections.add()
            entry.name = coll.name
            entry.hide_viewport = coll.hide_viewport
            entry.hide_render = coll.hide_render
            lc = layer_coll_lookup.get(coll.name)
            entry.exclude = lc.exclude if lc is not None else False

        for child in scene.collection.children:
            _walk_collections(child, seen, add_collection)

        # Walk objects in the scene
        for obj in scene.objects:
            entry = f.objects.add()
            entry.name = obj.name
            entry.hide_viewport = obj.hide_viewport
            entry.hide_render = obj.hide_render

    def apply(self, scene, studio) -> None:
        f = studio.facet_visibility
        if not f.captured:
            return

        view_layer = _first_view_layer(scene)
        layer_coll_lookup: dict = {}
        if view_layer is not None:
            _build_layer_collection_lookup(view_layer.layer_collection, layer_coll_lookup)

        for entry in f.collections:
            coll = bpy.data.collections.get(entry.name)
            if coll is None:
                _log.warning(
                    "Collection %r not found; skipping its visibility apply",
                    entry.name,
                )
            else:
                coll.hide_viewport = entry.hide_viewport
                coll.hide_render = entry.hide_render

            lc = layer_coll_lookup.get(entry.name)
            if lc is not None:
                lc.exclude = entry.exclude

        for entry in f.objects:
            obj = bpy.data.objects.get(entry.name)
            if obj is None:
                _log.warning(
                    "Object %r not found; skipping its visibility apply",
                    entry.name,
                )
                continue
            obj.hide_viewport = entry.hide_viewport
            obj.hide_render = entry.hide_render


register_facet(VisibilityFacet())
