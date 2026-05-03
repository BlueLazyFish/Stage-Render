"""Add / remove Studio Groups."""

import bpy
from bpy.types import Operator
from bpy.props import IntProperty, StringProperty

from ..utils.naming import unique_name


def _data(context):
    return context.scene.stage_data


class STAGE_OT_add_group(Operator):
    bl_idname = "stage.add_group"
    bl_label = "Add Group"
    bl_description = "Create a new Studio Group (variant axis)"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Name", default="Group")

    def execute(self, context):
        data = _data(context)
        group = data.groups.add()
        # Auto-disambiguate so back-to-back clicks produce Group, Group.001,
        # Group.002… (Blender's standard convention).
        existing = [g.name for g in data.groups if g != group]
        group.name = unique_name(self.name or "Group", existing)
        self.report({'INFO'}, f"Added group: {group.name}")
        return {'FINISHED'}


class STAGE_OT_remove_group(Operator):
    bl_idname = "stage.remove_group"
    bl_label = "Remove Group"
    bl_description = (
        "Remove this group. Studios that referenced it become ungrouped"
    )
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()

    def execute(self, context):
        data = _data(context)
        if not (0 <= self.index < len(data.groups)):
            return {'CANCELLED'}
        removed_name = data.groups[self.index].name
        # Detach any Studio that referenced this group so the dropdown
        # doesn't dangle a stale name.
        for s in data.studios:
            if s.group_name == removed_name:
                s.group_name = ""
        data.groups.remove(self.index)
        self.report({'INFO'}, f"Removed group: {removed_name}")
        return {'FINISHED'}


_classes = (STAGE_OT_add_group, STAGE_OT_remove_group)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
