"""UserTemplate — render-settings preset persisted in addon preferences.

Mirrors the FacetRender shape (engine + resolution + settings bag) so the
core/templates.py helpers can convert between this PropertyGroup and the
dict-form template that apply_template_to_studio() consumes.

Lives in addon prefs (StagePreferences.user_templates) rather than per-blend,
so saved templates persist across files and across Blender upgrades (Blender
migrates userpref.blend forward).
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    StringProperty,
    IntProperty,
    CollectionProperty,
)

from .stored_prop import StoredProp


class UserTemplate(PropertyGroup):
    # Display label shown in the templates menu and the Manage popup
    display_name: StringProperty(name="Name", default="Untitled")

    # Render engine ID, e.g. 'CYCLES', 'BLENDER_EEVEE', 'BLENDER_WORKBENCH'
    engine: StringProperty(default="BLENDER_EEVEE")

    # Common cross-engine settings
    resolution_x: IntProperty(default=1920)
    resolution_y: IntProperty(default=1080)
    resolution_percentage: IntProperty(default=100)

    # Engine-specific (rna_path, value) entries — same shape as
    # FacetRender.settings and Studio.custom_paths
    settings: CollectionProperty(type=StoredProp)


def register() -> None:
    bpy.utils.register_class(UserTemplate)


def unregister() -> None:
    bpy.utils.unregister_class(UserTemplate)
