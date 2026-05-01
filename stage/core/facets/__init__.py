"""Facet capture/restore — one module per facet type.

Each facet exposes a small protocol:

    facet_id: str
    is_enabled(studio) -> bool
    capture(scene, studio) -> None
    apply(scene, studio) -> None

Facets must satisfy the round-trip invariant:
    capture → mutate → apply → state-equal

This is the central Phase 1 correctness check; see ADDON_PLAN.md §5 testing.
"""

from __future__ import annotations

from typing import Protocol


class Facet(Protocol):
    facet_id: str

    def is_enabled(self, studio) -> bool:
        ...

    def capture(self, scene, studio) -> None:
        ...

    def apply(self, scene, studio) -> None:
        ...


_FACETS: dict[str, Facet] = {}


def register_facet(facet: Facet) -> None:
    """Register a facet. Re-registering with the same `facet_id` replaces."""
    _FACETS[facet.facet_id] = facet


def all_facets() -> list[Facet]:
    return list(_FACETS.values())


def capture_all(scene, studio) -> None:
    """Capture every enabled facet from `scene` into `studio`."""
    for facet in _FACETS.values():
        if facet.is_enabled(studio):
            facet.capture(scene, studio)


def apply_all(scene, studio) -> None:
    """Apply every enabled facet from `studio` into `scene`."""
    for facet in _FACETS.values():
        if facet.is_enabled(studio):
            facet.apply(scene, studio)


# Import each facet module so they self-register on first import.
# Append new facets here as Phase 1 progresses.
from . import output_path  # noqa: F401, E402
from . import world  # noqa: F401, E402
from . import camera  # noqa: F401, E402
from . import visibility  # noqa: F401, E402
from . import render_settings  # noqa: F401, E402
