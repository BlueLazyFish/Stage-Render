"""Studio inheritance — parent-chain resolution for apply.

A child Studio with parent_name="X" inherits from X: on apply, X's facets
write first, then the child's enabled facets override. Disable a facet on
the child to keep the parent's value (the facet's apply step is skipped
when its enabled flag is False).

Order on apply: root → ... → parent → child. Each level overwrites the
previous. The studio referenced by the user's Apply click is the leaf;
its own facets win the final pass.

See ADDON_PLAN.md §5 'Studio inheritance resolution'.
"""

from __future__ import annotations

from .facets import apply_all
from ..utils.logger import get_logger


_log = get_logger()

# Cap deep chains to avoid runaway recursion if data is corrupted in some
# way the cycle detector misses. 8 levels is plenty for real use.
MAX_INHERITANCE_DEPTH = 8


def resolve_parent_chain(
    scene_data,
    studio,
    max_depth: int = MAX_INHERITANCE_DEPTH,
) -> list:
    """Walk parent_name links upward. Returns [root, ..., parent], excluding studio.

    Halts on:
      - empty parent_name (no parent)
      - parent_name not found in scene_data.studios (parent renamed/deleted)
      - cycle detected (a parent appears twice in the chain)
      - max_depth reached
    """
    chain: list = []
    current = studio
    seen = {studio.name}

    for _ in range(max_depth):
        if not current.parent_name:
            break
        parent = scene_data.studios.get(current.parent_name)
        if parent is None:
            _log.warning(
                "Parent %r not found for Studio %r — chain truncated",
                current.parent_name, current.name,
            )
            break
        if parent.name in seen:
            _log.warning(
                "Cycle detected in inheritance at %r — chain truncated",
                parent.name,
            )
            break
        seen.add(parent.name)
        chain.append(parent)
        current = parent

    chain.reverse()
    return chain


def apply_studio(scene, studio) -> None:
    """Apply parent chain (root → parent), then studio's own facets.

    Disabled facets on a child are skipped, so the parent's value for that
    facet survives — this is how 'override only what's stored' works.
    """
    chain = resolve_parent_chain(scene.stage_data, studio) + [studio]
    for s in chain:
        apply_all(scene, s)
