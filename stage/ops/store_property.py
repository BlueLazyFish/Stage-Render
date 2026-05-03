"""Right-click -> Store Property operator + context-menu hook.

Adds a "Store in Stage" entry to Blender's button context menu (the menu
that appears when you right-click a property in any panel). Selecting it
captures the property's current value into the active Studio's
custom_paths CollectionProperty. Right-clicking an already-stored
property shows "Remove from Stage" instead.
"""

import bpy
from bpy.types import Operator
from bpy.props import EnumProperty

from ..core.store_property import (
    apply_value,
    encode_value,
    get_button_data_path,
    resolve_value,
)
from ..utils.logger import get_logger


_log = get_logger()


def _active_studio(context):
    data = getattr(context.scene, "stage_data", None)
    if data is None:
        return None
    if not (0 <= data.active_index < len(data.studios)):
        return None
    return data.studios[data.active_index]


def _is_stored(studio, data_path: str) -> bool:
    return any(p.data_path == data_path for p in studio.custom_paths)


class STAGE_OT_toggle_store_property(Operator):
    bl_idname = "stage.toggle_store_property"
    bl_label = "Toggle Store Property"
    bl_description = "Add or remove the right-clicked property from the active Studio's stored properties"
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(
        items=(
            ('ADD', "Add", "Store the property"),
            ('REMOVE', "Remove", "Stop storing the property"),
        ),
        default='ADD',
    )

    @classmethod
    def description(cls, context, properties):
        if properties.mode == 'ADD':
            return "Capture the current value and store it as part of the active Studio"
        return "Remove this property from the active Studio's stored list"

    def execute(self, context):
        data_path = get_button_data_path(context)
        if data_path is None:
            self.report({'ERROR'}, "Could not determine the property's data path")
            return {'CANCELLED'}

        studio = _active_studio(context)
        if studio is None:
            self.report({'ERROR'}, "No active Studio")
            return {'CANCELLED'}

        if self.mode == 'ADD':
            if _is_stored(studio, data_path):
                return {'CANCELLED'}  # already stored; no-op
            try:
                value = resolve_value(data_path)
            except Exception as e:
                self.report({'ERROR'}, f"Could not read property: {e}")
                return {'CANCELLED'}
            value_repr, value_type = encode_value(value)
            entry = studio.custom_paths.add()
            entry.data_path = data_path
            entry.value_repr = value_repr
            entry.value_type = value_type
            self.report({'INFO'}, f"Stored {data_path} on {studio.name}")
            _log.info("Stored %s on %s", data_path, studio.name)
            return {'FINISHED'}

        # REMOVE
        for i, entry in enumerate(studio.custom_paths):
            if entry.data_path == data_path:
                studio.custom_paths.remove(i)
                self.report({'INFO'}, f"Removed {data_path} from {studio.name}")
                return {'FINISHED'}
        return {'CANCELLED'}


def _draw_context_menu_entry(self, context):
    """Append 'Store in Stage' / 'Remove from Stage' to the property right-click menu."""
    data_path = get_button_data_path(context)
    if data_path is None:
        return
    studio = _active_studio(context)
    if studio is None:
        return

    stored = _is_stored(studio, data_path)
    self.layout.separator()
    op = self.layout.operator(
        STAGE_OT_toggle_store_property.bl_idname,
        text="Remove from Stage" if stored else "Store in Stage",
        icon='X' if stored else 'CHECKMARK',
    )
    op.mode = 'REMOVE' if stored else 'ADD'


_classes = (STAGE_OT_toggle_store_property,)


_DRAW_FUNC_NAME = "_draw_context_menu_entry"


def _purge_stale_draw_funcs() -> None:
    """Remove any leftover ``_draw_context_menu_entry`` references from
    prior addon reloads.

    Module reloads (dev workflow, hot-reload addons) re-import this file,
    which produces a *new* function object — leaving the previously-appended
    ones orphaned in ``UI_MT_button_context_menu``'s draw list. unregister()
    can only remove the current module's reference, so without this purge
    the right-click menu would show "Store in Stage" once per reload.
    """
    menu = bpy.types.UI_MT_button_context_menu
    draw_funcs = getattr(menu, "_dyn_ui_initialize", lambda: [])()
    for func in list(draw_funcs):
        if getattr(func, "__name__", "") == _DRAW_FUNC_NAME:
            try:
                menu.remove(func)
            except ValueError:
                pass


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)
    _purge_stale_draw_funcs()
    bpy.types.UI_MT_button_context_menu.append(_draw_context_menu_entry)


def unregister() -> None:
    _purge_stale_draw_funcs()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
