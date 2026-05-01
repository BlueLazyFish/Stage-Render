"""Blender app handlers — load / save / exit + depsgraph (dirty tracking)."""

from __future__ import annotations

import bpy
from bpy.app.handlers import persistent

from .utils.logger import get_logger


_log = get_logger()


# Module-level flag that lets Stage's own apply / update operators silence
# the depsgraph handler while they're running — otherwise the writes those
# operators perform on the scene would immediately re-flag the scene as dirty.
_apply_in_progress: bool = False


def set_apply_in_progress(value: bool) -> None:
    """Toggle the dirty-handler suppression flag.

    Apply / Update operators wrap their work in `set_apply_in_progress(True)`
    ... `set_apply_in_progress(False)` so they can mutate the scene without
    self-firing the dirty handler.
    """
    global _apply_in_progress
    _apply_in_progress = value


@persistent
def depsgraph_update_post(scene, depsgraph) -> None:
    """Mark the scene dirty if it mutates after a Studio was applied."""
    if _apply_in_progress:
        return
    data = getattr(scene, "stage_data", None)
    if data is None:
        return
    if not data.last_applied_studio_uuid:
        # Never applied — nothing to be dirty against.
        return
    if data.suppress_next_dirty_fire:
        # The Apply / Update operator just finished and scheduled this skip
        # to absorb the post-operator depsgraph fire from its own writes.
        data.suppress_next_dirty_fire = False
        return
    if data.dirty:
        # Already flagged; skip the write to avoid handler ping-pong.
        return
    data.dirty = True


@persistent
def load_post(*_args) -> None:
    """After .blend load — re-validate Stage data, run any pending migrations."""
    from .core.migration import migrate
    for scene in bpy.data.scenes:
        migrate(getattr(scene, "stage_data", None))


@persistent
def save_pre(*_args) -> None:
    """Before .blend save — flush any pending state. (Stub.)"""
    pass


def exit_pre() -> None:
    """Before Blender exits — terminate orphan render subprocesses, mark
    in-flight queue jobs as `interrupted` for crash-recovery."""
    _log.debug("exit_pre handler firing")


def register() -> None:
    if load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_post)
    if save_pre not in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.append(save_pre)
    if depsgraph_update_post not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(depsgraph_update_post)
    # exit_pre is 5.1+; we target 5.1+ but guard for safety
    if hasattr(bpy.app.handlers, "exit_pre"):
        if exit_pre not in bpy.app.handlers.exit_pre:
            bpy.app.handlers.exit_pre.append(exit_pre)


def unregister() -> None:
    if hasattr(bpy.app.handlers, "exit_pre") and exit_pre in bpy.app.handlers.exit_pre:
        bpy.app.handlers.exit_pre.remove(exit_pre)
    if depsgraph_update_post in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update_post)
    if save_pre in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(save_pre)
    if load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post)
