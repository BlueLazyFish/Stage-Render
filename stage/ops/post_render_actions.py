"""Add / remove / reorder post-render actions on the active Studio."""

import bpy
from bpy.types import Operator
from bpy.props import IntProperty, StringProperty


def _active_studio(context):
    data = context.scene.stage_data
    if not (0 <= data.active_index < len(data.studios)):
        return None
    return data.studios[data.active_index]


class STAGE_OT_add_post_render_action(Operator):
    bl_idname = "stage.add_post_render_action"
    bl_label = "Add Post-Render Action"
    bl_description = "Add a new post-render action to the active Studio"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return _active_studio(context) is not None

    def execute(self, context):
        studio = _active_studio(context)
        action = studio.post_render_actions.add()
        action.action_type = 'COPY_FILE'
        return {'FINISHED'}


class STAGE_OT_remove_post_render_action(Operator):
    bl_idname = "stage.remove_post_render_action"
    bl_label = "Remove Post-Render Action"
    bl_description = "Remove this post-render action from the active Studio"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()

    @classmethod
    def poll(cls, context):
        return _active_studio(context) is not None

    def execute(self, context):
        studio = _active_studio(context)
        if 0 <= self.index < len(studio.post_render_actions):
            studio.post_render_actions.remove(self.index)
        return {'FINISHED'}


class STAGE_OT_move_post_render_action(Operator):
    bl_idname = "stage.move_post_render_action"
    bl_label = "Move Post-Render Action"
    bl_description = "Reorder a post-render action (order matters; move-before-copy breaks the chain)"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()
    direction: StringProperty(default='UP')  # 'UP' | 'DOWN'

    @classmethod
    def poll(cls, context):
        return _active_studio(context) is not None

    def execute(self, context):
        studio = _active_studio(context)
        n = len(studio.post_render_actions)
        if not (0 <= self.index < n):
            return {'CANCELLED'}
        if self.direction == 'UP' and self.index > 0:
            new_idx = self.index - 1
        elif self.direction == 'DOWN' and self.index < n - 1:
            new_idx = self.index + 1
        else:
            return {'CANCELLED'}
        studio.post_render_actions.move(self.index, new_idx)
        return {'FINISHED'}


_classes = (
    STAGE_OT_add_post_render_action,
    STAGE_OT_remove_post_render_action,
    STAGE_OT_move_post_render_action,
)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
