"""Operator registration."""

from . import studio_crud
from . import apply
from . import thumbnails
from . import render


_modules = (studio_crud, apply, thumbnails, render)


def register() -> None:
    for m in _modules:
        m.register()


def unregister() -> None:
    for m in reversed(_modules):
        m.unregister()
