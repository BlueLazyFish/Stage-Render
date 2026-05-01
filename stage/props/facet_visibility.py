"""FacetVisibility — captured visibility state per Studio.

Per Collection (entries built from the scene's collection tree):
    hide_viewport — Collection.hide_viewport (monitor restriction)
    hide_render   — Collection.hide_render (camera restriction)
    exclude       — LayerCollection.exclude (view-layer scoped)

Per Object (entries built from scene.objects):
    hide_viewport — Object.hide_viewport (monitor restriction)
    hide_render   — Object.hide_render (camera restriction)

NOT captured: the view-layer-scoped EYE icon (Object.hide_get()) — this
is the known Blender limitation noted in ADDON_PLAN.md §6. We don't
attempt to store it.
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, CollectionProperty, StringProperty


class CollectionVisEntry(PropertyGroup):
    name: StringProperty()
    hide_viewport: BoolProperty(default=False)
    hide_render: BoolProperty(default=False)
    exclude: BoolProperty(default=False)


class ObjectVisEntry(PropertyGroup):
    name: StringProperty()
    hide_viewport: BoolProperty(default=False)
    hide_render: BoolProperty(default=False)


class FacetVisibility(PropertyGroup):
    captured: BoolProperty(default=False)
    collections: CollectionProperty(type=CollectionVisEntry)
    objects: CollectionProperty(type=ObjectVisEntry)


_classes = (CollectionVisEntry, ObjectVisEntry, FacetVisibility)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
