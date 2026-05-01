"""Studio UIList — the row template for the main Studio list."""

import bpy
from bpy.types import UIList


class STAGE_UL_studios(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "color", text="")
            row.prop(item, "name", text="", emboss=False)
            if item.locked:
                row.label(text="", icon='LOCKED')
            row.prop(item, "enabled", text="")
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='IMAGE_DATA')


def register() -> None:
    bpy.utils.register_class(STAGE_UL_studios)


def unregister() -> None:
    bpy.utils.unregister_class(STAGE_UL_studios)
