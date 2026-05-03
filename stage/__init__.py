"""Stage — KeyShot-inspired scene state manager and render queue for Blender.

Entry point. Submodules import bpy and are deferred to register / unregister
time so pure-Python tooling (CI unit tests, doc generation) can import
stage.core.paths without bpy being available.
"""


def _modules():
    """Return registration-ordered modules. Imported lazily so that
    `import stage.core.paths` from a CI runner without bpy succeeds."""
    from . import props
    from . import prefs
    from . import ops
    from . import ui
    from . import handlers
    return (props, prefs, ops, ui, handlers)


def register() -> None:
    for m in _modules():
        m.register()

    # Queue: reset orphaned RUNNING jobs (process died mid-render last
    # session), then start the monitor timer so the worker subprocess
    # gets nudged whenever the queue has pending work. Wrapped in
    # try/except because bpy.app.timers isn't safe to register from a
    # non-Blender context (CI imports this module).
    try:
        from .queue import db as queue_db
        from .queue import monitor as queue_monitor
        with queue_db.connect() as conn:
            queue_db.reset_orphaned_running(conn)
        queue_monitor.register()
    except Exception:
        pass


def unregister() -> None:
    # Tear down the preview cache before unregistering UI/etc. — the cache
    # holds bpy.utils.previews handles that must be released cleanly.
    from .utils import preview_cache
    preview_cache.cleanup()

    # Stop the queue monitor + kill any active worker so we don't leak
    # subprocesses past addon disable.
    try:
        from .queue import monitor as queue_monitor
        queue_monitor.unregister()
    except Exception:
        pass

    for m in reversed(_modules()):
        m.unregister()
