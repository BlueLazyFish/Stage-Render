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
    PointerProperty,
    CollectionProperty,
)

from .stored_prop import StoredProp
from .facet_world import FacetWorld
from .facet_camera import FacetCamera
from .facet_visibility import FacetVisibility
from .facet_render import FacetRender
from .post_render_action import PostRenderAction


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

    # Multi-selection — orthogonal to active_index. The UIList shows a
    # checkbox column; bulk-edit operators act on every Studio with
    # selected=True. Locked Studios are still selectable but bulk ops skip
    # them so locked deliverables can't be touched accidentally.
    selected: BoolProperty(
        name="Selected",
        description="Include in bulk-edit operations",
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
        description=(
            "Comma-separated tags (e.g. 'wip, client-a, final'). "
            "Use the filter funnel at the bottom of the Studio list to "
            "filter by tag — substring matches name, tags, and group."
        ),
        default="",
    )

    # Group membership — one Studio belongs to at most one group. The group's
    # metadata (color, etc.) lives on StudioGroup in StudioCollection.groups;
    # this string is the name lookup. Empty = ungrouped.
    group_name: StringProperty(
        name="Group",
        description="Optional group / variant axis this Studio belongs to",
        default="",
    )

    # Inheritance — child stores deltas only; parent supplies the rest.
    # Stored by name (not UUID) so the parent picker can use prop_search
    # directly. Tradeoff: rename a parent and child links break; we accept
    # this for v1.0 simplicity. UUID-based linking can come in v1.x if
    # rename-resilience becomes a real problem.
    parent_name: StringProperty(
        name="Parent",
        description="Optional parent Studio. The parent's facets apply first; this Studio's enabled facets override",
        default="",
    )

    # Frame range
    frame_start: IntProperty(name="Frame Start", default=1)
    frame_end: IntProperty(name="Frame End", default=250)
    frame_step: IntProperty(name="Frame Step", default=1, min=1)

    # Output override (empty = inherit from project/prefs)
    output_override: StringProperty(
        name="Output Override",
        description="Per-Studio output path override — empty falls back to the addon-prefs default. Supports {studio}, {frame}, {date_time}, etc.",
        subtype='FILE_PATH',
        default="",
    )

    # Per-facet captured data (one PropertyGroup per facet needing structured storage)
    facet_world: PointerProperty(type=FacetWorld)
    facet_camera: PointerProperty(type=FacetCamera)
    facet_visibility: PointerProperty(type=FacetVisibility)
    facet_render: PointerProperty(type=FacetRender)

    # Custom-stored RNA paths (right-click → Store in Studio, v1.0)
    custom_paths: CollectionProperty(type=StoredProp)

    # Post-render actions — execute in declared order after each render
    post_render_actions: CollectionProperty(type=PostRenderAction)


def register() -> None:
    bpy.utils.register_class(Studio)


def unregister() -> None:
    bpy.utils.unregister_class(Studio)
