"""Studio — atomic snapshot of scene state.

See ADDON_PLAN.md §5 data model for the full schema rationale.
Facet capture/restore lives in stage.core.facets (Phase 1).
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    StringProperty,
    BoolProperty,
    IntProperty,
    FloatVectorProperty,
    CollectionProperty,
)

from .stored_prop import StoredProp


class Studio(PropertyGroup):
    # Identity
    name: StringProperty(name="Name", default="Studio")

    uuid: StringProperty(
        name="UUID",
        description="Stable identifier — never changes once created",
        default="",
    )

    # State
    enabled: BoolProperty(
        name="Enabled",
        description="Include in Render All",
        default=True,
    )

    locked: BoolProperty(
        name="Locked",
        description="Refuse Update operations until unlocked — for client deliverables",
        default=False,
    )

    # Per-Studio facet toggles — choose which facets this Studio captures/applies
    facet_camera_enabled: BoolProperty(name="Capture Camera", default=True)
    facet_world_enabled: BoolProperty(name="Capture World", default=True)
    facet_visibility_enabled: BoolProperty(name="Capture Visibility", default=True)
    facet_render_enabled: BoolProperty(name="Capture Render Settings", default=True)
    facet_output_path_enabled: BoolProperty(name="Capture Output Path", default=True)

    # Display
    color: FloatVectorProperty(
        name="Color",
        subtype='COLOR',
        size=4,
        min=0.0, max=1.0,
        default=(0.5, 0.5, 0.5, 1.0),
    )

    color_label: StringProperty(
        name="Color Label",
        description="Optional meaning for the color (e.g. 'WIP', 'Approved')",
        default="",
    )

    thumbnail_path: StringProperty(
        name="Thumbnail Path",
        subtype='FILE_PATH',
        default="",
    )

    notes: StringProperty(
        name="Notes",
        description="Free-form notes — paste client feedback here",
        default="",
    )

    tags: StringProperty(
        name="Tags",
        description="Comma-separated tags (e.g. 'wip, client-a, final')",
        default="",
    )

    # Inheritance — child stores deltas only; parent supplies the rest
    parent_uuid: StringProperty(
        name="Parent UUID",
        description="Optional parent Studio for inheritance",
        default="",
    )

    # Frame range
    frame_start: IntProperty(name="Frame Start", default=1)
    frame_end: IntProperty(name="Frame End", default=250)
    frame_step: IntProperty(name="Frame Step", default=1, min=1)

    # Output override (empty = inherit from project/prefs)
    output_override: StringProperty(
        name="Output Override",
        description="Per-Studio output path override — empty falls back to inherited",
        default="",
    )

    # Custom-stored RNA paths (right-click → Store in Studio, v1.0)
    custom_paths: CollectionProperty(type=StoredProp)


def register() -> None:
    bpy.utils.register_class(Studio)


def unregister() -> None:
    bpy.utils.unregister_class(Studio)
