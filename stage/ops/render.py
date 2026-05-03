"""Render operators — render the active Studio or all enabled Studios.

Both operators delegate to stage.core.render.render_studio_to_disk so
their output paths and post-render-action behaviour stay identical to
the queue worker subprocess (stage.queue.render_script). Foreground
ops pass show_view=True to pop up the Render Result window; the
subprocess passes show_view=False.
"""

from __future__ import annotations

import datetime

import bpy
from bpy.types import Operator

from ..core.render import render_studio_to_disk
from ..prefs import get_default_output_pattern
from ..utils.logger import get_logger


_log = get_logger()


class STAGE_OT_studio_render_one(Operator):
    bl_idname = "stage.studio_render_one"
    bl_label = "Render Studio"
    bl_description = "Apply the active Studio and render a still to its output path"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        data = context.scene.stage_data
        return 0 <= data.active_index < len(data.studios)

    def execute(self, context):
        data = context.scene.stage_data
        studio = data.studios[data.active_index]
        result = render_studio_to_disk(
            context.scene, studio,
            get_default_output_pattern(context),
            show_view=True,
        )
        if result is None:
            self.report({'WARNING'}, f"Render failed or skipped: {studio.name}")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Rendered: {studio.name} → {result}")
        _log.info("Rendered %s → %s", studio.name, result)
        return {'FINISHED'}


class STAGE_OT_studio_render_all(Operator):
    bl_idname = "stage.studio_render_all"
    bl_label = "Render All"
    bl_description = "Apply and render each enabled Studio sequentially"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        data = context.scene.stage_data
        return any(s.enabled for s in data.studios)

    def execute(self, context):
        data = context.scene.stage_data
        default_pattern = get_default_output_pattern(context)

        # Freeze-time trick — every Studio in this batch sees the same
        # {date_time}, so outputs cluster as a coherent batch instead of
        # drifting by milliseconds. Per ADDON_PLAN.md §3 v1.0.
        frozen = datetime.datetime.now()

        rendered = []
        for studio in data.studios:
            if not studio.enabled:
                continue
            result = render_studio_to_disk(
                context.scene, studio, default_pattern,
                frozen_now=frozen, show_view=True,
            )
            if result is not None:
                rendered.append((studio.name, result))

        self.report({'INFO'}, f"Rendered {len(rendered)} Studios")
        _log.info("Rendered %d Studios", len(rendered))
        return {'FINISHED'}


_classes = (STAGE_OT_studio_render_one, STAGE_OT_studio_render_all)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
