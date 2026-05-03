"""Add / remove Studio Groups."""

import bpy
from bpy.types import Operator
from bpy.props import IntProperty, StringProperty


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
        # Auto-disambiguate the default name so back-to-back clicks don't
        # produce duplicates that prop_search can't tell apart
        base = self.name or "Group"
        existing_names = {g.name for g in data.groups}
        candidate = base
        i = 1
        while candidate in existing_names:
            i += 1
            candidate = f"{base}.{i:03d}"
        group = data.groups.add()
        group.name = candidate
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
