"""PostRenderAction — one entry in a Studio's post-render action chain.

Per ADDON_PLAN.md §3 v1.0, post-render actions execute in declared order
after each render. Five primitives ship in v1.0:

    COPY_FILE       — copy the render output to `target` path
    MOVE_FILE       — move the render output to `target` path
    DELETE_FOLDER   — remove `target` folder (use with care)
    PLAY_SOUND      — play `target` sound file (or system beep if "default")
    SLACK_WEBHOOK   — POST to `target` URL with `message` body

`target` is a path-template string (supports {studio}, {frame}, etc.) or
a webhook URL depending on type. `message` is only used for SLACK_WEBHOOK
and supports the same template tokens.
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import EnumProperty, StringProperty


ACTION_TYPES = (
    ('COPY_FILE', "Copy File", "Copy the render output to a destination path"),
    ('MOVE_FILE', "Move File", "Move the render output to a destination path"),
    ('DELETE_FOLDER', "Delete Folder", "Remove an output folder"),
    ('PLAY_SOUND', "Play Sound", "Play a sound file (system beep if empty)"),
    ('SLACK_WEBHOOK', "Slack Webhook", "POST to a Slack incoming webhook URL"),
)


class PostRenderAction(PropertyGroup):
    action_type: EnumProperty(
        name="Type",
        items=ACTION_TYPES,
        default='COPY_FILE',
    )

    target: StringProperty(
        name="Target",
        description=(
            "Destination path (for COPY/MOVE/DELETE), sound file path "
            "(for PLAY_SOUND), or webhook URL (for SLACK_WEBHOOK). "
            "Path templates support {studio}, {frame}, {date_time}, etc."
        ),
        default="",
        subtype='FILE_PATH',
    )

    message: StringProperty(
        name="Message",
        description=(
            "Message body for SLACK_WEBHOOK actions. Supports {studio}, "
            "{output_path}, {frame}, {date_time} template tokens. "
            "Defaults to a sensible 'Render complete' message if empty."
        ),
        default="",
    )


def register() -> None:
    bpy.utils.register_class(PostRenderAction)


def unregister() -> None:
    bpy.utils.unregister_class(PostRenderAction)
