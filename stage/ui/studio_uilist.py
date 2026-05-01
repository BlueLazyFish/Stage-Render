"""Studio UIList — the row template for the main Studio list."""

import bpy
from bpy.types import UIList

from ..utils.preview_cache import get_icon_id


class STAGE_UL_studios(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "color", text="")
            # Thumbnail icon, if rendered. Falls back to no icon (just name)
            # so the row stays compact when the Studio hasn't been thumbed yet.
            if item.thumbnail_path:
                icon_id = get_icon_id(item.uuid, item.thumbnail_path)
                if icon_id:
                    row.label(text="", icon_value=icon_id)
            row.prop(item, "name", text="", emboss=False)
            if item.locked:
                row.label(text="", icon='LOCKED')
            row.prop(item, "enabled", text="")
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            if item.thumbnail_path:
                icon_id = get_icon_id(item.uuid, item.thumbnail_path)
                if icon_id:
                    layout.template_icon(icon_value=icon_id, scale=4.0)
                    return
            layout.label(text="", icon='IMAGE_DATA')


def register() -> None:
    bpy.utils.register_class(STAGE_UL_studios)


def unregister() -> None:
    bpy.utils.unregister_class(STAGE_UL_studios)
