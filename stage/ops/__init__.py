"""Operator registration."""

from . import studio_crud


_modules = (studio_crud,)


def register() -> None:
    for m in _modules:
        m.register()


def unregister() -> None:
    for m in reversed(_modules):
        m.unregister()
