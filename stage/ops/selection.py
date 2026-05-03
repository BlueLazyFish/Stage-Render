"""Multi-selection operators (select all / none / invert / by group / by tag).

The selection state lives on Studio.selected. Bulk-edit operators in
ops/bulk_edit.py act on every Studio with selected=True.
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty


def _data(context):
    return context.scene.stage_data


class STAGE_OT_select_all(Operator):
    bl_idname = "stage.select_all"
    bl_label = "Select All"
    bl_description = "Tick the multi-select checkbox on every Studio"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        data = _data(context)
        for s in data.studios:
            s.selected = True
        return {'FINISHED'}


class STAGE_OT_select_none(Operator):
    bl_idname = "stage.select_none"
    bl_label = "Select None"
    bl_description = "Clear the multi-select checkbox on every Studio"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        data = _data(context)
        for s in data.studios:
            s.selected = False
        return {'FINISHED'}


class STAGE_OT_select_invert(Operator):
    bl_idname = "stage.select_invert"
    bl_label = "Invert Selection"
    bl_description = "Flip the multi-select state on every Studio"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        data = _data(context)
        for s in data.studios:
            s.selected = not s.selected
        return {'FINISHED'}


class STAGE_OT_select_by_group(Operator):
    bl_idname = "stage.select_by_group"
    bl_label = "Select by Group"
    bl_description = "Tick every Studio whose group_name matches"
    bl_options = {'REGISTER', 'UNDO'}

    group_name: StringProperty(name="Group", default="")

    def execute(self, context):
        data = _data(context)
        target = self.group_name
        n = 0
        for s in data.studios:
            if s.group_name == target:
                s.selected = True
                n += 1
        self.report({'INFO'}, f"Selected {n} Studio(s) in group '{target or '(ungrouped)'}'")
        return {'FINISHED'}


class STAGE_OT_select_by_tag(Operator):
    bl_idname = "stage.select_by_tag"
    bl_label = "Select by Tag"
    bl_description = "Tick every Studio whose tags contain the given substring (case-insensitive)"
    bl_options = {'REGISTER', 'UNDO'}

    tag: StringProperty(name="Tag", default="")

    def execute(self, context):
        data = _data(context)
        needle = self.tag.lower().strip()
        if not needle:
            self.report({'WARNING'}, "Empty tag — no selection change")
            return {'CANCELLED'}
        n = 0
        for s in data.studios:
            if needle in s.tags.lower():
                s.selected = True
                n += 1
        self.report({'INFO'}, f"Selected {n} Studio(s) with tag matching '{self.tag}'")
        return {'FINISHED'}


_classes = (
    STAGE_OT_select_all,
    STAGE_OT_select_none,
    STAGE_OT_select_invert,
    STAGE_OT_select_by_group,
    STAGE_OT_select_by_tag,
)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
