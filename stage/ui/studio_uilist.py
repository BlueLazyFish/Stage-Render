"""Studio UIList — the row template for the main Studio list."""

import bpy
from bpy.types import UIList

from ..utils.preview_cache import get_icon_id


class STAGE_UL_studios(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # Resolve thumbnail icon (or 0 if not rendered / file missing)
        icon_id = 0
        if item.thumbnail_path:
            icon_id = get_icon_id(item.uuid, item.thumbnail_path)

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            # Color stripe — small visual marker per Studio
            row.prop(item, "color", text="")
            # Thumbnail (or fallback icon if not yet rendered / file missing)
            if icon_id:
                row.label(text="", icon_value=icon_id)
            else:
                row.label(text="", icon='IMAGE_DATA')
            row.prop(item, "name", text="", emboss=False)
            if item.locked:
                row.label(text="", icon='LOCKED')
            row.prop(item, "enabled", text="")
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            if icon_id:
                layout.template_icon(icon_value=icon_id, scale=4.0)
            else:
                layout.label(text="", icon='IMAGE_DATA')


def register() -> None:
    bpy.utils.register_class(STAGE_UL_studios)


def unregister() -> None:
    bpy.utils.unregister_class(STAGE_UL_studios)
