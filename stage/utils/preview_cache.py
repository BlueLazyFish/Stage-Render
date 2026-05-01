"""Preview cache for Studio thumbnails.

bpy.utils.previews provides a managed icon collection — load image files
into it once per Studio uuid, retrieve via icon_id for UIList rows.

The collection is created lazily on first access and torn down via
cleanup() on addon unregister.
"""

from __future__ import annotations

from pathlib import Path

import bpy
import bpy.utils.previews


_pcoll = None


def _get_collection():
    global _pcoll
    if _pcoll is None:
        _pcoll = bpy.utils.previews.new()
    return _pcoll


def get_icon_id(uuid: str, thumbnail_path: str) -> int:
    """Return an icon_id for the Studio. Loads from disk on first call.

    Returns 0 (no icon) if the file is missing or load fails.
    """
    if not uuid or not thumbnail_path:
        return 0
    pcoll = _get_collection()
    if uuid in pcoll:
        return pcoll[uuid].icon_id
    if not Path(thumbnail_path).exists():
        return 0
    try:
        preview = pcoll.load(uuid, thumbnail_path, 'IMAGE')
        return preview.icon_id
    except Exception:
        return 0


def invalidate(uuid: str) -> None:
    """Drop the cached preview so next get_icon_id reloads from disk."""
    pcoll = _get_collection()
    if uuid in pcoll:
        del pcoll[uuid]


def cleanup() -> None:
    """Clear the preview collection. Called on addon unregister."""
    global _pcoll
    if _pcoll is not None:
        bpy.utils.previews.remove(_pcoll)
        _pcoll = None
