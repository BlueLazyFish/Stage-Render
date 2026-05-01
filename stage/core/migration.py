"""In-blend storage format migrations.

Schema version lives on Scene.stage_data.format_version. When we make a
breaking change, bump CURRENT_FORMAT_VERSION in props.studio_collection
and add a forward migration here.
"""

from __future__ import annotations

from typing import Callable

from ..props.studio_collection import CURRENT_FORMAT_VERSION
from ..utils.logger import get_logger


_log = get_logger()


# Map: version we're migrating FROM → callable that migrates to FROM+1.
# Each migration must be idempotent and modify only what changed.
_MIGRATIONS: dict[int, Callable[..., None]] = {}


def migrate(stage_data) -> None:
    """Apply forward migrations until format_version matches CURRENT_FORMAT_VERSION."""
    if stage_data is None:
        return

    while stage_data.format_version < CURRENT_FORMAT_VERSION:
        v = stage_data.format_version
        fn = _MIGRATIONS.get(v)
        if fn is None:
            _log.warning(
                "No migration registered for format_version %d → %d; halting",
                v, v + 1,
            )
            break
        _log.info("Migrating Stage data: v%d → v%d", v, v + 1)
        fn(stage_data)
        stage_data.format_version = v + 1
