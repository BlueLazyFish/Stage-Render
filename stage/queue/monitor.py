"""Foreground polling loop — drives worker spawning and UI refreshes.

Runs as a `bpy.app.timers` callback every POLL_INTERVAL_SECONDS. Each
tick:
  1. Reap the active worker if it has exited (records nothing — the
     subprocess wrote its own DONE/FAILED status before exiting).
  2. If no worker is alive and pending jobs exist, spawn the next one.
  3. Tag the View3D for redraw so the queue panel's job list refreshes.

The timer auto-starts on addon register. It survives until unregister
even when the queue is empty (cheap — one DB hit per tick).
"""

from __future__ import annotations

import bpy

from . import worker as queue_worker
from ..utils.logger import get_logger


_log = get_logger()


# Two seconds is responsive enough for a render queue — frames take many
# seconds at minimum, so finer polling buys nothing.
POLL_INTERVAL_SECONDS = 2.0


def _tag_redraw() -> None:
    """Force the Stage queue panel to redraw so progress updates land."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def _tick() -> float:
    """Single timer iteration. Returns POLL_INTERVAL_SECONDS so the timer
    fires again, or None to stop."""
    try:
        finished_job_id = queue_worker.reap_if_finished()
        if finished_job_id is not None:
            _log.info("Queue: job %d finished", finished_job_id)

        # Spawn next pending job if no worker is currently busy
        spawned = queue_worker.spawn_next()
        if spawned is not None:
            _log.info("Queue: spawned worker for job %d", spawned)

        _tag_redraw()
    except Exception as e:
        # Never let a tick exception kill the timer — log and keep going.
        _log.warning("Queue monitor tick failed: %s: %s", type(e).__name__, e)

    return POLL_INTERVAL_SECONDS


def register() -> None:
    if not bpy.app.timers.is_registered(_tick):
        bpy.app.timers.register(_tick, first_interval=POLL_INTERVAL_SECONDS)


def unregister() -> None:
    if bpy.app.timers.is_registered(_tick):
        try:
            bpy.app.timers.unregister(_tick)
        except Exception:
            pass

    # On unregister, kill any active worker so we don't leak subprocesses.
    queue_worker.cancel_active(mark_db=True)
