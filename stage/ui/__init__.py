"""UI registration — UILists first (referenced by panels), then panels."""

from . import studio_uilist
from . import n_panel
from . import lister
from . import queue_panel


_modules = (studio_uilist, n_panel, lister, queue_panel)


def register() -> None:
    for m in _modules:
        m.register()


def unregister() -> None:
    for m in reversed(_modules):
        m.unregister()
