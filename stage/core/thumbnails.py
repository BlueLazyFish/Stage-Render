"""Thumbnail rendering — Workbench render to bpy.app.cachedir.

Per ADDON_PLAN.md §5: thumbnails live on disk, not in the .blend, so the
.blend stays sane at 1000-Studio scale. Cache path:

    bpy.app.cachedir/stage/thumbnails/<studio_uuid>.png

Synchronous Phase 1 — measured 100 ms for a 256×256 Workbench render of a
small scene, which is acceptable for Add / Update operations. v1.x can
refactor to a non-blocking modal operator if it becomes a UX problem.
"""

from __future__ import annotations

from pathlib import Path

import bpy

from ..utils.logger import get_logger


_log = get_logger()

THUMBNAIL_RESOLUTION = 256


def thumbnail_path_for(uuid: str) -> Path:
    """Return the on-disk path for a Studio's thumbnail. Creates the
    parent directory if needed."""
    cache = Path(bpy.app.cachedir) / "stage" / "thumbnails"
    cache.mkdir(parents=True, exist_ok=True)
    return cache / f"{uuid}.png"


def render_thumbnail(scene, studio, resolution: int = THUMBNAIL_RESOLUTION):
    """Render a Workbench thumbnail of the scene and save it for the Studio.

    Saves to thumbnail_path_for(studio.uuid), updates studio.thumbnail_path,
    and invalidates the preview cache so the next UI redraw reloads the icon.
    Returns the Path on success, None on failure.

    Caller should already be in set_apply_in_progress(True) so that the engine
    swap doesn't fire the dirty handler.
    """
    if not studio.uuid:
        _log.warning("Cannot render thumbnail for Studio with no uuid")
        return None

    out = thumbnail_path_for(studio.uuid)

    saved = {
        "engine": scene.render.engine,
        "resolution_x": scene.render.resolution_x,
        "resolution_y": scene.render.resolution_y,
        "resolution_percentage": scene.render.resolution_percentage,
        "filepath": scene.render.filepath,
        "file_format": scene.render.image_settings.file_format,
        "use_lock_interface": scene.render.use_lock_interface,
    }

    # bpy.ops.render.render uses bpy.context.scene; make sure that's our scene
    # for the duration of the render. temp_override propagates scene + window.
    window = bpy.context.window
    saved_active_scene = window.scene if window is not None else None

    try:
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.render.resolution_x = resolution
        scene.render.resolution_y = resolution
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        # Blender appends the file extension based on file_format, so strip it
        scene.render.filepath = str(out.with_suffix(""))
        # Don't lock the interface for an addon-internal render
        scene.render.use_lock_interface = False

        if window is not None and saved_active_scene is not scene:
            window.scene = scene

        if scene.camera is not None:
            # Camera available — standard scene render via Workbench engine
            bpy.ops.render.render(write_still=True)
        else:
            # No camera: fall back to OpenGL viewport render (uses the user's
            # current view). Faster too — ~50 ms vs ~100 ms for engine render.
            target_area = None
            target_region = None
            for w in bpy.context.window_manager.windows:
                for area in w.screen.areas:
                    if area.type == 'VIEW_3D':
                        target_area = area
                        target_region = next(
                            (r for r in area.regions if r.type == 'WINDOW'), None
                        )
                        break
                if target_area:
                    break
            if target_area is None or target_region is None:
                _log.debug(
                    "Skipping thumbnail for %s: no camera and no 3D viewport",
                    studio.name,
                )
                return None
            with bpy.context.temp_override(area=target_area, region=target_region):
                bpy.ops.render.opengl(write_still=True, view_context=True)
    except Exception as e:
        _log.warning("Thumbnail render failed for Studio %s: %s", studio.name, e)
        return None
    finally:
        scene.render.engine = saved["engine"]
        scene.render.resolution_x = saved["resolution_x"]
        scene.render.resolution_y = saved["resolution_y"]
        scene.render.resolution_percentage = saved["resolution_percentage"]
        scene.render.filepath = saved["filepath"]
        scene.render.image_settings.file_format = saved["file_format"]
        scene.render.use_lock_interface = saved["use_lock_interface"]
        if window is not None and saved_active_scene is not None and window.scene is not saved_active_scene:
            window.scene = saved_active_scene

    if not out.exists():
        _log.warning("Thumbnail render completed but file missing: %s", out)
        return None

    studio.thumbnail_path = str(out)

    from ..utils.preview_cache import invalidate
    invalidate(studio.uuid)

    return out
