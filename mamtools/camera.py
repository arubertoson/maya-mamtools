"""
"""
import logging
import collections

from PySide import QtGui

from maya import cmds, mel
import maya.api.OpenMaya as api

from mampy.core import mvp
from mampy.core.dagnodes import Camera
from mampy.utils import History

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


__all__ = ['viewport_snap', 'fit_selection', 'maximize_viewport_toggle']


fit_view_history = History()
CameraAttr = collections.namedtuple('CameraAttr', 'name translate rotate centerOfInterest')


def walk_fit_camera_history(prev=False):
    """
    Walk saved camera positions.
    """
    if prev:
        fit_view_history.jump_back()
    else:
        fit_view_history.jump_forward()

    # Restore attributes
    current = fit_view_history.current_element
    camera = Camera(current.name)
    camera_trns = camera.get_transform()

    camera_trns.attr['translate'] = current.translate
    camera_trns.attr['rotate'] = current.rotate
    camera.attr['centerOfInterest'] = current.centerOfInterest


def fit_selection(fit_type='selected'):
    """
    Fit selection with history. For easy jumping between position on a mesh
    while changing selection.
    """
    mel.eval('fitPanel -{}'.format(fit_type))

    # Save camera info
    view = mvp.Viewport.active()
    camera = Camera(view.camera)
    camera_trns = camera.get_transform()

    cam_attr = CameraAttr(
        str(camera),
        camera_trns.attr['translate'],
        camera_trns.attr['rotate'],
        camera.attr['centerOfInterest'],
    )
    fit_view_history.push(cam_attr)


def viewport_snap():
    view = mvp.Viewport.active()
    camera = Camera(view.camera)
    if camera.is_ortho():
        camera.attr['orthographic'] = False
    else:
        view_vector = camera.get_view_direction()
        camera_center = camera.get_center_of_interest().z
        center_of_interest_approx = view_vector * camera_center

        # Find matching axis from world axes
        axes = [
            ('x', (1, 0, 0)),
            ('y', (0, 1, 0)),
            ('z', (0, 0, 1)),
            ('x', (-1, 0, 0)),
            ('y', (0, -1, 0)),
            ('z', (0, 0, -1)),
        ]
        dots = {}
        for axis, world_vector in axes:
            dot = view_vector * api.MVector(world_vector)
            if axis not in dots or (axis in dots and dot > dots[axis]):
                dots[axis] = dot
        axis = max(dots, key=dots.get)

        # Get necessary transforms
        cam_transform = camera.get_transform()
        cam_translate = cam_transform.get_translation()
        cam_rotate = cam_transform.get_rotate()

        view_vector = cam_translate - center_of_interest_approx
        # Modify non matching world vectors.
        for i in 'xyz'.replace(axis, ''):
            setattr(cam_translate, i, getattr(view_vector, i))

        camera.attr['orthographic'] = True
        camera.attr['orthographicWidth'] = abs(camera_center)
        cam_transform.attr['translate'] = list(cam_translate)
        cam_transform.attr['rotateX'] = int(90 * round(float(cam_rotate.x)/90))
        cam_transform.attr['rotateY'] = int(90 * round(float(cam_rotate.y)/90))


def maximize_viewport_toggle():
    """
    Maximize or minimize the viewport, same as hotbox.
    """
    pos = QtGui.QCursor.pos()
    mel.eval('panePopAt({}, {})'.format(pos.x(), pos.y()))


def reset_camera(camera=None):
    """Reset camera in to default values."""
    active = mvp.Viewport.active()
    camera = camera or active.camera

    cmds.xform(camera, os=True, rp=[0, 0, 0])
    cmds.xform(camera, os=True, sp=[0, 0, 0])
    rot = cmds.xform(camera, q=True, ws=True, ro=True)
    trn = cmds.xform(camera, q=True, ws=True, rp=True)

    cmds.xform(camera, ws=True, t=[0, 0, 0])
    cmds.xform(camera, ws=True, ro=[0, 0, 0])

    rotP = cmds.xform(camera, q=True, ws=True, rp=True)
    cmds.xform(camera, ws=True, t=[rotP[0] * -1, rotP[1] * -1, rotP[2] * -1])
    cmds.makeIdentity(camera, t=1, r=1, s=1, apply=True)

    cmds.xform(camera, ws=True, t=[trn[0], trn[1], trn[2]])
    cmds.xform(camera, os=True, ro=[rot[0], rot[1], 0])


if __name__ == '__main__':
    viewport_snap()
