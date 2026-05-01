"""FacetRender — captured Render Settings facet data per Studio.

Stores the render engine ID, common cross-engine settings, and an
engine-specific bag of (rna_path, value) entries populated by the
engine adapters in stage.core.facets.render_settings.

Reuses StoredProp as the per-entry shape — same (data_path, value_repr,
value_type) triple as the right-click → Store mechanism.
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)

from .stored_prop import StoredProp


class FacetRender(PropertyGroup):
    captured: BoolProperty(default=False)

    # Engine identifier — controls which adapter runs on apply.
    # Examples: 'CYCLES', 'BLENDER_EEVEE_NEXT', 'BLENDER_WORKBENCH'.
    engine: StringProperty(default="")

    # Common cross-engine settings (always meaningful regardless of engine)
    resolution_x: IntProperty(default=1920)
    resolution_y: IntProperty(default=1080)
    resolution_percentage: IntProperty(default=100)
    fps: IntProperty(default=24)
    fps_base: FloatProperty(default=1.0)

    # Engine-specific bag — populated by the active engine's adapter.
    settings: CollectionProperty(type=StoredProp)


def register() -> None:
    bpy.utils.register_class(FacetRender)


def unregister() -> None:
    bpy.utils.unregister_class(FacetRender)
