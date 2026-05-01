"""N-panel layout — see ADDON_PLAN.md §5 for the full subpanel structure.

Phase 0 ships the Studio List + minimal Toolbox. Subpanels arrive in Phase 1.
"""

import bpy
from bpy.types import Panel


_CATEGORY = "Stage"


class STAGE_PT_main(Panel):
    bl_idname = "STAGE_PT_main"
    bl_label = "Stage"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = _CATEGORY

    def draw(self, context):
        layout = self.layout
        data = context.scene.stage_data

        row = layout.row()
        row.template_list(
            "STAGE_UL_studios", "",
            data, "studios",
            data, "active_index",
            rows=4,
        )

        col = row.column(align=True)
        col.operator("stage.studio_add", icon='ADD', text="")
        col.operator("stage.studio_remove", icon='REMOVE', text="")
        col.separator()
        col.operator("stage.studio_duplicate", icon='DUPLICATE', text="")
        col.separator()
        op_up = col.operator("stage.studio_move", icon='TRIA_UP', text="")
        op_up.direction = 'UP'
        op_down = col.operator("stage.studio_move", icon='TRIA_DOWN', text="")
        op_down.direction = 'DOWN'

        if data.studios and 0 <= data.active_index < len(data.studios):
            active = data.studios[data.active_index]
            box = layout.box()
            box.prop(active, "name")
            box.prop(active, "notes")
            box.prop(active, "tags")


_classes = (STAGE_PT_main,)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
