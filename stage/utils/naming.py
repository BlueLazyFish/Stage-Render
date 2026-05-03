"""Name disambiguation — Blender-standard `Foo`, `Foo.001`, `Foo.002`...

Used by Studio CRUD and Group CRUD so newly-added items don't collide
with existing names. Blender does this for its own datablocks (Cube,
Cube.001, etc.) and users expect the same convention.
"""

from __future__ import annotations

from typing import Iterable


def unique_name(base: str, existing: Iterable[str]) -> str:
    """Return ``base`` if it isn't in ``existing``, otherwise append
    ``.001``, ``.002``, … until a free name is found.

    Empty/whitespace base is replaced with a single underscore so the
    result is always a usable identifier.
    """
    base = (base or "").strip() or "_"
    existing_set = set(existing)
    if base not in existing_set:
        return base
    i = 1
    while True:
        candidate = f"{base}.{i:03d}"
        if candidate not in existing_set:
            return candidate
        i += 1
