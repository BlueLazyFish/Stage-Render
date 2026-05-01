"""FacetCamera — captured Camera facet data per Studio.

Stores the active camera Object name (we resolve via bpy.data.objects on
apply rather than holding a PointerProperty, so that storage survives
camera renames/relinks gracefully), plus the Object transform and the
Camera data lens / sensor / DoF settings.

See ADDON_PLAN.md §3 MVP and §5 data model.
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
    StringProperty,
)


class FacetCamera(PropertyGroup):
    captured: BoolProperty(
        name="Captured",
        description="True once capture() has populated this facet",
        default=False,
    )

    # Active camera Object name. Empty = scene had no camera at capture time.
    camera_name: StringProperty(default="")

    # --- Object transform ---
    location: FloatVectorProperty(size=3, default=(0.0, 0.0, 0.0))
    rotation_euler: FloatVectorProperty(
        size=3, subtype='EULER', default=(0.0, 0.0, 0.0)
    )
    rotation_mode: StringProperty(default='XYZ')
    scale: FloatVectorProperty(size=3, default=(1.0, 1.0, 1.0))

    # --- Camera data: type, lens, sensor ---
    type: StringProperty(default='PERSP')   # PERSP / ORTHO / PANO
    lens: FloatProperty(default=50.0)
    clip_start: FloatProperty(default=0.1)
    clip_end: FloatProperty(default=1000.0)
    shift_x: FloatProperty(default=0.0)
    shift_y: FloatProperty(default=0.0)
    sensor_width: FloatProperty(default=36.0)
    sensor_height: FloatProperty(default=24.0)
    sensor_fit: StringProperty(default='AUTO')  # AUTO / HORIZONTAL / VERTICAL
    ortho_scale: FloatProperty(default=6.0)

    # --- Depth of Field ---
    dof_use: BoolProperty(default=False)
    dof_aperture_fstop: FloatProperty(default=2.8)
    dof_focus_distance: FloatProperty(default=10.0)
    dof_focus_object_name: StringProperty(default="")


def register() -> None:
    bpy.utils.register_class(FacetCamera)


def unregister() -> None:
    bpy.utils.unregister_class(FacetCamera)
