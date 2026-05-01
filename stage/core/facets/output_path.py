"""Output Path facet — captures and applies Scene.render.filepath.

Simplest of the 5 MVP facets — uses the Studio's existing `output_override`
field rather than a dedicated PropertyGroup.
"""

from __future__ import annotations

from . import register_facet


class OutputPathFacet:
    facet_id = "output_path"

    def is_enabled(self, studio) -> bool:
        return studio.facet_output_path_enabled

    def capture(self, scene, studio) -> None:
        # Snapshot the current scene's render path. Empty string is valid —
        # it means "no override; inherit from prefs/project."
        studio.output_override = scene.render.filepath or ""

    def apply(self, scene, studio) -> None:
        if studio.output_override:
            scene.render.filepath = studio.output_override


register_facet(OutputPathFacet())
