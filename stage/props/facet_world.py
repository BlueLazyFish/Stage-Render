"""FacetWorld — captured World facet data per Studio.

`captured` distinguishes "this facet has been initialised" from
"world_name happens to be empty" — important for the round-trip
invariant when applying a Studio that was created without a capture.
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import StringProperty, BoolProperty


class FacetWorld(PropertyGroup):
    captured: BoolProperty(
        name="Captured",
        description="True once capture() has populated this facet at least once",
        default=False,
    )

    world_name: StringProperty(
        name="World",
        description="Name of the captured World datablock; empty = scene had no world",
        default="",
    )

    film_transparent: BoolProperty(
        name="Transparent Background",
        description="scene.render.film_transparent at capture time",
        default=False,
    )


def register() -> None:
    bpy.utils.register_class(FacetWorld)


def unregister() -> None:
    bpy.utils.unregister_class(FacetWorld)
