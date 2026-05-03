"""SQLite layer for the render queue.

Single table (`jobs`) holds every queued / running / completed render.
The schema is intentionally tiny — one row per render job — and every
status transition (PENDING → RUNNING → DONE/FAILED/CANCELLED) is a
single UPDATE statement.

A `meta` table records the schema_version so future migrations have a
known starting point. v1.0 ships schema_version = 1.

Concurrency: one writer at a time. Foreground addon writes when adding
or cancelling jobs; background subprocess writes when transitioning
status. SQLite's default journal mode is enough for this contention
level (a job state transition every few seconds at most).
"""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from . import paths as _paths


# --- status enum -----------------------------------------------------------


STATUS_PENDING = "PENDING"
STATUS_RUNNING = "RUNNING"
STATUS_DONE = "DONE"
STATUS_FAILED = "FAILED"
STATUS_CANCELLED = "CANCELLED"

STATUSES = (
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_DONE,
    STATUS_FAILED,
    STATUS_CANCELLED,
)

TERMINAL_STATUSES = (STATUS_DONE, STATUS_FAILED, STATUS_CANCELLED)


# --- schema ----------------------------------------------------------------


SCHEMA_VERSION = 1

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    blend_file_path      TEXT    NOT NULL,
    scene_name           TEXT    NOT NULL,
    studio_uuid          TEXT    NOT NULL,
    studio_name_at_queue TEXT    NOT NULL,
    status               TEXT    NOT NULL,
    submitted_at         REAL    NOT NULL,
    started_at           REAL,
    completed_at         REAL,
    output_path          TEXT,
    error_message        TEXT,
    pid                  INTEGER
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_submitted_at ON jobs(submitted_at);
"""


# --- connection ------------------------------------------------------------


@contextmanager
def connect(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection, ensuring schema is initialized."""
    # Re-resolve via the paths module each call so test monkey-patches
    # of paths.queue_db_path land here too.
    path = db_path if db_path is not None else _paths.queue_db_path()
    # isolation_level=None gives us autocommit so each statement is durable
    # immediately — fine for our low write volume.
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        _init_schema(conn)
        yield conn
    finally:
        conn.close()


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_SQL)
    cur = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'")
    row = cur.fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )


# --- CRUD ------------------------------------------------------------------


def add_job(
    conn: sqlite3.Connection,
    *,
    blend_file_path: str,
    scene_name: str,
    studio_uuid: str,
    studio_name: str,
) -> int:
    """Insert a new PENDING job. Returns the new row's id."""
    cur = conn.execute(
        """
        INSERT INTO jobs (
            blend_file_path, scene_name, studio_uuid, studio_name_at_queue,
            status, submitted_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            blend_file_path,
            scene_name,
            studio_uuid,
            studio_name,
            STATUS_PENDING,
            time.time(),
        ),
    )
    return int(cur.lastrowid)


def get_job(conn: sqlite3.Connection, job_id: int) -> sqlite3.Row | None:
    cur = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    return cur.fetchone()


def list_jobs(
    conn: sqlite3.Connection,
    *,
    statuses: tuple[str, ...] | None = None,
    limit: int | None = None,
) -> list[sqlite3.Row]:
    """Return jobs ordered by submitted_at ascending (oldest first)."""
    sql = "SELECT * FROM jobs"
    params: list = []
    if statuses:
        placeholders = ",".join("?" for _ in statuses)
        sql += f" WHERE status IN ({placeholders})"
        params.extend(statuses)
    sql += " ORDER BY submitted_at ASC"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    cur = conn.execute(sql, params)
    return cur.fetchall()


def next_pending_job(conn: sqlite3.Connection) -> sqlite3.Row | None:
    """Oldest PENDING job, or None."""
    cur = conn.execute(
        "SELECT * FROM jobs WHERE status = ? ORDER BY submitted_at ASC LIMIT 1",
        (STATUS_PENDING,),
    )
    return cur.fetchone()


def has_running_job(conn: sqlite3.Connection) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM jobs WHERE status = ? LIMIT 1", (STATUS_RUNNING,)
    )
    return cur.fetchone() is not None


def mark_running(conn: sqlite3.Connection, job_id: int, *, pid: int) -> None:
    conn.execute(
        "UPDATE jobs SET status = ?, started_at = ?, pid = ? WHERE id = ?",
        (STATUS_RUNNING, time.time(), pid, job_id),
    )


def mark_done(
    conn: sqlite3.Connection, job_id: int, *, output_path: str | None = None
) -> None:
    conn.execute(
        "UPDATE jobs SET status = ?, completed_at = ?, output_path = ? WHERE id = ?",
        (STATUS_DONE, time.time(), output_path, job_id),
    )


def mark_failed(
    conn: sqlite3.Connection, job_id: int, *, error_message: str
) -> None:
    conn.execute(
        "UPDATE jobs SET status = ?, completed_at = ?, error_message = ? WHERE id = ?",
        (STATUS_FAILED, time.time(), error_message, job_id),
    )


def mark_cancelled(conn: sqlite3.Connection, job_id: int) -> None:
    conn.execute(
        "UPDATE jobs SET status = ?, completed_at = ? WHERE id = ?",
        (STATUS_CANCELLED, time.time(), job_id),
    )


def delete_job(conn: sqlite3.Connection, job_id: int) -> None:
    conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))


def clear_completed(conn: sqlite3.Connection) -> int:
    """Drop every job in a terminal status. Returns the number deleted."""
    placeholders = ",".join("?" for _ in TERMINAL_STATUSES)
    cur = conn.execute(
        f"DELETE FROM jobs WHERE status IN ({placeholders})",
        TERMINAL_STATUSES,
    )
    return cur.rowcount


def reset_orphaned_running(conn: sqlite3.Connection) -> int:
    """Mark RUNNING jobs as FAILED on startup.

    A job in RUNNING status when the addon loads must have been
    interrupted — Blender crashed, machine rebooted, subprocess was
    killed. Without this, the queue would think a job is still in flight
    and never spawn a new worker.
    """
    cur = conn.execute(
        "UPDATE jobs SET status = ?, completed_at = ?, error_message = ? WHERE status = ?",
        (
            STATUS_FAILED,
            time.time(),
            "Worker process did not finish — likely a crash or restart.",
            STATUS_RUNNING,
        ),
    )
    return cur.rowcount
