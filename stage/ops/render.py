"""Render operators — render the active Studio or all enabled Studios.

Phase 1 ships synchronous rendering (UI locks during render). v1.0 adds
subprocess-based background rendering per the plan §5 ("Background
rendering — the engineering challenge").

Both operators expand each Studio's output path template through
core.paths.expand_path so {studio}, {date_time}, {frame}, etc. work
consistently with the right-click → Store and post-render-action paths.
"""

from __future__ import annotations

import datetime

import bpy
from bpy.types import Operator

from ..core.facets import apply_all
from ..core.paths import build_default_context, expand_path
from ..handlers import set_apply_in_progress
from ..prefs import get_default_output_pattern
from ..utils.logger import get_logger


_log = get_logger()


# Map Blender file_format → conventional extension. Used to auto-sync the
# {ext} variable in the path template to whatever the user has set on
# scene.render.image_settings.file_format.
_FORMAT_EXT = {
    'PNG': 'png',
    'JPEG': 'jpg',
    'JPEG2000': 'jp2',
    'OPEN_EXR': 'exr',
    'OPEN_EXR_MULTILAYER': 'exr',
    'TIFF': 'tif',
    'BMP': 'bmp',
    'TARGA': 'tga',
    'TARGA_RAW': 'tga',
    'WEBP': 'webp',
    'AVI_RAW': 'avi',
    'AVI_JPEG': 'avi',
    'FFMPEG': 'mp4',
}


def _render_studio(scene, studio, default_pattern: str, *, frozen_now=None):
    """Apply the Studio, expand its output path, render a still.

    Returns the output path string on success, None on failure or skip.
    """
    if not studio.enabled:
        return None

    saved_filepath = scene.render.filepath

    set_apply_in_progress(True)
    try:
        apply_all(scene, studio)

        template = studio.output_override or default_pattern
        ctx = build_default_context(
            studio_name=studio.name,
            blend_path=bpy.data.filepath,
            scene=scene,
            frame=scene.frame_current,
            frozen_now=frozen_now,
        )
        # Sync {ext} to the actual file format the scene is set to render as
        ctx["ext"] = _FORMAT_EXT.get(
            scene.render.image_settings.file_format, ctx.get("ext", "png")
        )
        scene.render.filepath = expand_path(template, ctx)
        target = scene.render.filepath

        # bpy.ops.render.render uses bpy.context.scene; ensure it's our scene
        window = bpy.context.window
        saved_active_scene = window.scene if window is not None else None
        if window is not None and saved_active_scene is not scene:
            window.scene = scene

        try:
            bpy.ops.render.render(write_still=True)
        finally:
            if (
                window is not None
                and saved_active_scene is not None
                and window.scene is not saved_active_scene
            ):
                window.scene = saved_active_scene

        return target
    except Exception as e:
        _log.warning("Render failed for %s: %s", studio.name, e)
        return None
    finally:
        scene.render.filepath = saved_filepath
        set_apply_in_progress(False)


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
        result = _render_studio(context.scene, studio, get_default_output_pattern(context))
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
            result = _render_studio(
                context.scene, studio, default_pattern, frozen_now=frozen,
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
