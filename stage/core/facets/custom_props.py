"""Custom-properties facet — applies Studio.custom_paths.

Custom paths are populated by the right-click -> Store Property feature
(see stage.ops.store_property). Capture re-reads the current value of
each stored path so Update keeps them fresh; apply walks the list and
writes each value back via stage.core.store_property.apply_value.

Always-enabled — there's no per-Studio toggle for the custom-props
facet because the user has already curated which paths to store; an
"enable all custom props" toggle would just be a footgun.
"""

from __future__ import annotations

from ..store_property import apply_value, encode_value, resolve_value
from ...utils.logger import get_logger
from . import register_facet


_log = get_logger()


class CustomPropsFacet:
    facet_id = "custom_props"

    def is_enabled(self, studio) -> bool:
        return True

    def capture(self, scene, studio) -> None:
        """Re-read each stored path's current value and update its entry."""
        for entry in studio.custom_paths:
            try:
                value = resolve_value(entry.data_path)
            except Exception as e:
                _log.warning(
                    "Could not re-read %r during capture: %s",
                    entry.data_path, e,
                )
                continue
            value_repr, value_type = encode_value(value, entry.value_type or None)
            entry.value_repr = value_repr
            entry.value_type = value_type

    def apply(self, scene, studio) -> None:
        """Walk custom_paths and apply each stored value."""
        from ..store_property import decode_value
        for entry in studio.custom_paths:
            try:
                value = decode_value(entry.value_repr, entry.value_type)
                apply_value(entry.data_path, value)
            except Exception as e:
                _log.warning(
                    "Failed to apply custom property %r: %s",
                    entry.data_path, e,
                )


register_facet(CustomPropsFacet())
