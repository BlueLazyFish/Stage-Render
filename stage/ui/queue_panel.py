"""Render Queue panel — a collapsible subpanel under the Stage tab.

Header summary: pending / running / done / failed counts.
Toolbar: Queue Active, Queue Selected, Queue All Enabled, Cancel, Clear.
Job list: one row per job, oldest first. Status badge + studio name + a
trash button per row.

The panel reads the SQLite queue every redraw — cheap because the
monitor (queue/monitor.py) tags this region for redraw on tick, not
constantly. List length is capped at MAX_VISIBLE_JOBS to keep draw()
fast even with hundreds of historical entries; a "+ N older" line
hints when items are hidden.
"""

from __future__ import annotations

import bpy
from bpy.types import Panel

from ..prefs import get_prefs
from ..queue import db as queue_db
from ..queue import worker as queue_worker


_CATEGORY = "Stage"
MAX_VISIBLE_JOBS = 50


_STATUS_ICON = {
    queue_db.STATUS_PENDING: 'TIME',
    queue_db.STATUS_RUNNING: 'REC',
    queue_db.STATUS_DONE: 'CHECKMARK',
    queue_db.STATUS_FAILED: 'ERROR',
    queue_db.STATUS_CANCELLED: 'X',
}


class STAGE_PT_queue(Panel):
    bl_idname = "STAGE_PT_queue"
    bl_label = "Render Queue"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = _CATEGORY
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Pull all jobs in one query so we have totals + the recent slice
        try:
            with queue_db.connect() as conn:
                all_jobs = queue_db.list_jobs(conn)
        except Exception as e:
            layout.label(text=f"Queue DB error: {e}", icon='ERROR')
            return

        # Header — counts by status
        counts = {s: 0 for s in queue_db.STATUSES}
        for j in all_jobs:
            counts[j["status"]] = counts.get(j["status"], 0) + 1

        header = layout.row(align=True)
        header.label(
            text=(
                f"{counts[queue_db.STATUS_PENDING]} pending  "
                f"{counts[queue_db.STATUS_RUNNING]} running  "
                f"{counts[queue_db.STATUS_DONE]} done  "
                f"{counts[queue_db.STATUS_FAILED]} failed"
            ),
            icon='RENDER_RESULT',
        )

        # Unsaved-changes warning — the silent footgun. The worker
        # subprocess reads the .blend from disk; in-memory edits to a
        # Studio (output path, captured facets, etc.) won't propagate
        # until the user saves. Surface this prominently so they don't
        # hit a queue with stale data.
        if bpy.data.is_dirty:
            warn = layout.box()
            warn_row = warn.row()
            warn_row.alert = True
            warn_row.label(
                text="Unsaved changes — Ctrl+S before queueing",
                icon='ERROR',
            )

        # Toolbar — add jobs
        col = layout.column(align=True)
        col.label(text="Add to queue:")
        row = col.row(align=True)
        row.operator("stage.queue_active", icon='ADD')
        row.operator("stage.queue_selected", icon='RESTRICT_SELECT_OFF', text="Selected")
        col.operator("stage.queue_all_enabled", icon='SCENE')

        # Toolbar — control
        col = layout.column(align=True)
        col.label(text="Control:")

        # Pause toggle drives auto-spawn behaviour in queue.monitor.
        # When paused the user must hit Start Worker to process one job.
        prefs = get_prefs(context)
        if prefs is not None:
            paused = prefs.queue_paused
            row = col.row(align=True)
            row.prop(
                prefs, "queue_paused",
                text="Paused" if paused else "Auto-Process",
                icon='PAUSE' if paused else 'PLAY',
                toggle=True,
            )

        row = col.row(align=True)
        row.enabled = queue_worker.is_worker_alive()
        row.operator("stage.queue_cancel_active", icon='CANCEL')
        row = col.row(align=True)
        row.operator("stage.queue_kick", icon='PLAY')
        row.operator("stage.queue_clear_completed", icon='TRASH')

        if not all_jobs:
            layout.label(text="Queue is empty.", icon='INFO')
            return

        # Job list — newest at top so the user sees recent action first.
        # Cap to MAX_VISIBLE_JOBS to keep draw() snappy.
        visible = list(reversed(all_jobs))[:MAX_VISIBLE_JOBS]
        hidden = max(0, len(all_jobs) - len(visible))

        box = layout.box()
        box.label(text=f"Jobs ({len(all_jobs)}):")
        for job in visible:
            self._draw_job_row(box, job)
        if hidden:
            box.label(text=f"+ {hidden} older job(s) hidden — Clear Completed to tidy up")

    def _draw_job_row(self, layout, job) -> None:
        row = layout.row(align=True)
        status = job["status"]
        icon = _STATUS_ICON.get(status, 'QUESTION')
        label = f"#{job['id']}  {job['studio_name_at_queue']}  ({status})"
        row.label(text=label, icon=icon)

        if status == queue_db.STATUS_RUNNING:
            # Don't expose Remove on a running job — they need to Cancel first.
            return

        op = row.operator("stage.queue_remove", icon='X', text="")
        op.job_id = int(job["id"])


def register() -> None:
    bpy.utils.register_class(STAGE_PT_queue)


def unregister() -> None:
    bpy.utils.unregister_class(STAGE_PT_queue)
