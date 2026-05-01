"""Camera facet — captures active camera Object + transform + Camera data + DoF.

Each Studio remembers a specific camera by name and applying restores that
camera's transform plus its lens/sensor/DoF settings. Matches KeyShot's
Studio model (camera-as-bundle).

If two Studios reference the same camera Object, applying either one will
mutate that camera's settings — that's intentional and matches the
KeyShot/Renderset pattern. Users wanting independent lens settings per
Studio without shared camera Objects should create distinct cameras.
"""

from __future__ import annotations

import bpy

from ...utils.logger import get_logger
from . import register_facet


_log = get_logger()


class CameraFacet:
    facet_id = "camera"

    def is_enabled(self, studio) -> bool:
        return studio.facet_camera_enabled

    def capture(self, scene, studio) -> None:
        f = studio.facet_camera
        f.captured = True

        cam_obj = scene.camera
        if cam_obj is None or cam_obj.data is None:
            f.camera_name = ""
            return  # captured "no camera"

        f.camera_name = cam_obj.name

        # Object transform
        f.location = cam_obj.location
        f.rotation_euler = cam_obj.rotation_euler
        f.rotation_mode = cam_obj.rotation_mode
        f.scale = cam_obj.scale

        # Camera data: type / lens / sensor
        cam = cam_obj.data
        f.type = cam.type
        f.lens = cam.lens
        f.clip_start = cam.clip_start
        f.clip_end = cam.clip_end
        f.shift_x = cam.shift_x
        f.shift_y = cam.shift_y
        f.sensor_width = cam.sensor_width
        f.sensor_height = cam.sensor_height
        f.sensor_fit = cam.sensor_fit
        f.ortho_scale = cam.ortho_scale

        # DoF
        dof = cam.dof
        f.dof_use = dof.use_dof
        f.dof_aperture_fstop = dof.aperture_fstop
        f.dof_focus_distance = dof.focus_distance
        f.dof_focus_object_name = (
            dof.focus_object.name if dof.focus_object else ""
        )

    def apply(self, scene, studio) -> None:
        f = studio.facet_camera
        if not f.captured:
            return

        if not f.camera_name:
            scene.camera = None
            return

        cam_obj = bpy.data.objects.get(f.camera_name)
        if cam_obj is None:
            _log.warning(
                "Camera Object %r not found; leaving scene.camera unchanged",
                f.camera_name,
            )
            return
        if cam_obj.type != 'CAMERA':
            _log.warning(
                "Object %r is not a camera (type=%s); skipping",
                f.camera_name, cam_obj.type,
            )
            return

        scene.camera = cam_obj

        # Object transform — set rotation_mode FIRST so the euler is interpreted
        # in the correct rotation order.
        cam_obj.rotation_mode = f.rotation_mode
        cam_obj.location = f.location
        cam_obj.rotation_euler = f.rotation_euler
        cam_obj.scale = f.scale

        # Camera data
        cam = cam_obj.data
        cam.type = f.type
        cam.lens = f.lens
        cam.clip_start = f.clip_start
        cam.clip_end = f.clip_end
        cam.shift_x = f.shift_x
        cam.shift_y = f.shift_y
        cam.sensor_width = f.sensor_width
        cam.sensor_height = f.sensor_height
        cam.sensor_fit = f.sensor_fit
        cam.ortho_scale = f.ortho_scale

        # DoF
        dof = cam.dof
        dof.use_dof = f.dof_use
        dof.aperture_fstop = f.dof_aperture_fstop
        dof.focus_distance = f.dof_focus_distance
        if f.dof_focus_object_name:
            dof.focus_object = bpy.data.objects.get(f.dof_focus_object_name)
            # If that lookup returns None, dof.focus_object is set to None
            # which is also a valid state (no focus target).
        else:
            dof.focus_object = None


register_facet(CameraFacet())
