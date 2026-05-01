"""StoredProp — a single captured RNA path inside a Studio's custom_paths.

Used for the right-click → Store in Studio feature (v1.0).
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import StringProperty, EnumProperty


class StoredProp(PropertyGroup):
    data_path: StringProperty(
        name="Data Path",
        description="Full RNA path (e.g. bpy.data.objects['Cube'].modifiers['Subsurf'].levels)",
    )

    value_repr: StringProperty(
        name="Value",
        description="Stored value (repr-encoded for round-trip safety)",
    )

    value_type: EnumProperty(
        name="Type",
        items=[
            ('FLOAT', "Float", ""),
            ('INT', "Int", ""),
            ('BOOL', "Bool", ""),
            ('STRING', "String", ""),
            ('ENUM', "Enum", ""),
            ('VECTOR', "Vector", ""),
            ('COLOR', "Color", ""),
            ('REFERENCE', "Reference", "Pointer to a datablock"),
        ],
        default='STRING',
    )


def register() -> None:
    bpy.utils.register_class(StoredProp)


def unregister() -> None:
    bpy.utils.unregister_class(StoredProp)
