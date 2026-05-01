#!/usr/bin/env python3
"""Stage stress test — Phase 1 deliverable.

Creates N Studios with M custom-stored props each, then times the
operations the plan calls out (§5 testing strategy):

    add | switch | save | load

Run from a Blender 5.1+ instance:

    blender -b -P scripts/stress.py [-- --studios N --props M]

Defaults match Renderset's claimed scale (1000 contexts × 50 props).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parent.parent


def _ensure_addon():
    """Register Stage if not already registered."""
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    import bpy
    if not hasattr(bpy.types.Scene, "stage_data"):
        import stage
        stage.register()


def _setup_test_scene(name: str = "stress"):
    import bpy
    if name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[name], do_unlink=True)
    scene = bpy.data.scenes.new(name)

    # A minimal but realistic scene: cube + camera + world
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    obj = bpy.data.objects.new(f"{name}_cube", mesh)
    scene.collection.objects.link(obj)

    cam_data = bpy.data.cameras.new(f"{name}_cam_data")
    cam_obj = bpy.data.objects.new(f"{name}_cam", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    world = bpy.data.worlds.new(f"{name}_world")
    scene.world = world

    return scene


def run(num_studios: int = 1000, num_props: int = 50) -> dict[str, Any]:
    """Execute the stress test. Returns a dict of timings + sizes (no print)."""
    _ensure_addon()
    import bpy

    from stage.core.facets import apply_all, capture_all
    from stage.utils.propgroup import copy_propgroup

    scene = _setup_test_scene()
    bpy.context.window.scene = scene
    data = scene.stage_data

    # --- Phase 1: build the template Studio (realistic facet data) ---
    t0 = time.perf_counter()
    template = data.studios.add()
    template.name = "Template"
    template.uuid = "stress-template"
    capture_all(scene, template)
    for j in range(num_props):
        p = template.custom_paths.add()
        p.data_path = f"bpy.context.scene.field_{j}"
        p.value_repr = str(j)
        p.value_type = 'INT'
    setup_template_ms = (time.perf_counter() - t0) * 1000

    # --- Phase 2: clone the template N-1 times via copy_propgroup ---
    t0 = time.perf_counter()
    for i in range(1, num_studios):
        new = data.studios.add()
        copy_propgroup(template, new)
        new.name = f"Studio {i:04d}"
        new.uuid = f"stress-{i}"
    add_studios_ms = (time.perf_counter() - t0) * 1000

    # --- Phase 3: switch (apply) — time three apply calls ---
    t0 = time.perf_counter()
    apply_all(scene, data.studios[0])
    apply_all(scene, data.studios[num_studios // 2])
    apply_all(scene, data.studios[-1])
    switch_total_ms = (time.perf_counter() - t0) * 1000

    # --- Phase 4: save .blend ---
    save_path = Path(tempfile.gettempdir()) / "stage_stress.blend"
    if save_path.exists():
        save_path.unlink()
    t0 = time.perf_counter()
    bpy.ops.wm.save_as_mainfile(filepath=str(save_path))
    save_ms = (time.perf_counter() - t0) * 1000
    blend_size_mb = save_path.stat().st_size / (1024 * 1024)

    # --- Phase 5: load .blend ---
    t0 = time.perf_counter()
    bpy.ops.wm.open_mainfile(filepath=str(save_path))
    load_ms = (time.perf_counter() - t0) * 1000

    # Verify reload preserved Studio count
    reloaded_count = len(bpy.context.scene.stage_data.studios)

    save_path.unlink(missing_ok=True)

    return {
        "num_studios": num_studios,
        "num_props_per_studio": num_props,
        "total_stored_props": num_studios * num_props,
        "setup_template_ms": setup_template_ms,
        "add_studios_ms": add_studios_ms,
        "add_per_studio_us": (add_studios_ms * 1000) / max(num_studios - 1, 1),
        "switch_avg_ms": switch_total_ms / 3,
        "save_ms": save_ms,
        "load_ms": load_ms,
        "blend_size_mb": blend_size_mb,
        "reloaded_studio_count": reloaded_count,
    }


def _format_report(r: dict[str, Any]) -> str:
    return "\n".join([
        f"Stage stress test — {r['num_studios']:,} Studios × {r['num_props_per_studio']} custom props each",
        f"Total stored entries: {r['total_stored_props']:,}",
        "",
        f"  Setup template Studio        {r['setup_template_ms']:>10.1f} ms",
        f"  Add {r['num_studios'] - 1:,} clones                {r['add_studios_ms']:>10.1f} ms  ({r['add_per_studio_us']:.0f} µs/Studio)",
        f"  Switch (avg of 3 applies)    {r['switch_avg_ms']:>10.1f} ms",
        f"  Save .blend                  {r['save_ms']:>10.1f} ms  ({r['blend_size_mb']:.2f} MB)",
        f"  Load .blend                  {r['load_ms']:>10.1f} ms  (Studios after reload: {r['reloaded_studio_count']:,})",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--studios", type=int, default=1000, help="Number of Studios (default: 1000)")
    parser.add_argument("--props", type=int, default=50, help="Custom-stored props per Studio (default: 50)")

    # When run via `blender -b -P scripts/stress.py -- --studios 100`, argparse
    # needs to skip everything before the `--` sentinel.
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)

    report = run(args.studios, args.props)
    print(_format_report(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
