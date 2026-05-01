"""Blender app handlers — load/save/exit hooks.

Phase 0 stubs; logic lands in Phase 1+.
"""

from __future__ import annotations

import bpy
from bpy.app.handlers import persistent

from .utils.logger import get_logger


_log = get_logger()


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
    # exit_pre is 5.1+; we target 5.1+ but guard for safety
    if hasattr(bpy.app.handlers, "exit_pre"):
        if exit_pre not in bpy.app.handlers.exit_pre:
            bpy.app.handlers.exit_pre.append(exit_pre)


def unregister() -> None:
    if hasattr(bpy.app.handlers, "exit_pre") and exit_pre in bpy.app.handlers.exit_pre:
        bpy.app.handlers.exit_pre.remove(exit_pre)
    if save_pre in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(save_pre)
    if load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post)
