"""Studio UIList — the row template for the main Studio list."""

import bpy
from bpy.types import UIList

from ..utils.preview_cache import get_icon_id


class STAGE_UL_studios(UIList):
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
