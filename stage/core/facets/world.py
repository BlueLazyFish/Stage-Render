"""World facet — captures active World datablock and film transparency.

Matches Renderset's default world capture (active world + transparency).
HDRI-specific node values (Background strength, Mapping rotation) come
in a later slice via the shader-node-input capture path.
"""

from __future__ import annotations

import bpy

from ...utils.logger import get_logger
from . import register_facet


_log = get_logger()


class WorldFacet:
    facet_id = "world"

    def is_enabled(self, studio) -> bool:
        return studio.facet_world_enabled

    def capture(self, scene, studio) -> None:
        f = studio.facet_world
        f.captured = True
        f.world_name = scene.world.name if scene.world else ""
        f.film_transparent = scene.render.film_transparent

    def apply(self, scene, studio) -> None:
        f = studio.facet_world
        if not f.captured:
            return  # nothing was ever captured; leave scene alone

        # World datablock reference
        if f.world_name:
            world = bpy.data.worlds.get(f.world_name)
            if world is None:
                _log.warning(
                    "World %r not found; leaving scene.world unchanged "
                    "(was the world renamed or deleted?)",
                    f.world_name,
                )
            else:
                scene.world = world
        else:
            # Captured "no world" — restore that explicitly
            scene.world = None

        # Film transparency (independent of world reference)
        scene.render.film_transparent = f.film_transparent


register_facet(WorldFacet())
