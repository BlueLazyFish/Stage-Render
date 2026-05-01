"""PropertyGroup utilities."""

from __future__ import annotations


def copy_propgroup(src, dst) -> None:
    """Copy writable RNA-defined properties from `src` to `dst`.

    - Skips read-only properties and the 'rna_type' descriptor.
    - Recurses into PointerProperty sub-PropertyGroups.
    - Recurses into CollectionProperty: clears `dst`, then for each item
      in `src`, adds a new item to `dst` and copies recursively.

    `src` and `dst` should be the same PropertyGroup type.
    """
    for prop in src.bl_rna.properties:
        ident = prop.identifier
        if ident == "rna_type":
            continue
        if getattr(prop, "is_readonly", False):
            continue
        if prop.type == 'COLLECTION':
            src_coll = getattr(src, ident)
            dst_coll = getattr(dst, ident)
            dst_coll.clear()
            for src_item in src_coll:
                dst_item = dst_coll.add()
                copy_propgroup(src_item, dst_item)
            continue
        if prop.type == 'POINTER':
            sub_src = getattr(src, ident, None)
            sub_dst = getattr(dst, ident, None)
            if sub_src is not None and sub_dst is not None:
                copy_propgroup(sub_src, sub_dst)
            continue
        try:
            setattr(dst, ident, getattr(src, ident))
        except (AttributeError, TypeError):
            # Some props are conditionally writable depending on parent state;
            # skip silently rather than fail the whole copy.
            pass
