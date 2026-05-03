"""Background worker subprocess management.

Foreground addon calls into this module to spawn / cancel a background
Blender render. We track the currently-active worker in a module-level
variable; the monitor (monitor.py) polls .poll() to detect completion
and triggers spawn_next() when the queue still has pending work.

One subprocess per job (simpler than a long-running worker that pulls
multiple jobs — easier to reason about errors and cancel semantics, and
the per-job ~1s Blender startup is negligible against multi-minute
renders).
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

import bpy

from . import db as queue_db
from . import paths as _paths


# Module-level handle to the currently-running worker subprocess. None when
# no worker is alive. Updated by spawn_next() and reaped by monitor.py.
_active_worker: Optional[subprocess.Popen] = None
_active_job_id: Optional[int] = None
_active_log_handle = None


def get_active_worker() -> Optional[subprocess.Popen]:
    return _active_worker


def get_active_job_id() -> Optional[int]:
    return _active_job_id


def is_worker_alive() -> bool:
    """True if there's a worker subprocess currently running."""
    if _active_worker is None:
        return False
    return _active_worker.poll() is None


def _render_script_path() -> Path:
    """Absolute path to render_script.py inside the addon."""
    return Path(__file__).resolve().parent / "render_script.py"


def spawn_next() -> Optional[int]:
    """If the queue has a PENDING job and no worker is alive, spawn one.

    Returns the job_id that was spawned, or None if nothing was started.
    """
    global _active_worker, _active_job_id, _active_log_handle

    if is_worker_alive():
        return None

    # Reap the previous worker's log handle if still open
    _close_log_handle()

    with queue_db.connect() as conn:
        job = queue_db.next_pending_job(conn)
        if job is None:
            return None
        job_id = int(job["id"])
        blend_path = job["blend_file_path"]

    if not Path(blend_path).is_file():
        # The .blend was moved or deleted after queueing — fail the job
        # rather than launch a doomed subprocess.
        with queue_db.connect() as conn:
            queue_db.mark_failed(
                conn, job_id,
                error_message=f"Blend file not found: {blend_path}",
            )
        # Try the next one (recursive — bounded by number of pending jobs)
        return spawn_next()

    cmd = [
        bpy.app.binary_path,
        "-b", str(blend_path),
        "-P", str(_render_script_path()),
        "--",
        f"--job-id={job_id}",
        f"--db-path={_paths.queue_db_path()}",
    ]

    log_path = _paths.job_log_path(job_id)
    log_handle = log_path.open("w", encoding="utf-8")

    # Detach from the foreground process group so signals to the foreground
    # Blender don't accidentally kill the worker.
    popen_kwargs: dict = {
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **popen_kwargs)
    _active_worker = proc
    _active_job_id = job_id
    _active_log_handle = log_handle
    return job_id


def cancel_active(*, mark_db: bool = True) -> bool:
    """Kill the running worker. Returns True if a worker was killed."""
    global _active_worker, _active_job_id

    if not is_worker_alive():
        return False

    proc = _active_worker
    job_id = _active_job_id
    try:
        if sys.platform == "win32":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

    # Give it a moment to die, then force-kill if needed
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except Exception:
            pass

    if mark_db and job_id is not None:
        try:
            with queue_db.connect() as conn:
                queue_db.mark_cancelled(conn, job_id)
        except Exception:
            pass

    _close_log_handle()
    _active_worker = None
    _active_job_id = None
    return True


def reap_if_finished() -> Optional[int]:
    """If the active worker has exited, clear the handle and return the
    job_id it was working on. Otherwise return None."""
    global _active_worker, _active_job_id

    if _active_worker is None:
        return None
    if _active_worker.poll() is None:
        return None

    finished_job_id = _active_job_id
    _close_log_handle()
    _active_worker = None
    _active_job_id = None
    return finished_job_id


def _close_log_handle() -> None:
    global _active_log_handle
    if _active_log_handle is not None:
        try:
            _active_log_handle.close()
        except Exception:
            pass
        _active_log_handle = None
