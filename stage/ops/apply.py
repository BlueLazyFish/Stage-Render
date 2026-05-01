"""Apply / Update operators — the heart of Studio switching.

Both operators use REGISTER + UNDO so each invocation produces exactly one
labeled undo step (per the plan's undo policy in §5).

They also manage the dirty-state flag: the scene is marked clean after apply
or update, and stage.handlers.depsgraph_update_post re-marks it dirty on any
subsequent scene mutation.
"""

import bpy
from bpy.types import Operator

from ..core.facets import apply_all, capture_all
from ..handlers import set_apply_in_progress
from ..utils.logger import get_logger


_log = get_logger()


class STAGE_OT_studio_apply(Operator):
    bl_idname = "stage.studio_apply"
    bl_label = "Apply Studio"
    bl_description = "Apply the active Studio's stored state to the scene"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        data = context.scene.stage_data
        return 0 <= data.active_index < len(data.studios)

    def execute(self, context):
        data = context.scene.stage_data
        studio = data.studios[data.active_index]
        set_apply_in_progress(True)
        try:
            apply_all(context.scene, studio)
            data.last_applied_studio_uuid = studio.uuid
            data.dirty = False
            # Absorb the post-operator depsgraph fire so it doesn't re-flag
            # the scene dirty (the fire is caused by our own writes).
            data.suppress_next_dirty_fire = True
        finally:
            set_apply_in_progress(False)
        self.report({'INFO'}, f"Applied: {studio.name}")
        _log.info("Applied Studio: %s", studio.name)
        return {'FINISHED'}


class STAGE_OT_studio_update_from_scene(Operator):
    bl_idname = "stage.studio_update_from_scene"
    bl_label = "Update Studio"
    bl_description = "Capture current scene state into the active Studio"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        data = context.scene.stage_data
        if not (0 <= data.active_index < len(data.studios)):
            return False
        return not data.studios[data.active_index].locked

    def execute(self, context):
        from ..core.thumbnails import render_thumbnail
        data = context.scene.stage_data
        studio = data.studios[data.active_index]
        if studio.locked:
            self.report({'WARNING'}, "Studio is locked — unlock to update")
            return {'CANCELLED'}
        set_apply_in_progress(True)
        try:
            capture_all(context.scene, studio)
            render_thumbnail(context.scene, studio)
            data.last_applied_studio_uuid = studio.uuid
            data.dirty = False
            data.suppress_next_dirty_fire = True
        finally:
            set_apply_in_progress(False)
        self.report({'INFO'}, f"Updated: {studio.name}")
        _log.info("Updated Studio from scene: %s", studio.name)
        return {'FINISHED'}


_classes = (STAGE_OT_studio_apply, STAGE_OT_studio_update_from_scene)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
