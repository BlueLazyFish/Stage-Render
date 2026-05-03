"""Studio render-settings templates.

A template is a render-settings preset (engine + resolution + per-engine
settings) that can be applied to a new Studio. Two sources:

  - Builtin TEMPLATES (this module)        : ship with the addon
  - User templates in StagePreferences     : created by the user via
                                             "Save Current as Template…"

Both share the same dict shape so apply_template_to_studio() works
uniformly. Helpers:

  - capture_template_dict_from_scene(scene)
        Snapshot the current scene's render settings into a template dict
        (used by the save-template operator).
  - user_template_to_dict(user_template)
        Convert a UserTemplate PropertyGroup into the same dict shape so
        apply_template_to_studio() can take either.

The builtin set is intentionally small: one neutral baseline plus four
common deliverable formats (square, portrait, story, YouTube). Users are
expected to save their own task-specific presets for the rest.
"""

from __future__ import annotations

import bpy

from .store_property import decode_value, encode_value


# --- builtin TEMPLATES -----------------------------------------------------


TEMPLATES: dict[str, dict] = {
    "default": {
        "display_name": "Default",
        "engine": "BLENDER_EEVEE",
        "resolution_x": 1920,
        "resolution_y": 1080,
        "resolution_percentage": 100,
        "render_settings": {
            "eevee.taa_render_samples": 64,
        },
    },
    "instagram_square": {
        "display_name": "Instagram Square (1080×1080)",
        "engine": "BLENDER_EEVEE",
        "resolution_x": 1080,
        "resolution_y": 1080,
        "resolution_percentage": 100,
        "render_settings": {
            "eevee.taa_render_samples": 64,
        },
    },
    "instagram_portrait": {
        "display_name": "Instagram Portrait (1080×1350)",
        "engine": "BLENDER_EEVEE",
        "resolution_x": 1080,
        "resolution_y": 1350,
        "resolution_percentage": 100,
        "render_settings": {
            "eevee.taa_render_samples": 64,
        },
    },
    "instagram_story": {
        "display_name": "Instagram Story / Reel (1080×1920)",
        "engine": "BLENDER_EEVEE",
        "resolution_x": 1080,
        "resolution_y": 1920,
        "resolution_percentage": 100,
        "render_settings": {
            "eevee.taa_render_samples": 64,
        },
    },
    "youtube_thumbnail": {
        "display_name": "YouTube Thumbnail (1920×1080)",
        "engine": "BLENDER_EEVEE",
        "resolution_x": 1920,
        "resolution_y": 1080,
        "resolution_percentage": 100,
        "render_settings": {
            "eevee.taa_render_samples": 64,
        },
    },
}


# --- apply -----------------------------------------------------------------


def apply_template_to_studio(studio, template: dict) -> None:
    """Overlay a template's render settings onto a Studio's facet_render.

    Doesn't touch other facets — caller is expected to have already run
    capture_all(scene, studio) so camera / world / visibility are captured
    from the user's current scene.
    """
    f = studio.facet_render
    f.captured = True
    f.engine = template["engine"]

    if "resolution_x" in template:
        f.resolution_x = template["resolution_x"]
    if "resolution_y" in template:
        f.resolution_y = template["resolution_y"]
    if "resolution_percentage" in template:
        f.resolution_percentage = template["resolution_percentage"]

    # Replace the engine-specific settings bag with the template's entries
    f.settings.clear()
    for path, value in template.get("render_settings", {}).items():
        entry = f.settings.add()
        entry.data_path = path
        encoded, type_tag = encode_value(value)
        entry.value_repr = encoded
        entry.value_type = type_tag


# --- capture from scene ----------------------------------------------------


def capture_template_dict_from_scene(scene, display_name: str) -> dict:
    """Snapshot the current scene's render settings as a template dict.

    Walks the engine adapter (if known) for engine-specific RNA paths so
    the saved template applies cleanly to a fresh Studio later.
    """
    # Lazy import — facets registration happens at addon register and we
    # don't want this module to depend on it at import time.
    from .facets.render_settings import _ADAPTERS  # type: ignore[attr-defined]

    engine = scene.render.engine
    template: dict = {
        "display_name": display_name,
        "engine": engine,
        "resolution_x": scene.render.resolution_x,
        "resolution_y": scene.render.resolution_y,
        "resolution_percentage": scene.render.resolution_percentage,
        "render_settings": {},
    }

    adapter = _ADAPTERS.get(engine)
    if adapter is not None:
        for path, type_hint in adapter.rna_paths:
            try:
                value = _resolve(scene, path)
            except AttributeError:
                continue
            template["render_settings"][path] = value

    return template


def _resolve(obj, path: str):
    for part in path.split("."):
        obj = getattr(obj, part)
    return obj


# --- user template <-> dict -----------------------------------------------


def user_template_to_dict(user_template) -> dict:
    """Convert a UserTemplate PropertyGroup into the dict shape that
    apply_template_to_studio() expects."""
    out: dict = {
        "display_name": user_template.display_name,
        "engine": user_template.engine,
        "resolution_x": user_template.resolution_x,
        "resolution_y": user_template.resolution_y,
        "resolution_percentage": user_template.resolution_percentage,
        "render_settings": {},
    }
    for entry in user_template.settings:
        out["render_settings"][entry.data_path] = decode_value(
            entry.value_repr, entry.value_type
        )
    return out


def write_dict_to_user_template(user_template, src: dict) -> None:
    """Inverse of user_template_to_dict — populate a UserTemplate from a
    template dict (used by the save-from-scene operator)."""
    user_template.display_name = src["display_name"]
    user_template.engine = src["engine"]
    user_template.resolution_x = src.get("resolution_x", 1920)
    user_template.resolution_y = src.get("resolution_y", 1080)
    user_template.resolution_percentage = src.get("resolution_percentage", 100)
    user_template.settings.clear()
    for path, value in src.get("render_settings", {}).items():
        entry = user_template.settings.add()
        entry.data_path = path
        encoded, type_tag = encode_value(value)
        entry.value_repr = encoded
        entry.value_type = type_tag
