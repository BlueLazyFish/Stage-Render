"""Platform-correct paths for the queue's persistent state.

All queue state (the SQLite DB, per-job log files) lives under a single
user-data directory chosen by OS convention:

    macOS    ~/Library/Application Support/Stage/
    Linux    ~/.local/share/Stage/   (or $XDG_DATA_HOME/Stage/ if set)
    Windows  %APPDATA%/Stage/

Pure stdlib — no platformdirs dependency, since we only need three forks
of one path.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


_APP_NAME = "Stage"


def stage_data_dir() -> Path:
    """Return the user-data directory for Stage. Creates it if missing."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    else:
        # Linux + everything else — XDG spec
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) if xdg else (Path.home() / ".local" / "share")
    path = base / _APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def queue_db_path() -> Path:
    """Path to the SQLite queue database."""
    return stage_data_dir() / "queue.db"


def jobs_log_dir() -> Path:
    """Directory holding per-job stdout/stderr log files."""
    path = stage_data_dir() / "jobs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def job_log_path(job_id: int) -> Path:
    """Combined stdout/stderr capture for a single job."""
    return jobs_log_dir() / f"job_{job_id}.log"
