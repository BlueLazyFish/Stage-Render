"""Add Studio from a starter template — operator + dropdown menu.

Two template sources, both share apply_template_to_studio():
  - Builtin TEMPLATES (stage.core.templates)  : ship with the addon
  - User templates                            : created via "Save Current
                                                as Template…", stored in
                                                addon prefs.user_templates

The studio_add_from_template operator looks up either source: if
user_template_name is set, it pulls from prefs.user_templates; otherwise
it looks up template_id in TEMPLATES. The menu populates both halves
with separator + a "Save Current…" / "Manage…" footer.
"""

import uuid

import bpy
from bpy.types import Menu, Operator
from bpy.props import IntProperty, StringProperty

from ..core.facets import capture_all
from ..core.templates import (
    TEMPLATES,
    apply_template_to_studio,
    capture_template_dict_from_scene,
    user_template_to_dict,
    write_dict_to_user_template,
)
from ..core.thumbnails import render_thumbnail
from ..handlers import set_apply_in_progress
from ..prefs import get_prefs
from ..utils.logger import get_logger


_log = get_logger()


def _find_user_template(prefs, name: str):
    """Return the UserTemplate matching display_name, or None."""
    if prefs is None:
        return None
    for ut in prefs.user_templates:
        if ut.display_name == name:
            return ut
    return None


# --- add Studio from template ----------------------------------------------


class STAGE_OT_studio_add_from_template(Operator):
    bl_idname = "stage.studio_add_from_template"
    bl_label = "Add Studio from Template"
    bl_description = "Create a new Studio pre-configured with a starter template's render settings"
    bl_options = {'REGISTER', 'UNDO'}

    # Builtin template lookup key (TEMPLATES dict key)
    template_id: StringProperty()
    # User-template lookup key (display_name in prefs.user_templates).
    # If set, takes precedence over template_id.
    user_template_name: StringProperty()

    def execute(self, context):
        # Resolve template dict from whichever source applies
        template: dict | None = None
        if self.user_template_name:
            ut = _find_user_template(get_prefs(context), self.user_template_name)
            if ut is None:
                self.report({'ERROR'}, f"Unknown user template: {self.user_template_name}")
                return {'CANCELLED'}
            template = user_template_to_dict(ut)
        else:
            template = TEMPLATES.get(self.template_id)
            if template is None:
                self.report({'ERROR'}, f"Unknown template: {self.template_id}")
                return {'CANCELLED'}

        data = context.scene.stage_data
        new_studio = data.studios.add()
        new_studio.name = template["display_name"]
        new_studio.uuid = str(uuid.uuid4())
        data.active_index = len(data.studios) - 1

        set_apply_in_progress(True)
        try:
            # Capture the user's current scene first — gets camera, world,
            # visibility, output path. Then overlay the template on top of
            # the render facet. Output path stays as captured / falls through
            # to the addon-prefs default; templates carry render settings only.
            capture_all(context.scene, new_studio)
            apply_template_to_studio(new_studio, template)

            render_thumbnail(context.scene, new_studio)

            data.last_applied_studio_uuid = new_studio.uuid
            data.dirty = False
            data.suppress_next_dirty_fire = True
        finally:
            set_apply_in_progress(False)

        self.report({'INFO'}, f"Added Studio from template: {template['display_name']}")
        _log.info("Added Studio from template: %s", template["display_name"])
        return {'FINISHED'}


# --- save current scene as a user template ---------------------------------


class STAGE_OT_save_template_from_scene(Operator):
    bl_idname = "stage.save_template_from_scene"
    bl_label = "Save Current as Template…"
    bl_description = (
        "Snapshot the current scene's render settings as a reusable "
        "template stored in addon preferences (persists across files)"
    )
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Template Name", default="My Template")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.label(text="Captures: engine, resolution, engine-specific settings")
        self.layout.prop(self, "name")
        prefs = get_prefs(context)
        if prefs is not None and any(
            ut.display_name == self.name for ut in prefs.user_templates
        ):
            row = self.layout.row()
            row.alert = True
            row.label(
                text=f"'{self.name}' already exists — will be overwritten",
                icon='ERROR',
            )

    def execute(self, context):
        prefs = get_prefs(context)
        if prefs is None:
            self.report(
                {'ERROR'},
                "Stage addon preferences unavailable — install via the extension manager",
            )
            return {'CANCELLED'}

        name = self.name.strip()
        if not name:
            self.report({'ERROR'}, "Template name cannot be empty")
            return {'CANCELLED'}

        template = capture_template_dict_from_scene(context.scene, name)

        # Overwrite an existing entry with the same name, otherwise append
        existing = _find_user_template(prefs, name)
        target = existing if existing is not None else prefs.user_templates.add()
        write_dict_to_user_template(target, template)

        self.report(
            {'INFO'},
            f"{'Updated' if existing else 'Saved'} user template: {name}",
        )
        _log.info("Saved user template: %s", name)
        return {'FINISHED'}


# --- delete a user template ------------------------------------------------


class STAGE_OT_delete_user_template(Operator):
    bl_idname = "stage.delete_user_template"
    bl_label = "Delete Template"
    bl_description = "Remove this user template from addon preferences"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()

    def execute(self, context):
        prefs = get_prefs(context)
        if prefs is None:
            self.report({'ERROR'}, "Stage addon preferences unavailable")
            return {'CANCELLED'}
        if not (0 <= self.index < len(prefs.user_templates)):
            return {'CANCELLED'}
        removed_name = prefs.user_templates[self.index].display_name
        prefs.user_templates.remove(self.index)
        self.report({'INFO'}, f"Deleted user template: {removed_name}")
        _log.info("Deleted user template: %s", removed_name)
        return {'FINISHED'}


# --- manage popup ----------------------------------------------------------


class STAGE_OT_manage_templates(Operator):
    bl_idname = "stage.manage_templates"
    bl_label = "Manage User Templates…"
    bl_description = (
        "Open Edit > Preferences > Add-ons > Stage — user templates are "
        "editable inline there with delete buttons per row"
    )
    bl_options = {'REGISTER'}

    def execute(self, context):
        # Popup dialogs invoked from menu items race with menu dismissal
        # in Blender, so popups never reliably appear. Sidestep the
        # whole issue: open the addon-prefs window and scroll to Stage.
        # The user templates list lives in StagePreferences.draw().
        try:
            bpy.ops.screen.userpref_show('INVOKE_DEFAULT')
            context.preferences.active_section = 'ADDONS'
            context.window_manager.addon_search = "Stage"
        except Exception as e:
            self.report({'WARNING'}, f"Couldn't open preferences: {e}")
            return {'CANCELLED'}
        self.report(
            {'INFO'},
            "Edit user templates inline in Edit › Preferences › Add-ons › Stage",
        )
        return {'FINISHED'}


# --- menu -------------------------------------------------------------------


class STAGE_MT_templates(Menu):
    bl_idname = "STAGE_MT_templates"
    bl_label = "Templates"

    def draw(self, context):
        layout = self.layout

        # Builtins
        for tid, template in TEMPLATES.items():
            op = layout.operator(
                STAGE_OT_studio_add_from_template.bl_idname,
                text=template["display_name"],
                icon='RENDER_STILL',
            )
            op.template_id = tid
            op.user_template_name = ""

        # User templates
        prefs = get_prefs(context)
        user_templates = list(prefs.user_templates) if prefs is not None else []
        if user_templates:
            layout.separator()
            layout.label(text="My Templates", icon='USER')
            for ut in user_templates:
                op = layout.operator(
                    STAGE_OT_studio_add_from_template.bl_idname,
                    text=ut.display_name,
                    icon='PRESET',
                )
                op.template_id = ""
                op.user_template_name = ut.display_name

        # Footer — save / manage
        layout.separator()
        layout.operator(
            STAGE_OT_save_template_from_scene.bl_idname,
            icon='ADD',
        )
        layout.operator(
            STAGE_OT_manage_templates.bl_idname,
            text="Manage Templates…",
            icon='PRESET',
        )


_classes = (
    STAGE_OT_studio_add_from_template,
    STAGE_OT_save_template_from_scene,
    STAGE_OT_delete_user_template,
    STAGE_OT_manage_templates,
    STAGE_MT_templates,
)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
