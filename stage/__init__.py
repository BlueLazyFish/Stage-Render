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


def unregister() -> None:
    # Tear down the preview cache before unregistering UI/etc. — the cache
    # holds bpy.utils.previews handles that must be released cleanly.
    from .utils import preview_cache
    preview_cache.cleanup()
    for m in reversed(_modules()):
        m.unregister()
