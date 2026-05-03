"""Stored-Properties Lister panel.

Dockable side-panel section that lists every stored custom property
across every Studio in the scene. Filter input matches Studio name,
data_path, or value (case-insensitive substring).

Sits under the main Stage panel, default-collapsed so it doesn't
clutter the panel for users who haven't stored anything yet.

For v1.0 the Lister covers custom_paths (right-click → Store) only.
Facet-level captured data (camera, world, render-settings) lives in
the structured PropertyGroups and is meaningful only via apply, so
listing it is less useful. v1.x can extend if a use case emerges.
"""

import bpy
from bpy.types import Panel
from bpy.props import StringProperty


_FILTER_PROP = "stage_lister_filter"


def matches_lister_filter(
    needle: str, studio_name: str, data_path: str, value_repr: str,
) -> bool:
    """Case-insensitive substring match against Studio name / path / value."""
    if not needle:
        return True
    needle_lower = needle.lower()
    return (
        needle_lower in studio_name.lower()
        or needle_lower in data_path.lower()
        or needle_lower in value_repr.lower()
    )


def _iter_stored_entries(scene_data):
    """Yield (studio, entry) tuples for every custom_path on every Studio."""
    for studio in scene_data.studios:
        for entry in studio.custom_paths:
            yield studio, entry


class STAGE_PT_lister(Panel):
    bl_idname = "STAGE_PT_lister"
    bl_label = "Stored Properties"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Stage"
    bl_options = {'DEFAULT_CLOSED'}
    # Bottom of the stack — it's a global-search panel, not in the daily
    # workflow flow (active Studio → queue → bulk → groups).
    bl_order = 5

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        data = context.scene.stage_data

        layout.prop(wm, _FILTER_PROP, text="", icon='VIEWZOOM')

        needle = getattr(wm, _FILTER_PROP, "")

        any_shown = False
        total = 0
        for studio, entry in _iter_stored_entries(data):
            total += 1
            if not matches_lister_filter(needle, studio.name, entry.data_path, entry.value_repr):
                continue
            any_shown = True
            row = layout.row(align=True)
            row.label(text=f"[{studio.name}]")
            row.label(text=entry.data_path)
            row.label(text=str(entry.value_repr))

        if total == 0:
            layout.label(text="No stored properties yet.", icon='INFO')
            layout.label(text="Right-click any property → Store in Stage.")
        elif not any_shown:
            layout.label(text=f"No matches in {total} stored entries.", icon='INFO')


def register() -> None:
    setattr(
        bpy.types.WindowManager,
        _FILTER_PROP,
        StringProperty(
            name="Filter",
            description="Filter stored properties by Studio name, data path, or value",
            default="",
        ),
    )
    bpy.utils.register_class(STAGE_PT_lister)


def unregister() -> None:
    bpy.utils.unregister_class(STAGE_PT_lister)
    if hasattr(bpy.types.WindowManager, _FILTER_PROP):
        delattr(bpy.types.WindowManager, _FILTER_PROP)
