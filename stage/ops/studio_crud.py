"""Studio CRUD operators — add, remove, duplicate, move.

The Active Studio invariant is enforced here: exactly one Studio is active
at all times when the list is non-empty; deleting the last is refused.
"""

import uuid

import bpy
from bpy.types import Operator
from bpy.props import StringProperty


class STAGE_OT_studio_add(Operator):
    bl_idname = "stage.studio_add"
    bl_label = "Add Studio"
    bl_description = "Create a new Studio capturing the current scene state"
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Name", default="Studio")

    def execute(self, context):
        from ..core.facets import capture_all
        data = context.scene.stage_data
        new_studio = data.studios.add()
        new_studio.name = self.name or "Studio"
        new_studio.uuid = str(uuid.uuid4())
        data.active_index = len(data.studios) - 1
        capture_all(context.scene, new_studio)
        self.report({'INFO'}, f"Added Studio: {new_studio.name}")
        return {'FINISHED'}


class STAGE_OT_studio_remove(Operator):
    bl_idname = "stage.studio_remove"
    bl_label = "Remove Studio"
    bl_description = "Remove the active Studio"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Active Studio invariant: keep at least one
        data = context.scene.stage_data
        return len(data.studios) > 1

    def execute(self, context):
        data = context.scene.stage_data
        idx = data.active_index
        if not (0 <= idx < len(data.studios)):
            return {'CANCELLED'}
        if data.studios[idx].locked:
            self.report({'WARNING'}, "Studio is locked — unlock before removing")
            return {'CANCELLED'}
        removed_name = data.studios[idx].name
        data.studios.remove(idx)
        # Re-establish invariant: active points at next or last
        data.active_index = min(idx, len(data.studios) - 1)
        self.report({'INFO'}, f"Removed Studio: {removed_name}")
        return {'FINISHED'}


class STAGE_OT_studio_duplicate(Operator):
    bl_idname = "stage.studio_duplicate"
    bl_label = "Duplicate Studio"
    bl_description = "Duplicate the active Studio"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        data = context.scene.stage_data
        return len(data.studios) > 0

    def execute(self, context):
        data = context.scene.stage_data
        src_idx = data.active_index
        if not (0 <= src_idx < len(data.studios)):
            return {'CANCELLED'}
        src = data.studios[src_idx]
        new = data.studios.add()
        # Scalar copy. Deep facet copy lands in Phase 1 alongside facet capture.
        new.name = f"{src.name} Copy"
        new.uuid = str(uuid.uuid4())
        new.enabled = src.enabled
        new.color = src.color
        new.color_label = src.color_label
        new.notes = src.notes
        new.tags = src.tags
        new.parent_uuid = src.parent_uuid
        new.frame_start = src.frame_start
        new.frame_end = src.frame_end
        new.frame_step = src.frame_step
        new.output_override = src.output_override
        new.facet_camera_enabled = src.facet_camera_enabled
        new.facet_world_enabled = src.facet_world_enabled
        new.facet_visibility_enabled = src.facet_visibility_enabled
        new.facet_render_enabled = src.facet_render_enabled
        new.facet_output_path_enabled = src.facet_output_path_enabled
        # TODO: copy custom_paths and per-facet sub-data (Phase 1 — facet PropertyGroups land per facet)
        data.active_index = len(data.studios) - 1
        return {'FINISHED'}


class STAGE_OT_studio_move(Operator):
    bl_idname = "stage.studio_move"
    bl_label = "Move Studio"
    bl_description = "Reorder the active Studio in the list"
    bl_options = {'REGISTER', 'UNDO'}

    direction: StringProperty(default='UP')  # 'UP' | 'DOWN' | 'TOP' | 'BOTTOM'

    @classmethod
    def poll(cls, context):
        data = context.scene.stage_data
        return len(data.studios) > 1

    def execute(self, context):
        data = context.scene.stage_data
        idx = data.active_index
        n = len(data.studios)
        if self.direction == 'UP' and idx > 0:
            new_idx = idx - 1
        elif self.direction == 'DOWN' and idx < n - 1:
            new_idx = idx + 1
        elif self.direction == 'TOP':
            new_idx = 0
        elif self.direction == 'BOTTOM':
            new_idx = n - 1
        else:
            return {'CANCELLED'}
        data.studios.move(idx, new_idx)
        data.active_index = new_idx
        return {'FINISHED'}


_classes = (
    STAGE_OT_studio_add,
    STAGE_OT_studio_remove,
    STAGE_OT_studio_duplicate,
    STAGE_OT_studio_move,
)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
