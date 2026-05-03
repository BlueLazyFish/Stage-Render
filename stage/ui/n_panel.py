"""N-panel layout — see ADDON_PLAN.md §5 for the full subpanel structure.

Three collapsible subpanels stack under STAGE_PT_main:

  STAGE_PT_main             Studio list, add/remove/duplicate/move,
                            Default Output Path, Apply/Update/Render row.
  STAGE_PT_active_studio    Per-Studio details (name, parent, group,
                            output, capture toggles, notes, tags,
                            stored properties, post-render actions).
                            Hidden when the list is empty.
  STAGE_PT_bulk_edit        Multi-selection + bulk operators.
  STAGE_PT_groups           Group/variant-axis management.

Other panels (queue_panel, lister) live in their own modules.

bl_order pins the visible stack so re-ordering subpanels happens here
rather than relying on registration order.
"""

import bpy
from bpy.types import Panel

from ..prefs import get_prefs


_CATEGORY = "Stage"


# --- helpers ---------------------------------------------------------------


def _active_studio(context):
    data = context.scene.stage_data
    if not data.studios:
        return None
    if not (0 <= data.active_index < len(data.studios)):
        return None
    return data.studios[data.active_index]


def _shorten_for_display(path: str, max_len: int = 60) -> tuple[str, str]:
    """Split a resolved path into (directory, filename) for two-line display.

    Filename is full; directory is truncated from the left with an ellipsis
    if longer than max_len so the most meaningful part (the leaf folder)
    stays visible.
    """
    if not path:
        return ("", "")
    if "/" in path:
        directory, filename = path.rsplit("/", 1)
    elif "\\" in path:
        directory, filename = path.rsplit("\\", 1)
    else:
        directory, filename = "", path
    if directory and len(directory) > max_len:
        directory = "…" + directory[-(max_len - 1):]
    return (directory, filename)


# --- main panel ------------------------------------------------------------


class STAGE_PT_main(Panel):
    bl_idname = "STAGE_PT_main"
    bl_label = "Stage"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = _CATEGORY
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        data = context.scene.stage_data

        # Studio list with sidebar buttons
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
        # wm.call_menu instead of col.menu so the button renders with the
        # same flat operator style as its siblings — col.menu draws the
        # menu trigger with a permanently-recessed look in narrow columns.
        col.operator("wm.call_menu", icon='PRESET_NEW', text="").name = "STAGE_MT_templates"
        col.separator()
        op_up = col.operator("stage.studio_move", icon='TRIA_UP', text="")
        op_up.direction = 'UP'
        op_down = col.operator("stage.studio_move", icon='TRIA_DOWN', text="")
        op_down.direction = 'DOWN'

        # Apply / Update / Render — only meaningful when a Studio is active
        active = _active_studio(context)
        if active is not None:
            if data.dirty:
                row = layout.row()
                row.alert = True
                row.label(text="● Uncommitted changes", icon='ERROR')

            # Apply | Update on one row, Render | Render All on another.
            # Update already re-renders the thumbnail.
            row = layout.row(align=True)
            row.operator("stage.studio_apply", icon='IMPORT')
            row.operator("stage.studio_update_from_scene", icon='FILE_REFRESH')

            row = layout.row(align=True)
            row.operator("stage.studio_render_one", icon='RENDER_STILL')
            row.operator("stage.studio_render_all", icon='RENDER_STILL', text="Render All")

        # Default Output Path — useful but rarely changed; tucked at the
        # bottom so it doesn't dominate the panel header. Editable here
        # for convenience instead of digging into addon prefs.
        prefs = get_prefs(context)
        if prefs is not None:
            layout.separator()
            col = layout.column(align=True)
            col.label(text="Default Output Path:", icon='FILE_FOLDER')
            col.prop(prefs, "default_output_pattern", text="")


# --- active studio details (own subpanel) ---------------------------------


class STAGE_PT_active_studio(Panel):
    bl_idname = "STAGE_PT_active_studio"
    bl_label = "Active Studio"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = _CATEGORY
    bl_order = 1

    @classmethod
    def poll(cls, context):
        # Hide entirely when there's no active Studio — no point rendering
        # a header that just says "nothing selected".
        return _active_studio(context) is not None

    def draw_header(self, context):
        active = _active_studio(context)
        if active is None:
            return
        # Lock toggle as a small icon in the header — out of the main
        # column so it doesn't dominate the details body. Always editable
        # so you can unlock from the same UI that's otherwise greyed out.
        row = self.layout.row(align=True)
        row.prop(
            active, "locked",
            text="",
            icon='LOCKED' if active.locked else 'UNLOCKED',
            emboss=False,
        )
        row.label(text=active.name)

    def draw(self, context):
        layout = self.layout
        data = context.scene.stage_data
        active = _active_studio(context)
        if active is None:
            return

        # Everything below: read-only when the Studio is locked.
        details = layout.column()
        details.enabled = not active.locked

        details.prop(active, "name")

        # Parent / Group on a row so they share width
        details.prop_search(
            active, "parent_name",
            data, "studios",
            text="Parent",
            icon='OUTLINER_OB_GROUP_INSTANCE',
        )
        details.prop_search(
            active, "group_name",
            data, "groups",
            text="Group",
            icon='GROUP',
        )

        # Output Path: field on its own line + a two-line resolved hint
        # (folder above, filename below) so long paths stay readable.
        col = details.column(align=True)
        col.label(text="Output Path:", icon='FILE_FOLDER')
        col.prop(active, "output_override", text="")
        try:
            from ..core.render import resolve_output_path
            from ..prefs import get_default_output_pattern
            resolved = resolve_output_path(
                context.scene, active,
                get_default_output_pattern(context),
            )
            directory, filename = _shorten_for_display(resolved)
            hint = col.box().column(align=True)
            hint.scale_y = 0.7
            if directory:
                hint.label(text=directory)
            hint.label(text=filename, icon='FILE_TICK')
        except Exception:
            pass

        # Capture toggles compacted into a single row of icon-toggles.
        # Tooltips come from each property's `name`. Saves 4 vertical rows.
        details.label(text="Capture:")
        row = details.row(align=True)
        row.prop(active, "facet_camera_enabled", text="", icon='OUTLINER_OB_CAMERA', toggle=True)
        row.prop(active, "facet_world_enabled", text="", icon='WORLD', toggle=True)
        row.prop(active, "facet_visibility_enabled", text="", icon='HIDE_OFF', toggle=True)
        row.prop(active, "facet_render_enabled", text="", icon='SCENE', toggle=True)
        row.prop(active, "facet_output_path_enabled", text="", icon='FILE_TICK', toggle=True)

        details.prop(active, "notes")
        details.prop(active, "tags")

        # Stored custom properties — only show the body when there's something
        # to show; the global Lister panel covers cross-Studio search.
        stored_count = len(active.custom_paths)
        if stored_count:
            sbox = details.box()
            sbox.label(
                text=f"Stored Properties ({stored_count})",
                icon='RNA',
            )
            for entry in active.custom_paths:
                row = sbox.row(align=True)
                row.label(text=entry.data_path)
                row.label(text=entry.value_repr)

        # Post-render actions
        pbox = details.box()
        header = pbox.row(align=True)
        header.label(
            text=f"Post-Render Actions ({len(active.post_render_actions)})",
            icon='SCRIPTPLUGINS',
        )
        header.operator("stage.add_post_render_action", icon='ADD', text="")
        for i, action in enumerate(active.post_render_actions):
            row = pbox.row(align=True)
            row.prop(action, "action_type", text="")
            row.prop(action, "target", text="")
            op_up = row.operator("stage.move_post_render_action", icon='TRIA_UP', text="")
            op_up.index = i
            op_up.direction = 'UP'
            op_down = row.operator("stage.move_post_render_action", icon='TRIA_DOWN', text="")
            op_down.index = i
            op_down.direction = 'DOWN'
            op_rm = row.operator("stage.remove_post_render_action", icon='X', text="")
            op_rm.index = i
            if action.action_type == 'SLACK_WEBHOOK':
                sub = pbox.row(align=True)
                sub.label(text="")
                sub.prop(action, "message", text="Message")


# --- bulk edit -------------------------------------------------------------


class STAGE_PT_bulk_edit(Panel):
    """Multi-selection + bulk-edit operators — collapsible subpanel."""
    bl_idname = "STAGE_PT_bulk_edit"
    bl_label = "Bulk Edit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = _CATEGORY
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 3

    def draw(self, context):
        layout = self.layout
        data = context.scene.stage_data

        sel = sum(1 for s in data.studios if s.selected)
        locked = sum(1 for s in data.studios if s.selected and s.locked)
        layout.label(
            text=f"{sel} selected ({locked} locked, skipped by edits)",
            icon='RESTRICT_SELECT_OFF' if sel else 'RESTRICT_SELECT_ON',
        )

        row = layout.row(align=True)
        row.operator("stage.select_all", text="All")
        row.operator("stage.select_none", text="None")
        row.operator("stage.select_invert", text="Invert")

        if not sel:
            layout.label(
                text="Tick the checkbox on Studios to bulk-edit them.",
                icon='INFO',
            )
            return

        col = layout.column(align=True)
        col.label(text="Apply to selection:")
        col.operator("stage.bulk_set_group", icon='GROUP')
        col.operator("stage.bulk_set_parent", icon='OUTLINER_OB_GROUP_INSTANCE')
        col.operator("stage.bulk_set_color", icon='COLOR')
        col.operator("stage.bulk_set_output", icon='FILE_FOLDER')
        col.operator("stage.bulk_set_facet", icon='SETTINGS')
        col.operator("stage.bulk_set_locked", icon='LOCKED')

        col = layout.column(align=True)
        col.label(text="Tags:")
        col.operator("stage.bulk_add_tag", icon='ADD')
        col.operator("stage.bulk_remove_tag", icon='REMOVE')


# --- groups ----------------------------------------------------------------


class STAGE_PT_groups(Panel):
    """Studio Groups management — collapsible, default-closed."""
    bl_idname = "STAGE_PT_groups"
    bl_label = "Groups"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = _CATEGORY
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 4

    def draw(self, context):
        layout = self.layout
        data = context.scene.stage_data

        row = layout.row(align=True)
        row.label(text=f"{len(data.groups)} group(s)")
        row.operator("stage.add_group", icon='ADD', text="")

        if not data.groups:
            layout.label(
                text="No groups yet. Click + to create a variant axis.",
                icon='INFO',
            )
            return

        for i, group in enumerate(data.groups):
            row = layout.row(align=True)
            row.prop(group, "color", text="")
            row.prop(group, "name", text="")
            op = row.operator("stage.remove_group", icon='X', text="")
            op.index = i


_classes = (
    STAGE_PT_main,
    STAGE_PT_active_studio,
    STAGE_PT_bulk_edit,
    STAGE_PT_groups,
)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
