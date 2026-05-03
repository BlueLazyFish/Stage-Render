"""Bulk-edit operators — apply a single field change to every selected Studio.

Operators here all share the same shape:
1. Iterate Studios with selected=True (skipping locked ones).
2. Write the requested field.
3. Report how many were touched.

Each operator exposes its target value as an Operator property so the
draw() popup gives the user a chance to preview before clicking OK.
Blender's undo stack handles rollback if the result isn't what they wanted.
"""

import bpy
from bpy.types import Operator
from bpy.props import (
    StringProperty,
    BoolProperty,
    FloatVectorProperty,
    EnumProperty,
)


def _data(context):
    return context.scene.stage_data


def _selected_unlocked(data):
    """Yield (index, studio) pairs the bulk op should actually touch."""
    for i, s in enumerate(data.studios):
        if s.selected and not s.locked:
            yield i, s


def _selection_count(data) -> tuple[int, int]:
    """Return (selected_count, locked_skipped_count)."""
    sel = sum(1 for s in data.studios if s.selected)
    locked = sum(1 for s in data.studios if s.selected and s.locked)
    return sel, locked


# --- group / parent --------------------------------------------------------


class STAGE_OT_bulk_set_group(Operator):
    bl_idname = "stage.bulk_set_group"
    bl_label = "Bulk: Set Group"
    bl_description = "Assign every selected unlocked Studio to a group (empty = ungroup)"
    bl_options = {'REGISTER', 'UNDO'}

    group_name: StringProperty(name="Group", default="")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        data = _data(context)
        sel, locked = _selection_count(data)
        self.layout.label(text=f"{sel - locked} Studio(s) will change ({locked} locked, skipped)")
        self.layout.prop_search(self, "group_name", data, "groups", text="Group")

    def execute(self, context):
        data = _data(context)
        n = 0
        for _, s in _selected_unlocked(data):
            s.group_name = self.group_name
            n += 1
        self.report({'INFO'}, f"Bulk: set group on {n} Studio(s)")
        return {'FINISHED'}


class STAGE_OT_bulk_set_parent(Operator):
    bl_idname = "stage.bulk_set_parent"
    bl_label = "Bulk: Set Parent"
    bl_description = "Assign a parent Studio to every selected unlocked Studio (empty = unparent)"
    bl_options = {'REGISTER', 'UNDO'}

    parent_name: StringProperty(name="Parent", default="")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        data = _data(context)
        sel, locked = _selection_count(data)
        self.layout.label(text=f"{sel - locked} Studio(s) will change ({locked} locked, skipped)")
        self.layout.prop_search(self, "parent_name", data, "studios", text="Parent")

    def execute(self, context):
        data = _data(context)
        n = 0
        skipped_self = 0
        for _, s in _selected_unlocked(data):
            # Don't let a Studio become its own parent — that would create
            # a one-step cycle that resolve_parent_chain would have to
            # eat. Cheap to filter here.
            if s.name == self.parent_name:
                skipped_self += 1
                continue
            s.parent_name = self.parent_name
            n += 1
        msg = f"Bulk: set parent on {n} Studio(s)"
        if skipped_self:
            msg += f" ({skipped_self} skipped — would have parented to self)"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


# --- color / lock ----------------------------------------------------------


class STAGE_OT_bulk_set_color(Operator):
    bl_idname = "stage.bulk_set_color"
    bl_label = "Bulk: Set Color"
    bl_description = "Set the color swatch on every selected unlocked Studio"
    bl_options = {'REGISTER', 'UNDO'}

    color: FloatVectorProperty(
        name="Color", subtype='COLOR', size=4,
        min=0.0, max=1.0, default=(0.5, 0.5, 0.5, 1.0),
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        data = _data(context)
        sel, locked = _selection_count(data)
        self.layout.label(text=f"{sel - locked} Studio(s) will change ({locked} locked, skipped)")
        self.layout.prop(self, "color", text="")

    def execute(self, context):
        data = _data(context)
        n = 0
        for _, s in _selected_unlocked(data):
            s.color = self.color
            n += 1
        self.report({'INFO'}, f"Bulk: set color on {n} Studio(s)")
        return {'FINISHED'}


class STAGE_OT_bulk_set_locked(Operator):
    bl_idname = "stage.bulk_set_locked"
    bl_label = "Bulk: Set Lock State"
    bl_description = "Lock or unlock every selected Studio (this op ignores its own 'skip locked' rule)"
    bl_options = {'REGISTER', 'UNDO'}

    locked: BoolProperty(name="Locked", default=True)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        data = _data(context)
        sel = sum(1 for s in data.studios if s.selected)
        self.layout.label(text=f"{sel} selected Studio(s) will be {'locked' if self.locked else 'unlocked'}")
        self.layout.prop(self, "locked")

    def execute(self, context):
        data = _data(context)
        n = 0
        # Lock op intentionally bypasses _selected_unlocked — otherwise
        # you could never bulk-unlock a batch of locked deliverables.
        for s in data.studios:
            if s.selected:
                s.locked = self.locked
                n += 1
        self.report({'INFO'}, f"Bulk: {'locked' if self.locked else 'unlocked'} {n} Studio(s)")
        return {'FINISHED'}


# --- tags ------------------------------------------------------------------


class STAGE_OT_bulk_add_tag(Operator):
    bl_idname = "stage.bulk_add_tag"
    bl_label = "Bulk: Add Tag"
    bl_description = "Append a tag to the comma-separated tags field on every selected unlocked Studio"
    bl_options = {'REGISTER', 'UNDO'}

    tag: StringProperty(name="Tag", default="")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        data = _data(context)
        sel, locked = _selection_count(data)
        self.layout.label(text=f"{sel - locked} Studio(s) will change ({locked} locked, skipped)")
        self.layout.prop(self, "tag")

    def execute(self, context):
        data = _data(context)
        new_tag = self.tag.strip()
        if not new_tag:
            self.report({'WARNING'}, "Empty tag — nothing added")
            return {'CANCELLED'}
        n = 0
        for _, s in _selected_unlocked(data):
            existing = [t.strip() for t in s.tags.split(",") if t.strip()]
            if new_tag in existing:
                continue
            existing.append(new_tag)
            s.tags = ", ".join(existing)
            n += 1
        self.report({'INFO'}, f"Bulk: added '{new_tag}' tag to {n} Studio(s)")
        return {'FINISHED'}


class STAGE_OT_bulk_remove_tag(Operator):
    bl_idname = "stage.bulk_remove_tag"
    bl_label = "Bulk: Remove Tag"
    bl_description = "Strip a tag from the comma-separated tags field on every selected unlocked Studio"
    bl_options = {'REGISTER', 'UNDO'}

    tag: StringProperty(name="Tag", default="")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        data = _data(context)
        sel, locked = _selection_count(data)
        self.layout.label(text=f"{sel - locked} Studio(s) will change ({locked} locked, skipped)")
        self.layout.prop(self, "tag")

    def execute(self, context):
        data = _data(context)
        target = self.tag.strip()
        if not target:
            self.report({'WARNING'}, "Empty tag — nothing removed")
            return {'CANCELLED'}
        n = 0
        for _, s in _selected_unlocked(data):
            existing = [t.strip() for t in s.tags.split(",") if t.strip()]
            if target not in existing:
                continue
            existing = [t for t in existing if t != target]
            s.tags = ", ".join(existing)
            n += 1
        self.report({'INFO'}, f"Bulk: removed '{target}' tag from {n} Studio(s)")
        return {'FINISHED'}


# --- output / facet toggles ------------------------------------------------


class STAGE_OT_bulk_set_output(Operator):
    bl_idname = "stage.bulk_set_output"
    bl_label = "Bulk: Set Output Path"
    bl_description = "Set the per-Studio output override on every selected unlocked Studio (empty = inherit)"
    bl_options = {'REGISTER', 'UNDO'}

    output_override: StringProperty(
        name="Output Path", subtype='FILE_PATH', default="",
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        data = _data(context)
        sel, locked = _selection_count(data)
        self.layout.label(text=f"{sel - locked} Studio(s) will change ({locked} locked, skipped)")
        col = self.layout.column(align=True)
        col.label(text="Output Override:")
        col.prop(self, "output_override", text="")

    def execute(self, context):
        data = _data(context)
        n = 0
        for _, s in _selected_unlocked(data):
            s.output_override = self.output_override
            n += 1
        self.report({'INFO'}, f"Bulk: set output override on {n} Studio(s)")
        return {'FINISHED'}


_FACET_ITEMS = (
    ('camera', "Camera", "Capture Camera"),
    ('world', "World", "Capture World"),
    ('visibility', "Visibility", "Capture Visibility"),
    ('render', "Render Settings", "Capture Render Settings"),
    ('output_path', "Output Path", "Capture Output Path"),
)


class STAGE_OT_bulk_set_facet(Operator):
    bl_idname = "stage.bulk_set_facet"
    bl_label = "Bulk: Toggle Facet"
    bl_description = "Enable or disable a single facet on every selected unlocked Studio"
    bl_options = {'REGISTER', 'UNDO'}

    facet: EnumProperty(
        name="Facet",
        items=[(k, label, desc) for k, label, desc in _FACET_ITEMS],
        default='camera',
    )
    enabled: BoolProperty(name="Enabled", default=True)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        data = _data(context)
        sel, locked = _selection_count(data)
        self.layout.label(text=f"{sel - locked} Studio(s) will change ({locked} locked, skipped)")
        self.layout.prop(self, "facet")
        self.layout.prop(self, "enabled")

    def execute(self, context):
        data = _data(context)
        attr = f"facet_{self.facet}_enabled"
        n = 0
        for _, s in _selected_unlocked(data):
            setattr(s, attr, self.enabled)
            n += 1
        word = "enabled" if self.enabled else "disabled"
        self.report({'INFO'}, f"Bulk: {word} '{self.facet}' facet on {n} Studio(s)")
        return {'FINISHED'}


_classes = (
    STAGE_OT_bulk_set_group,
    STAGE_OT_bulk_set_parent,
    STAGE_OT_bulk_set_color,
    STAGE_OT_bulk_set_locked,
    STAGE_OT_bulk_add_tag,
    STAGE_OT_bulk_remove_tag,
    STAGE_OT_bulk_set_output,
    STAGE_OT_bulk_set_facet,
)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
