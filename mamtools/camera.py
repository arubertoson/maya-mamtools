import logging

from PySide import QtGui

import maya.cmds as cmds
import maya.mel as mel

import mampy
from mampy.nodes import Camera
from mampy.utils import mvp

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


__all__ = ['viewport_snap', 'fit_selection', 'maximize_viewport_toggle']


fit_view_history = mampy.utils.HistoryList()


def fit_selection(mode=None, add=True):
    """
    Fit selection with history. For easy jumping between position on a mesh
    while changing selection.
    """
    s = mampy.selected()
    if mode is None:
        fit_view_history.push_selection(s)
    elif mode == 'next':
        fit_view_history.jump_forward(s)
        cmds.select(fit_view_history.current_element, r=True)
    elif mode == 'back':
        fit_view_history.jump_back(s)
        cmds.select(fit_view_history.current_element, r=True)
    elif mode == 'last':
        print 'last'
        last_selected = mampy.ordered_selection()
        fit_view_history.push_selection(last_selected[-1])
        cmds.select(list(last_selected[-1]), r=True)
        cmds.viewFit(f=0.75)
        cmds.select(list(s))
        return

    cmds.viewFit(f=0.75)
    if mode is not None and add:
        cmds.select(list(s), add=True)


def viewport_snap(fit=True):
    """ZBrush style camera snapping."""
    cameras = cmds.listCameras(o=True)

    if 'bottom' not in cameras:
        top = Camera('top')

        new_camera = mampy.DagNode(cmds.duplicate('top', name='bottom').pop())
        new_camera['translateY'] = top.translateY * -1
        new_camera['rotateX'] = top.rotateX * -1

    if 'back' not in cameras:
        back = Camera('front')

        new_camera = mampy.DagNode(cmds.duplicate('front', name='back').pop())
        new_camera['translateZ'] = back.translateZ * -1
        new_camera['rotateY'] = -180

    if 'left' not in cameras:
        side = Camera('side')

        new_camera = mampy.DagNode(cmds.duplicate('side', name='left').pop())
        new_camera['translateX'] = side.translateX * -1
        new_camera['rotateY'] = side.rotateY * -1

    view = mampy.Viewport.active()
    camera = Camera(view.camera)
    if not camera.name.startswith('persp'):
        return cmds.lookThru(view.panel, 'persp')

    # create vector map
    main_vector = camera.get_view_direction()
    camera_vector = {}
    for cam in cameras:
        c = Camera(cam)
        vec = c.get_view_direction()
        camera_vector[c] = main_vector * vec

    cam = max(camera_vector, key=camera_vector.get)
    cmds.lookThru(view.panel, cam.name)
    if fit:
        cmds.viewFit(all=True)


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
    cmds.makeIdentity(apply=True, t=1, r=1, s=1)

    cmds.xform(camera, ws=True, t=[trn[0], trn[1], trn[2]])
    cmds.xform(camera, os=True, ro=[rot[0], rot[1], rot[2]])

if __name__ == '__main__':
    reset_camera()
