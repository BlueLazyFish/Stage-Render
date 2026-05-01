"""Thumbnail-related operators."""

import bpy
from bpy.types import Operator

from ..core.thumbnails import render_thumbnail
from ..handlers import set_apply_in_progress
from ..utils.logger import get_logger


_log = get_logger()


class STAGE_OT_studio_refresh_thumbnail(Operator):
    bl_idname = "stage.studio_refresh_thumbnail"
    bl_label = "Refresh Thumbnail"
    bl_description = "Re-render the active Studio's thumbnail using the current scene state"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        data = context.scene.stage_data
        return 0 <= data.active_index < len(data.studios)

    def execute(self, context):
        data = context.scene.stage_data
        studio = data.studios[data.active_index]
        set_apply_in_progress(True)
        try:
            result = render_thumbnail(context.scene, studio)
        finally:
            set_apply_in_progress(False)
        if result is None:
            self.report({'WARNING'}, f"Failed to render thumbnail for {studio.name}")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Refreshed thumbnail: {studio.name}")
        return {'FINISHED'}


_classes = (STAGE_OT_studio_refresh_thumbnail,)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
