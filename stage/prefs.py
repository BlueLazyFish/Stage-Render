"""Addon preferences — global defaults that propagate down the override chain.

Hierarchy (see ADDON_PLAN.md §5):
    Addon Preferences  →  Project Settings  →  Studio Group  →  Studio
"""

import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty, BoolProperty, EnumProperty


# Module-level default so callers (render ops, tests) can fall back to it
# when the addon hasn't been registered through Blender's extension manager
# (e.g. raw `import stage; stage.register()` from a Python script doesn't
# populate context.preferences.addons).
DEFAULT_OUTPUT_PATTERN = "//{blendname}/{studio}/{frame}.{ext}"


class StagePreferences(AddonPreferences):
    bl_idname = __package__

    # Output
    default_output_pattern: StringProperty(
        name="Default Output Pattern",
        description="Default path template applied to every Studio across every scene unless that Studio sets its own override. Supports {studio}, {frame}, {date_time}, etc.",
        subtype='FILE_PATH',
        default=DEFAULT_OUTPUT_PATTERN,
    )

    library_path: StringProperty(
        name="Preset Library",
        description="Folder where cross-file Studio presets are stored",
        subtype='DIR_PATH',
        default="",
    )

    # Render reliability
    auto_lock_interface_during_render: BoolProperty(
        name="Auto-Lock Interface During Render",
        description="Lock the Blender UI during render. Recommended — prevents crashes and speeds rendering",
        default=True,
    )

    free_persistent_data_after_render: BoolProperty(
        name="Free Persistent Data After Render",
        description="Auto-free Cycles persistent data after queue completes (memory hygiene)",
        default=True,
    )

    viewport_solid_during_render: BoolProperty(
        name="Switch to Solid Viewport During Render",
        description="VRAM saver for heavy scenes",
        default=False,
    )

    # UI
    show_dirty_badge: BoolProperty(
        name="Show Dirty-State Badge",
        default=True,
    )

    enable_pie_menu: BoolProperty(
        name="Enable Studio Pie Menu",
        default=False,
    )

    enable_studio_hotkeys: BoolProperty(
        name="Enable Studio Hotkeys (1-9)",
        default=False,
    )

    # Logging
    log_level: EnumProperty(
        name="Log Level",
        items=[
            ('DEBUG', "Debug", "Verbose diagnostic output"),
            ('INFO', "Info", "General information"),
            ('WARNING', "Warning", "Warnings only"),
            ('ERROR', "Error", "Errors only"),
        ],
        default='INFO',
    )

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        col.label(text="Output", icon='FILE_FOLDER')
        col.prop(self, "default_output_pattern")
        col.prop(self, "library_path")

        col = layout.column(align=True)
        col.label(text="Render", icon='RENDER_STILL')
        col.prop(self, "auto_lock_interface_during_render")
        col.prop(self, "free_persistent_data_after_render")
        col.prop(self, "viewport_solid_during_render")

        col = layout.column(align=True)
        col.label(text="UI", icon='WINDOW')
        col.prop(self, "show_dirty_badge")
        col.prop(self, "enable_pie_menu")
        col.prop(self, "enable_studio_hotkeys")

        col = layout.column(align=True)
        col.label(text="Diagnostics", icon='CONSOLE')
        col.prop(self, "log_level")


def get_prefs(context):
    """Return the addon's AddonPreferences instance, or None if the addon
    isn't registered in Blender's extension manager (e.g. raw script import)."""
    addons = context.preferences.addons
    if StagePreferences.bl_idname in addons:
        return addons[StagePreferences.bl_idname].preferences
    return None


def get_default_output_pattern(context) -> str:
    """Return the user's configured pattern, or the module default if the
    addon isn't fully installed (tests / dev script registration)."""
    prefs = get_prefs(context)
    if prefs is not None:
        return prefs.default_output_pattern
    return DEFAULT_OUTPUT_PATTERN


def register() -> None:
    bpy.utils.register_class(StagePreferences)


def unregister() -> None:
    bpy.utils.unregister_class(StagePreferences)
