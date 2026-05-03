"""Add Studio from a starter template — operator + dropdown menu."""

import uuid

import bpy
from bpy.types import Menu, Operator
from bpy.props import StringProperty

from ..core.facets import capture_all
from ..core.templates import TEMPLATES, apply_template_to_studio
from ..core.thumbnails import render_thumbnail
from ..handlers import set_apply_in_progress
from ..utils.logger import get_logger


_log = get_logger()


class STAGE_OT_studio_add_from_template(Operator):
    bl_idname = "stage.studio_add_from_template"
    bl_label = "Add Studio from Template"
    bl_description = "Create a new Studio pre-configured with a starter template's render settings"
    bl_options = {'REGISTER', 'UNDO'}

    template_id: StringProperty()

    def execute(self, context):
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


class STAGE_MT_templates(Menu):
    bl_idname = "STAGE_MT_templates"
    bl_label = "Starter Templates"

    def draw(self, context):
        for tid, template in TEMPLATES.items():
            op = self.layout.operator(
                STAGE_OT_studio_add_from_template.bl_idname,
                text=template["display_name"],
                icon='RENDER_STILL',
            )
            op.template_id = tid


_classes = (STAGE_OT_studio_add_from_template, STAGE_MT_templates)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
