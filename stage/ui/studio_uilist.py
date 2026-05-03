"""Studio UIList — the row template for the main Studio list."""

import bpy
from bpy.types import UIList

from ..utils.preview_cache import get_icon_id


def matches_filter(needle: str, item) -> bool:
    """Case-insensitive substring match against Studio name, tags, OR group.

    Empty needle matches everything. Pulled out of the UIList class so it's
    testable without instantiating a UIList (which Blender doesn't support).
    """
    if not needle:
        return True
    needle_lower = needle.lower()
    return (
        needle_lower in item.name.lower()
        or needle_lower in item.tags.lower()
        or needle_lower in item.group_name.lower()
    )


class STAGE_UL_studios(UIList):
    def filter_items(self, context, data, propname):
        """Filter Studios by name OR tags — case-insensitive substring match.

        Triggered by the user typing in the filter funnel at the bottom of
        the UIList. Standard `name` matching is extended to also check the
        Studio's comma-separated `tags` field, so a search for "wip" finds
        Studios tagged #wip alongside any whose name contains "wip".
        """
        items = getattr(data, propname)
        flt_flags = [self.bitflag_filter_item] * len(items)
        flt_neworder: list = []

        if self.filter_name:
            for i, item in enumerate(items):
                if not matches_filter(self.filter_name, item):
                    flt_flags[i] = 0

            if self.use_filter_invert:
                flt_flags = [
                    self.bitflag_filter_item if f == 0 else 0
                    for f in flt_flags
                ]

        return flt_flags, flt_neworder

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # List view: color marker + name. Thumbnails were causing UI
            # redraw lag during window resize (template_icon + scale_y=2.0
            # forces layout recalc every frame), and they show better in
            # the grid layout anyway. List view stays snappy this way.
            row = layout.row(align=True)
            color_sub = row.row()
            color_sub.scale_x = 0.4
            color_sub.prop(item, "color", text="")
            row.prop(item, "name", text="", emboss=False)
            if item.locked:
                row.label(text="", icon='LOCKED')
            row.prop(item, "enabled", text="")
        elif self.layout_type == 'GRID':
            # Grid view: this is where thumbnails shine. Toggle from list
            # to grid via the icon at the top-right of the UIList.
            icon_id = 0
            if item.thumbnail_path:
                icon_id = get_icon_id(item.uuid, item.thumbnail_path)
            layout.alignment = 'CENTER'
            if icon_id:
                layout.template_icon(icon_value=icon_id, scale=4.0)
            else:
                layout.label(text="", icon='IMAGE_DATA')


def register() -> None:
    bpy.utils.register_class(STAGE_UL_studios)


def unregister() -> None:
    bpy.utils.unregister_class(STAGE_UL_studios)
