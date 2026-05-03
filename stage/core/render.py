"""Single source of truth for "render this Studio to disk".

Both the foreground render operators (stage.ops.render) and the queue
worker subprocess (stage.queue.render_script) call render_studio_to_disk
so the resolved output path and post-render-action behaviour are
identical regardless of where the render runs.

Before this module existed, the subprocess just read scene.render.filepath
raw after apply — which skipped template expansion ({studio}, {frame},
{ext}) and the addon-prefs fallback, so queued renders silently went to
the wrong place. Pulling the render path into one place keeps the two
code paths from drifting.
"""

from __future__ import annotations

import bpy

from .facets import apply_all
from .paths import build_default_context, expand_path
from .post_render import run_actions
from ..handlers import set_apply_in_progress
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


def _looks_like_directory(path: str) -> bool:
    """True if this looks like a folder path the user picked via the browse
    button rather than a full filename pattern.

    Heuristic: no {tokens} AND (ends with a path separator OR has no extension).
    A path with tokens is assumed intentional and used as-is. A path with an
    extension and no tokens is a single-file output (one Studio scenario,
    user accepts the overwrite if they queue multiple).
    """
    if not path:
        return False
    if "{" in path and "}" in path:
        return False
    if path.endswith(("/", "\\")):
        return True
    # No separator at end — check if there's a file extension on the leaf
    leaf = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return "." not in leaf


# Filename used when the user picks a folder via the browse button. Both
# {studio} and {frame} are included so distinct Studios queued together
# produce distinct files (the bug that motivated this whole helper) and
# multi-frame animations don't overwrite themselves.
_DIR_FALLBACK_FILENAME = "{studio}_{frame:04d}.{ext}"


def _join_dir_and_filename(directory: str, filename: str) -> str:
    """Concatenate, normalising the separator between them. Preserves the
    leading '//' blend-relative prefix on the directory."""
    if directory.endswith(("/", "\\")):
        return directory + filename
    return directory + "/" + filename


def resolve_output_path(scene, studio, default_pattern: str, *, frozen_now=None) -> str:
    """Pure function: compute the expanded output path for this Studio.

    Behaviour:
      - Empty override: use default_pattern
      - Override is a *directory* (no tokens, ends with / or no extension):
          combine override (directory) with the default_pattern's filename
          portion, so the user can pick a folder via the browse button
          and still get distinct per-Studio filenames.
      - Override has tokens or looks like a file: use override as-is.

    No side effects on the scene. Use this when you need to know where a
    render WOULD go without actually running the render.
    """
    override = studio.output_override
    if not override:
        template = default_pattern
    elif _looks_like_directory(override):
        # default_pattern's filename portion isn't safe to reuse here —
        # if it's just "{frame}.{ext}" then every Studio collides on the
        # same file. Use a guaranteed-distinct {studio}_{frame:04d}.{ext}
        # template instead.
        template = _join_dir_and_filename(override, _DIR_FALLBACK_FILENAME)
    else:
        template = override

    ctx = build_default_context(
        studio_name=studio.name,
        blend_path=bpy.data.filepath,
        scene=scene,
        frame=scene.frame_current,
        frozen_now=frozen_now,
    )
    ctx["ext"] = _FORMAT_EXT.get(
        scene.render.image_settings.file_format, ctx.get("ext", "png")
    )
    return expand_path(template, ctx)


def render_studio_to_disk(
    scene,
    studio,
    default_pattern: str,
    *,
    frozen_now=None,
    show_view: bool = False,
) -> str | None:
    """Apply the Studio, expand its output path, render a still, run any
    post-render actions. Returns the output path on success, None on
    failure or skip.

    Parameters
    ----------
    scene
        The bpy.types.Scene to render. Must already exist in bpy.data.scenes.
    studio
        A Stage Studio (PropertyGroup). Must have a uuid and at least
        the facet enable flags populated.
    default_pattern
        Fallback path template applied when studio.output_override is empty.
        Foreground callers pass `get_default_output_pattern(context)`;
        the queue subprocess passes the same via context.preferences.
    frozen_now : optional
        Datetime to freeze {date_time} substitutions to. Used by Render
        All so a batch shares one timestamp; queue jobs don't need this.
    show_view : bool
        If True (foreground only), pop up the Render Result view via
        wm.render.view_show. Always False in headless subprocess context.
    """
    if not studio.enabled:
        return None

    saved_filepath = scene.render.filepath

    set_apply_in_progress(True)
    try:
        apply_all(scene, studio)

        target = resolve_output_path(
            scene, studio, default_pattern, frozen_now=frozen_now
        )
        scene.render.filepath = target

        # bpy.ops.render.render uses bpy.context.scene; ensure it's our scene
        window = bpy.context.window
        saved_active_scene = window.scene if window is not None else None
        if window is not None and saved_active_scene is not scene:
            window.scene = scene

        try:
            if show_view:
                try:
                    bpy.ops.render.view_show('INVOKE_DEFAULT')
                except (RuntimeError, TypeError):
                    pass
            bpy.ops.render.render(write_still=True)
        finally:
            if (
                window is not None
                and saved_active_scene is not None
                and window.scene is not saved_active_scene
            ):
                window.scene = saved_active_scene

        # Post-render actions — execute in declared order. Per-action errors
        # are swallowed inside run_actions so one bad action doesn't poison
        # the rest. Runs the same in foreground and subprocess contexts.
        run_actions(scene, studio, target)

        return target
    except Exception as e:
        _log.warning("Render failed for %s: %s", studio.name, e)
        return None
    finally:
        scene.render.filepath = saved_filepath
        set_apply_in_progress(False)
