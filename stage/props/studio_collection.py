"""StudioCollection — top-level container attached to Scene.stage_data.

Holds the Studio list, active index (with invariant), groups, and the
in-blend storage format version for migrations.
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    StringProperty,
    IntProperty,
    BoolProperty,
    FloatVectorProperty,
    CollectionProperty,
)

from .studio import Studio


# Bump on every breaking schema change. core/migration.py reads this.
CURRENT_FORMAT_VERSION = 1


class StudioGroup(PropertyGroup):
    """A variant axis containing related Studios (e.g. 'Cameras', 'Lighting Moods')."""

    name: StringProperty(default="Group")

    color: FloatVectorProperty(
        subtype='COLOR', size=4, min=0.0, max=1.0,
        default=(0.5, 0.5, 0.5, 1.0),
    )

    expanded: BoolProperty(default=True)

    # UUIDs of member Studios (comma-separated). Studios live in StudioCollection.studios;
    # groups are a flat lookup, not an alternate storage location.
    studio_uuids: StringProperty(
        description="Comma-separated UUIDs of member Studios",
        default="",
    )


class StudioCollection(PropertyGroup):
    studios: CollectionProperty(type=Studio)
    groups: CollectionProperty(type=StudioGroup)

    active_index: IntProperty(
        name="Active Studio Index",
        default=0,
        description="Invariant: 0 ≤ active_index < len(studios) when non-empty",
    )

    format_version: IntProperty(
        name="Storage Format Version",
        default=CURRENT_FORMAT_VERSION,
        description="In-blend storage schema version — used by core.migration",
    )


def register() -> None:
    bpy.utils.register_class(StudioGroup)
    bpy.utils.register_class(StudioCollection)


def unregister() -> None:
    bpy.utils.unregister_class(StudioCollection)
    bpy.utils.unregister_class(StudioGroup)
