"""Facet capture/restore — one module per facet type.

Each facet exposes:
    capture(scene, studio) -> None
    restore(scene, studio) -> None

Facets must satisfy the round-trip invariant:
    capture → mutate → restore → equal

This is the central Phase 1 correctness check; see ADDON_PLAN.md §5 testing.
"""
