"""Render queue — persistent SQLite-backed background rendering.

Stage's render queue is the v1.0 architectural finale. It lets the user
queue Studios for rendering, then watch a background Blender subprocess
chew through them while the foreground UI stays responsive. The queue
persists across Blender restarts (and across machine reboots) because
its state lives in a SQLite database under the user's data dir.

Architecture (3 cooperating processes):

  - Foreground Blender (this addon)
      Adds jobs to the SQLite queue, polls for status changes via a
      bpy.app.timers callback (monitor.py), spawns a worker subprocess
      when the queue has pending work and no worker is alive.

  - Background Blender subprocess (one per job)
      Launched via `blender -b <blend> -P render_script.py -- <job_id>`.
      Reads the job from SQLite, applies the Studio, renders, writes
      status back to SQLite, exits.

  - SQLite database
      Single writer at a time (jobs table is the source of truth for
      job state). Lives at `<user_data_dir>/Stage/queue.db`.

Modules:
  - paths.py         platform-correct data directory + DB path helpers
  - db.py            schema, CRUD, status enums
  - render_script.py the standalone subprocess entrypoint (no bpy import
                     at module load; only when run as `__main__`)
  - worker.py        subprocess.Popen lifecycle (foreground side)
  - monitor.py       bpy.app.timers polling + auto-spawn next job
"""
