"""Output Path facet — captures and applies Scene.render.filepath.

Simplest of the 5 MVP facets — uses the Studio's existing `output_override`
field rather than a dedicated PropertyGroup.
"""

from __future__ import annotations

import bpy

from . import register_facet


class OutputPathFacet:
    facet_id = "output_path"

    def is_enabled(self, studio) -> bool:
        return studio.facet_output_path_enabled

    def capture(self, scene, studio) -> None:
        fp = scene.render.filepath or ""
        # Studio.output_override is subtype='FILE_PATH', which Blender
        # documents as not accepting the "//" blend-relative prefix. Convert
        # to absolute when the .blend is saved; fall back to empty when it
        # isn't (an unsaved "//" has no anchor and would round-trip as a
        # warning every capture). Empty means "use the addon-prefs default."
        if fp.startswith("//"):
            abs_fp = bpy.path.abspath(fp)
            fp = abs_fp if not abs_fp.startswith("//") else ""
        studio.output_override = fp

    def apply(self, scene, studio) -> None:
        if studio.output_override:
            scene.render.filepath = studio.output_override


register_facet(OutputPathFacet())
