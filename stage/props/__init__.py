"""PropertyGroup registration. Order matters — leaf groups before container groups."""

import bpy

from . import stored_prop
from . import facet_world
from . import facet_camera
from . import studio
from . import studio_collection


_modules = (stored_prop, facet_world, facet_camera, studio, studio_collection)


def register() -> None:
    for m in _modules:
        m.register()
    bpy.types.Scene.stage_data = bpy.props.PointerProperty(
        type=studio_collection.StudioCollection,
        name="Stage Data",
        description="Stage scene state container",
    )


def unregister() -> None:
    if hasattr(bpy.types.Scene, "stage_data"):
        del bpy.types.Scene.stage_data
    for m in reversed(_modules):
        m.unregister()
