"""Output path variable expansion — single source of truth for {var} substitution.

Used by every output-related feature (render output, queue jobs, post-render
actions). See ADDON_PLAN.md §3 MVP for the full variable list.

Pure-Python — no bpy import — so it's unit-testable outside Blender.
"""

from __future__ import annotations

import datetime
import getpass
import platform as _platform
import re
from pathlib import Path
from typing import Any


# Characters that must never appear in a path component generated from
# user input (Studio names, group names). Slashes specifically must NOT
# act as path delimiters when interpolated into {studio} — Renderset
# fixed this footgun in 2.0.1; we avoid it from day one.
_UNSAFE_RE = re.compile(r'[/\\:*?"<>|\x00-\x1f]')

_RESERVED_WIN = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

# Matches {var} or {var:format_spec} — anchored so we don't accidentally
# capture `{` inside literal text.
_TOKEN_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)(:[^{}]*)?\}")


def sanitize_name(name: str) -> str:
    """Strip path-unsafe characters and reserved Windows names from a display name."""
    cleaned = _UNSAFE_RE.sub("_", name).strip().rstrip(".")
    if cleaned.upper() in _RESERVED_WIN:
        cleaned = f"_{cleaned}"
    return cleaned or "_"


def expand_path(template: str, ctx: dict[str, Any]) -> str:
    """Expand {var} tokens in template using ctx.

    Unknown variables are left as literal {var} rather than raising — fail open.
    String values are passed through sanitize_name to keep them path-safe.
    Format specs like {frame:04d} are honored.
    """
    if not template:
        return ""

    safe_ctx: dict[str, Any] = {}
    for k, v in ctx.items():
        safe_ctx[k] = sanitize_name(v) if isinstance(v, str) else v

    def sub(m: re.Match) -> str:
        key = m.group(1)
        spec = m.group(2) or ""
        if key not in safe_ctx:
            return m.group(0)
        try:
            return f"{{{spec}}}".format(safe_ctx[key])
        except (ValueError, TypeError):
            return str(safe_ctx[key])

    return _TOKEN_RE.sub(sub, template)


def build_default_context(
    *,
    studio_name: str = "",
    studio_group: str = "",
    blend_path: str | Path = "",
    scene: Any = None,
    frame: int = 1,
    render_type: str = "still",
    frozen_now: datetime.datetime | None = None,
) -> dict[str, Any]:
    """Build the full variable context for one render.

    `frozen_now` lets a batch of renders share a single timestamp so outputs
    group as a coherent batch (Renderset's "Freeze time" trick — see plan §3 v1.0).
    """
    now = frozen_now or datetime.datetime.now()
    blend = Path(blend_path) if blend_path else Path()

    ctx: dict[str, Any] = {
        # Studio context
        "studio": studio_name,
        "studio_group": studio_group,
        "context_render_type": render_type,
        # File
        "blendname": blend.stem if blend.name else "",
        "blend_filename": blend.stem if blend.name else "",
        "blend_parent_folder": str(blend.parent) if blend.name else "",
        "blend_full_path": str(blend) if blend.name else "",
        # Frame
        "frame": frame,
        "frame_current": frame,
        "frame_start": 1,
        "frame_end": 250,
        "frame_step": 1,
        # Date/time — split components let users build folder hierarchies
        "date_time": now.strftime("%Y-%m-%dT%H-%M-%S"),
        "year": now.strftime("%Y"),
        "month": now.strftime("%m"),
        "day": now.strftime("%d"),
        "hour": now.strftime("%H"),
        "minute": now.strftime("%M"),
        "second": now.strftime("%S"),
        # System
        "user": getpass.getuser(),
        "machine": _platform.node(),
        "hostname": _platform.node(),
        "ext": "png",
    }

    if scene is not None:
        cam = getattr(scene, "camera", None)
        world = getattr(scene, "world", None)
        render = getattr(scene, "render", None)
        ctx["camera"] = getattr(cam, "name", "") if cam else ""
        ctx["world"] = getattr(world, "name", "") if world else ""
        if render is not None:
            res_x = render.resolution_x
            res_y = render.resolution_y
            pct = render.resolution_percentage
            ctx["resolution_x"] = res_x
            ctx["resolution_y"] = res_y
            ctx["resolution_percentage"] = pct
            ctx["resolution_x_scaled"] = int(res_x * pct / 100)
            ctx["resolution_y_scaled"] = int(res_y * pct / 100)

    return ctx
