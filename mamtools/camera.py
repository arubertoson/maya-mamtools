import logging
import maya.cmds as cmds
import mampy

logger = logging.getLogger(__name__)


__all__ = ['viewport_snap', 'fit']


class FitSelection(object):
    """Saves previous selection to fit selection on.

    .. todo::
        - Switch from selection to position so selections wont change.
    """

    instance = None

    def __init__(self):
        self._sels = []

    def prev(self):
        if not len(self._sels) >= 2:
            return logger.warn('Fit list is empty')
        fit_sel = self._sels.pop(-2)
        cmds.select(fit_sel, r=True)
        self.fit()

    def next(self):
        fit_sel = cmds.ls(sl=True)
        if len(self._sels) > 10:
            self._sels.pop(0)
        self._sels.append(fit_sel)

        print self._sels
        self.fit()

    def fit(self):
        cmds.viewFit(f=0.75)


def viewport_snap():
    """ZBrush style camera snapping."""
    cameras = cmds.listCameras(o=True)

    if 'bottom' not in cameras:
        top = mampy.Camera('top')

        new_camera = mampy.DagNode(cmds.duplicate('top', name='bottom').pop())
        new_camera.translateY.set(top.translateY.get()*-1)
        new_camera.rotateX.set(top.rotateX.get()*-1)

    if 'back' not in cameras:
        back = mampy.Camera('front')

        new_camera = mampy.DagNode(cmds.duplicate('front', name='back').pop())
        new_camera.translateZ.set(back.translateZ.get()*-1)
        new_camera.rotateY.set(-180)

    if 'left' not in cameras:
        side = mampy.Camera('side')

        new_camera = mampy.DagNode(cmds.duplicate('side', name='left').pop())
        new_camera.translateX.set(side.translateX.get()*-1)
        new_camera.rotateY.set(side.rotateY.get()*-1)

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


def fit(backwards=False):
    if FitSelection.instance is None:
        FitSelection.instance = FitSelection()

    if backwards:
        FitSelection.instance.prev()
    else:
        FitSelection.instance.next()


if __name__ == '__main__':
    fit(True)
