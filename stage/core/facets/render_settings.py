"""Render Settings facet — engine + common settings + engine-specific bag.

The facet itself is engine-agnostic. Engine adapters know which RNA paths
matter for each engine. Switching a Studio's engine populates a fresh
bag from that engine's adapter rather than carrying stale settings.

Adapters (Phase 1):
  - CyclesAdapter    — 'CYCLES'
  - EeveeAdapter     — 'BLENDER_EEVEE' (this is EEVEE Next — the engine
                       ID reverted to 'BLENDER_EEVEE' in Blender 4.3+
                       after the legacy engine was removed)
  - WorkbenchAdapter — 'BLENDER_WORKBENCH'

Adding third-party engines (Octane, LuxCore, TurboTools) is just a matter
of registering another adapter — see Phase 4 in ADDON_PLAN.md.

Each adapter declares `engine_id` and `rna_paths` (a tuple of
(scene-relative path, value type hint)). The shared _BaseAdapter handles
the capture/apply loop generically. Missing RNA paths are logged + skipped
rather than raising, so adapters don't need to be exhaustively correct
across every Blender version.
"""

from __future__ import annotations

import bpy

from ...utils.logger import get_logger
from . import register_facet


_log = get_logger()


# --- value encode/decode ----------------------------------------------------


def _encode(value) -> str:
    return str(value)


def _decode(s: str, type_hint: str):
    if type_hint == 'INT':
        return int(s)
    if type_hint == 'FLOAT':
        return float(s)
    if type_hint == 'BOOL':
        return s == 'True'
    return s  # STRING, ENUM


def _resolve(obj, path: str):
    """Walk a dotted path on obj. Raises AttributeError on missing segment."""
    for part in path.split('.'):
        obj = getattr(obj, part)
    return obj


def _set(obj, path: str, value) -> None:
    """Walk to the parent of the final segment, then setattr."""
    parts = path.split('.')
    parent = obj
    for part in parts[:-1]:
        parent = getattr(parent, part)
    setattr(parent, parts[-1], value)


# --- engine adapters --------------------------------------------------------


class _BaseAdapter:
    engine_id: str = ""
    rna_paths: tuple[tuple[str, str], ...] = ()

    def capture(self, scene, facet) -> None:
        for path, type_hint in self.rna_paths:
            try:
                value = _resolve(scene, path)
            except AttributeError:
                # Path doesn't exist on this Blender version / engine setup
                continue
            entry = facet.settings.add()
            entry.data_path = path
            entry.value_repr = _encode(value)
            entry.value_type = type_hint

    def apply(self, scene, facet) -> None:
        for entry in facet.settings:
            try:
                _set(scene, entry.data_path, _decode(entry.value_repr, entry.value_type))
            except (AttributeError, TypeError, ValueError) as e:
                _log.warning(
                    "Failed to apply render setting %r: %s: %s",
                    entry.data_path, type(e).__name__, e,
                )


class CyclesAdapter(_BaseAdapter):
    engine_id = 'CYCLES'
    rna_paths = (
        ('cycles.samples', 'INT'),
        ('cycles.preview_samples', 'INT'),
        ('cycles.use_denoising', 'BOOL'),
        ('cycles.use_preview_denoising', 'BOOL'),
        ('cycles.max_bounces', 'INT'),
        ('cycles.diffuse_bounces', 'INT'),
        ('cycles.glossy_bounces', 'INT'),
        ('cycles.transmission_bounces', 'INT'),
        ('cycles.volume_bounces', 'INT'),
        ('cycles.transparent_max_bounces', 'INT'),
        ('cycles.use_animated_seed', 'BOOL'),
        ('cycles.seed', 'INT'),
        ('cycles.device', 'ENUM'),
        ('cycles.feature_set', 'ENUM'),
    )


class EeveeAdapter(_BaseAdapter):
    # 'BLENDER_EEVEE' is EEVEE Next — the engine ID reverted in 4.3+ after
    # the legacy engine was removed. The plan (§5 compatibility) needs
    # updating to reflect this.
    engine_id = 'BLENDER_EEVEE'
    rna_paths = (
        ('eevee.taa_render_samples', 'INT'),
        ('eevee.taa_samples', 'INT'),
    )


class WorkbenchAdapter(_BaseAdapter):
    engine_id = 'BLENDER_WORKBENCH'
    # No engine-specific settings captured for Phase 1; Workbench is mostly
    # configured via View3DShading-equivalent settings on render.shading.
    rna_paths = ()


_ADAPTERS = {
    a.engine_id: a
    for a in (CyclesAdapter(), EeveeAdapter(), WorkbenchAdapter())
}


# --- facet ------------------------------------------------------------------


class RenderSettingsFacet:
    facet_id = "render_settings"

    def is_enabled(self, studio) -> bool:
        return studio.facet_render_enabled

    def capture(self, scene, studio) -> None:
        f = studio.facet_render
        f.captured = True
        f.settings.clear()

        f.engine = scene.render.engine
        f.resolution_x = scene.render.resolution_x
        f.resolution_y = scene.render.resolution_y
        f.resolution_percentage = scene.render.resolution_percentage
        f.fps = scene.render.fps
        f.fps_base = scene.render.fps_base

        adapter = _ADAPTERS.get(f.engine)
        if adapter is not None:
            adapter.capture(scene, f)
        # Unknown engine (e.g. third-party not yet adapted) is fine — we still
        # capture common settings + the engine ID so apply restores at least
        # those.

    def apply(self, scene, studio) -> None:
        f = studio.facet_render
        if not f.captured:
            return

        # Engine first — engine-specific properties only become valid after
        # scene.render.engine is set.
        if f.engine:
            try:
                scene.render.engine = f.engine
            except (TypeError, ValueError) as e:
                _log.warning("Could not set render engine to %r: %s", f.engine, e)

        scene.render.resolution_x = f.resolution_x
        scene.render.resolution_y = f.resolution_y
        scene.render.resolution_percentage = f.resolution_percentage
        scene.render.fps = f.fps
        scene.render.fps_base = f.fps_base

        adapter = _ADAPTERS.get(f.engine)
        if adapter is not None:
            adapter.apply(scene, f)


register_facet(RenderSettingsFacet())
