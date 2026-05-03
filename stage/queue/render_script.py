"""Subprocess entrypoint — invoked by the foreground addon as:

    blender -b <blend_file> -P render_script.py -- --job-id=<N> [--db-path=<path>]

Steps:
  1. Parse --job-id and --db-path from argv (Blender passes everything
     after `--` to the script).
  2. Add Stage's package root to sys.path so we can `import stage`.
  3. Open the SQLite DB; mark the job RUNNING (with our pid).
  4. Open the .blend (we were launched against it via `blender -b <blend>`,
     but Blender will also call wm.open_mainfile via `-b` so context.scene
     is already populated).
  5. Find the Studio by uuid. Apply it. Render.
  6. Mark DONE (or FAILED on any exception).

Errors propagate as FAILED status with the exception message — never
crash silently. Exit code is 0 on DONE, 1 otherwise so the worker side
can fall back if SQLite write itself failed.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path


def _parse_args(argv: list[str]) -> tuple[int, str | None]:
    """Extract --job-id and --db-path from the post-`--` portion of argv."""
    if "--" in argv:
        tail = argv[argv.index("--") + 1:]
    else:
        tail = argv

    job_id: int | None = None
    db_path: str | None = None
    for arg in tail:
        if arg.startswith("--job-id="):
            job_id = int(arg.split("=", 1)[1])
        elif arg.startswith("--db-path="):
            db_path = arg.split("=", 1)[1]
    if job_id is None:
        raise SystemExit("render_script.py: --job-id=N is required")
    return job_id, db_path


def _add_stage_to_path() -> None:
    """Make `import stage` work when run via `blender -P` from anywhere."""
    # __file__ → .../stage/queue/render_script.py
    # Parent of stage package → .../  → on sys.path so `import stage` works
    pkg_root = Path(__file__).resolve().parent.parent.parent
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))


def _find_studio_by_uuid(scene, studio_uuid: str):
    data = getattr(scene, "stage_data", None)
    if data is None:
        return None
    for s in data.studios:
        if s.uuid == studio_uuid:
            return s
    return None


def _render_one_job(job_id: int, db_path_arg: str | None) -> int:
    """Body of the subprocess. Returns the desired exit code."""
    import bpy  # noqa: PLC0415 — only valid inside Blender

    _add_stage_to_path()

    from stage import register as stage_register  # noqa: PLC0415
    from stage.queue import db as queue_db  # noqa: PLC0415

    db_path = Path(db_path_arg) if db_path_arg else None

    # Stage isn't auto-loaded in `blender -b`; we register it ourselves so
    # Scene.stage_data is wired up.
    try:
        stage_register()
    except Exception:
        # Already registered (rare in subprocess but be safe)
        pass

    with queue_db.connect(db_path) as conn:
        job = queue_db.get_job(conn, job_id)
        if job is None:
            print(f"render_script: job {job_id} not found", file=sys.stderr)
            return 1

        import os
        queue_db.mark_running(conn, job_id, pid=os.getpid())

        try:
            scene_name = job["scene_name"]
            if scene_name not in bpy.data.scenes:
                raise RuntimeError(
                    f"Scene '{scene_name}' not found in the .blend file"
                )
            scene = bpy.data.scenes[scene_name]
            bpy.context.window.scene = scene

            studio = _find_studio_by_uuid(scene, job["studio_uuid"])
            if studio is None:
                raise RuntimeError(
                    f"Studio uuid {job['studio_uuid']!r} not found in scene "
                    f"'{scene_name}'. Was it deleted after queueing?"
                )

            # Apply the Studio (walks the parent chain too via apply_studio)
            from stage.core.inheritance import apply_studio  # noqa: PLC0415
            from stage.handlers import set_apply_in_progress  # noqa: PLC0415

            set_apply_in_progress(True)
            try:
                apply_studio(scene, studio)
            finally:
                set_apply_in_progress(False)

            # Render. Output path is whatever the Studio's render facet /
            # scene.render.filepath resolved to. We don't override here —
            # the Studio's apply already set scene.render.filepath if its
            # output_override / facet_output_path was populated.
            output_path = scene.render.filepath
            print(
                f"render_script: rendering job {job_id} "
                f"(studio={studio.name!r}) -> {output_path}",
                flush=True,
            )

            # Animation = False renders the current frame as a still.
            # For multi-frame animations users will set frame_start/end
            # in the Studio; v1.0 ships single-frame only and we extend
            # later. (`scene.frame_current` is what gets rendered.)
            bpy.ops.render.render(write_still=True)

            queue_db.mark_done(conn, job_id, output_path=output_path)
            print(
                f"render_script: job {job_id} done -> {output_path}", flush=True
            )
            return 0
        except Exception as e:
            tb = traceback.format_exc()
            err = f"{type(e).__name__}: {e}\n{tb}"
            print(f"render_script: job {job_id} FAILED:\n{err}", file=sys.stderr)
            try:
                queue_db.mark_failed(conn, job_id, error_message=str(e))
            except Exception:
                pass
            return 1


def main() -> int:
    job_id, db_path = _parse_args(sys.argv)
    return _render_one_job(job_id, db_path)


if __name__ == "__main__":
    sys.exit(main())
