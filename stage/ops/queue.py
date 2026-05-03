"""Render-queue operators (add / remove / cancel / clear).

These are the user-facing entry points to the persistent SQLite queue.
The actual subprocess work happens in stage.queue.worker, polled by
stage.queue.monitor — operators here just mutate the DB and let the
monitor tick spawn workers as appropriate.
"""

from __future__ import annotations

import bpy
from bpy.types import Operator
from bpy.props import IntProperty

from ..queue import db as queue_db
from ..queue import worker as queue_worker
from ..utils.logger import get_logger


_log = get_logger()


def _data(context):
    return context.scene.stage_data


def _current_blend_filepath() -> str:
    """Indirection over bpy.data.filepath so tests can monkeypatch the
    'is the .blend saved' check without doing destructive things to the
    Blender session (bpy.data.filepath itself is read-only)."""
    return bpy.data.filepath


def _blend_path_or_warn(self, context) -> str | None:
    """Return the absolute path of the saved .blend, or report a warning
    and return None if the file is unsaved or has dirty in-memory edits.

    The dirty-edit check is the silent footgun: the user changes a Studio's
    output_override in the panel, hits Queue, and the subprocess loads the
    .blend from disk — which still has the OLD override. The render goes
    somewhere unexpected with no visible error. Refuse here so the user
    knows to save first.
    """
    path = _current_blend_filepath()
    if not path:
        self.report(
            {'ERROR'},
            "Save the .blend file before queueing renders — the worker "
            "subprocess loads from disk, so unsaved scenes can't be used.",
        )
        return None
    if bpy.data.is_dirty:
        self.report(
            {'ERROR'},
            "Your .blend has unsaved changes. Save first (Ctrl+S) — the "
            "queue worker loads from disk and won't see in-memory edits "
            "like a freshly-typed output path.",
        )
        return None
    return path


def _enqueue(scene, blend_path: str, studio) -> int:
    with queue_db.connect() as conn:
        return queue_db.add_job(
            conn,
            blend_file_path=blend_path,
            scene_name=scene.name,
            studio_uuid=studio.uuid,
            studio_name=studio.name,
        )


# Earlier versions of this module attempted to peek into the saved .blend
# via bpy.data.libraries.load() to confirm the scene name actually exists
# on disk before queueing. That doesn't work — Blender refuses to
# library-load the currently-open file ("Cannot load from the current
# blend file"). With no reliable foreground way to check, we trust the
# subprocess to fail clearly when the scene isn't found and surface that
# message to the user via the queue panel's job error column.


# --- add jobs --------------------------------------------------------------


class STAGE_OT_queue_active(Operator):
    bl_idname = "stage.queue_active"
    bl_label = "Queue Active Studio"
    bl_description = "Add the active Studio to the persistent render queue"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        data = context.scene.stage_data
        return 0 <= data.active_index < len(data.studios)

    def execute(self, context):
        blend_path = _blend_path_or_warn(self, context)
        if blend_path is None:
            return {'CANCELLED'}

        data = _data(context)
        studio = data.studios[data.active_index]
        job_id = _enqueue(context.scene, blend_path, studio)
        self.report({'INFO'}, f"Queued: {studio.name} (job #{job_id})")
        _log.info("Queued job %d: studio=%r", job_id, studio.name)
        return {'FINISHED'}


class STAGE_OT_queue_selected(Operator):
    bl_idname = "stage.queue_selected"
    bl_label = "Queue Selected Studios"
    bl_description = "Add every selected (multi-select) Studio to the render queue"
    bl_options = {'REGISTER'}

    def execute(self, context):
        blend_path = _blend_path_or_warn(self, context)
        if blend_path is None:
            return {'CANCELLED'}

        data = _data(context)
        targets = [s for s in data.studios if s.selected]
        if not targets:
            self.report({'WARNING'}, "No Studios selected — tick the checkbox in the list first")
            return {'CANCELLED'}

        n = 0
        for studio in targets:
            _enqueue(context.scene, blend_path, studio)
            n += 1
        self.report({'INFO'}, f"Queued {n} Studio(s)")
        _log.info("Queued %d studios from selection", n)
        return {'FINISHED'}


class STAGE_OT_queue_all_enabled(Operator):
    bl_idname = "stage.queue_all_enabled"
    bl_label = "Queue All Enabled"
    bl_description = "Add every enabled Studio in the current scene to the render queue"
    bl_options = {'REGISTER'}

    def execute(self, context):
        blend_path = _blend_path_or_warn(self, context)
        if blend_path is None:
            return {'CANCELLED'}

        data = _data(context)
        targets = [s for s in data.studios if s.enabled]
        if not targets:
            self.report({'WARNING'}, "No enabled Studios in this scene")
            return {'CANCELLED'}

        for studio in targets:
            _enqueue(context.scene, blend_path, studio)
        self.report({'INFO'}, f"Queued {len(targets)} Studio(s)")
        _log.info("Queued %d enabled studios", len(targets))
        return {'FINISHED'}


# --- remove / cancel / clear ----------------------------------------------


class STAGE_OT_queue_remove(Operator):
    bl_idname = "stage.queue_remove"
    bl_label = "Remove Job"
    bl_description = (
        "Remove this job from the queue. If the job is currently running, "
        "use Cancel Active instead — this op only deletes the DB row"
    )
    bl_options = {'REGISTER'}

    job_id: IntProperty()

    def execute(self, context):
        with queue_db.connect() as conn:
            row = queue_db.get_job(conn, self.job_id)
            if row is None:
                return {'CANCELLED'}
            if row["status"] == queue_db.STATUS_RUNNING:
                self.report(
                    {'WARNING'},
                    "Job is running — use Cancel first, then Remove",
                )
                return {'CANCELLED'}
            queue_db.delete_job(conn, self.job_id)
        self.report({'INFO'}, f"Removed job #{self.job_id}")
        return {'FINISHED'}


class STAGE_OT_queue_cancel_active(Operator):
    bl_idname = "stage.queue_cancel_active"
    bl_label = "Cancel Running Job"
    bl_description = "Kill the worker subprocess and mark its job CANCELLED"
    bl_options = {'REGISTER'}

    def execute(self, context):
        if not queue_worker.is_worker_alive():
            self.report({'INFO'}, "No worker running")
            return {'CANCELLED'}
        cancelled = queue_worker.cancel_active()
        if cancelled:
            self.report({'INFO'}, "Cancelled running job")
            return {'FINISHED'}
        return {'CANCELLED'}


class STAGE_OT_queue_clear_completed(Operator):
    bl_idname = "stage.queue_clear_completed"
    bl_label = "Clear Completed"
    bl_description = "Drop every DONE / FAILED / CANCELLED job from the queue history"
    bl_options = {'REGISTER'}

    def execute(self, context):
        with queue_db.connect() as conn:
            n = queue_db.clear_completed(conn)
        self.report({'INFO'}, f"Cleared {n} completed job(s)")
        return {'FINISHED'}


class STAGE_OT_queue_kick(Operator):
    bl_idname = "stage.queue_kick"
    bl_label = "Start Worker"
    bl_description = (
        "Manually nudge the queue to spawn a worker for the next pending "
        "job. Normally the monitor handles this on its own"
    )
    bl_options = {'REGISTER'}

    def execute(self, context):
        spawned = queue_worker.spawn_next()
        if spawned is None:
            if queue_worker.is_worker_alive():
                self.report({'INFO'}, "Worker already running")
            else:
                self.report({'INFO'}, "No pending jobs")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Started worker for job #{spawned}")
        return {'FINISHED'}


_classes = (
    STAGE_OT_queue_active,
    STAGE_OT_queue_selected,
    STAGE_OT_queue_all_enabled,
    STAGE_OT_queue_remove,
    STAGE_OT_queue_cancel_active,
    STAGE_OT_queue_clear_completed,
    STAGE_OT_queue_kick,
)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
