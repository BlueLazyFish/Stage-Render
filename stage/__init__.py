"""Stage — KeyShot-inspired scene state manager and render queue for Blender.

Entry point. Modules register in dependency order; unregister in reverse.
"""

from . import props
from . import prefs
from . import ops
from . import ui
from . import handlers


_modules = (props, prefs, ops, ui, handlers)


def register() -> None:
    for m in _modules:
        m.register()


def unregister() -> None:
    for m in reversed(_modules):
        m.unregister()
