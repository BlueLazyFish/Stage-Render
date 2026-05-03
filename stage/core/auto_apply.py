"""Click-to-preview — auto-apply on active_index change.

When the user enables `auto_apply_on_select` in addon preferences,
selecting a different Studio in the UIList instantly applies that
Studio to the scene. KeyShot-style "hover to preview" is left for
v1.x (it requires a modal operator polling mouse position over
UIList row bounds — significantly more code).

Logic lives here so it's testable independently of the property-
update callback that wires it into StudioCollection.active_index.
"""

from __future__ import annotations

from .inheritance import apply_studio
from ..handlers import set_apply_in_progress


def maybe_auto_apply(stage_data, scene, *, auto_apply: bool) -> bool:
    """Apply the active Studio if `auto_apply` is True. Returns True if applied."""
    if not auto_apply:
        return False
    idx = stage_data.active_index
    if not (0 <= idx < len(stage_data.studios)):
        return False
    studio = stage_data.studios[idx]

    set_apply_in_progress(True)
    try:
        apply_studio(scene, studio)
        stage_data.last_applied_studio_uuid = studio.uuid
        stage_data.dirty = False
        stage_data.suppress_next_dirty_fire = True
    finally:
        set_apply_in_progress(False)
    return True


def on_active_index_change(self, context) -> None:
    """Property-update callback wired to StudioCollection.active_index.

    Reads the prefs toggle and delegates. Imports prefs lazily because
    studio_collection is registered before prefs in props/__init__.py.
    """
    from ..prefs import get_prefs
    prefs = get_prefs(context)
    auto_apply = bool(prefs and prefs.auto_apply_on_select)
    maybe_auto_apply(self, context.scene, auto_apply=auto_apply)
