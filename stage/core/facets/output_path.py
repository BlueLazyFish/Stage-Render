"""Output Path facet — captures and applies Scene.render.filepath.

Simplest of the 5 MVP facets — uses the Studio's existing `output_override`
field rather than a dedicated PropertyGroup.
"""

from __future__ import annotations

import bpy

from . import register_facet


# scene.render.filepath values that Blender auto-populates and that the
# user almost certainly didn't intend as a real output target. Capturing
# any of these would clobber a user-set Studio.output_override on every
# Update Studio click — not what the user expects.
_BLENDER_DEFAULT_FILEPATHS = ("", "/tmp/", "/tmp\\", "//", "//tmp/")


class OutputPathFacet:
    facet_id = "output_path"

    def is_enabled(self, studio) -> bool:
        return studio.facet_output_path_enabled

    def capture(self, scene, studio) -> None:
        fp = scene.render.filepath or ""

        # Don't overwrite a user-set output_override with Blender's
        # auto-populated default. After a render completes, our render
        # helper restores scene.render.filepath to its pre-render value,
        # which is often "/tmp/" — then Update Studio would silently
        # destroy the path the user typed in the Output Path field.
        if fp in _BLENDER_DEFAULT_FILEPATHS:
            return

        # Studio.output_override is subtype='FILE_PATH', which Blender
        # documents as not accepting the "//" blend-relative prefix. Convert
        # to absolute when the .blend is saved; fall back to leaving the
        # existing override alone when it can't be resolved.
        if fp.startswith("//"):
            abs_fp = bpy.path.abspath(fp)
            if abs_fp.startswith("//"):
                return  # .blend not saved — can't make this absolute, skip
            fp = abs_fp

        studio.output_override = fp

    def apply(self, scene, studio) -> None:
        if studio.output_override:
            scene.render.filepath = studio.output_override


register_facet(OutputPathFacet())
