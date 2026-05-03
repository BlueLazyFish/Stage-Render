"""N-panel layout — see ADDON_PLAN.md §5 for the full subpanel structure.

Phase 0 ships the Studio List + minimal Toolbox. Subpanels arrive in Phase 1.
"""

import bpy
from bpy.types import Panel

from ..prefs import get_prefs


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

        # Default output path — shared across all scenes (addon-level setting,
        # editable here for convenience instead of digging into prefs). Each
        # Studio can override this in its details box below.
        prefs = get_prefs(context)
        if prefs is not None:
            col = layout.column(align=True)
            col.label(text="Default Output Path:")
            col.prop(prefs, "default_output_pattern", text="")
            layout.separator()

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
        col.menu("STAGE_MT_templates", icon='PRESET', text="")
        col.separator()
        op_up = col.operator("stage.studio_move", icon='TRIA_UP', text="")
        op_up.direction = 'UP'
        op_down = col.operator("stage.studio_move", icon='TRIA_DOWN', text="")
        op_down.direction = 'DOWN'

        if data.studios and 0 <= data.active_index < len(data.studios):
            active = data.studios[data.active_index]

            # Dirty-state badge — visible only when the scene was mutated after
            # the last apply or update. Apply re-applies (discards changes);
            # Update captures the current scene into the Studio.
            if data.dirty:
                row = layout.row()
                row.alert = True
                row.label(text="● Uncommitted changes", icon='ERROR')

            # Apply / Update — the central operations
            row = layout.row(align=True)
            row.operator("stage.studio_apply", icon='IMPORT')
            row.operator("stage.studio_update_from_scene", icon='FILE_REFRESH')
            row.operator("stage.studio_refresh_thumbnail", icon='IMAGE_DATA', text="")

            # Render — single Studio or batch all enabled
            row = layout.row(align=True)
            row.operator("stage.studio_render_one", icon='RENDER_STILL')
            row.operator("stage.studio_render_all", icon='RENDER_STILL', text="Render All")

            box = layout.box()

            # Lock toggle — always editable so the user can unlock from the
            # same UI that's otherwise greyed out.
            row = box.row()
            row.prop(
                active, "locked",
                icon='LOCKED' if active.locked else 'UNLOCKED',
            )

            # Everything below: read-only when the Studio is locked.
            details = box.column()
            details.enabled = not active.locked

            details.prop(active, "name")

            # Parent Studio — inheritance. Disable a facet on this Studio to
            # keep the parent's value for that facet.
            details.prop_search(
                active, "parent_name",
                data, "studios",
                text="Parent",
                icon='OUTLINER_OB_GROUP_INSTANCE',
            )

            # Output Path — label on its own line so the field gets full width
            col = details.column(align=True)
            col.label(text="Output Path:")
            col.prop(active, "output_override", text="")

            # Facet capture toggles — what this Studio remembers
            fcol = details.column(align=True)
            fcol.label(text="Capture:")
            fcol.prop(active, "facet_camera_enabled", text="Camera")
            fcol.prop(active, "facet_world_enabled", text="World")
            fcol.prop(active, "facet_visibility_enabled", text="Visibility")
            fcol.prop(active, "facet_render_enabled", text="Render Settings")
            fcol.prop(active, "facet_output_path_enabled", text="Output Path")

            details.prop(active, "notes")
            details.prop(active, "tags")

            # Stored custom properties — added via right-click → Store in Stage.
            stored_count = len(active.custom_paths)
            if stored_count:
                box = details.box()
                box.label(
                    text=f"Stored Properties ({stored_count})",
                    icon='RNA',
                )
                for entry in active.custom_paths:
                    row = box.row(align=True)
                    row.label(text=entry.data_path)
                    row.label(text=entry.value_repr)


_classes = (STAGE_PT_main,)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
