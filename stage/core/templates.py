"""Starter Studio templates — pre-configured Studios for first-install activation.

Each template is a dict with engine + resolution + per-engine settings +
default output pattern. The template operator (stage.ops.templates) creates
a new Studio, captures the user's current scene state for non-render facets,
then overlays the template's render settings on top.

Three render-settings templates ship in v1.0:
  - Cycles Quality   : 256 samples, denoising, max_bounces=12, 1080p
  - EEVEE Preview    : EEVEE Next, low samples, 720p (fast iteration)
  - Print 4K         : Cycles 512 samples + denoising, 3840×2160

Full scene-setup templates (Three-point lighting, Product turntable,
Architectural day/night per the plan) require bundled .blend assets and
land in v1.x.
"""

from __future__ import annotations

from .store_property import encode_value


# Templates carry render settings only — output paths fall through to the
# addon-prefs default_output_pattern (or a per-Studio override the user picks
# via the FILE_PATH browse button). Setting output_override from the template
# would inherit the "//" relative-prefix issue (FILE_PATH subtype rejects it).
TEMPLATES: dict[str, dict] = {
    "cycles_quality": {
        "display_name": "Cycles Quality",
        "engine": "CYCLES",
        "resolution_x": 1920,
        "resolution_y": 1080,
        "resolution_percentage": 100,
        "render_settings": {
            "cycles.samples": 256,
            "cycles.use_denoising": True,
            "cycles.max_bounces": 12,
        },
    },
    "eevee_preview": {
        "display_name": "EEVEE Preview",
        "engine": "BLENDER_EEVEE",
        "resolution_x": 1280,
        "resolution_y": 720,
        "resolution_percentage": 100,
        "render_settings": {
            "eevee.taa_render_samples": 16,
        },
    },
    "print_4k": {
        "display_name": "Print 4K",
        "engine": "CYCLES",
        "resolution_x": 3840,
        "resolution_y": 2160,
        "resolution_percentage": 100,
        "render_settings": {
            "cycles.samples": 512,
            "cycles.use_denoising": True,
        },
    },
}


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
