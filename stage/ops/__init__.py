"""Operator registration."""

from . import studio_crud
from . import apply
from . import thumbnails
from . import render
from . import store_property
from . import templates
from . import post_render_actions
from . import groups
from . import selection
from . import bulk_edit
from . import queue


_modules = (
    studio_crud, apply, thumbnails, render, store_property, templates,
    post_render_actions, groups, selection, bulk_edit, queue,
)


def register() -> None:
    for m in _modules:
        m.register()


def unregister() -> None:
    for m in reversed(_modules):
        m.unregister()
