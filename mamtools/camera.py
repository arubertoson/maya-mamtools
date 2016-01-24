import logging

from PySide import QtGui

import maya.cmds as cmds
import maya.mel as mel

import mampy

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
        cmds.select(fit_view_history.jump_forward(s), r=True)
    elif mode == 'back':
        cmds.select(fit_view_history.jump_back(s), r=True)

    cmds.viewFit(f=0.75)
    if mode is not None and add:
        cmds.select(list(s), add=True)


def viewport_snap():
    """ZBrush style camera snapping."""
    cameras = cmds.listCameras(o=True)

    if 'bottom' not in cameras:
        top = mampy.Camera('top')

        new_camera = mampy.DagNode(cmds.duplicate('top', name='bottom').pop())
        new_camera['translateY'] = top.translateY*-1
        new_camera['rotateX'] = top.rotateX*-1

    if 'back' not in cameras:
        back = mampy.Camera('front')

        new_camera = mampy.DagNode(cmds.duplicate('front', name='back').pop())
        new_camera['translateZ'] = back.translateZ*-1
        new_camera['rotateY'] = -180

    if 'left' not in cameras:
        side = mampy.Camera('side')

        new_camera = mampy.DagNode(cmds.duplicate('side', name='left').pop())
        new_camera['translateX'] = side.translateX*-1
        new_camera['rotateY'] = side.rotateY*-1

    view = mampy.Viewport.active()
    camera = mampy.Camera(view.camera)
    if not camera.name.startswith('persp'):
        return cmds.lookThru(view.panel, 'persp')

    # create vector map
    main_vector = camera.get_view_direction()
    camera_vector = {}
    for cam in cameras:
        c = mampy.Camera(cam)
        vec = c.get_view_direction()
        camera_vector[c] = main_vector * vec

    cam = max(camera_vector, key=camera_vector.get)
    cmds.lookThru(view.panel, cam.name)


def maximize_viewport_toggle():
    """
    Maximize or minimize the viewport, same as hotbox.
    """
    pos = QtGui.QCursor.pos()
    mel.eval('panePopAt({}, {})'.format(pos.x(), pos.y()))


if __name__ == '__main__':
    viewport_snap()
    # cmds.select('persp')

    # cmds.xform('persp', os=True, rp=[0,0,0])
    # cmds.xform('persp', os=True, sp=[0,0,0])
    # rot = cmds.xform('persp', q=True, ws=True, ro=True)
    # trn = cmds.xform('persp', q=True, ws=True, rp=True)

    # cmds.xform('persp', ws=True, t=[0,0,0])
    # cmds.xform('persp', ws=True, ro=[0,0,0])

    # rotP = cmds.xform('persp', q=True, ws=True, rp=True)
    # cmds.xform('persp', ws=True, t=[rotP[0]*-1, rotP[1]*-1, rotP[2]*-1])
    # cmds.makeIdentity( apply=True, t=1, r=1, s=1 )

    # cmds.xform('persp', ws=True, t=[trn[0], trn[1], trn[2]])
    # cmds.xform('persp', os=True, ro=[rot[0], rot[1], rot[2]])
